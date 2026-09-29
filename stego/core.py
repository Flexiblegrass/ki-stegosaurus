import numpy as np
from PIL import Image

from . import crypto
from . import prng
from .lsb import (bytes_to_bits, bits_to_bytes, set_lsb, get_lsb,
                  set_mbits, get_mbits, check_m, MAX_M)

MAGIC = b"ST"
# Byte ke-3 header menyimpan m (jumlah bit per slot). m = 1 sama dengan
# "VERSION = 1" pada versi awal, sehingga stego lama tetap bisa diekstrak.
VERSION = 1
HEADER_LEN = 7                 # byte
HEADER_BITS = HEADER_LEN * 8   # 56 bit (selalu ditulis 1-bit LSB)


class CapacityError(Exception):
    """Pesan melebihi kapasitas citra."""
    pass


class ExtractionError(Exception):
    """Ekstraksi gagal (stego-key salah / bukan citra stego)."""
    pass


def load_image_rgb(path: str) -> np.ndarray:
    """Muat citra sebagai array RGB uint8 (H x W x 3)."""
    img = Image.open(path).convert("RGB")
    return np.array(img, dtype=np.uint8)


def save_image(arr: np.ndarray, path: str) -> None:
    """Simpan array RGB uint8 sebagai citra (PNG/BMP -> lossless)."""
    Image.fromarray(arr.astype(np.uint8), "RGB").save(path)


def capacity_bytes(arr: np.ndarray, m: int = 1) -> int:
    """Kapasitas payload (byte) bila tiap slot menampung m bit."""
    m = check_m(m)
    total_slots = arr.size          # H*W*3
    return ((total_slots - HEADER_BITS) * m) // 8


def _build_stream(payload: bytes, m: int = 1) -> list:
    header = MAGIC + bytes([m]) + len(payload).to_bytes(4, "big")
    return bytes_to_bits(header + payload)


def embed_flat(flat: np.ndarray, message: bytes, password: str,
               stego_key: str, m: int = 1) -> np.ndarray:
    """Inti penyisipan pada larik 1-D unsigned (byte kanal citra).

    Mengembalikan salinan `flat` yang sudah disisipi. Dipakai bersama oleh
    core.embed.
    """
    m = check_m(m)
    if isinstance(message, str):
        message = message.encode("utf-8")

    # 1) enkripsi pesan
    payload = crypto.encrypt(message, password)

    # 2) cek kapasitas
    cap = capacity_bytes(flat, m)
    if len(payload) > cap:
        raise CapacityError(
            f"Pesan terlalu besar. Kapasitas {cap} byte (m={m}), "
            f"payload terenkripsi {len(payload)} byte."
        )

    # 3) susun aliran bit (header + payload)
    bits = np.asarray(_build_stream(payload, m), dtype=np.uint8)

    # 4) acak urutan slot berdasarkan stego-key
    out = flat.copy()
    perm = prng.permutation(out.size, stego_key)

    # 5) header: 1-bit LSB pada 56 slot pertama; payload: m bit/slot sesudahnya
    set_lsb(out, perm[:HEADER_BITS], bits[:HEADER_BITS])
    set_mbits(out, perm[HEADER_BITS:], bits[HEADER_BITS:], m)
    return out


def extract_flat(flat: np.ndarray, password: str, stego_key: str) -> bytes:
    perm = prng.permutation(flat.size, stego_key)

    # 1) baca header dulu (56 bit pertama pada urutan acak)
    header_bits = get_lsb(flat, perm[:HEADER_BITS])
    header = bits_to_bytes(header_bits)
    if header[:2] != MAGIC:
        raise ExtractionError(
            "Stego-key salah atau citra tidak berisi pesan (penanda tidak cocok)."
        )
    m = header[2]
    if not (1 <= m <= MAX_M):
        raise ExtractionError("Parameter m pada header tidak valid (stego-key salah?).")
    payload_len = int.from_bytes(header[3:7], "big")

    # sanity check panjang payload
    max_payload = capacity_bytes(flat, m)
    if payload_len <= 0 or payload_len > max_payload:
        raise ExtractionError("Panjang payload tidak valid (stego-key salah?).")

    # 2) baca payload
    payload_bits = get_mbits(flat, perm[HEADER_BITS:], payload_len * 8, m)
    payload = bits_to_bytes(payload_bits)

    # 3) dekripsi (AES-GCM memverifikasi keaslian)
    return crypto.decrypt(payload, password)


def embed(cover: np.ndarray, message: bytes, password: str, stego_key: str,
          m: int = 1) -> np.ndarray:
    """Sisipkan pesan ke citra RGB (H x W x 3). m = bit per kanal (1..6)."""
    flat = np.ascontiguousarray(cover, dtype=np.uint8).reshape(-1)
    return embed_flat(flat, message, password, stego_key, m).reshape(cover.shape)


def extract(stego: np.ndarray, password: str, stego_key: str) -> bytes:
    """Ekstrak pesan; nilai m dibaca otomatis dari header."""
    flat = np.ascontiguousarray(stego, dtype=np.uint8).reshape(-1)
    return extract_flat(flat, password, stego_key)


# fungsi bantu berbasis path (dipakai GUI) 

def embed_to_file(cover_path, out_path, message, password, stego_key, m=1):
    cover = load_image_rgb(cover_path)
    stego = embed(cover, message, password, stego_key, m)
    save_image(stego, out_path)
    return cover, stego


def extract_from_file(stego_path, password, stego_key):
    stego = load_image_rgb(stego_path)
    return extract(stego, password, stego_key)
