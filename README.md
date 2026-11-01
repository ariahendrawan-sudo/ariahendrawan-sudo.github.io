# Situs Kepakaran Dr. Aria Hendrawan

Situs profil kepakaran (penelitian, publikasi, dan pengabdian kepada masyarakat) yang
di-hosting di **GitHub Pages** dan diperbarui otomatis setiap **Senin 05.07 WIB** melalui
GitHub Actions.

## Struktur

| Berkas | Fungsi |
|---|---|
| `template.html` | Sumber tampilan situs. **Edit file ini**, bukan `index.html`. |
| `index.html` | Hasil pre-render otomatis (HTML statis untuk mesin pencari). Jangan diedit manual. |
| `scripts/prerender.py` | Membuat `index.html` dan `sitemap.xml` dari `template.html` + `data.json`. |
| `robots.txt`, `sitemap.xml` | Petunjuk untuk mesin pencari. |
| `data.json` | Seluruh isi: metrik, publikasi, PkM, tautan profil. |
| `scripts/update_data.py` | Menarik data dari OpenAlex, Crossref, dan SINTA, lalu menambahkan entri baru. |
| `scripts/merge_sinta.py` | Menggabungkan hasil ekstraksi SINTA (JSON) ke `data.json`. |
| `status.json` | Laporan tiap pembaruan: jumlah data per sumber dan peringatan. |
| `scripts/sinta.py` | Pembaca profil publik SINTA (skor, metrik, hibah, PkM, HKI, buku, Scopus). |
| `.github/workflows/update-and-deploy.yml` | Jadwal mingguan, pembaruan data, dan deploy ke Pages. |

## Pemasangan (sekali saja)

1. Buat repositori **publik** bernama persis `<username>.github.io`
   (untuk situs ini: `ariahendrawan-sudo.github.io` di akun `ariahendrawan-sudo`).
2. Unggah seluruh isi folder ini ke branch `main`.
3. Buka **Settings → Pages → Build and deployment → Source**, pilih **GitHub Actions**.
4. Buka tab **Actions**, pilih *Update data & deploy site*, klik **Run workflow**.
5. Setelah selesai (±1 menit), situs aktif di `https://ariahendrawan-sudo.github.io`.

## Pemeliharaan

- **Koreksi atau tambah entri manual:** edit `data.json` langsung di GitHub (ikon pensil),
  lalu *Commit*. Situs otomatis ter-deploy ulang. Entri lama tidak pernah ditimpa skrip;
  hanya jumlah sitasi (`n`) yang diperbarui.
- **Skema entri publikasi:**
  `{"y":2026,"t":"Judul","v":"Nama Jurnal 8(2)","k":"jurnal|prosiding|buku|pkm","c":"cv|its|ml|nlp|dss|iot|sis|pkm","a":"Rekan penulis","doi":"10.xxxx/...","n":0,"en":1}`
  Gunakan `"url"` bila tidak ada DOI. `"en":1` menandai judul berbahasa Inggris.
- **Entri baru otomatis** ditandai `"src":"auto"`. Periksa klaster/jenisnya sesekali.
- **Pembaruan seketika:** tab Actions → Run workflow.

## Catatan data

- Metrik (karya, sitasi, h-index, i10) bersumber dari OpenAlex dan dapat berbeda dari Scopus.
  Metrik Scopus resmi memerlukan Elsevier API key (umumnya melalui langganan institusi).
- SINTA menolak akses dari server GitHub (HTTP 403), sehingga data SINTA diperbarui oleh
  tugas terjadwal Claude setiap Senin yang membaca profil SINTA lalu menjalankan
  `scripts/merge_sinta.py`. Bila SINTA kelak membuka akses, `scripts/sinta.py` di workflow
  GitHub akan otomatis ikut bekerja.
- SINTA dibaca dari profil publik (10 entri terbaru per tab tanpa login). Entri lama di luar
  10 terbaru sudah tersimpan di `data.json` dan tidak akan hilang.
- Judul yang tidak ingin ditampilkan dimasukkan ke daftar `exclude` di `data.json`.

## SEO dan Google Search Console

1. Buka https://search.google.com/search-console → **Add property → URL prefix** →
   `https://ariahendrawan-sudo.github.io/`.
2. Pilih metode **HTML tag**, salin nilai `content="..."` saja.
3. Isi nilai itu ke `"gsc_verification"` di `data.json` (edit di GitHub, lalu Commit).
   Situs ter-deploy ulang dengan meta verifikasi; kembali ke Search Console dan klik **Verify**.
4. Menu **Sitemaps** → kirim `sitemap.xml`. Menu **URL Inspection** → **Request Indexing**.
