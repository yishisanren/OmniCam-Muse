"""Upgrade the paired APK/KSU package after a fresh backup; preserve app data and scopes."""
import hashlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import tarfile
from install_x9spro import ROOT, ADB, root, MUSE
from device_actions import exclusive_ui


def remote_sha(path):
    return root('sha256sum ' + shlex.quote(path)).decode().split()[0]


def other_flags():
    command = 'for d in /data/adb/modules/*; do [ -d "$d" ] || continue; '
    command += 'printf "%s " "${d##*/}"; if [ -e "$d/disable" ]; then echo disabled; else echo enabled; fi; done'
    lines = root(command).decode().splitlines()
    return {name: state for name, state in (line.split() for line in lines) if name != MUSE}


@exclusive_ui
def main():
    profile_bytes = (ROOT / 'module/profile.json').read_bytes()
    profile = json.loads(profile_bytes)
    version = profile['version']
    assert version == '4.0.0-x9spro.2'
    out = ROOT / 'evidence/device-20261017/upgrade-40002'
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'upgraded.json').exists():
        raise RuntimeError('Upgrade already staged; verify/reboot it without replacing the backup')
    for key, prop in [('model', 'ro.product.model'), ('firmware', 'ro.build.display.id')]:
        assert subprocess.check_output(ADB + ['shell', 'getprop', prop], text=True).strip() == profile[key]
    assert remote_sha('/product/app/OplusCamera/OplusCamera.apk') == profile['apk_sha256']
    assert remote_sha('/odm/lib64/libAlgoInterface.so') == profile['algo_sha256']
    assert subprocess.check_output(ADB + ['shell', 'getprop', 'sys.user.0.ce_available'], text=True).strip() == 'true'
    manifest = json.loads((ROOT / 'evidence/package-verification.json').read_text())
    apk_name, zip_name = 'omnicam-muse-' + version + '.apk', 'OmniCam-Muse-' + version + '-KSU.zip'
    for name in [apk_name, zip_name]:
        assert hashlib.sha256((ROOT / 'dist' / name).read_bytes()).hexdigest() == manifest[name]['sha256']
    previous_apk = subprocess.check_output(ADB + ['shell', 'pm', 'path', 'local.jiege.camera'], text=True).strip().removeprefix('package:')
    before = {'apk_sha256': remote_sha(previous_apk), 'other_module_flags': other_flags(),
              'app_uid': root('stat -c %u /data/user/0/local.jiege.camera').decode().strip()}
    active = '/data/adb/modules/' + MUSE
    if not (out / 'before.json').exists():
        root('am force-stop com.oplus.camera; am force-stop local.jiege.camera')
        old_apk = '/data/local/tmp/omnicam_muse_probe/rollback-' + before['apk_sha256'] + '.apk'
        root('cp -p ' + shlex.quote(previous_apk) + ' ' + shlex.quote(old_apk) + ' && chmod 0644 ' + shlex.quote(old_apk))
        assert remote_sha(old_apk) == before['apk_sha256']
        subprocess.run(ADB + ['pull', old_apk, str(out / 'previous.apk')], check=True, capture_output=True)
        assert hashlib.sha256((out / 'previous.apk').read_bytes()).hexdigest() == before['apk_sha256']
        backup = root('/data/adb/ksu/bin/busybox tar --exclude=' + MUSE + '/merged -czf - -C /data/adb/modules ' + MUSE)
        with tarfile.open(fileobj=io.BytesIO(backup), mode='r:gz') as archive:
            assert MUSE + '/profile.json' in archive.getnames()
        (out / 'previous-module.tar.gz').write_bytes(backup)
        (out / 'before.json').write_text(json.dumps(before, indent=2) + '\n')
    else:
        assert json.loads((out / 'before.json').read_text()) == before, 'Device changed after the upgrade backup'
    # The official module installer installs its embedded APK using pm -r; it
    # preserves the existing application, preferences and LSPosed scope.
    remote = '/data/local/tmp/omnicam_muse_probe/upgrade-40002.zip'
    subprocess.run(ADB + ['push', str(ROOT / 'dist' / zip_name), remote], check=True, capture_output=True)
    assert remote_sha(remote) == manifest[zip_name]['sha256']
    command = '/data/adb/ksu/bin/ksud module install ' + remote
    run = subprocess.run(ADB + ['exec-out', shlex.join(['su', '-c', command])], capture_output=True, text=True)
    (out / 'installer.log').write_text(run.stdout + run.stderr)
    run.check_returncode()
    staged = root('for d in /data/adb/modules_update/' + MUSE + ' ' + active + '; do '
                  'if [ -f "$d/profile.json" ]; then echo "$d"; break; fi; done').decode().strip()
    assert staged in ['/data/adb/modules_update/' + MUSE, active]
    assert remote_sha(staged + '/profile.json') == hashlib.sha256(profile_bytes).hexdigest()
    assert 'Success' in root('cat ' + staged + '/install.log').decode()
    current = subprocess.check_output(ADB + ['shell', 'pm', 'path', 'local.jiege.camera'], text=True).strip().removeprefix('package:')
    assert remote_sha(current) == remote_sha(staged + '/' + apk_name) == manifest[apk_name]['sha256']
    assert root('stat -c %u /data/user/0/local.jiege.camera').decode().strip() == before['app_uid']
    assert other_flags() == before['other_module_flags'], 'Another module enabled state changed'
    report = {'version': version, 'apk_sha256': manifest[apk_name]['sha256'],
              'module_zip_sha256': manifest[zip_name]['sha256'], 'module_directory': staged,
              'app_uid_preserved': True, 'other_module_flags_preserved': True, 'rebooted': False}
    (out / 'upgraded.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
