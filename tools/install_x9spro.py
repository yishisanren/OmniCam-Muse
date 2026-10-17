"""Install the reviewed candidate after a fresh, recoverable baseline; never reboot."""
import hashlib
import fcntl
import json
import os
from pathlib import Path
import shlex
import shutil
import sqlite3
import subprocess
from snapshot_device import extract

ROOT = Path(__file__).resolve().parent.parent
ADB = [shutil.which('adb') or 'adb', '-s', os.environ['MUSE_DEVICE_SERIAL']]
OUT = ROOT / 'evidence/device-20261017/install'
AURA = '/data/adb/modules/omnicam_aura_x9spro'
MUSE = 'omnicam_muse_x9spro'


def root(command):
    return subprocess.check_output(ADB + ['exec-out', shlex.join(['su', '-c', command])])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / 'installed.json').exists():
        raise RuntimeError('Candidate already installed; verify it instead of overwriting the baseline')
    profile = json.loads((ROOT / 'module/profile.json').read_text())
    for key, prop in [('model', 'ro.product.model'), ('firmware', 'ro.build.display.id')]:
        assert subprocess.check_output(ADB + ['shell', 'getprop', prop], text=True).strip() == profile[key]
    assert root('sha256sum /product/app/OplusCamera/OplusCamera.apk').decode().split()[0] == profile['apk_sha256']
    assert root('sha256sum /odm/lib64/libAlgoInterface.so').decode().split()[0] == profile['algo_sha256']
    assert subprocess.check_output(ADB + ['shell', 'getprop', 'sys.user.0.ce_available'], text=True).strip() == 'true'
    baseline_file = OUT / 'before.json'
    if not baseline_file.exists():
        baseline = {'aura_disabled': root('if [ -f ' + AURA + '/disable ]; then echo yes; else echo no; fi').decode().strip() == 'yes',
                    'existing_muse': subprocess.run(ADB + ['shell', 'pm', 'path', 'local.jiege.camera'], capture_output=True, text=True).stdout.strip()}
        backup = root('/data/adb/ksu/bin/busybox tar --exclude=omnicam_aura_x9spro/merged -czf - -C /data/adb/modules omnicam_aura_x9spro')
        (OUT / 'Aura-module-before.tar.gz').write_bytes(backup)
        db = root('tar -cf - -C /data/adb/lspd/config modules_config.db modules_config.db-wal modules_config.db-shm')
        extract(db, OUT / 'lsposed-before')
        conn = sqlite3.connect(str(OUT / 'lsposed-before/modules_config.db'))
        assert conn.execute('pragma integrity_check').fetchone()[0] == 'ok'
        baseline['aura_lsposed'] = conn.execute('select * from modules_state where module_pkg_name=?', ['local.omnicam.aura']).fetchall()
        conn.close()
        baseline_file.write_text(json.dumps(baseline, indent=2) + '\n')
    baseline = json.loads(baseline_file.read_text())
    version = profile['version']
    apk = ROOT / 'dist' / ('omnicam-muse-' + version + '.apk')
    archive = ROOT / 'dist' / ('OmniCam-Muse-' + version + '-KSU.zip')
    expected = json.loads((ROOT / 'evidence/package-verification.json').read_text())
    for file in [apk, archive]:
        assert hashlib.sha256(file.read_bytes()).hexdigest() == expected[file.name]['sha256']
    # ColorOS intercepts shell-UID streaming ADB installs. Use the same root package-manager
    # interface as the approved KernelSU module installer; no system security setting changes.
    remote_apk = '/data/local/tmp/omnicam_muse_probe/muse.apk'
    subprocess.run(ADB + ['push', str(apk), remote_apk], check=True, capture_output=True)
    assert root('sha256sum ' + remote_apk).decode().split()[0] == expected[apk.name]['sha256']
    apk_result = root('pm install -r ' + remote_apk + ' 2>/dev/null').decode()
    (OUT / 'apk-install.log').write_text(apk_result)
    assert 'Success' in apk_result, 'APK install failed; existing app preserved'
    actual_apk = subprocess.check_output(ADB + ['shell', 'pm', 'path', 'local.jiege.camera'], text=True).strip().removeprefix('package:')
    assert root('sha256sum ' + shlex.quote(actual_apk)).decode().split()[0] == expected[apk.name]['sha256']
    remote = '/data/local/tmp/omnicam_muse_probe/module.zip'
    subprocess.run(ADB + ['push', str(archive), remote], check=True, capture_output=True)
    try:
        root('touch ' + AURA + '/disable')
        run = subprocess.run(ADB + ['exec-out', shlex.join(['su', '-c', '/data/adb/ksu/bin/ksud module install ' + remote])],
                             capture_output=True, text=True)
        (OUT / 'module-install.log').write_text(run.stdout + run.stderr)
        run.check_returncode()
        staged = root('for d in /data/adb/modules_update/' + MUSE + ' /data/adb/modules/' + MUSE + '; do if [ -f "$d/profile.json" ]; then echo "$d"; break; fi; done').decode().strip()
        assert staged
        assert root('sha256sum ' + staged + '/profile.json').decode().split()[0] == hashlib.sha256((ROOT / 'module/profile.json').read_bytes()).hexdigest()
        assert 'Success' in root('cat ' + staged + '/install.log').decode()
    except Exception:
        if not baseline['aura_disabled']:
            root('rm -f ' + AURA + '/disable')
        for directory in ['/data/adb/modules/' + MUSE, '/data/adb/modules_update/' + MUSE]:
            root('if [ -d ' + directory + ' ]; then touch ' + directory + '/disable; fi')
        raise
    report = {'apk_sha256': expected[apk.name]['sha256'], 'module_zip_sha256': expected[archive.name]['sha256'],
              'module_directory': staged, 'aura_ksu_disabled': True, 'rebooted': False,
              'lsposed_scope': 'pending UI configuration', 'runtime_acceptance': 'pending reboot and capture tests'}
    (OUT / 'installed.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / '.installer.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        main()
