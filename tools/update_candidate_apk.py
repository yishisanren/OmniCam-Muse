"""Serialize a signed candidate APK update, preserving the existing device baseline."""
import fcntl
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import zipfile
from install_x9spro import ADB, ROOT, OUT, root
from device_actions import exclusive_ui


@exclusive_ui
def main():
    label = sys.argv[1]
    assert label.replace('-', '').isalnum()
    apk = Path('/private/tmp/omnicam-muse-x9spro-build/outputs/apk/release/app-release.apk')
    with zipfile.ZipFile(apk) as archive:
        profile = archive.read('assets/device_profile.json')
    assert profile == (ROOT / 'module/profile.json').read_bytes()
    expected_profile = hashlib.sha256(profile).hexdigest()
    assert root('sha256sum /data/adb/modules/omnicam_muse_x9spro/profile.json').decode().split()[0] == expected_profile
    digest = hashlib.sha256(apk.read_bytes()).hexdigest()
    remote = '/data/local/tmp/omnicam_muse_probe/candidate.apk'
    subprocess.run(ADB + ['push', str(apk), remote], check=True, capture_output=True)
    assert root('sha256sum ' + remote).decode().split()[0] == digest
    result = root('pm install -r ' + remote + ' 2>/dev/null').decode()
    assert 'Success' in result, result
    actual = subprocess.check_output(ADB + ['shell', 'pm', 'path', 'local.jiege.camera'], text=True).strip().removeprefix('package:')
    assert root('sha256sum ' + shlex.quote(actual)).decode().split()[0] == digest
    root('am force-stop com.oplus.camera')
    subprocess.run(ADB + ['shell', 'am', 'start', '-a', 'android.media.action.STILL_IMAGE_CAMERA'], check=True, capture_output=True)
    report = {'apk_sha256': digest, 'profile_sha256': expected_profile, 'result': result.strip()}
    (ROOT / 'evidence/device-20261017/acceptance' / (label + '-apk.json')).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    with (OUT / '.installer.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        main()
