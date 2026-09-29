"""Steganalisis statistik: uji chi-square (Westfeld & Pfitzmann, 1999) -- fitur pengayaan.

Ide: LSB replacement dengan bit acak (hasil enkripsi) "menyamakan" frekuensi
tiap pasangan nilai (2i, 2i+1) pada histogram. Pada citra alami frekuensi kedua
anggota pasangan biasanya berbeda; setelah disisipi (rate tinggi) keduanya
mendekati sama.

    E_i = (h[2i] + h[2i+1]) / 2          (frekuensi harapan bila disisipi)
    chi2 = sum_i (h[2i] - E_i)^2 / E_i   (df = jumlah pasangan terpakai - 1)
    p    = P(X >= chi2), X ~ chi-square(df)

p kecil (~0)  -> histogram TIDAK setara     -> kemungkinan cover bersih
p besar (~1)  -> histogram sangat setara    -> kemungkinan ada penyisipan

Fungsi survival chi-square ditulis sendiri (gamma tak-lengkap teregularisasi,
Numerical Recipes) sehingga tidak butuh SciPy.
"""
import math

import numpy as np

_EPS = 3e-16
_MAX_ITER = 500


def _gamma_series(a: float, x: float) -> float:
    """P(a, x) lewat deret (efisien untuk x < a + 1)."""
    ap, total, delta = a, 1.0 / a, 1.0 / a
    for _ in range(_MAX_ITER):
        ap += 1.0
        delta *= x / ap
        total += delta
        if abs(delta) < abs(total) * _EPS:
            break
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gamma_cf(a: float, x: float) -> float:
    """Q(a, x) lewat pecahan berlanjut (efisien untuk x >= a + 1)."""
    tiny = 1e-300
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, _MAX_ITER):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < _EPS:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def gammaincc(a: float, x: float) -> float:
    """Q(a, x) = gamma tak-lengkap atas teregularisasi."""
    if x <= 0:
        return 1.0
    if x < a + 1.0:
        return 1.0 - _gamma_series(a, x)
    return _gamma_cf(a, x)


def chi2_sf(chi2: float, df: int) -> float:
    """P(X >= chi2) untuk X ~ chi-square dengan derajat bebas df."""
    if df <= 0:
        return float("nan")
    return float(min(1.0, max(0.0, gammaincc(df / 2.0, chi2 / 2.0))))


def pov_histogram(values: np.ndarray, levels: int = 256) -> np.ndarray:
    """Histogram nilai (0..levels-1) dari larik unsigned."""
    return np.bincount(values.reshape(-1).astype(np.int64), minlength=levels)[:levels]


def chi_square_pov(hist: np.ndarray, min_expected: float = 5.0):
    """Hitung statistik chi-square 'pairs of values' dari sebuah histogram.

    Pasangan dengan frekuensi harapan < min_expected dibuang (syarat validitas
    uji chi-square). Return (chi2, df, p_embedding).
    """
    h = np.asarray(hist, dtype=np.float64)
    if h.size % 2:
        h = h[:-1]
    even, odd = h[0::2], h[1::2]
    expected = (even + odd) / 2.0
    use = expected >= min_expected
    n_used = int(use.sum())
    if n_used < 2:
        return 0.0, 0, float("nan")
    chi2 = float(np.sum((even[use] - expected[use]) ** 2 / expected[use]))
    df = n_used - 1
    return chi2, df, chi2_sf(chi2, df)


def analyze(values: np.ndarray, levels: int = 256, alpha: float = 0.05) -> dict:
    """Uji chi-square pada seluruh larik nilai (byte citra / sampel 8-bit).

    Keputusan: p > alpha  ->  'terindikasi ada penyisipan'.
    (Pada cover alami p ~ 0; pada stego dengan laju sisip tinggi p menyebar 0..1.)
    """
    hist = pov_histogram(values, levels)
    chi2, df, p = chi_square_pov(hist)
    if df == 0:
        verdict = "tidak dapat diuji (data terlalu sedikit/homogen)"
        flagged = None
    else:
        flagged = bool(p > alpha)
        verdict = ("TERINDIKASI ada penyisipan (histogram pasangan menyamarata)"
                   if flagged else "tidak terindikasi penyisipan")
    return {"chi2": chi2, "df": df, "p_value": p, "flagged": flagged,
            "verdict": verdict, "alpha": alpha}


def analyze_image(arr: np.ndarray, alpha: float = 0.05) -> dict:
    """Uji chi-square pada citra RGB: gabungan + per kanal (R, G, B)."""
    res = {"gabungan": analyze(arr, alpha=alpha)}
    if arr.ndim == 3:
        for i, name in enumerate("RGB"[:arr.shape[2]]):
            res[name] = analyze(arr[:, :, i], alpha=alpha)
    return res


def pair_difference(values: np.ndarray, levels: int = 256) -> np.ndarray:
    """d_i = h[2i] - h[2i+1]; mendekati 0 untuk semua i bila histogram disamaratakan."""
    h = pov_histogram(values, levels).astype(np.int64)
    return h[0::2] - h[1::2]
