"""Compile the current production SymbolSearch for a read-only Android app_process probe."""
import os
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'evidence/symbol-probe'


def find(cache, group, artifact, filename):
    files = list((cache / group / artifact).rglob(filename))
    if not files:
        raise RuntimeError('Build dependencies not cached: ' + artifact)
    return sorted(files)[-1]


def main():
    sdk = Path(os.environ['ANDROID_HOME'])
    java = Path(os.environ['JAVA_HOME']) / 'bin'
    cache = ROOT / 'tools/gradle-home/caches/modules-2/files-2.1'
    aar = find(cache, 'org.luckypray', 'dexkit', 'dexkit-2.3.0.aar')
    kotlin = find(cache, 'org.jetbrains.kotlin', 'kotlin-stdlib', 'kotlin-stdlib-2.4.20.jar')
    flat = find(cache, 'com.google.flatbuffers', 'flatbuffers-java', 'flatbuffers-java-23.5.26.jar')
    android = sorted((sdk / 'platforms').glob('android-37*/android.jar'))[-1]
    OUT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(aar) as z:
        (OUT / 'dexkit.jar').write_bytes(z.read('classes.jar'))
        (OUT / 'libdexkit.so').write_bytes(z.read('jni/arm64-v8a/libdexkit.so'))
    classes = OUT / 'classes'
    classes.mkdir(exist_ok=True)
    cp = os.pathsep.join(map(str, [OUT / 'dexkit.jar', kotlin, flat, android]))
    subprocess.run([str(java / 'javac'), '--release', '17', '-encoding', 'UTF-8', '-cp', cp, '-d', str(classes),
                    str(ROOT / 'tools/SymbolProbe.java'),
                    str(ROOT / 'app/src/main/java/local/jiege/hook/common/SymbolSearch.java')], check=True)
    jar = OUT / 'probe-classes.jar'
    subprocess.run([str(java / 'jar'), 'cf', str(jar), '-C', str(classes), '.'], check=True)
    d8 = sorted((sdk / 'build-tools').glob('*/d8'))[-1]
    with (OUT / 'build.log').open('w') as log:
        subprocess.run([str(d8), '--min-api', '28', '--lib', str(android), '--output', str(OUT / 'probe.jar'),
                        str(jar), str(OUT / 'dexkit.jar'), str(kotlin), str(flat)], check=True,
                       stdout=log, stderr=subprocess.STDOUT)
    print('Probe built:', OUT / 'probe.jar')


if __name__ == '__main__':
    main()
