"""Deploy only reviewed boot scripts, keeping the installed APK and resource pair intact."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
ADB = [shutil.which('adb') or 'adb', '-s', os.environ['MUSE_DEVICE_SERIAL']]
OUT = ROOT / 'evidence/device-20261017/acceptance'
MOD = '/data/adb/modules/omnicam_muse_x9spro'
TMP = '/data/local/tmp/omnicam_muse_probe'


def root(command):
    return subprocess.check_output(ADB + ['exec-out', shlex.join(['su', '-c', command])])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assert root('getprop ro.build.display.id').decode().strip() == 'PME110_17.0.0.103(CN01)'
    assert root('sha256sum ' + MOD + '/profile.json').decode().split()[0] == hashlib.sha256((ROOT / 'module/profile.json').read_bytes()).hexdigest()
    backup = OUT / 'before-sdk-fix.tar'
    assert not backup.exists(), 'Do not overwrite the recovery baseline'
    backup.write_bytes(root('tar -cf - -C ' + MOD + ' post-mount.sh service.sh profile.json module.prop'))
    script = ROOT / 'module/camera-sdk.sh'
    subprocess.run(ADB + ['push', str(script), TMP + '/camera-sdk.sh'], check=True, capture_output=True)
    check = '. ' + TMP + '/camera-sdk.sh; muse_restore_camera_sdk_registration; muse_sdk_ready'
    test = root('/data/adb/ksu/bin/busybox unshare -m --propagation private sh -c ' + shlex.quote(check)).decode()
    assert 'restored read-only' in test
    rows = {}
    for name in ['camera-sdk.sh', 'post-mount.sh', 'service.sh']:
        file = ROOT / 'module' / name
        remote = TMP + '/' + name
        subprocess.run(ADB + ['push', str(file), remote], check=True, capture_output=True)
        expected = hashlib.sha256(file.read_bytes()).hexdigest()
        assert root('sha256sum ' + remote).decode().split()[0] == expected
        root('cp ' + remote + ' ' + MOD + '/' + name + '.new && chmod 0755 ' + MOD + '/' + name + '.new && chown 0:0 ' + MOD + '/' + name + '.new && mv ' + MOD + '/' + name + '.new ' + MOD + '/' + name)
        assert root('sha256sum ' + MOD + '/' + name).decode().split()[0] == expected
        rows[name] = expected
    root('if [ -f /data/user/0/com.oplus.camera/files/jiege/muse_profile.sha256.diagnostic ]; then mv /data/user/0/com.oplus.camera/files/jiege/muse_profile.sha256.diagnostic /data/user/0/com.oplus.camera/files/jiege/muse_profile.sha256; fi')
    (OUT / 'sdk-fix-deployed.json').write_text(json.dumps({'scripts': rows, 'isolated_restore': test, 'reboot_required': True}, indent=2) + '\n')
    print('Three boot scripts deployed and read back; isolated stock SDK restoration passed. Reboot required.')


if __name__ == '__main__':
    main()
