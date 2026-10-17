"""Inspect APK dex files with the current SymbolSearch; do not start camera/gallery."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
ADB = [shutil.which('adb') or 'adb', '-s', os.environ['MUSE_DEVICE_SERIAL']]
DEST = '/data/local/tmp/omnicam_muse_probe'


def main():
    model = subprocess.check_output(ADB + ['shell', 'getprop', 'ro.product.model'], text=True).strip()
    if model != 'PME110':
        raise RuntimeError('Unexpected probe target')
    subprocess.run(ADB + ['shell', 'mkdir', '-p', DEST], check=True, capture_output=True)
    for source in [ROOT / 'evidence/symbol-probe/probe.jar', ROOT / 'evidence/symbol-probe/libdexkit.so',
                   ROOT / 'app/src/main/assets/symbols.json']:
        subprocess.run(ADB + ['push', str(source), DEST + '/' + source.name], check=True, capture_output=True)
    for section, apk in [('camera', '/product/app/OplusCamera/OplusCamera.apk'),
                         ('gallery', '/product/priv-app/OppoGallery2/OppoGallery2.apk')]:
        command = 'CLASSPATH=' + shlex.quote(DEST + '/probe.jar') + ' app_process /system/bin SymbolProbe ' + shlex.join([
            DEST + '/libdexkit.so', apk, DEST + '/symbols.json', section])
        run = subprocess.run(ADB + ['exec-out', shlex.join(['su', '-c', command])], capture_output=True, text=True)
        (ROOT / 'evidence' / (section + '-probe.log')).write_text(run.stdout + '\n' + run.stderr)
        run.check_returncode()
        line = next(line for line in reversed(run.stdout.splitlines()) if line.startswith('{"resolved"') or '"failures"' in line and line.startswith('{'))
        result = json.loads(line)
        (ROOT / 'evidence' / (section + '-symbols.json')).write_text(json.dumps(result, indent=2) + '\n')
        print(section, 'resolved:', len(result['resolved']), 'failures:', result['failures'])


if __name__ == '__main__':
    main()
