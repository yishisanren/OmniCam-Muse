"""Package only reviewed module files and the exact signed, paired APK."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def main():
    module = ROOT / 'module'
    profile = (module / 'profile.json').read_bytes()
    assert (ROOT / 'app/src/main/assets/device_profile.json').read_bytes() == profile
    version = next(x.split('=', 1)[1] for x in (module / 'module.prop').read_text().splitlines() if x.startswith('version='))
    build = Path(os.environ.get('MUSE_BUILD_DIR', '/private/tmp/omnicam-muse-x9spro-build'))
    artifact = build / 'outputs/apk/release/app-release.apk'
    sdk = Path(os.environ['ANDROID_HOME'])
    signer = sorted((sdk / 'build-tools').glob('*/apksigner'))[-1]
    run = subprocess.run([str(signer), 'verify', '--verbose', '--print-certs', str(artifact)],
                         capture_output=True, text=True, check=True)
    (ROOT / 'evidence/apk-signature.txt').write_text(run.stdout + run.stderr)
    with zipfile.ZipFile(artifact) as apk:
        assert apk.read('assets/device_profile.json') == profile
        assert hashlib.sha256(profile).hexdigest().encode() in apk.read('lib/arm64-v8a/libjiege_native.so')
        spec = json.loads(apk.read('assets/symbols.json'))
        assert len(spec['camera']) == 254 and len(spec['gallery']) == 31
    for script in module.glob('*.sh'):
        assert b'\r' not in script.read_bytes(), script
        subprocess.run(['sh', '-n', str(script)], check=True)
    assert not (module / 'system/odm/lib64/libAlgoInterface.so').exists()
    assert not (module / 'payload/isp').exists() and not (module / 'payload/gamma').exists()
    assert (module / 'skip_mount').exists()
    assert 'am force-stop' not in (module / 'service.sh').read_text()
    assert 'TILT_DB' not in (module / 'service.sh').read_text()
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    apk_name = 'omnicam-muse-' + version + '.apk'
    shutil.copy2(artifact, dist / apk_name)
    for old in module.glob('omnicam-muse-*.apk'):
        old.unlink()
    shutil.copy2(artifact, module / apk_name)
    archive = dist / ('OmniCam-Muse-' + version + '-KSU.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for file in sorted(module.rglob('*')):
            relative = file.relative_to(module)
            if any(x.startswith('.') or x in {'merged', 'disable', 'remove', 'update'} for x in relative.parts):
                continue
            if file.is_symlink():
                raise ValueError('Unexpected package symlink: ' + str(relative))
            if not file.is_file() or file.suffix == '.log':
                continue
            info = zipfile.ZipInfo(relative.as_posix(), (2026, 10, 17, 0, 0, 0))
            info.external_attr = (0o100755 if file.suffix == '.sh' else 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, file.read_bytes())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and z.read(apk_name) == artifact.read_bytes()
    manifest = {file.name: {'sha256': hashlib.sha256(file.read_bytes()).hexdigest(), 'size': file.stat().st_size}
                for file in [dist / apk_name, archive]}
    (dist / 'SHA256SUMS').write_text(''.join(v['sha256'] + '  ' + k + '\n' for k, v in manifest.items()))
    (ROOT / 'evidence/package-verification.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
