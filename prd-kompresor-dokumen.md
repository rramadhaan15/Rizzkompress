# PRD: Rizzkompress — Kompresor Dokumen Lokal (PDF & Gambar)

**Pemilik produk:** Rizki Ramadhan (adacmiawcs)
**Status:** Draft
**Versi:** 1.0

## 1. Latar Belakang

Mengirim dokumen (PDF hasil scan, tugas kuliah, lampiran email) sering terkendala ukuran file yang besar. Layanan kompresi online (iLovePDF, SmallPDF, dsb.) mengharuskan file diunggah ke server pihak ketiga, yang bermasalah untuk dokumen sensitif (KTP, surat resmi, data akademik) dan bergantung pada koneksi internet. Dibutuhkan alat kompresi yang berjalan sepenuhnya di komputer sendiri (localhost), tanpa upload ke internet.

## 2. Tujuan (Goals)

- Mengompresi PDF dan gambar (JPG, PNG, dll.) secara lokal dengan antarmuka web sederhana.
- Memberi kontrol tingkat kompresi (kuat/sedang/ringan) agar pengguna bisa menyeimbangkan ukuran vs kualitas.
- Mendukung dokumen Office (DOCX/PPTX/XLSX) dengan mengonversinya ke PDF sebelum dikompres.
- Tidak ada data yang meninggalkan perangkat pengguna.

## 3. Non-Goals

- Bukan layanan cloud multi-user atau SaaS berbayar.
- Tidak menyediakan OCR atau editing konten dokumen.
- Tidak menargetkan skala enterprise (ribuan pengguna bersamaan).

## 4. Target Pengguna

- Diri sendiri dan teman kuliah/kerja yang perlu mengompresi dokumen tugas, laporan, atau lampiran tanpa upload ke pihak ketiga.

## 5. User Flow

1. Pengguna membuka `http://127.0.0.1:5000` di browser.
2. Memilih file (PDF, gambar, atau file Office).
3. Memilih tingkat kompresi: Kuat / Sedang / Ringan.
4. Klik "Kompres & Unduh".
5. Server memproses file, lalu browser otomatis mengunduh hasilnya.
6. Jika gagal (dependency tidak terpasang, format tak didukung), pesan error ditampilkan di halaman yang sama.

## 6. Kebutuhan Fungsional

| ID | Kebutuhan | Prioritas |
|----|-----------|-----------|
| F1 | Upload satu file PDF dan kompresi via Ghostscript (preset screen/ebook/printer) | Wajib |
| F2 | Upload gambar (JPG/PNG/WebP/BMP/TIFF), resize + re-encode JPEG kualitas terkontrol | Wajib |
| F3 | Konversi DOCX/PPTX/XLSX ke PDF via LibreOffice headless, lalu kompres | Wajib |
| F4 | Pilihan 3 tingkat kompresi dengan deskripsi trade-off | Wajib |
| F5 | Fallback: jika hasil kompresi lebih besar dari file asli, kirim file asli | Wajib |
| F6 | Validasi ukuran file maksimum (200 MB) dan format yang didukung | Wajib |
| F7 | Kompresi banyak file sekaligus (batch) dalam satu request | Nice-to-have |
| F8 | Preview ukuran file sebelum/sesudah kompresi di UI | Nice-to-have |
| F9 | Drag-and-drop file | Nice-to-have |
| F10 | Pembersihan otomatis file sementara (temp folder) setelah selesai | Wajib (perbaikan teknis) |

## 7. Kebutuhan Non-Fungsional

- **Privasi:** seluruh pemrosesan terjadi di localhost; tidak ada request keluar ke internet.
- **Performa:** file 20 MB selesai diproses dalam <10 detik pada laptop biasa.
- **Portabilitas:** berjalan di Windows, macOS, dan Linux dengan dependency yang jelas didokumentasikan.
- **Keandalan:** error dari proses eksternal (Ghostscript/LibreOffice) ditangani dan ditampilkan dengan pesan yang jelas, bukan crash.

## 8. Arsitektur Teknis

- **Backend:** Python (Flask), menerima upload lewat form multipart.
- **Kompresi PDF:** Ghostscript (`gs`/`gswin64c`) dengan `-dPDFSETTINGS`.
- **Kompresi gambar:** Pillow (resize + re-encode JPEG).
- **Konversi Office → PDF:** LibreOffice headless (`soffice --headless --convert-to pdf`).
- **Frontend:** satu halaman HTML sederhana (form + hasil), tanpa framework JS.
- **Penyimpanan:** file sementara di folder temp per-request, idealnya dihapus otomatis setelah response terkirim.

## 9. Dependensi Eksternal

- Ghostscript (wajib untuk PDF).
- LibreOffice (opsional, hanya untuk dokumen Office).
- Python 3 + paket `flask`, `pillow`.

## 10. Metrik Keberhasilan

- Rasio kompresi rata-rata ≥50% untuk PDF hasil scan.
- Tidak ada file yang gagal diproses karena bug (bukan karena dependency hilang).
- Waktu setup dari nol (install dependency + jalankan) di bawah 10 menit mengikuti dokumentasi.

## 11. Risiko & Mitigasi

| Risiko | Mitigasi |
|--------|----------|
| Ghostscript/LibreOffice tidak terpasang di perangkat pengguna | Pesan error yang jelas + instruksi instalasi di README |
| File temp menumpuk memenuhi disk | Tambahkan pembersihan otomatis (F10) sebelum dipakai rutin |
| PDF berbasis teks murni tidak banyak mengecil | Fallback ke file asli (F5) agar tidak merugikan pengguna |
| Upload file berbahaya/besar membebani sistem | Batas ukuran file (F6) dan validasi ekstensi |

## 12. Roadmap Singkat

- **v1 (selesai):** kompresi PDF & gambar, konversi Office dasar, UI form sederhana.
- **v1.1:** pembersihan temp file otomatis, validasi format lebih ketat.
- **v1.2:** batch upload, preview ukuran before/after.
- **v2 (opsional):** drag-and-drop, dark mode UI, riwayat kompresi lokal.
