#!/usr/bin/env python3
"""
Pre-render template.html + data.json menjadi index.html statis (untuk SEO).

Halaman dibuka di Chromium headless, JavaScript mengisi semua bagian
(publikasi, hibah, PkM, buku, HKI, metrik), lalu DOM hasilnya disimpan sebagai
index.html. Dengan begitu mesin pencari membaca seluruh konten di HTML awal;
di browser pengunjung, JavaScript tetap berjalan (filter, pencarian) dan
menampilkan ulang data yang sama.

Juga menulis sitemap.xml (lastmod = tanggal pembaruan data) dan menyisipkan
meta verifikasi Google Search Console bila "gsc_verification" diisi di data.json.

Kebutuhan: pip install playwright && python -m playwright install --with-deps chromium
"""
import functools
import html
import http.server
import json
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://ariahendrawan-sudo.github.io/"


def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    handler = functools.partial(Quiet, directory=str(ROOT))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main():
    data = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
    srv = serve()
    url = f"http://127.0.0.1:{srv.server_address[1]}/template.html"
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1280, "height": 900}, locale="id-ID",
                          timezone_id="Asia/Jakarta")
        # font Google tidak perlu dimuat saat pre-render
        page.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        page.route("**/fonts.gstatic.com/**", lambda r: r.abort())
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url, wait_until="load")
        page.wait_for_selector("#ledger .pub", timeout=20000)
        page.wait_for_selector("#grants .g", timeout=20000)
        doc = page.content()
        b.close()
    srv.shutdown()
    if errors:
        raise SystemExit("Pre-render gagal: " + "; ".join(errors))

    code = (data.get("gsc_verification") or "").strip()
    if code:
        doc = doc.replace("<!--GSC-VERIFICATION-->",
                          f'<meta name="google-site-verification" content="{html.escape(code, quote=True)}">')
    (ROOT / "index.html").write_text(doc, encoding="utf-8")

    lastmod = data.get("updated", "")
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url>\n    <loc>{SITE}</loc>\n    <lastmod>{lastmod}</lastmod>\n"
        "    <changefreq>weekly</changefreq>\n    <priority>1.0</priority>\n  </url>\n"
        "</urlset>\n", encoding="utf-8")
    n_pub = doc.count('class="pub"')
    print(f"index.html: {len(doc)//1024} KB, {n_pub} publikasi ter-render; sitemap lastmod {lastmod}")


if __name__ == "__main__":
    main()
