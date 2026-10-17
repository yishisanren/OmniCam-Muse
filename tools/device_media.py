"""Capture a named camera test and validate the stable final file, not its placeholder."""
import hashlib
import os
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time
from PIL import Image
from device_actions import ADB, snapshot, camera_snapshot, tap_node, exclusive_ui, DISMISSED_POPUPS
from verify_capture import picture_stats
from verify_video import verify_video

OUT = Path(os.environ.get('MUSE_EVIDENCE_DIR', Path(__file__).resolve().parent.parent / 'evidence/device-20261017/acceptance'))
Image.MAX_IMAGE_PIXELS = None  # Trusted 200MP media created by this explicit device test.


def root(command):
    return subprocess.check_output(ADB + ['exec-out', shlex.join(['su', '-c', command])], text=True)


def recent(kind, start):
    uri = 'content://media/external/' + ('video' if kind == 'video' else 'images') + '/media'
    projection = '_id:_display_name:_data:width:height:date_added'
    if kind == 'video':
        projection += ':duration'
    cmd = ['content', 'query', '--uri', uri, '--projection', projection, '--where', f'date_added>={start}']
    result = subprocess.check_output(ADB + ['shell', shlex.join(cmd)], text=True)
    return [dict(pair.split('=', 1) for pair in line.split(' ', 2)[2].split(', '))
            for line in result.splitlines() if line.startswith('Row: ')]


def digest(remote):
    return root('sha256sum ' + shlex.quote(remote)).split()[0]


