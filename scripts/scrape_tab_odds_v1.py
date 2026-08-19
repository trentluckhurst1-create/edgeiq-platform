import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "public" / "data"
DEBUG_DIR = OUT_DIR / "tab_debug_v1"
OUT_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

START_URL = "https://www.tab.com.au/racing"
OUT = OUT_DIR / "edgeiq_tab_odds_raw_v1.csv"

PRICE_KEYS = [
    "fixedOdds", "fixedPrice", "fixedWinPrice", "winPrice", "price",
    "odds", "returnWin", "displayPrice", "decimalPrice", "win"
]

NAME_KEYS = [
    "runnerName", "runner_name", "name", "displayName", "competitorName",
    "entrantName", "participantName", "selectionName", "horseName",
    "runner", "description"
]


def walk(x, path=""):
    if isinstance(x, dict):
        yield path, x
        for k, v in x.items():
            yield from walk(v, f"{path}.{k}" if path else str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from walk(v, f"{path}[{i}]")


def price(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        x = float(v)
        if 1.01 <= x <= 501:
            return round(x, 2)
        if 101 <= x <= 50100:
            return round(x / 100, 2)
    if isinstance(v, str):
        m = re.search(r"(?<!\d)([1-9]\d{0,2}(?:\.\d{1,2})?)(?!\d)", v)
        if m:
            x = float(m.group(1))
            if 1.01 <= x <= 501:
                return round(x, 2)
    return None


def get_price(d):
    for k in PRICE_KEYS:
        if k in d:
            v = d[k]
            if isinstance(v, dict):
                for kk in PRICE_KEYS:
                    p = price(v.get(kk))
                    if p:
                        return p
            p = price(v)
            if p:
                return p

    for k, v in d.items():
        if any(s in str(k).lower() for s in ["price", "odds", "return"]):
            p = price(v)
            if p:
                return p
    return None


def get_name(d):
    for k in NAME_KEYS:
        v = d.get(k)
        if isinstance(v, str):
            s = v.strip()
            if 2 <= len(s) <= 60:
                bad = ["RACE ", "MARKET ", "WIN ", "PLACE ", "FIXED ", "TOTAL "]
                if not any(s.upper().startswith(b) for b in bad):
                    return s.upper()
    return None


def get_no(d):
    for k in ["runnerNumber", "runner_number", "number", "tabNo", "saddlecloth", "clothNumber"]:
        if d.get(k) not in [None, ""]:
            return d.get(k)
    return None


def extract(payload, source_url):
    rows = []
    for path, d in walk(payload):
        if not isinstance(d, dict):
            continue
        horse = get_name(d)
        p = get_price(d)
        if horse and p:
            rows.append({
                "scraped_at": datetime.now().isoformat(timespec="seconds"),
                "source": "TAB",
                "source_url": source_url,
                "json_path": path,
                "runner_no": get_no(d),
                "horse": horse,
                "tab_fixed_win": p,
            })
    return rows


def parse_saved_json():
    rows = []
    for fp in DEBUG_DIR.glob("tab_response_*.json"):
        try:
            payload = json.loads(fp.read_text(encoding="utf-8"))
            rows.extend(extract(payload, fp.name))
        except Exception:
            pass
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=25)
    ap.add_argument("--headful", action="store_true")
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    rows = []
    saved = 0
    network = []

    if not args.offline:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not args.headful)
            context = browser.new_context(
                viewport={"width": 1500, "height": 950},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
            )
            page = context.new_page()

            def on_response(resp):
                nonlocal rows, saved
                url = resp.url
                ctype = resp.headers.get("content-type", "")
                if "tab" not in url.lower():
                    return

                network.append({"status": resp.status, "content_type": ctype, "url": url})

                if "json" not in ctype.lower():
                    return

                try:
                    payload = resp.json()
                    rows.extend(extract(payload, url))
                    fp = DEBUG_DIR / f"tab_response_{saved:03d}.json"
                    fp.write_text(json.dumps(payload, indent=2)[:400000], encoding="utf-8")
                    saved += 1
                except Exception:
                    pass

            page.on("response", on_response)

            print("[edgeiq_tab_odds_v1] opening", START_URL)

            try:
                page.goto(START_URL, wait_until="domcontentloaded", timeout=30000)
            except PlaywrightTimeoutError:
                print("[edgeiq_tab_odds_v1] domcontentloaded timeout ignored")

            page.wait_for_timeout(args.seconds * 1000)

            try:
                text = page.locator("body").inner_text(timeout=5000)
                (DEBUG_DIR / "tab_visible_text.txt").write_text(text, encoding="utf-8")
            except Exception:
                pass

            pd.DataFrame(network).to_csv(DEBUG_DIR / "tab_network_log.csv", index=False)
            browser.close()

    rows.extend(parse_saved_json())

    df = pd.DataFrame(rows)
    if not df.empty:
        df["horse"] = df["horse"].astype(str).str.upper().str.strip()
        df = df.drop_duplicates(subset=["source_url", "horse", "tab_fixed_win"])
        df = df.sort_values(["horse", "tab_fixed_win"])

    df.to_csv(OUT, index=False)

    print("[edgeiq_tab_odds_v1] rows=", len(df))
    print("[edgeiq_tab_odds_v1] wrote", OUT)
    print("[edgeiq_tab_odds_v1] debug_dir", DEBUG_DIR)


if __name__ == "__main__":
    main()
