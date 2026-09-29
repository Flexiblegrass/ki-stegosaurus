# StegoLSB: Aplikasi Steganografi LSB + AES

Aplikasi steganografi untuk **menyembunyikan pesan atau berkas ke dalam citra digital** menggunakan metode **LSB (Least Significant Bit)** yang ditulis sendiri. Pesan **dienkripsi menggunakan AES-256-GCM** terlebih dahulu sebelum disisipkan. Aplikasi ini dibuat untuk Tugas Proyek Aplikasi Kriptografi (Topik B: Steganografi), mata kuliah Keamanan Informasi.

## Anggota Kelompok

1. Najmi Sabila Almusfiroh, NPM: 247006111125
2. Muthia Febrahma Khoirunnisa, NPM: 247006111130
3. Siti Qori'ah Muhafidloh, NPM: 247006111141

## Fitur

1. Penyisipan dan ekstraksi pesan menggunakan metode **LSB** pada citra **PNG/BMP** yang bersifat lossless.
2. **Header penanda panjang pesan** menggunakan magic `ST`, versi, dan panjang pesan agar proses ekstraksi berhenti pada posisi yang tepat.
3. **Pengacakan posisi bit** menggunakan PRNG LCG dan Fisher-Yates dengan seed dari **stego-key**.
4. Pesan **dienkripsi menggunakan AES-256-GCM** dengan kunci yang diturunkan dari kata sandi menggunakan **PBKDF2**.
5. Salt dan nonce dibuat secara acak pada setiap proses enkripsi.
6. Perhitungan kapasitas citra dan penolakan pesan yang melebihi kapasitas.
7. Ekstraksi ditolak jika **stego-key salah**, **kata sandi salah**, atau citra telah diubah. Kondisi ini diverifikasi menggunakan tag AES-GCM.
8. GUI Tkinter menampilkan **citra cover dan stego secara berdampingan** beserta nilai **PSNR**.

### Fitur Pengayaan

1. **Varian m-bit LSB**, dengan m = 1 sampai 6. GUI menyediakan m = 1 sampai 4. Setiap kanal dapat menyimpan m bit.
2. Nilai m disimpan di header sehingga proses **ekstraksi dapat dilakukan secara otomatis** tanpa perlu memilih m kembali.
3. Analisis trade-off kapasitas dan PSNR tersedia melalui `hasil_uji/mbit_tradeoff.png`.
4. **Steganografi audio WAV** dengan format PCM 8-bit dan 16-bit, baik mono maupun stereo. Fitur ini menggunakan AES-GCM, header, pengacakan posisi sampel berdasarkan stego-key, dan m-bit LSB.
5. Metrik audio yang digunakan adalah **SNR, PSNR, dan MSE**.
6. **Steganalisis statistik menggunakan uji chi-square** berdasarkan metode Westfeld dan Pfitzmann.
7. Perhitungan p-value menggunakan fungsi gamma tak lengkap yang ditulis sendiri tanpa SciPy.
8. Pengujian chi-square dapat dilakukan secara gabungan maupun pada setiap kanal R/G/B, serta dilengkapi grafik selisih pasangan nilai `h[2i] − h[2i+1]`.

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

Keterangan beberapa file utama:

`crypto.py` menangani AES-256-GCM dan PBKDF2 menggunakan library `cryptography`.

`prng.py` berisi LCG dan Fisher-Yates untuk mengacak posisi berdasarkan stego-key.

`lsb.py` menangani logika LSB 1-bit dan m-bit, termasuk proses konversi serta pembacaan dan penulisan bit.

`core.py` menangani proses penyisipan dan ekstraksi, termasuk header, payload, citra, dan m-bit.

`audio.py` menangani steganografi audio WAV menggunakan inti yang sama.

`steganalysis.py` menangani uji chi-square dengan perhitungan p-value yang ditulis sendiri.

`metrics.py` berisi perhitungan PSNR, MSE, SNR, histogram, dan bidang LSB.

`gui.py` merupakan aplikasi GUI berbasis Tkinter untuk citra, audio, dan chi-square.

## Cara Instalasi

Aplikasi membutuhkan **Python 3.9 atau lebih baru**.

Buat virtual environment jika diperlukan:

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

Install dependensi:

```bash
pip install -r requirements.txt
```

Tkinter digunakan untuk GUI. Pada Windows dan macOS biasanya sudah tersedia bersama Python. Pada Linux, jika Tkinter belum tersedia, install dengan:

```bash
sudo apt install python3-tk
```

## Cara Menjalankan

### Aplikasi GUI

Jalankan aplikasi dengan:

```bash
python gui.py
```

