#!/usr/bin/env python3
"""
Gabungkan data SINTA yang sudah diekstrak (file JSON) ke data.json.

Dipakai karena server SINTA menolak akses dari GitHub Actions (HTTP 403).
Ekstraksi dilakukan di luar GitHub (misalnya tugas terjadwal Claude yang membaca
profil SINTA), lalu hasilnya digabung dengan aturan yang sama: hanya menambah
entri baru, tidak menghapus atau mengubah entri lama.

Pemakaian:
    python scripts/merge_sinta.py sinta_extract.json

Format sinta_extract.json (semua kunci opsional):
{
  "profile": {"score": "1.539", "score3": "707", "affil_score": "1.539",
              "table": {"Scopus": {"articles":7,"citations":33,"cited":5,"h":4,"i10":1,"g":6},
                        "Google Scholar": {...}, "Web of Science": {...}}},
  "grants":   [{"y":2025,"t":"Judul","lead":"Nama Ketua","members":"A, B","scheme":"Skema","funder":"BIMA"}],
  "services": [ ...sama dengan grants... ],
  "iprs":     [{"y":2026,"t":"Judul","cat":"Hak Cipta","inventors":"A, B","no":"EC00..."}],
  "books":    [{"y":2026,"t":"Judul","cat":"Buku Referensi","isbn":"978...","authors":"A, B","pub":"Penerbit, Kota"}],
  "scopus":   [{"y":2024,"t":"Judul","v":"Nama jurnal/konferensi","q":"Q2","n":9,"link":"https://www.scopus.com/...","kind":"jurnal|prosiding"}]
}
"""
import json
import sys
from datetime import datetime, timedelta, timezone

import update_data as u


def main(path):
    s = json.load(open(path, encoding="utf-8"))
    for key in ("grants", "services"):
        for g in s.get(key, []):
            g.setdefault("members", "")
            g.setdefault("scheme", "-")
            g.setdefault("funder", "-")
            g.setdefault("lead", "-")
            g["role"] = "Ketua" if "aria hendrawan" in g["lead"].lower() else "Anggota"
            g["src"] = "sinta"
    for key in ("iprs", "books"):
        for x in s.get(key, []):
            x["src"] = "sinta"
    for sc in s.get("scopus", []):
        sc.setdefault("n", 0)
        sc.setdefault("v", "-")
        sc.setdefault("kind", "jurnal")

    data = json.loads(u.DATA.read_text(encoding="utf-8"))
    report = []
    if u.apply_sinta(data, s, report):
        for key in ("grants", "services", "iprs", "books"):
            data.get(key, []).sort(key=lambda x: (-x["y"], x["t"]))
        data["pubs"].sort(key=lambda p: (-p["y"], p["t"]))
        data["updated"] = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d")
        u.DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("\n".join(report) if report else "Tidak ada perubahan dari SINTA.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
