import numpy as np


def bytes_to_bits(data: bytes):
    bits = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def bits_to_bytes(bits) -> bytes:
    out = bytearray()
    for i in range(0, len(bits) - len(bits) % 8, 8):
        byte = 0
        for b in bits[i:i + 8]:
            byte = (byte << 1) | int(b)
        out.append(byte)
    return bytes(out)


def set_lsb(values: np.ndarray, positions, bits) -> None:

    positions = np.asarray(positions, dtype=np.int64)
    bits = np.asarray(bits, dtype=np.uint8)
    values[positions] = (values[positions] & 0xFE) | bits


def get_lsb(values: np.ndarray, positions) -> np.ndarray:
    positions = np.asarray(positions, dtype=np.int64)
    return (values[positions] & 1).astype(np.uint8)