1. **Tab Sisip Pesan**

   Pilih citra cover dalam format PNG/BMP, ketik pesan atau pilih berkas, kemudian isi **Kata Sandi** dan **Stego-key**. Pilih nilai **m** sebagai jumlah bit per kanal, dengan nilai default 1. Setelah itu klik **SISIP & SIMPAN STEGO**.

   Citra cover dan stego akan ditampilkan berdampingan beserta nilai PSNR.

2. **Tab Ekstrak Pesan**

   Pilih citra stego, masukkan kata sandi dan stego-key yang sama, kemudian klik **EKSTRAK PESAN**. Nilai m akan dibaca secara otomatis dari header.

3. **Tab Audio WAV**

   Pilih berkas WAV PCM 8-bit atau 16-bit, masukkan pesan, kata sandi, stego-key, dan nilai m. Setelah proses penyisipan selesai, aplikasi menampilkan nilai SNR, PSNR, dan MSE. Bagian bawah tab digunakan untuk mengekstraksi pesan dari WAV stego.

4. **Tab Chi-Square**

   Pilih citra cover dan stego, atau gunakan citra dari tab Sisip Pesan. Jalankan pengujian untuk melihat hasil chi-square dan grafik selisih pasangan nilai.

### Menjalankan Pengujian

Pengujian utama dapat dijalankan dengan:

```bash
python run_experiments.py
```

Hasil pengujian tersimpan di folder `hasil_uji/`, yaitu:

1. `hasil_psnr_mse.xlsx`, berisi tabel PSNR dan MSE untuk 5 citra dengan 3 ukuran pesan serta uji kerapuhan JPEG.
2. `histogram_*.png`, berisi perbandingan histogram cover dan stego.
3. `lsb_plane_*.png`, berisi visualisasi bidang LSB.
4. `berdampingan_*.png`, berisi perbandingan citra cover dan stego.

### Menjalankan Pengujian Pengayaan

```bash
python run_experiments_pengayaan.py
```

Waktu pengujian sekitar 2 menit.

Hasil pengujian disimpan di folder `hasil_uji/`, meliputi:

1. `hasil_pengayaan.xlsx`, dengan 4 sheet untuk m-bit pesan tetap, m-bit kapasitas penuh, chi-square, dan audio WAV.
2. `mbit_tradeoff.png`
3. `chi_square_pvalue.png`
4. `chi_square_selisih_pasangan.png`
5. `audio_snr.png`

Berkas WAV untuk pengujian akan dibuat secara otomatis di `sample_audio/` jika belum tersedia.

### Menjalankan Unit Test

Jalankan setiap pengujian dengan:

```bash
python tests/test_core_lsb.py
python tests/test_crypto_prng.py
python tests/test_metrics.py
python tests/test_pengayaan.py
```

Atau jalankan semuanya sekaligus:

```bash
python -m pytest -v
```

## Contoh Penggunaan

Contoh penggunaan tanpa GUI:

```python
from stego import core

# Sisip
cover, stego = core.embed_to_file(
    "sample_images/04_foto_sintetis.png",
    "stego.png",
    message="Pesan sangat rahasia",
    password="kata-sandi-ku",
    stego_key="kunci-posisi"
)

# Ekstrak
pesan = core.extract_from_file(
    "stego.png",
    password="kata-sandi-ku",
    stego_key="kunci-posisi"
)

print(pesan.decode())
```

Hasil:

```text
Pesan sangat rahasia
```

### Varian m-bit, Audio WAV, dan Chi-Square

```python
from stego import core, audio, steganalysis

# m-bit LSB dengan 3 bit per kanal
# Ekstraksi tetap dilakukan secara otomatis
core.embed_to_file(
    "sample_images/04_foto_sintetis.png",
    "stego_m3.png",
    "pesan",
    "kata-sandi-ku",
    "kunci-posisi",
    m=3
)

# Audio WAV
audio.embed_to_file(
    "sample_audio/01_nada_16bit_mono.wav",
    "stego.wav",
    "pesan audio",
    "kata-sandi-ku",
    "kunci-posisi",
    m=2
)

print(
    audio.extract_from_file(
        "stego.wav",
        "kata-sandi-ku",
        "kunci-posisi"
    )
)

# Uji chi-square pada citra
hasil = steganalysis.analyze_image(
    core.load_image_rgb("stego_m3.png")
)

print(hasil["gabungan"])
```

Hasil chi-square berisi nilai `chi2`, `df`, `p_value`, `flagged`, dan `verdict`.

## Cara Kerja Singkat

