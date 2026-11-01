# Situs Kepakaran Dr. Aria Hendrawan

Situs profil kepakaran (penelitian, publikasi, dan pengabdian kepada masyarakat) yang
di-hosting di **GitHub Pages** dan diperbarui otomatis setiap **Senin 05.07 WIB** melalui
GitHub Actions.

## Struktur

| Berkas | Fungsi |
|---|---|
| `index.html` | Tampilan situs (satu halaman, responsif, mode terang/gelap). |
| `data.json` | Seluruh isi: metrik, publikasi, PkM, tautan profil. |
| `scripts/update_data.py` | Menarik data dari OpenAlex dan Crossref, lalu menambahkan karya baru. |
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
- SINTA/BIMA tidak menyediakan API publik; hibah penelitian dan PkM dari SINTA ditambahkan
  manual ke `data.json`.
