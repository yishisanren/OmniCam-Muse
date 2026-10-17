"""Pair the module's embedded APK with the installed final app, then read back every packaged file."""
import hashlib
import json
import shlex
import subprocess
import zipfile
from install_x9spro import ROOT, ADB, root


def sha(path):
    return root('sha256sum ' + shlex.quote(path)).decode().split()[0]


def main():
    manifest = json.loads((ROOT / 'evidence/package-verification.json').read_text())
    apk_name = next(n for n in manifest if n.endswith('.apk'))
    archive_name = next(n for n in manifest if n.endswith('.zip'))
    expected_apk = manifest[apk_name]['sha256']
    installed = subprocess.check_output(ADB + ['shell', 'pm', 'path', 'local.jiege.camera'], text=True).strip().removeprefix('package:')
    assert sha(installed) == expected_apk, 'Install the final app before reconciling its embedded copy'
    mod = '/data/adb/modules/omnicam_muse_x9spro/'
    remote_apk = mod + apk_name
    old_hash = sha(remote_apk)
    if old_hash != expected_apk:
        staged = '/data/local/tmp/omnicam_muse_probe/final.apk'
        subprocess.run(ADB + ['push', str(ROOT / 'dist' / apk_name), staged], check=True, capture_output=True)
        assert sha(staged) == expected_apk
        backup = '/data/local/tmp/omnicam_muse_probe/embedded-' + old_hash + '.apk'
        root('test -f ' + shlex.quote(backup) + ' || cp -p ' + shlex.quote(remote_apk) + ' ' + shlex.quote(backup))
        root('cp ' + shlex.quote(staged) + ' ' + shlex.quote(remote_apk) + ' && chmod 0644 ' + shlex.quote(remote_apk) + ' && chown 0:0 ' + shlex.quote(remote_apk))
    assert sha(remote_apk) == expected_apk
    # KernelSU removes installation-only documentation and customize.sh after
    # flashing. Their archive bytes are checked by package_x9spro; they are not
    # runtime module files and must not be recreated just to satisfy a hash scan.
    install_only = {'README.md', 'customize.sh'}
    with zipfile.ZipFile(ROOT / 'dist' / archive_name) as z:
        expected = {mod + n: hashlib.sha256(z.read(n)).hexdigest()
                    for n in z.namelist() if n not in install_only}
    # Keep each command below Android's argument limit and avoid hashing runtime image/log files.
    actual = {}
    names = list(expected)
    for i in range(0, len(names), 80):
        lines = root('sha256sum ' + ' '.join(map(shlex.quote, names[i:i + 80]))).decode().splitlines()
        actual.update({line.split(None, 1)[1].strip(): line.split()[0] for line in lines})
    mismatches = [n for n, digest in expected.items() if actual.get(n) != digest]
    report = {'apk_sha256': expected_apk, 'module_zip_sha256': manifest[archive_name]['sha256'],
              'packaged_runtime_files': len(expected), 'installer_only_files': sorted(install_only),
              'mismatches': mismatches, 'installed_and_embedded_apk_match': True}
    (ROOT / 'evidence/device-20261017/acceptance/final-installed.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    assert not mismatches, 'Installed module does not match the final package'


if __name__ == '__main__':
    main()