1. **Enkripsi**

   Pesan dienkripsi menggunakan AES-256-GCM. Kunci diturunkan dari kata sandi menggunakan PBKDF2 dan salt acak.

   Hasil enkripsi terdiri dari:

   ```text
   salt(16) + nonce(12) + ciphertext + tag
   ```

2. **Header**

   Header berukuran 7 byte ditambahkan sebelum payload:

   ```text
   'ST' + versi + panjang_payload(4 byte)
   ```

   Header digunakan untuk mengetahui panjang payload dan membantu mendeteksi penggunaan stego-key yang salah.

3. **Pengacakan Posisi**

   Seluruh slot LSB pada kanal R, G, dan B diacak menggunakan Fisher-Yates dengan PRNG LCG. Seed PRNG berasal dari stego-key.

4. **Penyisipan**

   Bit header dan payload ditulis ke posisi LSB yang telah diacak.

5. **Ekstraksi**

   Dengan stego-key yang sama, urutan posisi acak dibuat kembali. Header dibaca untuk mengetahui panjang payload, kemudian payload diekstraksi dan didekripsi. Tag GCM digunakan untuk memverifikasi keaslian data.

## Cara Kerja Fitur Pengayaan

### m-bit LSB

Header berukuran 56 bit tetap ditulis menggunakan 1-bit LSB pada 56 slot pertama dari urutan acak. Byte ke-3 pada header menyimpan nilai m.

Payload ditulis pada slot berikutnya menggunakan m bit per slot. Kapasitas dihitung dengan rumus:

```text
(jumlah_slot − 56) × m / 8
```

Jika bit yang disisipkan bersifat acak dan kapasitas digunakan secara penuh, perkiraan MSE adalah:

```text
MSE ≈ (4^m − 1) / 6
```

Perkiraan PSNR:

```text
PSNR ≈ 10 × log10(255² × 6 / (4^m − 1))
```

Hasil perkiraan:

```text
m=1 → 51,1 dB
m=2 → 44,1 dB
m=3 → 37,9 dB
m=4 → 31,9 dB
m=5 → 25,8 dB
```

Dengan demikian, m ≤ 4 masih berada di atas ambang 30 dB pada kapasitas penuh.

### Audio WAV

Sampel audio, termasuk sampel yang saling berselang pada audio stereo, diperlakukan sebagai slot seperti kanal pada citra.

Perhitungan SNR:

```text
SNR = 10 × log10(Σx² / Σ(x−y)²)
```

PSNR menggunakan nilai puncak 32767 untuk audio 16-bit dan 255 untuk audio 8-bit.

### Chi-Square

Untuk histogram `h`, nilai yang diharapkan dihitung dengan:

```text
E_i = (h[2i] + h[2i+1]) / 2
```

Nilai chi-square:

```text
χ² = Σ (h[2i] − E_i)² / E_i
```

Derajat kebebasan:

```text
df = jumlah_pasangan − 1
```

Nilai p:

```text
p = P(X ≥ χ²)
```

Pada LSB replacement dengan bit acak, nilai `h[2i]` dan `h[2i+1]` cenderung menjadi lebih seimbang. Pada stego dengan penyisipan penuh, nilai p dapat menjadi besar, sedangkan cover alami dapat memiliki nilai p yang mendekati 0.

Karena posisi penyisipan diacak di seluruh citra, pengujian ini lebih dapat diandalkan pada laju penyisipan yang tinggi. Pada citra cover yang memiliki banyak noise, seperti `02_derau.png`, dapat terjadi false positive. Keterbatasan ini dianalisis dalam laporan.

## Keamanan

1. Tidak ada kunci atau kata sandi yang ditulis di dalam kode sumber. Keduanya dimasukkan saat aplikasi dijalankan.
2. Salt dan nonce dibuat menggunakan `os.urandom`.
3. Aplikasi tidak menggunakan algoritma MD5, SHA-1, DES, RC4, maupun mode ECB.
4. Metode LSB, header, dan pengacakan posisi ditulis sendiri.

## Batasan

1. Pada format header, byte ke-3 menyimpan nilai m. Nilai m = 1 tetap kompatibel dengan versi awal sehingga stego dari versi sebelumnya masih dapat diekstraksi.
2. Audio yang didukung hanya WAV PCM 8-bit dan 16-bit. Format 24-bit, float, dan MP3 belum didukung.
3. Menyimpan ulang audio ke format lossy seperti MP3 atau AAC dapat merusak pesan.
4. Metode LSB bersifat **fragile**. Menyimpan ulang citra stego ke format lossy seperti JPEG dapat merusak pesan. Gunakan PNG atau BMP untuk menjaga pesan tetap dapat diekstraksi.
