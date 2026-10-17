"""Collect private, hash-checked acceptance evidence without publishing device media."""
import hashlib
import json
from pathlib import Path
import shlex
import tarfile
from device_media import recent, digest, root
from install_x9spro import ROOT


def main():
    out = ROOT / 'evidence/device-20261017/acceptance'
    sizes = {'normal-photo': [4416, 5888], 'gr-bw-final': [3072, 4080],
             'gr-positive-final': [3072, 4080], 'pop-repro': [3408, 5488],
             'highpixel-50mp': [6144, 8160], 'highpixel-200mp-standard': [12288, 16320],
             'highpixel-200mp-clear': [12288, 16320]}
    photos = []
    for case, size in sizes.items():
        data = json.loads((out / (case + '-media.json')).read_text())
        assert data['size'] == size and data['full_decode'] and data['stable_before_and_after_pull']
        assert not data.get('picture_stats', {}).get('zero_plane_green', False)
        local = out / (case + Path(data['media']['_data']).suffix.lower())
        assert hashlib.sha256(local.read_bytes()).hexdigest() == data['sha256']
        photos.append({k: data.get(k) for k in ['case', 'size', 'sha256', 'style', 'full_decode']})
    video = out / 'video-4k60.mp4'
    video_sha = hashlib.sha256(video.read_bytes()).hexdigest()
    verification = json.loads(video.with_suffix('.verification.json').read_text())
    assert verification['full_decode']
    stream = next(s for s in verification['streams'] if s['codec_type'] == 'video')
    rows = [r for r in recent('video', int(video.stat().st_mtime) - 1800)
            if r['width'] == '3840' and r['height'] == '2160']
    matched = [r for r in rows if digest(r['_data']) == video_sha]
    assert len(matched) == 1, 'Final video is not identical on the phone'
    video_report = {'case': 'video-4k60', 'media': matched[0], 'sha256': video_sha,
                    'stable_before_and_after_pull': True,
                    'module_apk_sha256': json.loads((out / 'gr-v2-final-apk.json').read_text())['apk_sha256'],
                    **verification}
    (out / 'video-4k60-media.json').write_text(json.dumps(video_report, ensure_ascii=False, indent=2) + '\n')
    with tarfile.open(out / 'preferences-before-extra.tar') as backup:
        prefs = next(m for m in backup.getmembers() if m.name.endswith('/module_settings.xml'))
        expected = hashlib.sha256(backup.extractfile(prefs).read()).hexdigest()
        assert digest('/' + prefs.name) == expected, 'User module settings changed'
    logpath = root('ls -t /data/adb/lspd/log/modules* | head -1').strip()
    (out / 'final-modules.log').write_text(root('cat ' + shlex.quote(logpath)))
    for name in ['frame-status', 'capture-status']:
        (out / ('master-' + name + '.txt')).write_text(root('cat /data/user/0/com.oplus.camera/files/jiege/mastercolor/' + name))
    natural = root('cat /data/user/0/com.oplus.camera/files/jiege/natural/status')
    (out / 'natural-status.txt').write_text(natural)
    assert 'tuning json: edited copy' in natural
    installed = json.loads((out / 'final-installed.json').read_text())
    health = json.loads((out / 'final-health.json').read_text())
    restored = json.loads((out / 'settings-restored.json').read_text())
    assert not installed['mismatches'] and installed['installed_and_embedded_apk_match']
    assert health['health'] == 'normal' and restored['photo_flash'] == 'auto'
    assert restored['highpixel_filter'] == '标准' and not restored['highpixel_200mp']
    summary = {'core_photos': photos, 'final_installation': installed,
               'final_injection': health, 'restored_settings': restored,
               'video': {'size': [stream['width'], stream['height']], 'duration': stream['duration'],
                         'frames': stream['nb_frames'], 'avg_frame_rate': stream['avg_frame_rate'],
                         'sha256': video_sha, 'full_decode': True, 'source_timing': verification['source_timing']},
               'module_settings_preserved': True,
               'limits': ['Master colour preview works; tested capture retains stock dynamic gamma/LMT',
                          'Further softening eps unavailable; original strength preserved',
                          'Physical soft light, high-spec video filters, extra grain and Pro Video ISZ not accepted']}
    (out / 'acceptance-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'photos_passed': len(photos), 'video_4k60_passed': True,
                      'module_settings_preserved': True, 'report': str(out / 'acceptance-summary.json')}))


if __name__ == '__main__':
    main()
