"""Restore only this experiment's module XML; never restore camera data or media DB."""
import hashlib
import json
import shlex
import subprocess
import tarfile
from install_x9spro import ADB, ROOT, root
from device_actions import exclusive_ui


@exclusive_ui
def main():
    out = ROOT / 'evidence/experiments-20261017'
    path = json.loads((out / 'before.json').read_text())['module_preferences']
    assert path.endswith('/prefs/local.jiege.camera/module_settings.xml')
    with tarfile.open(out / 'before.tar') as archive:
        original = archive.extractfile(path.lstrip('/')).read()
    root('am force-stop local.jiege.camera; am force-stop com.oplus.camera')
    before = root('cat ' + shlex.quote(path))
    (out / 'module-settings-before-final-restore.xml').write_bytes(before)
    local = out / 'module-settings-original.xml'
    local.write_bytes(original)
    remote = '/data/local/tmp/omnicam_muse_probe/original-module-settings.xml'
    subprocess.run(ADB + ['push', str(local), remote], check=True, capture_output=True)
    metadata = root('stat -c "%u:%g:%a" ' + shlex.quote(path)).decode().strip()
    root('cat ' + shlex.quote(remote) + ' > ' + shlex.quote(path))
    assert root('cat ' + shlex.quote(path)) == original
    assert root('stat -c "%u:%g:%a" ' + shlex.quote(path)).decode().strip() == metadata
    report = {'module_xml_sha256': hashlib.sha256(original).hexdigest(),
              'exact_original_bytes': True, 'owner_mode_preserved': True,
              'camera_database_restored': False, 'camera_media_preserved': True}
    (out / 'module-settings-restored.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
