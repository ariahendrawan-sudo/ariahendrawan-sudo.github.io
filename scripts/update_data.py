#!/usr/bin/env python3
"""
Pembaruan otomatis data.json untuk situs kepakaran Dr. Aria Hendrawan.

Sumber:
  - OpenAlex  : metrik penulis (karya, sitasi, h-index, i10), produktivitas per tahun,
                daftar karya + jumlah sitasi per DOI.
  - Crossref  : karya yang terhubung ke ORCID.

Aturan penggabungan:
  - Entri lama (termasuk yang dikurasi manual, "src": "curated") TIDAK dihapus dan
    teksnya TIDAK diubah; hanya jumlah sitasi "n" yang diperbarui bila lebih besar.
  - Karya baru ditambahkan bila DOI atau judul ternormalisasinya belum ada.
  - Klaster ("c") dan jenis ("k") karya baru ditentukan dengan aturan kata kunci;
    koreksi manual cukup dilakukan langsung di data.json, tidak akan ditimpa.

Hanya memakai pustaka standar Python 3.9+.
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ORCID = "0000-0002-0732-6447"
OPENALEX_AUTHOR = "A5085345108"
MAILTO = "ariahendrawan@usm.ac.id"  # dipakai sebagai "polite pool" OpenAlex/Crossref
SELF_NAMES = {"aria hendrawan", "hendrawan aria", "a. hendrawan", "hendrawan, aria"}

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data.json"
UA = f"ariahendrawan-site-updater/1.0 (mailto:{MAILTO})"

PKM_VENUES = ("surya masyarakat", "dimastik", "tematik", "e-dimas", "pengabdian",
              "abdimas", "community service", "dedikasi", "pemberdayaan")
PKM_TITLE = ("pelatihan", "pemberdayaan", "peningkatan kemampuan", "peningkatan kapasitas",
             "peningkatan penggunaan", "peningkatan sumber daya", "pendampingan",
             "sosialisasi", "bagi guru", "pada siswa", "umkm rw", "masyarakat desa")

RULES = [  # urutan penting: aturan pertama yang cocok dipakai
    ("its", ("traffic", "lalu lintas", "transport", "mobility", "mobilitas", "passenger",
             "penumpang", "road-vehicle", "metr-la", "spatiotemporal", "terminal")),
    ("cv", ("detection", "deteksi objek", "vehicle detection", "image", "citra", "vision",
            "yolo", "face", "wajah", "cnn-based detection", "detr", "r-cnn", "tracking",
            "clahe", "segmentation", "segmentasi", "picnosis", "underwater", "bawah air")),
    ("nlp", ("sentimen", "sentiment", "text", "teks", "klasifikasi pertanyaan", "nlp",
             "komentar", "tweet", "opini")),
    ("dss", ("decision", "keputusan", "mcdm", "vikor", "aras", "electre", "topsis", "saw ",
             "ahp", "smarter", "multi-criteria", "multikriteria")),
    ("iot", ("iot", "internet of things", "arduino", "raspberry", "sensor", "embedded",
             "telegram bot", "voice", "suara", "robot")),
    ("sis", ("enterprise architecture", "arsitektur enterprise", "knowledge management",
             "sistem informasi", "information system", "website", "web-based", "berbasis web",
             "mern", "higher education", "perguruan tinggi")),
]


def get_json(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"Gagal mengambil {url}: {last}")


def norm_title(t):
    t = re.sub(r"<[^>]+>", " ", t or "").lower()
    return re.sub(r"[^a-z0-9]+", "", t)


def norm_doi(d):
    if not d:
        return ""
    d = d.strip().lower()
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", d)


def clean(t):
    t = re.sub(r"<[^>]+>", "", t or "")
    return re.sub(r"\s+", " ", t).strip()


def is_english(title):
    words = re.findall(r"[a-zA-Z]+", title.lower())
    if not words:
        return False
    idn = {"dan", "yang", "untuk", "dengan", "pada", "menggunakan", "berbasis", "analisis",
           "sistem", "dalam", "terhadap", "penerapan", "implementasi", "peningkatan", "metode"}
    return sum(w in idn for w in words) == 0


def classify(title, venue):
    tl, vl = title.lower(), (venue or "").lower()
    if any(v in vl for v in PKM_VENUES) or any(k in tl for k in PKM_TITLE):
        return "pkm"
    for c, kws in RULES:
        if any(k in tl for k in kws):
            return c
    return "ml"


def kind_from(type_str, cluster):
    if cluster == "pkm":
        return "pkm"
    t = (type_str or "").lower()
    if "proceedings" in t or "conference" in t:
        return "prosiding"
    if "book" in t or "chapter" in t:
        return "buku"
    return "jurnal"


def coauthors(names):
    out = [n for n in names if n and n.strip().lower() not in SELF_NAMES]
    return ", ".join(out)


# ---------- OpenAlex ----------
def openalex_author():
    return get_json(f"https://api.openalex.org/authors/{OPENALEX_AUTHOR}?mailto={MAILTO}")


def openalex_works():
    works, cursor = [], "*"
    while cursor:
        q = urllib.parse.urlencode({
            "filter": f"author.id:{OPENALEX_AUTHOR}", "per-page": 200,
            "cursor": cursor, "mailto": MAILTO,
        })
        page = get_json(f"https://api.openalex.org/works?{q}")
        works.extend(page.get("results", []))
        cursor = page.get("meta", {}).get("next_cursor")
        if not page.get("results"):
            break
    out = []
    for w in works:
        loc = w.get("primary_location") or {}
        src = (loc.get("source") or {}).get("display_name") or ""
        bib = w.get("biblio") or {}
        vol, iss = bib.get("volume"), bib.get("issue")
        venue = src + (f" {vol}" if vol else "") + (f"({iss})" if iss else "")
        names = [((a.get("author") or {}).get("display_name") or "") for a in w.get("authorships", [])]
        out.append({
            "y": w.get("publication_year"), "t": clean(w.get("title") or w.get("display_name")),
            "v": venue.strip() or "-", "type": w.get("type"), "doi": norm_doi(w.get("doi")),
            "n": w.get("cited_by_count") or 0, "a": coauthors(names),
            "url": (loc.get("landing_page_url") or w.get("id")),
        })
    return out


# ---------- Crossref ----------
def crossref_works():
    q = urllib.parse.urlencode({"filter": f"orcid:{ORCID}", "rows": 200, "mailto": MAILTO})
    items = get_json(f"https://api.crossref.org/works?{q}").get("message", {}).get("items", [])
    out = []
    for it in items:
        title = clean((it.get("title") or [""])[0])
        parts = (it.get("issued") or {}).get("date-parts") or [[None]]
        venue = (it.get("container-title") or [""])[0]
        vol, iss = it.get("volume"), it.get("issue")
        venue = venue + (f" {vol}" if vol else "") + (f"({iss})" if iss else "")
        names = [" ".join(x for x in (a.get("given"), a.get("family")) if x) for a in it.get("author", [])]
        out.append({
            "y": parts[0][0], "t": title, "v": venue.strip() or "-", "type": it.get("type"),
            "doi": norm_doi(it.get("DOI")), "n": it.get("is-referenced-by-count") or 0,
            "a": coauthors(names), "url": None,
        })
    return out


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    pubs = data["pubs"]
    by_doi = {norm_doi(p.get("doi")): p for p in pubs if p.get("doi")}
    by_title = {norm_title(p["t"]): p for p in pubs}
    report, changed, failures = [], False, []

    # 1) metrik penulis
    try:
        a = openalex_author()
        ss = a.get("summary_stats") or {}
        metrics = {"works": a.get("works_count", 0), "citations": a.get("cited_by_count", 0),
                   "h_index": ss.get("h_index", 0), "i10_index": ss.get("i10_index", 0),
                   "source": "OpenAlex"}
        cby = sorted([[c["year"], c.get("works_count", 0), c.get("cited_by_count", 0)]
                      for c in a.get("counts_by_year", [])])
        if metrics != data.get("metrics"):
            report.append(f"Metrik: {data.get('metrics')} -> {metrics}")
            data["metrics"] = metrics
            changed = True
        # OpenAlex hanya memberi ~10 tahun terakhir; pertahankan tahun lama yang sudah tercatat
        old = {r[0]: r for r in data.get("counts_by_year", [])}
        for r in cby:
            old[r[0]] = r
        merged = sorted(old.values())
        if merged != data.get("counts_by_year"):
            data["counts_by_year"] = merged
            changed = True
    except Exception as e:  # noqa: BLE001
        failures.append(f"OpenAlex author: {e}")

    # 2) karya
    candidates = []
    for name, fn in (("OpenAlex works", openalex_works), ("Crossref", crossref_works)):
        try:
            candidates.extend(fn())
        except Exception as e:  # noqa: BLE001
            failures.append(f"{name}: {e}")

    for w in candidates:
        if not w["t"] or not w["y"]:
            continue
        existing = by_doi.get(w["doi"]) if w["doi"] else None
        existing = existing or by_title.get(norm_title(w["t"]))
        if existing:
            if (w["n"] or 0) > (existing.get("n") or 0):
                existing["n"] = w["n"]
                changed = True
            continue
        c = classify(w["t"], w["v"])
        entry = {"y": int(w["y"]), "t": w["t"], "v": w["v"], "k": kind_from(w["type"], c),
                 "c": c, "a": w["a"], "n": w["n"], "src": "auto"}
        if w["doi"]:
            entry["doi"] = w["doi"]
        elif w.get("url"):
            entry["url"] = w["url"]
        if is_english(w["t"]):
            entry["en"] = 1
        pubs.append(entry)
        if entry.get("doi"):
            by_doi[entry["doi"]] = entry
        by_title[norm_title(entry["t"])] = entry
        report.append(f"+ [{entry['y']}] {entry['t']} ({entry['k']}/{entry['c']})")
        changed = True

    if changed:
        pubs.sort(key=lambda p: (-p["y"], p["t"]))
        wib = timezone(timedelta(hours=7))
        data["updated"] = datetime.now(wib).strftime("%Y-%m-%d")
        DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print("\n".join(report) if report else "Tidak ada karya atau metrik baru.")
    for f in failures:
        print("PERINGATAN:", f, file=sys.stderr)
    # gagal total hanya bila semua sumber gagal
    if len(failures) >= 3:
        sys.exit(1)


if __name__ == "__main__":
    main()