@exclusive_ui
def main():
    name, mode, shutter_id = sys.argv[1:4]
    assert name.replace('-', '').replace('_', '').isalnum()
    duration = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    assert duration == 0 or 20 <= duration <= 45
    kind = 'video' if duration else 'photo'
    expected_style = sys.argv[5] if len(sys.argv) > 5 else None
    OUT.mkdir(parents=True, exist_ok=True)
    module_apk = subprocess.check_output(ADB + ['shell', 'pm', 'path', 'local.jiege.camera'], text=True).strip().removeprefix('package:')
    module_sha = digest(module_apk)
    tree = camera_snapshot()
    nodes = list(tree.iter('node'))
    headline = next((n.get('content-desc', '') for n in nodes if n.get('resource-id') == 'com.oplus.camera:id/headline_view'), '')
    if not headline:
        headline = next((n.get('content-desc', '') for n in nodes if n.get('resource-id') == 'com.oplus.camera:id/preview_talkback'), '')
    assert mode in headline, (mode, headline)
    style = next((n.get('text', '') for n in nodes if n.get('resource-id') == 'com.oplus.camera:id/master_effect_menu_soft_light_value_text'), '')
    if not style:
        style = next((n.get('text', '') for n in nodes if n.get('resource-id') == 'com.oplus.camera:id/effect_style_filter_hint'), '')
    if expected_style:
        assert style == expected_style, ('Expected style', expected_style, style)
    assert not any(n.get('resource-id') == 'com.oplus.camera:id/top_expand_touch_mask' for n in nodes)
    shutters = [n for n in nodes if n.get('resource-id') == shutter_id and n.get('enabled') == 'true']
    assert len(shutters) == 1, 'Expected exactly one enabled shutter control'
    start = int(subprocess.check_output(ADB + ['shell', 'date', '+%s'], text=True))
    before = {r['_data'] for r in recent(kind, start)}
    (OUT / (name + '-before.png')).write_bytes(subprocess.check_output(ADB + ['exec-out', 'screencap', '-p']))
    record_seconds = int(os.environ.get('MUSE_UI_RECORD_SECONDS', '0'))
    assert record_seconds in [0, 6, 8]
    recorder = None
    ui_remote = '/data/local/tmp/omnicam_muse_probe/' + name + '-ui.mp4'
    if record_seconds:
        recorder = subprocess.Popen(ADB + ['shell', 'screenrecord', '--size', '608x1320',
            '--bit-rate', '4000000', '--time-limit', str(record_seconds), ui_remote],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(.6)
    tap_node('com.oplus.camera', shutters[0])
    if duration:
        time.sleep(5)
        (OUT / (name + '-recording.png')).write_bytes(subprocess.check_output(ADB + ['exec-out', 'screencap', '-p']))
        time.sleep(duration - 5)
        current = snapshot()
        stop = next(n for n in current.iter('node') if n.get('resource-id') == shutter_id)
        tap_node('com.oplus.camera', stop)
    rows = []
    for _ in range(20):
        time.sleep(2)
        rows = [r for r in recent(kind, start) if r['_data'] not in before]
        if rows:
            break
    assert len(rows) == 1, rows
    row = rows[0]
    remote = row['_data']
    if kind == 'photo':
        # ColorOS can leave a valid, stable placeholder for minutes. Opening the
        # latest photo asks the capture service to finish its deferred main job.
        tree = camera_snapshot()
        thumbnail = next(n for n in tree.iter('node') if n.get('resource-id') == 'com.oplus.camera:id/thumbnail')
        tap_node('com.oplus.camera', thumbnail)
        time.sleep(15)
    # Wait for 12 seconds of identical bytes; camera processing can replace the same JPEG path.
    previous, stable = None, 0
    for _ in range(30):
        current = digest(remote)
        stable = stable + 1 if current == previous else 0
        if stable >= 3:
            break
        previous = current
        time.sleep(4)
    assert stable >= 3, 'Final media never stabilised'
    final = OUT / (name + Path(remote).suffix.lower())
    subprocess.run(ADB + ['pull', remote, str(final)], check=True, capture_output=True)
    actual = hashlib.sha256(final.read_bytes()).hexdigest()
    assert actual == digest(remote) == current, 'File changed during transfer'
    (OUT / (name + '-transfer.json')).write_text(json.dumps({
        'case': name, 'kind': kind, 'mode': headline, 'style': style,
        'media': row, 'sha256': actual, 'module_apk_sha256': module_sha,
        'stable_before_and_after_pull': True,
    }, ensure_ascii=False, indent=2) + '\n')
    details = {}
    if kind == 'photo':
        with Image.open(final) as image:
            details['size'] = list(image.size)
            image.load()
        details['picture_stats'] = picture_stats(final)
    else:
        details = verify_video(final, expected_fps=int(os.environ.get('MUSE_EXPECT_FPS', '60')),
                               monochrome=os.environ.get('MUSE_EXPECT_MONOCHROME', '0') == '1')
    assert digest(module_apk) == module_sha, 'Module APK changed during capture'
    if recorder is not None:
        assert recorder.wait(timeout=record_seconds + 5) == 0, 'Camera UI recording failed'
        subprocess.run(ADB + ['pull', ui_remote, str(OUT / (name + '-ui.mp4'))], check=True, capture_output=True)
    native = {}
    for feature, leaf in [('natural', 'status'), ('mastercolor', 'frame-status'),
                          ('mastercolor', 'capture-status'), ('mastercolor', 'applied-status'), ('mastercolor', 'look')]:
        path = '/data/user/0/com.oplus.camera/files/jiege/' + feature + '/' + leaf
        native[feature + '/' + leaf] = root('cat ' + shlex.quote(path) + ' 2>/dev/null').strip()
    for leaf in ['soft-light-status', 'master-grain-status']:
        native[leaf] = root('cat /data/user/0/com.oplus.camera/files/jiege/' + leaf + ' 2>/dev/null').strip()
    report = {'case': name, 'kind': kind, 'mode': headline, 'style': style, 'media': row, 'sha256': actual,
              'deferred_view_requested': kind == 'photo',
              'native': native,
              'dismissed_automatic_popups': DISMISSED_POPUPS,
              'module_apk_sha256': module_sha,
              'bytes': final.stat().st_size, 'stable_before_and_after_pull': True, 'full_decode': True, **details}
    (OUT / (name + '-media.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ['streams', 'format', 'media', 'native']}, ensure_ascii=False))
    assert not details.get('picture_stats', {}).get('zero_plane_green', False), 'GR zero-plane green output'


if __name__ == '__main__':
    main()
