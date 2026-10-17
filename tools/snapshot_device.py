"""Read the selected phone and its stock ODM through a private mount namespace."""
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(os.environ.get('MUSE_EVIDENCE_DIR', ROOT / 'evidence/device-20261017'))
SERIAL = os.environ['MUSE_DEVICE_SERIAL']
ADB = [shutil.which('adb') or 'adb', '-s', SERIAL]


def root(command):
    return subprocess.check_output(ADB + ['exec-out', shlex.join(['su', '-c', command])])


def extract(data, destination):
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for member in archive:
            name = member.name.removeprefix('./')
            target = destination / name
            if member.isdir():
                continue
            if not member.isfile() or name.startswith('/') or '..' in Path(name).parts:
                raise ValueError('Unexpected archive entry: ' + name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fields = {'model': 'ro.product.model', 'firmware': 'ro.build.display.id',
              'platform': 'ro.board.platform', 'unlocked': 'sys.user.0.ce_available'}
    profile = {k: subprocess.check_output(ADB + ['shell', 'getprop', v], text=True).strip()
               for k, v in fields.items()}
    if profile['model'] != 'PME110' or profile['platform'] != 'mt6993':
        raise RuntimeError('Device is not the approved PME110 target')
    for package in ['com.oplus.camera', 'com.coloros.gallery3d']:
        dump = subprocess.check_output(ADB + ['shell', 'dumpsys', 'package', package], text=True)
        profile[package] = next(l.split('=', 1)[1].strip() for l in dump.splitlines() if 'versionName=' in l)
    (OUT / 'live-profile.json').write_text(json.dumps(profile, indent=2) + '\n')
    (OUT / 'mounts-before.txt').write_bytes(root('cat /proc/mounts'))
    (OUT / 'module-state.txt').write_bytes(root('for d in /data/adb/modules/*; do echo "$d"; cat "$d/module.prop"; ls "$d/disable" 2>/dev/null; done'))
    state = root('tar -cf - -C /data/adb/lspd/config modules_config.db modules_config.db-wal modules_config.db-shm')
    extract(state, OUT / 'lsposed-before')
    paths = ['data/user/0/com.oplus.camera/shared_prefs',
             'data/user/0/com.oplus.camera/databases',
             'data/user/0/com.coloros.gallery3d/shared_prefs/business_featureSwitch_config.xml']
    (OUT / 'preferences-before.tar').write_bytes(root('tar -cf - -C / ' + shlex.join(paths)))
    # The unshare process inherits the current view, makes propagation private, then removes
    # only its inherited Aura overlays. The phone's camera and other processes keep their view.
    script = '''set -eu
for target in /odm/etc/camera/config /odm/etc/camera/meishe_lut /odm/etc/camera/basictone /odm/lib64; do
    if grep -q "overlay $target overlay" /proc/mounts; then umount "$target"; fi
done
tar -cf - -C / odm/etc/camera/config odm/etc/camera/conf_tuning_params.json odm/lib64/libAlgoInterface.so odm/lib64/libBasicTonePhoto.so odm/lib64/libOplusSecurity.so odm/lib64/libOPAlgoCamHDRTransformCamera.so
'''
    command = '/data/adb/ksu/bin/busybox unshare -m --propagation private /system/bin/sh -c ' + shlex.quote(script)
    data = root(command)
    extract(data, OUT / 'stock-tree')
    (OUT / 'stock-manifest.json').write_text(json.dumps({
        str(f.relative_to(OUT / 'stock-tree')): hashlib.sha256(f.read_bytes()).hexdigest()
        for f in (OUT / 'stock-tree').rglob('*') if f.is_file()}, indent=2) + '\n')
    print(json.dumps(profile, indent=2))
    print('Stock files:', len(json.loads((OUT / 'stock-manifest.json').read_text())))
    print('Private evidence:', OUT)


if __name__ == '__main__':
    main()
