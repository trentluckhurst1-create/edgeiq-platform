from pathlib import Path
from playwright.sync_api import sync_playwright
import json
import re
import pandas as pd
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DATA.mkdir(parents=True, exist_ok=True)

OUT_LINKS = DATA / "edgeiq_tab_vic_thoroughbred_urls_v1.csv"
OUT_ALL = DATA / "edgeiq_tab_all_frontend_race_links_v1.csv"
OUT_TEXT = DATA / "tab_frontend_discovery_text_v1.txt"

PAGES = [
    "https://www.tab.com.au/racing/meetings/today/R",
    "https://www.tab.com.au/racing/meetings/tomorrow/R",
    "https://www.tab.com.au/racing/meetings/2026-06-07/R",
    "https://www.tab.com.au/racing/meetings/2026-06-08/R",
    "https://www.tab.com.au/racing/next-to-go",
]

RACE_RE = re.compile(r"/racing/(\d{4}-\d{2}-\d{2})/([^/]+)/([^/]+)/([RGH])/(\d+)$")

all_links = []
all_text = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={"width": 1600, "height": 1000})

    for url in PAGES:
        print("[find_vic_frontend] opening", url)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(12000)

            for _ in range(6):
                page.mouse.wheel(0, 1400)
                page.wait_for_timeout(1500)

            body = page.locator("body").inner_text(timeout=10000)
            all_text.append("===== " + url + " =====")
            all_text.append(body)

            links = page.locator("a").evaluate_all("""
                els => els.map(a => ({
                    text: (a.innerText || a.textContent || '').trim(),
                    href: a.href || ''
                })).filter(x => x.href.includes('/racing/20'))
            """)

            print("[find_vic_frontend] links", len(links))

            for x in links:
                href = str(x.get("href", ""))
                text = str(x.get("text", "")).replace("\\n", " ").strip()
                m = RACE_RE.search(href)
                if not m:
                    continue

                meeting_date, meeting_slug, venue, race_type, race_no = m.groups()

                all_links.append({
                    "source_page": url,
                    "text": text,
                    "meeting_date": meeting_date,
                    "meeting_slug": meeting_slug,
                    "venue_mnemonic": venue,
                    "race_type": race_type,
                    "race_no": int(race_no),
                    "tab_frontend_url": href,
                    "is_vic_text": "(VIC)" in text.upper(),
                    "is_thoroughbred": race_type == "R",
                })

        except Exception as e:
            print("[find_vic_frontend] ERROR", url, e)

    browser.close()

df = pd.DataFrame(all_links)

if not df.empty:
    df = df.drop_duplicates(subset=["tab_frontend_url"])
    df = df.sort_values(["meeting_date", "meeting_slug", "race_type", "race_no"])

df.to_csv(OUT_ALL, index=False)

vic = df[
    (df["is_vic_text"] == True) &
    (df["race_type"].astype(str).str.upper() == "R")
].copy() if not df.empty else df.copy()

vic.to_csv(OUT_LINKS, index=False)

OUT_TEXT.write_text("\n\n".join(all_text), encoding="utf-8", errors="ignore")

print("[find_vic_frontend] all_race_links", len(df))
print("[find_vic_frontend] vic_thoroughbred_links", len(vic))
print("[find_vic_frontend] wrote", OUT_ALL)
print("[find_vic_frontend] wrote", OUT_LINKS)

if not df.empty:
    print("[find_vic_frontend] ALL R LINKS SAMPLE")
    print(df[df["race_type"] == "R"][["text","meeting_date","meeting_slug","venue_mnemonic","race_type","race_no","tab_frontend_url"]].head(100).to_string(index=False))

if not vic.empty:
    print("[find_vic_frontend] VIC THOROUGHBRED LINKS")
    print(vic[["text","meeting_date","meeting_slug","venue_mnemonic","race_no","tab_frontend_url"]].to_string(index=False))
else:
    print("[find_vic_frontend] NO VIC THOROUGHBRED LINKS FOUND IN TAB FRONTEND PAGES")
