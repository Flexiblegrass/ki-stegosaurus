import numpy as np

def mse(cover: np.ndarray, stego: np.ndarray) -> float:
    a = cover.astype(np.float64)
    b = stego.astype(np.float64)
    return float(np.mean((a - b) ** 2))

def psnr(cover: np.ndarray, stego: np.ndarray) -> float:
    m = mse(cover, stego)
    if m == 0:
        return float("inf")
    return 10.0 * np.log10((255.0 ** 2) / m)

def histogram(arr: np.ndarray) -> np.ndarray:
    hist, _ = np.histogram(arr.reshape(-1), bins=256, range=(0, 255))
    return hist

def lsb_plane(arr: np.ndarray) -> np.ndarray:
    return ((arr & 1) * 255).astype(np.uint8)

def changed_pixels_percent(cover: np.ndarray, stego: np.ndarray) -> float:
    diff = (cover.astype(np.int16) != stego.astype(np.int16))
    return 100.0 * np.count_nonzero(diff) / cover.size
