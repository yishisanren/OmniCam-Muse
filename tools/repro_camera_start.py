"""Device regression: the actual camera must remain alive and reach its preview."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
ADB = [shutil.which('adb') or 'adb', '-s', os.environ['MUSE_DEVICE_SERIAL']]
OUT = ROOT / 'evidence/device-20261017/acceptance'


def root(command):
    return subprocess.check_output(ADB + ['exec-out', shlex.join(['su', '-c', command])], text=True)


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else 'startup'
    assert name.replace('-', '').replace('_', '').isalnum()
    OUT.mkdir(parents=True, exist_ok=True)
    timestamp = subprocess.check_output(ADB + ['shell', shlex.join(['date', '+%m-%d %H:%M:%S.000'])], text=True).strip()
    root('am force-stop com.oplus.camera')
    subprocess.run(ADB + ['shell', 'am', 'start', '-a', 'android.media.action.STILL_IMAGE_CAMERA'], check=True, capture_output=True)
    time.sleep(12)
    pid = root('pidof com.oplus.camera').strip()
    focus = subprocess.check_output(ADB + ['shell', 'dumpsys', 'window'], text=True)
    focus = next((l.strip() for l in focus.splitlines() if 'mCurrentFocus=' in l), '')
    crash = subprocess.check_output(ADB + ['shell', shlex.join(['logcat', '-d', '-b', 'crash', '-T', timestamp])], text=True)
    (OUT / (name + '-crash.log')).write_text(crash)
    (OUT / (name + '-modules.log')).write_text(root('cat /data/adb/lspd/log/modules_*.log'))
    failure = 'Process: com.oplus.camera' in crash or '>>> com.oplus.camera <<<' in crash
    report = {'case': name, 'pid': pid, 'focus': focus, 'camera_crash': failure,
              'survives_12_seconds': bool(pid) and not failure}
    (OUT / (name + '.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))
    assert report['survives_12_seconds'], 'Camera startup regression'


if __name__ == '__main__':
    main()
