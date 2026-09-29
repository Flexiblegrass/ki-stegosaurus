"""Unit test varian m-bit LSB (fitur pengayaan)."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stego import core, crypto, metrics
from stego.lsb import set_mbits, get_mbits

GAGAL = (core.ExtractionError, crypto.DecryptionError)


def _img(w=96, h=96, seed=0):
    return np.random.default_rng(seed).integers(0, 256, size=(h, w, 3), dtype=np.uint8)


def test_mbit_sisip_ekstrak_semua_m():
    img = _img()
    for m in range(1, 7):
        pesan = f"pesan uji m={m}".encode()
        st = core.embed(img, pesan, "pw", "key", m)
        assert core.extract(st, "pw", "key") == pesan     # m dibaca dari header


def test_mbit_kapasitas_naik_sebanding_m():
    img = _img()
    c1 = core.capacity_bytes(img, 1)
    assert core.capacity_bytes(img, 3) > 2.9 * c1
    assert core.capacity_bytes(img, 4) == ((img.size - core.HEADER_BITS) * 4) // 8


def test_mbit_perubahan_pixel_dibatasi_2pangkat_m():
    img = _img()
    st = core.embed(img, b"x" * 500, "pw", "key", 3)
    assert np.abs(img.astype(int) - st.astype(int)).max() < 2 ** 3


def test_mbit_psnr_turun_saat_m_naik():
    img = _img(128, 128)
    pesan = os.urandom(1500)
    p = [metrics.psnr(img, core.embed(img, pesan, "pw", "key", m)) for m in (1, 2, 3, 4)]
    assert p[0] > p[1] > p[2] > p[3]
    assert p[3] > 30.0            # m=4 masih di atas ambang materi kuliah


def test_mbit_m_tidak_valid_ditolak():
    for m in (0, 7, -1):
        try:
            core.embed(_img(), b"a", "pw", "key", m)
            assert False, "seharusnya ValueError"
        except ValueError:
            pass


def test_mbit_kapasitas_ditolak_dan_kunci_salah():
    img = _img(16, 16)
    try:
        core.embed(img, b"A" * 5000, "pw", "key", 2)
        assert False
    except core.CapacityError:
        pass
    st = core.embed(_img(), b"rahasia", "pw", "key-benar", 4)
    try:
        core.extract(st, "pw", "key-salah")
        assert False
    except GAGAL:
        pass


def test_mbit_set_get_bolak_balik_uint16():
    rng = np.random.default_rng(0)
    v = rng.integers(0, 65535, 500, dtype=np.uint16)
    asli = v.copy()
    bits = rng.integers(0, 2, 101, dtype=np.uint8)
    pos = rng.permutation(500)
    set_mbits(v, pos, bits, 3)
    assert (get_mbits(v, pos, 101, 3) == bits).all()
    assert (np.abs(v.astype(int) - asli.astype(int)) < 8).all()




if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    lulus = 0
    for fn in fns:
        try:
            fn(); print(f"PASS  {fn.__name__}"); lulus += 1
        except Exception as e:
            print(f"FAIL  {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{lulus}/{len(fns)} test lulus.")
