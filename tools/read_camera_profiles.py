"""Read calibration metadata without opening the camera; use only an explicit device."""
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def main():
    sdk, java = Path(os.environ['ANDROID_HOME']), Path(os.environ['JAVA_HOME']) / 'bin'
    adb = [shutil.which('adb') or 'adb', '-s', os.environ['MUSE_DEVICE_SERIAL']]
    if subprocess.check_output(adb + ['shell', 'getprop', 'ro.product.model'], text=True).strip() != 'PME110':
        raise RuntimeError('Unexpected phone')
    out = ROOT / 'evidence/characteristics-probe'
    out.mkdir(exist_ok=True)
    android = sorted((sdk / 'platforms').glob('android-37*/android.jar'))[-1]
    subprocess.run([str(java / 'javac'), '--release', '17', '-cp', str(android), '-d', str(out),
                    str(ROOT / 'tools/CameraProfileProbe.java')], check=True, capture_output=True)
    d8 = sorted((sdk / 'build-tools').glob('*/d8'))[-1]
    subprocess.run([str(d8), '--min-api', '28', '--lib', str(android), '--output', str(out / 'probe.jar'),
                    str(out / 'CameraProfileProbe.class')], check=True, capture_output=True)
    dest = '/data/local/tmp/omnicam_muse_probe/characteristics.jar'
    subprocess.run(adb + ['shell', 'mkdir', '-p', str(Path(dest).parent)], check=True, capture_output=True)
    subprocess.run(adb + ['push', str(out / 'probe.jar'), dest], check=True, capture_output=True)
    run = subprocess.run(adb + ['exec-out', "su -c 'CLASSPATH=" + dest +
                              " app_process /system/bin CameraProfileProbe'"], capture_output=True, text=True, timeout=30)
    (out / 'result.log').write_text(run.stdout + '\n' + run.stderr)
    run.check_returncode()
    result = json.loads(next(line for line in run.stdout.splitlines() if line.startswith('{')))
    capture = Path(os.environ.get('MUSE_CAPTURE_DIR', ROOT / 'evidence/device-20261017'))
    (capture / 'camera-characteristics.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Read camera profiles:', list(result), 'physical rear:', result['0']['physical_ids'])


if __name__ == '__main__':
    main()
