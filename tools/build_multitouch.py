"""Build a small, temporary Android multi-pointer input helper."""
import os
from pathlib import Path
import subprocess
ROOT = Path(__file__).resolve().parent.parent
sdk = Path(os.environ['ANDROID_HOME'])
java = Path(os.environ['JAVA_HOME']) / 'bin'
out = ROOT / 'evidence/multitouch-probe'
out.mkdir(exist_ok=True)
android = sorted((sdk / 'platforms').glob('android-37*/android.jar'))[-1]
subprocess.run([str(java / 'javac'), '--release', '17', '-cp', str(android), '-d', str(out),
                str(ROOT / 'tools/MultiTouchProbe.java')], check=True)
d8 = sorted((sdk / 'build-tools').glob('*/d8'))[-1]
subprocess.run([str(d8), '--min-api', '28', '--lib', str(android), '--output', str(out / 'probe.jar'),
                str(out / 'MultiTouchProbe.class')], check=True)
print(out / 'probe.jar')
