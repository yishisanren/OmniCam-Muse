"""Create a private local signing identity once; never print its password."""
import os
from pathlib import Path
import secrets
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def main():
    key = ROOT / 'port.keystore'
    config = ROOT / 'evidence/signing.env'
    if key.exists() or config.exists():
        if not key.is_file() or not config.is_file():
            raise RuntimeError('Incomplete existing signing identity; refusing to overwrite')
        print('Existing private signing identity retained')
        return
    config.parent.mkdir(parents=True, exist_ok=True)
    password = secrets.token_urlsafe(36)
    environment = dict(os.environ, OMNICAM_STORE_PASSWORD=password, OMNICAM_KEY_PASSWORD=password)
    subprocess.run([str(Path(os.environ['JAVA_HOME']) / 'bin/keytool'), '-genkeypair',
                    '-keystore', str(key), '-storetype', 'PKCS12', '-alias', 'muse-x9spro',
                    '-storepass:env', 'OMNICAM_STORE_PASSWORD', '-keypass:env', 'OMNICAM_KEY_PASSWORD',
                    '-keyalg', 'RSA', '-keysize', '3072', '-validity', '10000',
                    '-dname', 'CN=OmniCam Muse Find X9s Pro port', '-noprompt'],
                   env=environment, check=True, capture_output=True)
    key.chmod(0o600)
    config.write_text('OMNICAM_KEYSTORE=port.keystore\nOMNICAM_KEY_ALIAS=muse-x9spro\n'
                      + 'OMNICAM_STORE_PASSWORD=' + password + '\n'
                      + 'OMNICAM_KEY_PASSWORD=' + password + '\n')
    config.chmod(0o600)
    print('Created private local signing identity; files excluded from Git')


if __name__ == '__main__':
    main()
