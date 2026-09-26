import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stego import crypto, prng

def test_enkripsi_dekripsi_benar():
    pesan = "Halo, ini pesan rahasia 123!".encode()
    blob = crypto.encrypt(pesan, "sandi-benar")
    assert crypto.decrypt(blob, "sandi-benar") == pesan

def test_dekripsi_sandi_salah_ditolak():
    blob = crypto.encrypt(b"rahasia", "sandi-benar")
    try:
        crypto.decrypt(blob, "sandi-salah")
        assert False, "seharusnya gagal"
    except crypto.DecryptionError:
        assert True

def test_ciphertext_selalu_berbeda():
    a = crypto.encrypt(b"pesan sama", "pw")
    b = crypto.encrypt(b"pesan sama", "pw")
    assert a != b

def test_prng_reproducible():
    p1 = prng.permutation(1000, "key-A")
    p2 = prng.permutation(1000, "key-A")
    p3 = prng.permutation(1000, "key-B")
    assert p1 == p2
    assert p1 != p3

def test_prng_permutasi_valid():
    p = prng.permutation(500, "kunci")
    assert sorted(p) == list(range(500))

if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    lulus = 0
    for fn in fns:
        try:
            fn(); print(f"PASS  {fn.__name__}"); lulus += 1
        except Exception as e:
            print(f"FAIL  {fn.__name__}: {e}")
    print(f"\n{lulus}/{len(fns)} test lulus.")
