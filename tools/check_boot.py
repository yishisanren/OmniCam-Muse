"""Read back boot activation, exact mounted bytes and the camera's own namespace."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
ADB = [shutil.which('adb') or 'adb', '-s', os.environ['MUSE_DEVICE_SERIAL']]
OUT = ROOT / 'evidence/device-20261017/acceptance'
MOD = '/data/adb/modules/omnicam_muse_x9spro'


def root(command):
    return subprocess.check_output(ADB + ['exec-out', shlex.join(['su', '-c', command])], text=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    profile = json.loads((ROOT / 'module/profile.json').read_text())
    expected = hashlib.sha256((ROOT / 'module/profile.json').read_bytes()).hexdigest()
    marker = root('cat /data/user/0/com.oplus.camera/files/jiege/muse_profile.sha256').strip()
    assert marker == expected, 'Resource staging is not complete'
    libs = root('cmd package list libraries')
    assert 'library:com.oplus.camera.unit.sdk\n' in libs, 'Original camera SDK not registered'
    pid = root('pidof com.oplus.camera').strip()
    namespace = '/proc/' + pid + '/root' if pid else ''
    if '--camera' in sys.argv:
        assert pid, 'Camera is not running'
    lines = root('sha256sum ' + ' '.join(shlex.quote(namespace + p) for p in profile['mounted_files'])).splitlines()
    actual = {line.split(None, 1)[1].strip().removeprefix(namespace): line.split()[0] for line in lines}
    assert actual == profile['mounted_files'], 'Mounted resources differ'
    mounts = root('cat /proc/' + (pid or '1') + '/mountinfo')
    overlays = {}
    for line in mounts.splitlines():
        fields = line.split()
        if fields[4] in ['/odm/lib64', '/odm/etc/camera/config', '/odm/etc/camera/meishe_lut', '/odm/etc/camera/basictone']:
            assert 'ro' in fields[5].split(',') and ' - overlay ' in line, line
            overlays[fields[4]] = line
    assert len(overlays) == 4
    assert root('if [ ! -d /data/adb/modules/omnicam_aura_x9spro ] || [ -f /data/adb/modules/omnicam_aura_x9spro/disable ]; then test ! -e ' + MOD + '/disable && echo yes; fi').strip() == 'yes'
    assert 'Muse resource staging complete' in root('cat ' + MOD + '/stage.log')
    name = 'camera-namespace' if pid else 'boot'
    report = {'profile_sha256': expected, 'marker_matches': True, 'resource_hashes_match': len(actual),
              'camera_sdk_registered': True, 'camera_pid': pid or None, 'read_only_overlays': list(overlays),
              'aura_disabled': True, 'muse_enabled': True}
    (OUT / (name + '.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    (OUT / (name + '-mountinfo.txt')).write_text(mounts)
    for file in ['bind.log', 'libraries.log', 'stage.log']:
        (OUT / file).write_text(root('cat ' + MOD + '/' + file))
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
