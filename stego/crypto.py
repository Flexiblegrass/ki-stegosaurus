from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import os

SALT_LEN = 16          
NONCE_LEN = 12         
KEY_LEN = 32          
PBKDF2_ITER = 200_000  


class DecryptionError(Exception):
    pass


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LEN,
        salt=salt,
        iterations=PBKDF2_ITER,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt(plaintext: bytes, password: str) -> bytes:

    if isinstance(plaintext, str):
        plaintext = plaintext.encode("utf-8")
    salt = os.urandom(SALT_LEN)          
    nonce = os.urandom(NONCE_LEN)        
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)   
    return salt + nonce + ciphertext


def decrypt(blob: bytes, password: str) -> bytes:

    if len(blob) < SALT_LEN + NONCE_LEN + 16:
        raise DecryptionError("Data terenkripsi tidak valid / terlalu pendek.")
    salt = blob[:SALT_LEN]
    nonce = blob[SALT_LEN:SALT_LEN + NONCE_LEN]
    ciphertext = blob[SALT_LEN + NONCE_LEN:]
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    try:
        return aesgcm.decrypt(nonce, ciphertext, None)
    except Exception:
        raise DecryptionError(
            "Dekripsi gagal: kata sandi salah atau data telah diubah."
        )
