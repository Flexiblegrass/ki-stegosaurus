# StegoLSB

### Aplikasi Steganografi LSB + AES

StegoLSB adalah aplikasi steganografi yang digunakan untuk menyembunyikan pesan atau berkas ke dalam citra digital.

Aplikasi ini menggunakan metode **LSB (Least Significant Bit)** yang dibuat sendiri. Sebelum disisipkan ke dalam citra, pesan terlebih dahulu dienkripsi menggunakan **AES-256-GCM** sehingga isi pesan tidak bisa langsung dibaca meskipun berhasil diekstraksi.

Aplikasi ini dibuat untuk memenuhi Tugas Proyek Aplikasi Kriptografi dengan topik **Steganografi** pada mata kuliah Keamanan Informasi.

## Anggota Kelompok

**Najmi Sabila Almusfiroh**
NPM: 247006111125

**Muthia Febrahma Khoirunnisa**
NPM: 247006111130

**Siti Qori'ah Muhafidloh**
NPM: 247006111141

## Fitur

StegoLSB memiliki beberapa fitur utama, yaitu:

1. Menyisipkan dan mengekstraksi pesan menggunakan metode LSB pada citra PNG dan BMP.
2. Menggunakan header untuk menyimpan informasi panjang pesan sehingga proses ekstraksi dapat berhenti pada bagian yang tepat.
3. Mengacak posisi bit menggunakan PRNG LCG dengan algoritma Fisher-Yates. Seed berasal dari stego-key yang dimasukkan pengguna.
4. Mengenkripsi pesan menggunakan AES-256-GCM sebelum pesan disisipkan.
5. Menggunakan PBKDF2 untuk menurunkan kunci dari kata sandi.
6. Menggunakan salt dan nonce acak pada setiap proses enkripsi.
7. Menghitung kapasitas citra dan menolak pesan jika ukurannya melebihi kapasitas yang tersedia.
8. Menolak proses ekstraksi jika stego-key atau kata sandi yang digunakan tidak sesuai.
9. Mendeteksi perubahan pada citra melalui verifikasi tag AES-GCM.
10. Menampilkan citra cover dan citra stego secara berdampingan pada GUI, lengkap dengan nilai PSNR.

## Struktur Proyek

```text
StegoLSB/
├── stego/
│   ├── crypto.py          # AES-256-GCM + PBKDF2
│   ├── prng.py            # LCG + Fisher-Yates untuk mengacak posisi
│   ├── lsb.py             # Logika konversi bit dan LSB
│   ├── core.py            # Proses penyisipan dan ekstraksi
│   └── metrics.py         # PSNR, MSE, histogram, dan bidang LSB
├── gui.py                 # Aplikasi GUI menggunakan Tkinter
├── run_experiments.py     # Pengujian otomatis dan pembuatan hasil
├── tests/
│   └── test_stego.py      # Unit test
├── sample_images/         # Citra yang digunakan untuk pengujian
├── hasil_uji/             # Hasil pengujian
├── requirements.txt
└── README.md
```

## Instalasi

StegoLSB membutuhkan **Python 3.9 atau lebih baru**.
```bash
python -m venv venv
```

Untuk Windows:
```bash
venv\Scripts\activate
```

Untuk Linux atau macOS:
```bash
source venv/bin/activate
```

Setelah itu, install semua library yang dibutuhkan:
```bash
pip install -r requirements.txt
```

StegoLSB menggunakan Tkinter untuk tampilan GUI. Pada Windows dan macOS, Tkinter biasanya sudah tersedia bersama Python.
Jika menggunakan Linux dan Tkinter belum tersedia, install dengan:
```bash
sudo apt install python3-tk
```

## Menjalankan Aplikasi

### GUI
Jalankan perintah berikut:
```bash
python gui.py
```

Setelah aplikasi terbuka, terdapat dua bagian utama.
**Sisip Pesan**
Pilih citra cover dalam format PNG atau BMP, kemudian masukkan pesan atau pilih berkas yang ingin disembunyikan.
Masukkan juga kata sandi dan stego-key. Setelah itu klik tombol **SISIP & SIMPAN STEGO**.
Aplikasi akan membuat citra stego dan menampilkan citra cover serta stego secara berdampingan. Nilai PSNR juga ditampilkan untuk melihat perubahan kualitas citra setelah proses penyisipan.

**Ekstrak Pesan**
Pilih citra stego yang sudah dibuat sebelumnya, kemudian masukkan kata sandi dan stego-key yang digunakan saat proses penyisipan.
Klik **EKSTRAK PESAN** untuk mengambil kembali pesan yang tersimpan di dalam citra.

