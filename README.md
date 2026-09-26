# StegoLSB — Aplikasi Steganografi LSB + AES

Aplikasi steganografi untuk **menyembunyikan pesan/berkas ke dalam citra digital**
memakai metode **LSB (Least Significant Bit)** yang ditulis sendiri, dengan pesan
**dienkripsi AES-256-GCM** terlebih dahulu sebelum disisipkan. Dibuat untuk Tugas
Proyek Aplikasi Kriptografi (Topik B — Steganografi), mata kuliah Keamanan Informasi.

## Anggota Kelompok
- Nama : Najmi Sabila Almusfiroh, NPM : 247006111125
- Nama : Muthia Febrahma Khoirunnisa, NPM : 247006111130
- Nama : Siti Qori'ah Muhafidloh, NPM : 247006111141

## Fitur

- Penyisipan & ekstraksi pesan dengan metode **LSB** pada citra **PNG/BMP** (lossless)
- **Header penanda panjang pesan** (magic `ST` + versi + panjang) agar ekstraksi berhenti tepat
- **Posisi bit diacak** memakai PRNG (LCG Fisher-Yates) dengan seed dari **stego-key**
- Pesan **dienkripsi AES-256-GCM**; kunci diturunkan dari kata sandi memakai **PBKDF2**
  (salt & nonce acak untuk setiap enkripsi)
- **Perhitungan kapasitas** citra dan **penolakan** pesan yang melebihi kapasitas
- Menolak ekstraksi bila **stego-key salah**, **kata sandi salah**, atau **citra telah diubah**
  (diverifikasi otomatis oleh tag AES-GCM)
- GUI (Tkinter) menampilkan **citra cover dan stego berdampingan** beserta nilai **PSNR**

## Struktur Proyek

```
StegoLSB/
├── stego/
│   ├── crypto.py      # AES-256-GCM + PBKDF2 (pustaka cryptography)
│   ├── prng.py        # LCG + Fisher-Yates untuk mengacak posisi (seed = stego-key)
│   ├── lsb.py         # logika LSB (konversi bit & baca/tulis LSB) — ditulis sendiri
│   ├── core.py        # alur penyisipan & ekstraksi (header + payload)
│   └── metrics.py     # PSNR, MSE, histogram, bidang LSB
├── gui.py             # aplikasi GUI (Tkinter)
├── run_experiments.py # skrip pengujian otomatis -> tabel & grafik di hasil_uji/
├── tests/test_stego.py# 9 unit test
├── sample_images/     # 5 citra uji
├── hasil_uji/         # hasil pengujian (XLSX, histogram, bidang LSB, dll)
├── requirements.txt
└── README.md
```

## Cara Instalasi

Butuh **Python 3.9+**.

```bash
# 1) (opsional) buat virtual environment
python -m venv venv
# Windows:  venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

# 2) install dependensi
pip install -r requirements.txt
```

Catatan: **Tkinter** dipakai oleh GUI. Pada Windows & macOS sudah termasuk bawaan
Python. Pada Linux, install bila belum ada: `sudo apt install python3-tk`.

## Cara Menjalankan

### Aplikasi GUI
```bash
python gui.py
```
1. Tab **Sisip Pesan**: pilih citra cover (PNG/BMP), ketik pesan atau pilih berkas,
   isi **Kata sandi** dan **Stego-key**, klik **SISIP & SIMPAN STEGO**. Citra cover
   dan stego tampil berdampingan beserta nilai PSNR.
2. Tab **Ekstrak Pesan**: pilih citra stego, isi kata sandi & stego-key yang sama,
   klik **EKSTRAK PESAN**.

### Menjalankan Pengujian (menghasilkan tabel & grafik untuk laporan)
```bash
python run_experiments.py
```
Hasil tersimpan di folder `hasil_uji/`:
- `hasil_psnr_mse.xlsx` — tabel PSNR & MSE (5 citra × 3 ukuran pesan) + uji kerapuhan JPEG
- `histogram_*.png` — perbandingan histogram cover vs stego
- `lsb_plane_*.png` — steganalisis visual (bidang LSB)
- `berdampingan_*.png` — citra cover vs stego

### Menjalankan Unit Test
```bash
python tests/test_stego.py
# atau
python -m pytest -v
```

## Contoh Penggunaan (tanpa GUI, lewat kode)

```python
from stego import core

# Sisip
cover, stego = core.embed_to_file(
    "sample_images/04_foto_sintetis.png", "stego.png",
    message="Pesan sangat rahasia",
    password="kata-sandi-ku", stego_key="kunci-posisi")

# Ekstrak
pesan = core.extract_from_file("stego.png",
    password="kata-sandi-ku", stego_key="kunci-posisi")
print(pesan.decode())   # -> Pesan sangat rahasia
```

## Cara Kerja Singkat

1. **Enkripsi** — pesan dienkripsi AES-256-GCM. Kunci diturunkan dari kata sandi
   dengan PBKDF2 + salt acak. Hasil: `salt(16) + nonce(12) + ciphertext + tag`.
2. **Header** — di depan payload ditambahkan header 7 byte:
   `'ST' + versi + panjang_payload(4 byte)` agar ekstraksi berhenti tepat dan
   stego-key salah dapat dideteksi.
3. **Pengacakan posisi** — seluruh slot LSB (setiap kanal R/G/B tiap pixel) diberi
   urutan acak memakai Fisher-Yates dengan PRNG (LCG) yang di-*seed* dari stego-key.
4. **Penyisipan** — bit header + payload ditulis ke LSB pada posisi acak tersebut.
5. **Ekstraksi** — dengan stego-key yang sama, urutan acak direproduksi, header dibaca
   untuk mengetahui panjang, payload dibaca, lalu didekripsi (tag GCM memverifikasi keaslian).

## Keamanan (sesuai ketentuan tugas)

- Tidak ada kunci/kata sandi yang ditulis di dalam kode sumber (dimasukkan saat runtime).
- Pembangkit acak aman kriptografis (`os.urandom`) untuk salt & nonce.
- Tidak memakai algoritma usang (MD5/SHA-1/DES/RC4) atau mode ECB.
- Metode LSB, header, dan pengacakan posisi ditulis sendiri.

## Batasan

- Metode LSB bersifat **fragile**: menyimpan ulang citra stego ke format **lossy**
  (mis. JPEG) akan merusak pesan (ditunjukkan pada uji kerapuhan). Gunakan PNG/BMP.