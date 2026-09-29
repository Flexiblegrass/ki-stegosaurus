# StegoLSB: Aplikasi Steganografi LSB + AES

Aplikasi steganografi untuk menyembunyikan pesan atau berkas ke dalam citra digital menggunakan metode LSB (Least Significant Bit) yang ditulis sendiri. Pesan dienkripsi menggunakan AES-256-GCM terlebih dahulu sebelum disisipkan. Aplikasi ini dibuat untuk Tugas Proyek Aplikasi Kriptografi (Topik B: Steganografi), mata kuliah Keamanan Informasi.

## Anggota Kelompok

Najmi Sabila Almusfiroh, NPM: 247006111125
Muthia Febrahma Khoirunnisa, NPM: 247006111130
Siti Qori'ah Muhafidloh, NPM: 247006111141

## Fitur

1. Penyisipan dan ekstraksi pesan menggunakan LSB pada citra PNG/BMP.
2. Header untuk menyimpan panjang pesan agar proses ekstraksi berhenti pada posisi yang tepat.
3. Pengacakan posisi bit menggunakan PRNG LCG dan Fisher-Yates dengan seed dari stego-key.
4. Enkripsi pesan menggunakan AES-256-GCM dengan kunci dari PBKDF2.
5. Salt dan nonce dibuat secara acak pada setiap proses enkripsi.
6. Perhitungan kapasitas citra dan penolakan pesan yang melebihi kapasitas.
7. Ekstraksi ditolak jika stego-key atau kata sandi salah, atau citra telah diubah.
8. GUI Tkinter menampilkan citra cover dan stego secara berdampingan beserta nilai PSNR.

### Fitur Pengayaan

Aplikasi juga memiliki varian m-bit LSB dengan m = 1 sampai 6, sedangkan GUI menyediakan m = 1 sampai 4. Nilai m disimpan di header sehingga proses ekstraksi dapat dilakukan secara otomatis.

Selain citra, aplikasi mendukung steganografi audio WAV PCM 8-bit dan 16-bit, baik mono maupun stereo. Fitur ini menggunakan enkripsi AES-GCM, header, pengacakan posisi sampel, dan m-bit LSB. Metrik yang digunakan adalah SNR, PSNR, dan MSE.

Terdapat juga fitur steganalisis menggunakan uji chi-square. Pengujian dilakukan secara gabungan dan per kanal R/G/B, serta dilengkapi grafik selisih pasangan nilai histogram.

## Struktur Proyek

```text
StegoLSB/
├── stego/
│   ├── crypto.py
│   ├── prng.py
│   ├── lsb.py
│   ├── core.py
│   ├── audio.py
│   ├── steganalysis.py
│   └── metrics.py
├── gui.py
├── run_experiments.py
├── run_experiments_pengayaan.py
├── tests/
├── sample_images/
├── sample_audio/
├── hasil_uji/
├── requirements.txt
└── README.md
```

## Cara Instalasi

Aplikasi membutuhkan Python 3.9 atau lebih baru.

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Linux/Mac:

```bash
source venv/bin/activate
```

Kemudian install dependensi:

```bash
pip install -r requirements.txt
```

Tkinter digunakan untuk GUI. Pada Windows dan macOS biasanya sudah tersedia bersama Python. Jika menggunakan Linux dan Tkinter belum tersedia, install dengan:

```bash
sudo apt install python3-tk
```

## Cara Menjalankan

Untuk menjalankan aplikasi GUI:

```bash
python gui.py
```

Pada tab **Sisip Pesan**, pilih citra cover, masukkan pesan atau berkas, kemudian isi kata sandi, stego-key, dan nilai m. Setelah itu klik **SISIP & SIMPAN STEGO**.

Pada tab **Ekstrak Pesan**, pilih citra stego dan masukkan kata sandi serta stego-key yang sama. Nilai m akan dibaca otomatis dari header.

Tab **Audio WAV** digunakan untuk menyisipkan dan mengekstraksi pesan dari berkas WAV. Tab **Chi-Square** digunakan untuk melakukan steganalisis pada citra.

## Pengujian

Pengujian utama dapat dijalankan dengan:

```bash
python run_experiments.py
```

Hasilnya disimpan di folder `hasil_uji/`, termasuk `hasil_psnr_mse.xlsx`, histogram, bidang LSB, dan citra cover serta stego.

Untuk pengujian fitur pengayaan:

```bash
python run_experiments_pengayaan.py
```

