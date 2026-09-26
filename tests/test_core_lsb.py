import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stego import core, crypto
from stego.lsb import bytes_to_bits, bits_to_bytes

def _dummy_image(w=128, h=128, seed=0):
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)


def test_sisip_lalu_ekstrak_utuh():
    img = _dummy_image()
    pesan = "Steganografi LSB + AES berhasil!"
    stego = core.embed(img, pesan, password="pw123", stego_key="key-abc")
    hasil = core.extract(stego, password="pw123", stego_key="key-abc")
    assert hasil.decode() == pesan


def test_stego_key_salah_gagal():
    img = _dummy_image()
    stego = core.embed(img, "rahasia", password="pw", stego_key="key-benar")
    gagal = False
    try:
        core.extract(stego, password="pw", stego_key="key-salah")
    except (core.ExtractionError, crypto.DecryptionError):
        gagal = True
    assert gagal


def test_kapasitas_ditolak():
    img = _dummy_image(w=16, h=16)
    ditolak = False
    try:
        core.embed(img, b"A" * 5000, password="pw", stego_key="key")
    except core.CapacityError:
        ditolak = True
    assert ditolak


def test_tamper_terdeteksi():
    img = _dummy_image()
    stego = core.embed(img, "pesan penting", password="pw", stego_key="key")
    rng = np.random.default_rng(1)
    flat = stego.reshape(-1)
    flat[rng.choice(flat.size, size=2000, replace=False)] ^= 1
    rusak = False
    try:
        core.extract(stego, password="pw", stego_key="key")
    except (core.ExtractionError, crypto.DecryptionError):
        rusak = True
    assert rusak


def test_konversi_bit_byte():
    data = b"\x00\xFF\xA5\x01"
    assert bits_to_bytes(bytes_to_bits(data)) == data


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    lulus = 0
    for fn in fns:
        try:
            fn(); print(f"PASS  {fn.__name__}"); lulus += 1
        except Exception as e:
            print(f"FAIL  {fn.__name__}: {e}")
    print(f"\n{lulus}/{len(fns)} test lulus.")