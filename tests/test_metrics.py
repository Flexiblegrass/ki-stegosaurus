import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stego import core, crypto, prng, metrics
from stego.lsb import bytes_to_bits, bits_to_bytes


def _dummy_image(w=128, h=128, seed=0):
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)


def test_1_enkripsi_dekripsi_benar():
    pesan = "Halo, ini pesan rahasia 123!".encode()
    blob = crypto.encrypt(pesan, "sandi-benar")
    assert crypto.decrypt(blob, "sandi-benar") == pesan


def test_2_dekripsi_sandi_salah_ditolak():
    blob = crypto.encrypt(b"rahasia", "sandi-benar")
    try:
        crypto.decrypt(blob, "sandi-salah")
        assert False, "seharusnya gagal"
    except crypto.DecryptionError:
        assert True


def test_3_sisip_lalu_ekstrak_utuh():
    img = _dummy_image()
    pesan = "Steganografi LSB + AES berhasil!"
    stego = core.embed(img, pesan, password="pw123", stego_key="key-abc")
    hasil = core.extract(stego, password="pw123", stego_key="key-abc")
    assert hasil.decode() == pesan


def test_4_stego_key_salah_gagal():
    img = _dummy_image()
    stego = core.embed(img, "rahasia", password="pw", stego_key="key-benar")
    gagal = False
    try:
        core.extract(stego, password="pw", stego_key="key-salah")
    except (core.ExtractionError, crypto.DecryptionError):
        gagal = True
    assert gagal, "stego-key salah seharusnya gagal ekstraksi"


def test_5_kapasitas_ditolak():
    img = _dummy_image(w=16, h=16)          
    pesan_besar = b"A" * 5000               
    ditolak = False
    try:
        core.embed(img, pesan_besar, password="pw", stego_key="key")
    except core.CapacityError:
        ditolak = True
    assert ditolak


def test_6_tamper_terdeteksi():
    img = _dummy_image()
    stego = core.embed(img, "pesan penting", password="pw", stego_key="key")
    rng = np.random.default_rng(1)
    flat = stego.reshape(-1)
    idx = rng.choice(flat.size, size=2000, replace=False)
    flat[idx] ^= 1
    rusak = False
    try:
        core.extract(stego, password="pw", stego_key="key")
    except (core.ExtractionError, crypto.DecryptionError):
        rusak = True
    assert rusak


def test_7_konversi_bit_byte():
    data = b"\x00\xFF\xA5\x01"
    assert bits_to_bytes(bytes_to_bits(data)) == data


def test_8_prng_reproducible():
    p1 = prng.permutation(1000, "key-A")
    p2 = prng.permutation(1000, "key-A")
    p3 = prng.permutation(1000, "key-B")
    assert p1 == p2
    assert p1 != p3
    assert sorted(p1) == list(range(1000))  


def test_9_psnr_citra_identik():
    img = _dummy_image()
    assert metrics.psnr(img, img) == float("inf")
    stego = core.embed(img, "uji psnr", password="pw", stego_key="key")
    assert metrics.psnr(img, stego) > 30.0


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    lulus = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
            lulus += 1
        except AssertionError as e:
            print(f"FAIL  {fn.__name__}: {e}")
        except Exception as e:
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{lulus}/{len(fns)} test lulus.")
