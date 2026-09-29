"""Unit test fitur pengayaan: m-bit LSB, audio WAV, steganalisis chi-square."""
import os
import sys
import tempfile
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stego import core, crypto, metrics, audio, steganalysis
from stego.lsb import set_mbits, get_mbits

GAGAL = (core.ExtractionError, crypto.DecryptionError)


def _img(w=96, h=96, seed=0):
    return np.random.default_rng(seed).integers(0, 256, size=(h, w, 3), dtype=np.uint8)


def _smooth_img(n=128):
    """Citra halus (kuantisasi kasar + derau kecil): histogram pasangan (2i,2i+1)
    tidak setara, seperti cover alami yang belum disisipi."""
    y, x = np.mgrid[0:n, 0:n]
    ch = []
    for k in range(3):
        base = 128 + 60 * np.sin(x / 9.0) * np.cos(y / 13.0) + (x + y) / 4.0 + k * 7
        base = np.round(base / 3) * 3 + np.random.default_rng(k).normal(0, 1, base.shape)
        ch.append(np.clip(base, 0, 255))
    return np.stack(ch, axis=2).astype(np.uint8)


def _wav(path, width=2, channels=1, n=8000, rate=8000):
    t = np.arange(n * channels) / rate
    x = np.sin(2 * np.pi * 300 * t) * 0.6
    raw = ((x * 32767).astype("<i2").tobytes() if width == 2
           else ((x * 127) + 128).astype(np.uint8).tobytes())
    with wave.open(path, "wb") as w:
        w.setnchannels(channels); w.setsampwidth(width)
        w.setframerate(rate); w.writeframes(raw)


# ---------------- m-bit LSB ----------------
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


# ---------------- audio WAV ----------------
def test_audio_16bit_stereo_utuh():
    with tempfile.TemporaryDirectory() as d:
        a, b = os.path.join(d, "a.wav"), os.path.join(d, "b.wav")
        _wav(a, width=2, channels=2)
        audio.embed_to_file(a, b, "rahasia audio", "pw", "key", m=2)
        assert audio.extract_from_file(b, "pw", "key") == b"rahasia audio"


def test_audio_8bit_utuh_dan_kunci_salah():
    with tempfile.TemporaryDirectory() as d:
        a, b = os.path.join(d, "a.wav"), os.path.join(d, "b.wav")
        _wav(a, width=1, channels=1)
        audio.embed_to_file(a, b, "pesan 8-bit", "pw", "key", m=1)
        assert audio.extract_from_file(b, "pw", "key") == b"pesan 8-bit"
        try:
            audio.extract_from_file(b, "pw", "key-salah")
            assert False
        except GAGAL:
            pass


def test_audio_byte_atas_sampel_16bit_tidak_rusak():
    """Regresi: penulisan header tidak boleh menghapus byte atas sampel 16-bit."""
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "a.wav")
        _wav(a, width=2)
        x, prm = audio.load_wav(a)
        st = audio.embed(x, b"halo", "pw", "key", 1)
        selisih = np.abs(audio.to_signed(x, 2) - audio.to_signed(st, 2))
        assert selisih.max() <= 1
        assert metrics.snr(audio.to_signed(x, 2), audio.to_signed(st, 2)) > 60


def test_audio_kapasitas_ditolak_dan_format_salah():
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "a.wav")
        _wav(a, n=500)
        x, _ = audio.load_wav(a)
        try:
            audio.embed(x, b"B" * 5000, "pw", "key")
            assert False
        except core.CapacityError:
            pass
        bukan_wav = os.path.join(d, "x.wav")
        open(bukan_wav, "wb").write(b"bukan wav")
        try:
            audio.load_wav(bukan_wav)
            assert False
        except audio.AudioFormatError:
            pass


# ---------------- chi-square ----------------
def test_chi2_sf_nilai_baku():
    # nilai tabel chi-square: P(X >= 3.841 | df=1) = 0.05 ; P(X >= 18.307 | df=10) = 0.05
    assert abs(steganalysis.chi2_sf(3.841, 1) - 0.05) < 1e-3
    assert abs(steganalysis.chi2_sf(18.307, 10) - 0.05) < 1e-3
    assert steganalysis.chi2_sf(0.0, 5) == 1.0
    assert steganalysis.chi2_sf(1000.0, 5) < 1e-100


def test_chi2_cover_alami_tidak_terdeteksi():
    r = steganalysis.analyze(_smooth_img())
    assert r["flagged"] is False and r["p_value"] < 0.05


def test_chi2_stego_penuh_terdeteksi():
    img = _smooth_img(128)
    pesan = os.urandom(core.capacity_bytes(img) - 44)
    st = core.embed(img, pesan, "pw", "key", 1)
    r = steganalysis.analyze(st)
    assert r["flagged"] is True and r["p_value"] > 0.05


def test_chi2_selisih_pasangan_mengecil_setelah_sisip():
    img = _smooth_img(128)
    st = core.embed(img, os.urandom(core.capacity_bytes(img) - 44), "pw", "key", 1)
    sebelum = np.abs(steganalysis.pair_difference(img)).sum()
    sesudah = np.abs(steganalysis.pair_difference(st)).sum()
    assert sesudah < 0.5 * sebelum


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    lulus = 0
    for fn in fns:
        try:
            fn(); print(f"PASS  {fn.__name__}"); lulus += 1
        except Exception as e:
            print(f"FAIL  {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{lulus}/{len(fns)} test lulus.")
