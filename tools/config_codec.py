"""Decode this device's OPLUS config envelope; never print or persist its key."""
from pathlib import Path


def decode(path: Path, security: Path) -> bytes:
    data = path.read_bytes()
    if not data.startswith(b'\x01\x01'):
        return data
    if len(data) < 24 or data[-1] != 255 or (len(data) - 8) % 16:
        raise ValueError('Unexpected config envelope: ' + path.name)
    library = security.read_bytes()
    key = bytes(value ^ 63 for value in library[0x7ab:0x7ab + 32])[::2]
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.padding import PKCS7
    decryptor = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
    clear = decryptor.update(data[4:-4]) + decryptor.finalize()
    unpadder = PKCS7(128).unpadder()
    return unpadder.update(clear) + unpadder.finalize()
