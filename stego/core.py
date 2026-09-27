import numpy as np
from PIL import Image

from . import crypto
from . import prng
from .lsb import bytes_to_bits, bits_to_bytes, set_lsb, get_lsb

MAGIC = b"ST"
VERSION = 1
HEADER_LEN = 7                 # byte
HEADER_BITS = HEADER_LEN * 8   # 56 bit


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


def capacity_bytes(arr: np.ndarray) -> int:
    """
    Kapasitas maksimum PAYLOAD (byte) untuk citra ini.
    Total slot = jumlah seluruh kanal warna. Dikurangi header, lalu /8.
    """
    total_slots = arr.size          # H*W*3
    return (total_slots - HEADER_BITS) // 8


def _build_stream(payload: bytes) -> list:
    header = MAGIC + bytes([VERSION]) + len(payload).to_bytes(4, "big")
    return bytes_to_bits(header + payload)


def embed(cover: np.ndarray, message: bytes, password: str, stego_key: str) -> np.ndarray:
    """
    Sisipkan `message` (bytes) ke dalam citra `cover`.
    Langkah: enkripsi AES -> susun header+payload -> acak posisi -> tulis LSB.
    Mengembalikan citra stego (array baru).
    """
    if isinstance(message, str):
        message = message.encode("utf-8")

    # 1) enkripsi pesan
    payload = crypto.encrypt(message, password)

    # 2) cek kapasitas
    cap = capacity_bytes(cover)
    if len(payload) > cap:
        raise CapacityError(
            f"Pesan terlalu besar. Kapasitas citra {cap} byte, "
            f"payload terenkripsi {len(payload)} byte."
        )

    # 3) susun aliran bit (header + payload)
    bits = _build_stream(payload)

    # 4) acak urutan slot berdasarkan stego-key, ambil sebanyak jumlah bit
    flat = cover.reshape(-1).copy()
    perm = prng.permutation(flat.size, stego_key)
    positions = perm[:len(bits)]

    # 5) tulis ke LSB
    set_lsb(flat, positions, bits)
    return flat.reshape(cover.shape)


def extract(stego: np.ndarray, password: str, stego_key: str) -> bytes:
    """
    Ekstrak dan dekripsi pesan dari citra `stego`.
    Melempar ExtractionError bila stego-key salah, atau crypto.DecryptionError
    bila kata sandi salah / data berubah.
    """
    flat = stego.reshape(-1)
    perm = prng.permutation(flat.size, stego_key)

    # 1) baca header dulu (56 bit pertama pada urutan acak)
    header_bits = get_lsb(flat, perm[:HEADER_BITS])
    header = bits_to_bytes(header_bits)
    if header[:2] != MAGIC:
        raise ExtractionError(
            "Stego-key salah atau citra tidak berisi pesan (penanda tidak cocok)."
        )
    payload_len = int.from_bytes(header[3:7], "big")

    # sanity check panjang payload
    max_payload = (flat.size - HEADER_BITS) // 8
    if payload_len <= 0 or payload_len > max_payload:
        raise ExtractionError("Panjang payload tidak valid (stego-key salah?).")

    # 2) baca payload
    nbits = payload_len * 8
    payload_bits = get_lsb(flat, perm[HEADER_BITS:HEADER_BITS + nbits])
    payload = bits_to_bytes(payload_bits)

    # 3) dekripsi (AES-GCM memverifikasi keaslian)
    return crypto.decrypt(payload, password)


# ---- fungsi bantu berbasis path (dipakai GUI) ----

def embed_to_file(cover_path, out_path, message, password, stego_key):
    cover = load_image_rgb(cover_path)
    stego = embed(cover, message, password, stego_key)
    save_image(stego, out_path)
    return cover, stego


def extract_from_file(stego_path, password, stego_key):
    stego = load_image_rgb(stego_path)
    return extract(stego, password, stego_key)
