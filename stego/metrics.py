import numpy as np

def mse(cover: np.ndarray, stego: np.ndarray) -> float:
    a = cover.astype(np.float64)
    b = stego.astype(np.float64)
    return float(np.mean((a - b) ** 2))

def psnr(cover: np.ndarray, stego: np.ndarray, peak: float = 255.0) -> float:
    """PSNR (dB). peak = nilai maksimum sinyal (255 untuk citra 8-bit,
    32767 untuk audio PCM 16-bit)."""
    m = mse(cover, stego)
    if m == 0:
        return float("inf")
    return 10.0 * np.log10((peak ** 2) / m)


def snr(cover: np.ndarray, stego: np.ndarray) -> float:
    """Signal-to-Noise Ratio (dB) = 10 log10( sum(x^2) / sum((x-y)^2) ). Untuk audio."""
    a = cover.astype(np.float64)
    b = stego.astype(np.float64)
    noise = np.sum((a - b) ** 2)
    if noise == 0:
        return float("inf")
    return float(10.0 * np.log10(np.sum(a ** 2) / noise))

def histogram(arr: np.ndarray) -> np.ndarray:
    hist, _ = np.histogram(arr.reshape(-1), bins=256, range=(0, 255))
    return hist

def lsb_plane(arr: np.ndarray) -> np.ndarray:
    return ((arr & 1) * 255).astype(np.uint8)

def changed_pixels_percent(cover: np.ndarray, stego: np.ndarray) -> float:
    diff = (cover.astype(np.int16) != stego.astype(np.int16))
    return 100.0 * np.count_nonzero(diff) / cover.size