## Pengujian
Untuk menjalankan pengujian otomatis, gunakan:
```bash
python run_experiments.py
```

Hasil pengujian akan disimpan di folder `hasil_uji/`.
Beberapa hasil yang dihasilkan antara lain:
`hasil_psnr_mse.xlsx` berisi tabel PSNR dan MSE dari 5 citra dengan 3 ukuran pesan yang berbeda, termasuk hasil uji kerapuhan terhadap JPEG.
`histogram_*.png` digunakan untuk membandingkan histogram citra cover dan citra stego.
`lsb_plane_*.png` digunakan untuk melihat perbandingan bidang LSB pada citra cover dan stego.
`berdampingan_*.png` menampilkan citra cover dan stego secara berdampingan.

## Unit Test

Unit test dapat dijalankan dengan:
```bash
python tests/test_stego.py
```

atau menggunakan pytest:
```bash
python -m pytest -v
```

## Contoh Penggunaan Tanpa GUI
StegoLSB juga dapat digunakan langsung melalui kode Python.
```python
from stego import core

# Sisip pesan
cover, stego = core.embed_to_file(
    "sample_images/04_foto_sintetis.png",
    "stego.png",
    message="Pesan sangat rahasia",
    password="kata-sandi-ku",
    stego_key="kunci-posisi"
)

# Ekstrak pesan
pesan = core.extract_from_file(
    "stego.png",
    password="kata-sandi-ku",
    stego_key="kunci-posisi"
)

print(pesan.decode())
# Output: Pesan sangat rahasia
```

## Cara Kerja

Proses kerja StegoLSB secara umum terdiri dari beberapa tahap.

**1. Enkripsi pesan**
Pesan terlebih dahulu dienkripsi menggunakan AES-256-GCM. Kunci enkripsi diperoleh dari kata sandi menggunakan PBKDF2.
Setiap proses enkripsi menggunakan salt dan nonce yang dibuat secara acak. Hasil enkripsi terdiri dari:
```text
salt (16 byte) + nonce (12 byte) + ciphertext + tag
```

**2. Pembuatan header**
Sebelum payload disisipkan, aplikasi menambahkan header berukuran 7 byte:
```text
'ST' + versi + panjang_payload (4 byte)
```
Header ini digunakan untuk mengetahui panjang payload sehingga proses ekstraksi dapat berhenti pada posisi yang benar.

**3. Pengacakan posisi bit**
Slot LSB pada setiap kanal R, G, dan B di dalam citra diacak menggunakan PRNG LCG dengan algoritma Fisher-Yates.
Urutan pengacakan ditentukan oleh seed yang berasal dari stego-key.

**4. Penyisipan**
Bit dari header dan payload kemudian ditulis ke bagian LSB pada posisi yang sudah diacak.
Dengan cara ini, pesan tidak disisipkan secara berurutan dari awal sampai akhir citra.

**5. Ekstraksi**

Pada proses ekstraksi, aplikasi menggunakan stego-key yang sama untuk menghasilkan kembali urutan posisi bit.
Header dibaca terlebih dahulu untuk mengetahui panjang payload. Setelah seluruh payload diperoleh, data didekripsi menggunakan kata sandi.
AES-GCM kemudian memeriksa tag untuk memastikan data masih sesuai dengan data saat enkripsi.

## Keamanan

Beberapa hal yang diperhatikan dalam implementasi StegoLSB:
1. Kata sandi dan kunci tidak disimpan di dalam source code. Keduanya dimasukkan oleh pengguna saat aplikasi dijalankan.
2. Salt dan nonce dibuat menggunakan `os.urandom` sehingga nilainya berbeda secara acak pada setiap proses enkripsi.
3. Pesan dilindungi menggunakan AES-256-GCM.
4. Kunci enkripsi diturunkan dari kata sandi menggunakan PBKDF2.
5. Aplikasi tidak menggunakan algoritma lama seperti MD5, SHA-1, DES, RC4, maupun mode ECB.
6. Implementasi LSB, header, dan pengacakan posisi dibuat sendiri untuk kebutuhan proyek.

## Batasan
Metode LSB yang digunakan pada aplikasi ini termasuk metode yang **fragile**.
Artinya, pesan yang sudah disisipkan dapat rusak apabila citra stego mengalami perubahan tertentu. Salah satu contohnya adalah ketika citra PNG disimpan ulang atau dikonversi ke format JPEG.
JPEG menggunakan kompresi lossy yang dapat mengubah nilai piksel, termasuk bagian LSB tempat pesan disisipkan.
Karena itu, citra hasil steganografi sebaiknya tetap disimpan dalam format **PNG atau BMP** agar pesan dapat diekstraksi dengan benar.
