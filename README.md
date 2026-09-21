# Rizzkompress

Kompres file di komputer sendiri. PDF, gambar, dan dokumen Office dioptimalkan dalam format aslinya, sedangkan format lainnya dibuat menjadi arsip ZIP. Aplikasi hanya berjalan pada `127.0.0.1`; berkas sementara dibersihkan sesudah unduhan selesai.

## Persiapan

Butuh Python 3.10 atau lebih baru. Dari folder proyek:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Buka [http://127.0.0.1:5000](http://127.0.0.1:5000). Di macOS/Linux, aktifkan virtual environment dengan `source .venv/bin/activate`.

### Alat tambahan

- **Ghostscript** diperlukan untuk PDF dan file Office. Instal dari [situs resminya](https://www.ghostscript.com/releases/gsdnld.html), lalu pastikan `gs` (macOS/Linux) atau `gswin64c` (Windows) ada di `PATH`. Di Windows, instalasi standar dalam `Program Files\gs` juga terdeteksi otomatis.
Kompresi gambar, DOCX, PPTX, XLSX, dan arsip generik hanya memerlukan paket Python dalam `requirements.txt`. Dokumen Office tidak membutuhkan Microsoft Office atau LibreOffice.

Untuk instalasi tanpa hak administrator di Windows, biner Ghostscript juga bisa ditempatkan di `.tools/ghostscript/` (misalnya `.tools/ghostscript/runtime/bin/gswin64c.exe`). Aplikasi akan menemukannya otomatis. Folder `.tools` diabaikan Git, jadi setiap komputer yang menjalankan hasil clone perlu menyiapkan Ghostscript sendiri.

## Cara pakai

Pilih atau seret satu file ke halaman, pilih tingkat kompresi, lalu klik **Kompres & Unduh**. Hasil akan terunduh otomatis dan ukuran sebelum/sesudah akan muncul di halaman.

| Tingkat | PDF | Gambar |
| --- | --- | --- |
| Kuat | Ghostscript `/screen` | JPEG kualitas 52, sisi maks. 1600 px |
| Sedang | Ghostscript `/ebook` | JPEG kualitas 72, sisi maks. 2400 px |
| Ringan | Ghostscript `/printer` | JPEG kualitas 86, sisi maks. 3600 px |

Gambar keluaran memakai JPEG; area transparan diberi latar putih. Bila PDF, gambar, atau dokumen Office hasil kompresi lebih besar, file asli dikembalikan. Format lain dikembalikan sebagai ZIP. Batas ukuran masukan: **200 MB**.

## Privasi

Tidak ada panggilan jaringan keluar dari aplikasi. Semua proses berjalan secara lokal. Server hanya menerima koneksi dari komputer ini (`127.0.0.1`). Berkas diproses di direktori sementara per permintaan dan dibersihkan ketika respons unduhan selesai atau terjadi kesalahan. Hindari menutup proses secara paksa ketika kompresi sedang berjalan.
