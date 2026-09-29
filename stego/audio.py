"""Steganografi LSB pada audio WAV (PCM 8-bit / 16-bit) -- fitur pengayaan.

Logika penyisipan/ekstraksi memakai inti yang sama dengan citra
(core.embed_flat / core.extract_flat): pesan dienkripsi AES-256-GCM, header
penanda panjang, posisi sampel diacak dengan PRNG berseed stego-key, dan
varian m-bit LSB. Yang berbeda hanya "cover"-nya: sampel audio, bukan pixel.
"""
import wave

import numpy as np

from . import core


class AudioFormatError(Exception):
    """Berkas WAV tidak didukung (hanya PCM 8/16-bit)."""
    pass


def load_wav(path: str):
    """Baca WAV PCM -> (samples 1-D unsigned, params).

    8-bit  : uint8 (WAV 8-bit memang unsigned).
    16-bit : int16 little-endian, disimpan sebagai uint16 (tampilan bit yang sama)
             supaya operasi bit murni; dikembalikan ke int16 lewat to_signed().
    Sampel multi-kanal disimpan interleaved (L,R,L,R,...).
    """
    try:
        with wave.open(path, "rb") as w:
            nch, width, rate, nframes, comptype, _ = w.getparams()
            raw = w.readframes(nframes)
    except wave.Error as e:
        raise AudioFormatError(f"Bukan WAV PCM yang valid: {e}")
    if comptype != "NONE":
        raise AudioFormatError("WAV terkompresi tidak didukung (harus PCM).")
    if width == 1:
        samples = np.frombuffer(raw, dtype=np.uint8).copy()
    elif width == 2:
        samples = np.frombuffer(raw, dtype="<u2").astype(np.uint16)
    else:
        raise AudioFormatError(f"Lebar sampel {8 * width}-bit belum didukung (pakai 8 atau 16-bit).")
    params = {"channels": nch, "width": width, "rate": rate, "frames": nframes}
    return samples, params


def save_wav(path: str, samples: np.ndarray, params: dict) -> None:
    if params["width"] == 1:
        raw = samples.astype(np.uint8).tobytes()
    else:
        raw = samples.astype("<u2").tobytes()
    with wave.open(path, "wb") as w:
        w.setnchannels(params["channels"])
        w.setsampwidth(params["width"])
        w.setframerate(params["rate"])
        w.writeframes(raw)


def to_signed(samples: np.ndarray, width: int) -> np.ndarray:
    """Nilai sampel bertanda (untuk metrik SNR/PSNR)."""
    if width == 2:
        return samples.astype(np.uint16).view(np.int16).astype(np.int64)
    return samples.astype(np.int64) - 128


def peak_value(width: int) -> float:
    """Nilai puncak untuk PSNR: 2^(bit-1)-1 (16-bit) atau 255 (8-bit unsigned)."""
    return 32767.0 if width == 2 else 255.0


def capacity_bytes(samples: np.ndarray, m: int = 1) -> int:
    return core.capacity_bytes(samples, m)


def embed(samples: np.ndarray, message, password: str, stego_key: str, m: int = 1):
    return core.embed_flat(samples, message, password, stego_key, m)


def extract(samples: np.ndarray, password: str, stego_key: str) -> bytes:
    return core.extract_flat(samples, password, stego_key)


def embed_to_file(cover_path, out_path, message, password, stego_key, m=1):
    samples, params = load_wav(cover_path)
    stego = embed(samples, message, password, stego_key, m)
    save_wav(out_path, stego, params)
    return samples, stego, params


def extract_from_file(stego_path, password, stego_key) -> bytes:
    samples, _ = load_wav(stego_path)
    return extract(samples, password, stego_key)
