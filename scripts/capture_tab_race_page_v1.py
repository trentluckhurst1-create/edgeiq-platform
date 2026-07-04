from pathlib import Path
from playwright.sync_api import sync_playwright
import json
import re
import pandas as pd
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DEBUG = DATA / "tab_race_page_debug_v1"
DEBUG.mkdir(parents=True, exist_ok=True)

NEXT = DATA / "edgeiq_tab_next_to_go_all_v1.csv"
NETWORK_OUT = DEBUG / "tab_race_page_network.json"
TEXT_OUT = DEBUG / "tab_race_page_text.txt"
CANDIDATES_OUT = DATA / "edgeiq_tab_race_page_runner_price_candidates_v1.csv"

df = pd.read_csv(NEXT)

# Prefer a simple local-ish race if available, otherwise first available race.
pick = df[
    (df["location"].astype(str).str.upper().isin(["VIC", "NSW", "QLD", "SA", "WA", "TAS"])) &
    (df["race_type"].astype(str).str.upper().isin(["R", "G", "H"]))
].copy()

if pick.empty:
    row = df.iloc[0].to_dict()
else:
    row = pick.iloc[0].to_dict()

race_url = str(row.get("race_details_url", "")).strip()

if not race_url or race_url.lower() == "nan":
    raise SystemExit("[tab_race_page_capture] No race_details_url found.")

# Convert API race URL into TAB website race URL shape where possible.
# API: /racing/dates/2026-06-06/meetings/G/SHE/races/1
m = re.search(r"/racing/dates/([^/]+)/meetings/([^/]+)/([^/]+)/races/(\d+)", race_url)
if not m:
    raise SystemExit("[tab_race_page_capture] Could not parse race_details_url: " + race_url)

meeting_date, race_type, venue, race_no = m.groups()
page_url = f"https://www.tab.com.au/racing/meetings/{meeting_date}/{race_type}/{venue}/races/{race_no}"

print("[tab_race_page_capture] selected:", row.get("meeting_name"), row.get("race_type"), row.get("race_no"), row.get("race_name"))
print("[tab_race_page_capture] page_url:", page_url)

events = []
runner_price_candidates = []

PRICE_RE = re.compile(r"(?<!\d)([1-9]\d{0,2}(?:\.\d{1,2})?)(?!\d)")
RUNNER_LINE_RE = re.compile(r"^\s*(\d{1,2})\s+([A-Z][A-Z '\-]{2,45})\s*$")

def scan_text_for_candidates(text):
    rows = []
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    for i, line in enumerate(lines):
        prices = []
        for p in PRICE_RE.findall(line):
            try:
                x = float(p)
                if 1.01 <= x <= 501:
                    prices.append(x)
            except Exception:
                pass

        if not prices:
            continue

        nearby = []
        for j in range(max(0, i - 4), min(len(lines), i + 3)):
            nearby.append(lines[j])

        horse = ""
        runner_no = ""

        for candidate in reversed(nearby):
            up = candidate.upper()
            m2 = RUNNER_LINE_RE.match(up)
            if m2:
                runner_no = m2.group(1)
                horse = m2.group(2)
                break

            if re.fullmatch(r"[A-Z][A-Z '\-]{2,45}", up) and not any(bad in up for bad in ["WIN", "PLACE", "FIXED", "TOTE", "RACE", "ODDS"]):
                horse = up
                break

        rows.append({
            "scraped_at": datetime.now().isoformat(timespec="seconds"),
            "source": "TAB_RACE_PAGE_TEXT",
            "page_url": page_url,
            "meeting_name": row.get("meeting_name"),
            "race_type": row.get("race_type"),
            "race_no": row.get("race_no"),
            "race_name": row.get("race_name"),
            "runner_no": runner_no,
            "horse": horse,
            "price_candidate": prices[0],
            "line": line,
            "nearby_text": " | ".join(nearby),
        })

    return rows

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        viewport={"width": 1500, "height": 950},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    )
    page = context.new_page()

    def handle_response(resp):
        url = resp.url
        low = url.lower()

        keep = (
            "api.beta.tab.com.au" in low
            or "tab-info-service" in low
            or "bff-racing" in low
            or "racing" in low
        )

        if not keep:
            return

        item = {
            "status": resp.status,
            "url": url,
            "content_type": resp.headers.get("content-type", ""),
            "text_start": "",
        }

        try:
            txt = resp.text()
            item["text_start"] = txt[:5000]

            safe_name = re.sub(r"[^A-Za-z0-9]+", "_", url)[:160]
            body_path = DEBUG / f"body_{len(events):03d}_{safe_name}.txt"
            body_path.write_text(txt[:250000], encoding="utf-8", errors="ignore")
            item["saved_body"] = str(body_path)
        except Exception as e:
            item["text_start"] = "READ_ERROR: " + str(e)

        events.append(item)
        print("[network]", resp.status, url)

    page.on("response", handle_response)

    print("[tab_race_page_capture] opening", page_url)
    page.goto(page_url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(25000)

    # Try common buttons/tabs that may reveal prices/runners.
    for word in ["Win", "Fixed", "Place", "Form", "Runners", "Market", "Odds"]:
        try:
            loc = page.get_by_text(word, exact=False)
            count = min(loc.count(), 5)
            for i in range(count):
                try:
                    loc.nth(i).click(timeout=1500)
                    page.wait_for_timeout(2500)
                except Exception:
                    pass
        except Exception:
            pass

    try:
        body_text = page.locator("body").inner_text(timeout=10000)
    except Exception:
        body_text = ""

    TEXT_OUT.write_text(body_text, encoding="utf-8", errors="ignore")

    runner_price_candidates.extend(scan_text_for_candidates(body_text))

    browser.close()

NETWORK_OUT.write_text(json.dumps(events, indent=2), encoding="utf-8")

cand = pd.DataFrame(runner_price_candidates)
cand.to_csv(CANDIDATES_OUT, index=False)

print("[tab_race_page_capture] network_events", len(events))
print("[tab_race_page_capture] candidates", len(cand))
print("[tab_race_page_capture] wrote", NETWORK_OUT)
print("[tab_race_page_capture] wrote", TEXT_OUT)
print("[tab_race_page_capture] wrote", CANDIDATES_OUT)

if not cand.empty:
    print(cand.head(40).to_string(index=False))
