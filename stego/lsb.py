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
    dt = values.dtype
    keep = dt.type(np.iinfo(dt).max ^ 1)      # 0xFE (uint8) / 0xFFFE (uint16)
    values[positions] = (values[positions] & keep) | bits.astype(dt)


def get_lsb(values: np.ndarray, positions) -> np.ndarray:
    positions = np.asarray(positions, dtype=np.int64)
    return (values[positions] & 1).astype(np.uint8)

# ---------------------------------------------------------------------------
# Varian m-bit LSB (fitur pengayaan)
# Satu slot (1 byte kanal warna) menampung m bit, bukan 1 bit.
# m = 1 identik dengan LSB biasa di atas.
# ---------------------------------------------------------------------------
MAX_M = 6


def check_m(m: int) -> int:
    if not isinstance(m, (int, np.integer)) or not (1 <= int(m) <= MAX_M):
        raise ValueError(f"m (bit per slot) harus bilangan bulat 1..{MAX_M}.")
    return int(m)


def set_mbits(values: np.ndarray, positions, bits, m: int) -> None:
    """Tulis `bits` ke m bit terendah pada tiap posisi (m bit per slot).

    len(bits) tidak harus kelipatan m; sisa pada slot terakhir diisi 0.
    `values` harus bertipe unsigned (uint8 / uint16).
    """
    m = check_m(m)
    bits = np.asarray(bits, dtype=np.uint8)
    n_slots = -(-len(bits) // m)                       # ceil(len/m)
    padded = np.zeros(n_slots * m, dtype=np.uint8)
    padded[:len(bits)] = bits
    groups = padded.reshape(n_slots, m)
    weights = (1 << np.arange(m - 1, -1, -1)).astype(np.int64)   # MSB dulu
    chunk = (groups.astype(np.int64) * weights).sum(axis=1)      # nilai 0..2^m-1

    positions = np.asarray(positions[:n_slots], dtype=np.int64)
    dt = values.dtype
    full = np.iinfo(dt).max
    keep = dt.type(full ^ ((1 << m) - 1))
    values[positions] = (values[positions] & keep) | chunk.astype(dt)


def get_mbits(values: np.ndarray, positions, n_bits: int, m: int) -> np.ndarray:
    """Baca n_bits bit dari m bit terendah pada tiap posisi (urutan sama dgn set_mbits)."""
    m = check_m(m)
    n_slots = -(-n_bits // m)
    positions = np.asarray(positions[:n_slots], dtype=np.int64)
    chunk = (values[positions].astype(np.int64)) & ((1 << m) - 1)
    shifts = np.arange(m - 1, -1, -1)
    bits = ((chunk[:, None] >> shifts[None, :]) & 1).astype(np.uint8).reshape(-1)
    return bits[:n_bits]
