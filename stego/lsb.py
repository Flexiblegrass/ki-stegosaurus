"""
Logika inti LSB (Least Significant Bit) -- DITULIS SENDIRI.

Prinsip: setiap byte kanal warna (R/G/B) sebuah pixel punya 1 bit paling tidak
signifikan (LSB). Bit itu diganti dengan 1 bit pesan. Perubahan nilai warna
maksimal hanya 1 tingkat, sehingga tidak terlihat oleh mata.

Modul ini hanya berurusan dengan konversi byte<->bit dan penulisan/pembacaan
bit LSB pada array. Pengacakan posisi ada di prng.py, enkripsi ada di crypto.py.
"""

import numpy as np


def bytes_to_bits(data: bytes):
    """Ubah byte string menjadi list bit (MSB first per byte)."""
    bits = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def bits_to_bytes(bits) -> bytes:
    """Ubah list/urutan bit (kelipatan 8, MSB first) kembali menjadi bytes."""
    out = bytearray()
    for i in range(0, len(bits) - len(bits) % 8, 8):
        byte = 0
        for b in bits[i:i + 8]:
            byte = (byte << 1) | int(b)
        out.append(byte)
    return bytes(out)


def set_lsb(values: np.ndarray, positions, bits) -> None:
    """
    Tulis `bits` ke LSB dari `values` pada indeks `positions` (in-place).
    values : array 1 dimensi uint8 (hasil flatten citra)
    Operasi: hapus LSB lama (AND 0xFE) lalu OR dengan bit baru.
    """
    positions = np.asarray(positions, dtype=np.int64)
    bits = np.asarray(bits, dtype=np.uint8)
    values[positions] = (values[positions] & 0xFE) | bits


def get_lsb(values: np.ndarray, positions) -> np.ndarray:
    """Baca LSB dari `values` pada indeks `positions`. Kembalikan array bit."""
    positions = np.asarray(positions, dtype=np.int64)
    return (values[positions] & 1).astype(np.uint8)