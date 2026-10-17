"""Run real production-source JVM suites and the MTK nonuniform gamma regression."""
import os
from pathlib import Path
import subprocess
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def main():
    java = Path(os.environ['JAVA_HOME']) / 'bin'
    sdk = Path(os.environ['ANDROID_HOME'])
    cache = ROOT / 'tools/gradle-home/caches/modules-2/files-2.1'
    kotlin = next((cache / 'org.jetbrains.kotlin/kotlin-stdlib/2.4.20').rglob('*.jar'))
    flat = next((cache / 'com.google.flatbuffers/flatbuffers-java/23.5.26').rglob('*.jar'))
    android = sorted((sdk / 'platforms').glob('android-37*/android.jar'))[-1]
    evidence = ROOT / 'evidence/offline-tests'
    evidence.mkdir(exist_ok=True)
    dexkit = evidence / 'dexkit.jar'
    aar = next((cache / 'org.luckypray/dexkit/2.3.0').rglob('*.aar'))
    with zipfile.ZipFile(aar) as archive:
        dexkit.write_bytes(archive.read('classes.jar'))
    json_jar = evidence / 'json-20240303.jar'
    if not json_jar.exists():
        with urllib.request.urlopen('https://repo.maven.apache.org/maven2/org/json/json/20240303/json-20240303.jar', timeout=30) as source:
            json_jar.write_bytes(source.read())
    test_root = ROOT / 'tools/offline_tests'
    src = ROOT / 'app/src/main/java/local/jiege'
    sources = list((src / 'hook/filters').glob('*.java')) + list((src / 'lut').glob('*.java'))
    for name in ['Log', 'Diagnostics', 'Settings', 'Symbols', 'SymbolSearch']:
        sources.append(src / 'hook/common' / (name + '.java'))
    for name in ['DiagnosticsContract', 'MasterFilterContract', 'MasterFilterStore', 'ModuleSettings',
                 'LaunchModes', 'ModelPresets', 'MasterLooks']:
        sources.append(src / 'settings' / (name + '.java'))
    tests = ['FiltersOfflineTest', 'LutBakerOfflineTest', 'StoreOfflineTest', 'MasterLooksOfflineTest']
    sources.extend(test_root / (name + '.java') for name in tests)
    with tempfile.TemporaryDirectory(prefix='muse-jvm-tests-') as folder:
        cp = os.pathsep.join(map(str, [folder, ROOT / 'app/libs/api-82.jar',
                 dexkit, kotlin, flat, json_jar, android]))
        subprocess.run([str(java / 'javac'), '-encoding', 'UTF-8', '-d', folder, '-cp', cp,
                        str(test_root / 'shim/de/robv/android/xposed/XposedHelpers.java')], check=True)
        subprocess.run([str(java / 'javac'), '-encoding', 'UTF-8', '-d', folder, '-cp', cp,
                        *map(str, sources)], check=True)
        with (evidence / 'results.log').open('w') as log:
            for name in tests:
                run = subprocess.run([str(java / 'java'), '-Dfile.encoding=UTF-8', '-cp', cp, name, str(ROOT)],
                                     capture_output=True, text=True)
                log.write(name + '\n' + run.stdout + run.stderr + '\n')
                run.check_returncode()
                print(name + ': PASS')
        gamma = Path(folder) / 'mtk-gamma-test'
        subprocess.run(['c++', '-std=c++17', '-I', str(ROOT / 'app/src/main/cpp'),
                        str(ROOT / 'tools/mtk_gamma_test.cpp'), '-o', str(gamma)], check=True)
        native = subprocess.run([str(gamma)], capture_output=True, text=True, check=True)
        with (evidence / 'results.log').open('a') as log:
            log.write(native.stdout + native.stderr)
        print(native.stdout.strip())
        grain = Path(folder) / 'mtk-grain-test'
        subprocess.run(['c++', '-std=c++17', '-I', str(ROOT / 'app/src/main/cpp'),
                        str(ROOT / 'tools/mtk_grain_test.cpp'), '-o', str(grain)], check=True)
        native_grain = subprocess.run([str(grain)], capture_output=True, text=True, check=True)
        with (evidence / 'results.log').open('a') as log:
            log.write(native_grain.stdout + native_grain.stderr)
        print(native_grain.stdout.strip())
        frame = ROOT / 'evidence/experiments-20261017/host-master'
        if (frame / 'frame-key.bin').is_file() and all((frame / ('LMTLut' + str(i))).is_file() for i in range(4)):
            master = Path(folder) / 'mtk-master-test'
            cpp = ROOT / 'app/src/main/cpp'
            subprocess.run(['c++', '-std=c++17', '-O2', '-pthread', '-I', str(cpp),
                            str(ROOT / 'tools/mtk_master_test.cpp'), str(cpp / 'master_core.cpp'),
                            str(cpp / 'master_dt.cpp'), str(cpp / 'master_canon.cpp'), '-o', str(master)], check=True)
            result = subprocess.run([str(master), str(ROOT / 'module/payload/master_color'),
                                     str(frame), str(frame / 'frame-key.bin')], capture_output=True, text=True, check=True)
            with (evidence / 'results.log').open('a') as log:
                log.write(result.stdout + result.stderr)
            print(result.stdout.strip())


if __name__ == '__main__':
    main()