Hasilnya meliputi `hasil_pengayaan.xlsx`, `mbit_tradeoff.png`, `chi_square_pvalue.png`, `chi_square_selisih_pasangan.png`, dan `audio_snr.png`.

Berkas WAV untuk pengujian akan dibuat otomatis di `sample_audio/` jika belum tersedia.

## Unit Test

```bash
python tests/test_core_lsb.py
python tests/test_crypto_prng.py
python tests/test_metrics.py
python tests/test_pengayaan.py
```

Atau jalankan semuanya dengan:

```bash
python -m pytest -v
```

## Contoh Penggunaan

```python
from stego import core

cover, stego = core.embed_to_file(
    "sample_images/04_foto_sintetis.png",
    "stego.png",
    message="Pesan sangat rahasia",
    password="kata-sandi-ku",
    stego_key="kunci-posisi"
)

pesan = core.extract_from_file(
    "stego.png",
    password="kata-sandi-ku",
    stego_key="kunci-posisi"
)

print(pesan.decode())
```

Untuk m-bit LSB:

```python
from stego import core

core.embed_to_file(
    "sample_images/04_foto_sintetis.png",
    "stego_m3.png",
    "pesan",
    "kata-sandi-ku",
    "kunci-posisi",
    m=3
)
```

Untuk audio WAV:

```python
from stego import audio

audio.embed_to_file(
    "sample_audio/01_nada_16bit_mono.wav",
    "stego.wav",
    "pesan audio",
    "kata-sandi-ku",
    "kunci-posisi",
    m=2
)

print(audio.extract_from_file(
    "stego.wav",
    "kata-sandi-ku",
    "kunci-posisi"
))
```

Untuk chi-square:

```python
from stego import core, steganalysis

hasil = steganalysis.analyze_image(
    core.load_image_rgb("stego_m3.png")
)

print(hasil["gabungan"])
```

## Cara Kerja Singkat

Pesan pertama kali dienkripsi menggunakan AES-256-GCM. Kunci diturunkan dari kata sandi menggunakan PBKDF2 dan salt acak. Hasil enkripsi terdiri dari `salt(16) + nonce(12) + ciphertext + tag`.

Selanjutnya ditambahkan header 7 byte berupa `'ST' + versi + panjang_payload`. Header digunakan untuk mengetahui panjang payload saat proses ekstraksi.

Posisi bit kemudian diacak menggunakan Fisher-Yates dengan PRNG LCG yang menggunakan stego-key sebagai seed. Bit header dan payload disisipkan ke posisi LSB yang sudah diacak.

Saat ekstraksi, urutan posisi dibuat kembali menggunakan stego-key yang sama. Header dibaca untuk mengetahui panjang payload, kemudian data didekripsi. Tag AES-GCM digunakan untuk memastikan data masih sesuai dan tidak mengalami perubahan.

## Fitur Pengayaan

Pada m-bit LSB, setiap kanal dapat menyimpan m bit. Header tetap ditulis menggunakan 1-bit LSB, sedangkan payload menggunakan m bit sesuai nilai yang dipilih.

Kapasitas dihitung dengan:

```text
(jumlah_slot − 56) × m / 8
```

Perkiraan PSNR saat kapasitas penuh:

```text
m=1 → 51,1 dB
m=2 → 44,1 dB
m=3 → 37,9 dB
m=4 → 31,9 dB
m=5 → 25,8 dB
```

Pada audio WAV, sampel audio diperlakukan sebagai slot seperti kanal pada citra. Metrik yang digunakan adalah SNR, PSNR, dan MSE.

Uji chi-square digunakan untuk melihat perubahan distribusi pasangan nilai histogram. Pengujian dapat dilakukan pada citra secara keseluruhan maupun pada masing-masing kanal R/G/B.

## Keamanan

Kunci dan kata sandi tidak disimpan di dalam source code dan dimasukkan saat aplikasi dijalankan. Salt dan nonce dibuat menggunakan `os.urandom`.

Aplikasi tidak menggunakan MD5, SHA-1, DES, RC4, maupun mode ECB. Metode LSB, header, dan pengacakan posisi dibuat sendiri.

## Batasan

Audio yang didukung adalah WAV PCM 8-bit dan 16-bit. Format 24-bit, float, dan MP3 belum didukung.

Metode LSB bersifat **fragile**. Menyimpan ulang citra stego ke format lossy seperti JPEG dapat merusak pesan. Karena itu, gunakan PNG atau BMP untuk menjaga pesan tetap dapat diekstraksi.
