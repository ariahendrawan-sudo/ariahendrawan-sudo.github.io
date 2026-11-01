"""
Penarik data publik profil SINTA (best-effort).

SINTA tidak menyediakan API; modul ini membaca halaman profil publik
(maksimal 10 entri terbaru per tab tanpa login). Hasilnya hanya dipakai untuk
MENAMBAH entri baru dan memperbarui skor/metrik; entri yang sudah ada di
data.json tidak pernah diubah atau dihapus. Bila struktur halaman SINTA
berubah dan tidak terbaca, modul mengembalikan data kosong dan update_data.py
mencatat peringatan tanpa merusak data.
"""
import html
import re
import urllib.request

BASE = "https://sinta.kemdiktisaintek.go.id/authors/profile/{id}/"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36 ariahendrawan-site-updater")
SELF = "aria hendrawan"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")


def _text(fragment):
    t = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def _num(s):
    s = (s or "").strip().replace(".", "").replace(",", "")
    return int(s) if s.isdigit() else None


def parse_profile(page):
    """Skor SINTA dan tabel Scopus / Google Scholar / WoS."""
    out = {}
    scores = {}
    for num, label in re.findall(r'class="pr-num"[^>]*>\s*([\d.,]+)\s*<.*?class="pr-txt"[^>]*>\s*([^<]+)<', page, re.S):
        scores[label.strip().lower()] = num.strip()
    if "sinta score overall" in scores:
        out["score"] = scores["sinta score overall"]
    if "sinta score 3yr" in scores:
        out["score3"] = scores["sinta score 3yr"]
    if "affil score" in scores:
        out["affil_score"] = scores["affil score"]

    m = re.search(r'<table[^>]*stat-table[^>]*>(.*?)</table>', page, re.S)
    if m:
        rows = {}
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(1), re.S):
            cells = [_text(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
            if len(cells) >= 4 and cells[0]:
                rows[cells[0].lower()] = cells[1:4]
        keymap = {"article": "articles", "citation": "citations", "cited document": "cited",
                  "h-index": "h", "i10-index": "i10", "g-index": "g"}
        table = {"Scopus": {}, "Google Scholar": {}, "Web of Science": {}}
        for raw, vals in rows.items():
            k = next((v for kk, v in keymap.items() if raw.startswith(kk)), None)
            if not k:
                continue
            for db, val in zip(table, vals):
                n = _num(val)
                if n is not None:
                    table[db][k] = n
        if all(len(v) >= 3 for v in table.values()):
            out["table"] = table
    return out


def _items(page):
    blocks = re.split(r'<div[^>]*class="[^"]*ar-list-item', page)[1:]
    items = []
    for b in blocks:
        tm = re.search(r'class="[^"]*ar-title[^"]*"[^>]*>(.*?)</div>', b, re.S)
        if not tm:
            continue
        title = _text(tm.group(1))
        link = re.search(r'href="([^"#][^"]*)"', tm.group(1))
        metas = [_text(x) for x in re.findall(r'<a[^>]*class="[^"]*ar-[a-z]+[^"]*"[^>]*>(.*?)</a>', b, re.S)]
        metas = [x for x in metas if x]
        ym = re.search(r'class="[^"]*ar-year[^"]*"[^>]*>(.*?)</a>', b, re.S)
        year = None
        if ym:
            yy = re.search(r"(19|20)\d{2}", _text(ym.group(1)))
            year = int(yy.group(0)) if yy else None
        full = _text(b)
        items.append({"title": title, "year": year, "metas": metas, "full": full,
                      "link": html.unescape(link.group(1)) if link else None})
    return [i for i in items if len(i["title"]) >= 8 and i["year"]]


def _after(metas, *keys):
    for m in metas:
        for k in keys:
            if m.lower().startswith(k.lower()):
                return m.split(":", 1)[1].strip() if ":" in m else m[len(k):].strip()
    return ""


def _grant(it):
    lead = _after(it["metas"], "Leader", "Ketua")
    members = _after(it["metas"], "Personils", "Personil", "Members", "Anggota")
    scheme = next((m for m in it["metas"] if re.search(r"penelitian|pengabdian|pkm|hibah|kompetitif", m, re.I)
                   and ":" not in m), "")
    funder = next((m for m in it["metas"] if re.search(r"bima|internal|source|dikti|kemdik|lpdp|brin", m, re.I)
                   and m != scheme), "")
    funder = re.sub(r"\bsource\b", "", funder, flags=re.I).strip() or "-"
    if scheme.isupper():
        scheme = scheme.title().replace("Pkm", "PkM")
    members = "; ".join(x.strip() for x in re.split(r"[;,]", members) if x.strip()).replace("; ", ", ")
    return {"y": it["year"], "t": it["title"], "lead": lead or "-", "members": members,
            "scheme": scheme or "-", "funder": funder,
            "role": "Ketua" if SELF in (lead or "").lower() else "Anggota", "src": "sinta"}


def _ipr(it):
    no = re.search(r"\b(EC\d{8,}|[PS]\d{8,}|IDP\d+|IDS\d+)\b", it["full"])
    cat = next((c for c in ("Hak Cipta", "Paten Sederhana", "Paten", "Desain Industri", "Merek")
                if c.lower() in it["full"].lower()), "HKI")
    inv = _after(it["metas"], "Inventor", "Pencipta", "Authors")
    return {"y": it["year"], "t": it["title"], "cat": cat, "inventors": inv or "-",
            "no": no.group(1) if no else "-", "src": "sinta"}


def _book(it):
    isbn = re.search(r"\b(97[89]\d{10})\b", it["full"].replace("-", ""))
    pub = next((m for m in it["metas"] if re.search(r"publish|press|penerbit|media|aksara|cv\.|pt\.", m, re.I)), "-")
    cat = next((m for m in it["metas"] if re.search(r"buku|book|monograf|lainnya", m, re.I)), "Buku")
    au = _after(it["metas"], "Author", "Penulis")
    return {"y": it["year"], "t": it["title"], "cat": cat.title() if cat.isupper() else cat,
            "isbn": isbn.group(1) if isbn else "-", "authors": au or "-", "pub": pub, "src": "sinta"}


def _scopus(it):
    q = re.search(r"\bQ([1-4])\b", it["full"])
    cit = re.search(r"(\d+)\s*cited", it["full"], re.I)
    venue = next((m for m in it["metas"] if not re.search(r"cited|creator|author order|^q[1-4]|^no q|(19|20)\d{2}$", m, re.I)), "-")
    conf = re.search(r"conference|proceeding|seminar|symposium|workshop", it["full"], re.I)
    return {"y": it["year"], "t": it["title"], "v": venue, "q": ("Q" + q.group(1)) if q else None,
            "n": int(cit.group(1)) if cit else 0, "link": it["link"],
            "kind": "prosiding" if conf else "jurnal"}


def fetch(author_id):
    """Mengembalikan dict: profile, grants, services, iprs, books, scopus. Bagian yang gagal = kosong."""
    url = BASE.format(id=author_id)
    out, errors = {}, []
    try:
        out["profile"] = parse_profile(_get(url))
    except Exception as e:  # noqa: BLE001
        errors.append(f"profil: {e}")
        out["profile"] = {}
    for key, view, fn in (("grants", "researches", _grant), ("services", "services", _grant),
                          ("iprs", "iprs", _ipr), ("books", "books", _book), ("scopus", "scopus", _scopus)):
        try:
            out[key] = [fn(i) for i in _items(_get(url + "?view=" + view))]
        except Exception as e:  # noqa: BLE001
            errors.append(f"{view}: {e}")
            out[key] = []
    out["errors"] = errors
    return out
