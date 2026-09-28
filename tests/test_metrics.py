import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stego import core, metrics


def _dummy_image(w=128, h=128, seed=0):
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)


def test_psnr_citra_identik():
    """PSNR citra identik = tak hingga, MSE = 0."""
    img = _dummy_image()
    assert metrics.mse(img, img) == 0.0
    assert metrics.psnr(img, img) == float("inf")


def test_psnr_stego_tinggi():
    """PSNR citra stego harus tinggi (>30 dB, ambang materi kuliah)."""
    img = _dummy_image()
    stego = core.embed(img, "uji psnr", password="pw", stego_key="key")
    assert metrics.psnr(img, stego) > 30.0


def test_histogram_256_bin():
    """Histogram harus punya 256 bin dan total = jumlah seluruh sampel."""
    img = _dummy_image(32, 32)
    h = metrics.histogram(img)
    assert len(h) == 256
    assert int(h.sum()) == img.size


def test_lsb_plane_biner():
    """Bidang LSB hanya berisi nilai 0 atau 255."""
    img = _dummy_image(32, 32)
    plane = metrics.lsb_plane(img)
    assert set(np.unique(plane)).issubset({0, 255})


def test_perubahan_kanal_kecil():
    """Persentase kanal yang berubah setelah penyisipan pesan kecil harus rendah."""
    img = _dummy_image()
    stego = core.embed(img, "pesan pendek", password="pw", stego_key="key")
    assert metrics.changed_pixels_percent(img, stego) < 5.0


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    lulus = 0
    for fn in fns:
        try:
            fn(); print(f"PASS  {fn.__name__}"); lulus += 1
        except Exception as e:
            print(f"FAIL  {fn.__name__}: {e}")
    print(f"\n{lulus}/{len(fns)} test lulus.")