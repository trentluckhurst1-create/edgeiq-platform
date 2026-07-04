from pathlib import Path
import pandas as pd
import re
import time
import urllib.request
import urllib.error
from bs4 import BeautifulSoup

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"
RAW_DIR = ROOT / "outputs" / "ra_active_profile_backfill"
RAW_DIR.mkdir(parents=True, exist_ok=True)

TARGETS = DATA / "edgeiq_active_ra_profile_backfill_targets_v1.csv"
FORM_RUNS = DATA / "form_card_runs.csv"
OUT = DATA / "edgeiq_active_ra_profile_backfill_v1.csv"
DIAG = DATA / "edgeiq_active_ra_profile_backfill_diagnostics_v1.csv"

def clean_key(x):
    s = str(x or "").upper()
    s = s.replace("’", "").replace("'", "")
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s.strip()

def fetch(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="ignore")

def extract_rows_from_text(horse, horse_key, profile_url, text):
    rows = []

    patterns = [
        r"([A-Z]{2,5})\s+(\d{2}[A-Z][a-z]{2}\d{2})\s+(\d{3,4})m\s+([A-Za-z0-9\s\-/]+?)\s+\$[\d,]+.*?(?:Barrier\s+(\d+))?.*?(?:Rtg\s+(\d+))?.*?(\d+(?:st|nd|rd|th)(?:\s+of\s+\d+)?)?.*?(\d+(?:\.\d+)?L).*?\$(\d+(?:\.\d+)?)",
        r"([A-Z]{2,5})\s+(\d{2}[A-Z][a-z]{2}\d{2})\s+(\d{3,4})m\s+([A-Za-z0-9\s\-/]+?)\s+.*?(\d+(?:st|nd|rd|th)(?:\s+of\s+\d+)?)",
    ]

    for pat in patterns:
        for m in re.finditer(pat, text):
            groups = m.groups()
            raw = m.group(0).strip()

            rows.append({
                "horse": horse,
                "horse_key": horse_key,
                "horse_url": profile_url,
                "horse_all_form_url": profile_url,
                "run_date_raw": groups[1] if len(groups) > 1 else "",
                "track": groups[0] if len(groups) > 0 else "",
                "distance": groups[2] + "m" if len(groups) > 2 and groups[2] else "",
                "race_class": groups[3].strip() if len(groups) > 3 and groups[3] else "",
                "finish_pos": groups[6] if len(groups) > 6 and groups[6] else "",
                "margin": groups[7] if len(groups) > 7 and groups[7] else "",
                "sp": groups[8] if len(groups) > 8 and groups[8] else "",
                "raw_text": raw,
                "run_type": "RACE",
                "is_official_race": True,
                "source": "RA_ACTIVE_PROFILE_BACKFILL",
            })

    return rows

targets = pd.read_csv(TARGETS)
all_rows = []
fetch_rows = []

for _, r in targets.iterrows():
    horse = str(r["horse"])
    horse_key = clean_key(r["horse_key"])
    url = str(r["profile_url"])

    status = "UNKNOWN"
    html_len = 0
    parsed_rows = 0

    try:
        html = fetch(url)
        html_len = len(html)

        raw_path = RAW_DIR / f"{horse_key}.html"
        raw_path.write_text(html, encoding="utf-8", errors="ignore")

        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)

        rows = extract_rows_from_text(horse, horse_key, url, text)
        parsed_rows = len(rows)
        all_rows.extend(rows)

        status = "FETCHED_PARSED" if parsed_rows else "FETCHED_NO_RUN_ROWS"

    except Exception as e:
        status = "FAILED_" + repr(e)[:120]

    fetch_rows.append({
        "horse": horse,
        "horse_key": horse_key,
        "profile_url": url,
        "status": status,
        "html_len": html_len,
        "parsed_rows": parsed_rows,
    })

    time.sleep(0.4)

backfill = pd.DataFrame(all_rows)
fetch_diag = pd.DataFrame(fetch_rows)

if len(backfill):
    backfill["run_date"] = pd.to_datetime(backfill["run_date_raw"], format="%d%b%y", errors="coerce").dt.strftime("%Y-%m-%d")
    backfill["date"] = backfill["run_date"]
    backfill["run_rating"] = ""
    backfill["rating"] = ""
    backfill["class_name"] = backfill["race_class"]
    backfill["track_condition"] = ""
    backfill["jockey"] = ""
    backfill["starting_price"] = backfill["sp"]
    backfill["sp_text"] = backfill["sp"]
    backfill["barrier"] = ""
    backfill["trainer"] = ""
    backfill["pos_800"] = ""
    backfill["pos_400"] = ""
    backfill["in_run_positions"] = ""
    backfill["rating_band"] = ""
    backfill["horse_soft"] = backfill["horse"]

    desired_cols = [
        "horse", "horse_key", "horse_url", "horse_all_form_url",
        "run_date", "date", "track", "distance", "race_class", "class_name",
        "race_name", "track_condition", "finish_pos", "margin", "jockey",
        "starting_price", "sp_text", "sp", "run_rating", "rating", "run_type",
        "is_official_race", "barrier", "trainer", "pos_800", "pos_400",
        "in_run_positions", "rating_band", "raw_text", "horse_soft"
    ]

    for c in desired_cols:
        if c not in backfill.columns:
            backfill[c] = ""

    backfill = backfill[desired_cols]

    existing = pd.read_csv(FORM_RUNS, low_memory=False) if FORM_RUNS.exists() else pd.DataFrame(columns=desired_cols)

    for c in desired_cols:
        if c not in existing.columns:
            existing[c] = ""

    existing = existing[desired_cols]

    combined = pd.concat([existing, backfill], ignore_index=True)
    combined["_dedupe"] = (
        combined["horse_key"].astype(str)
        + "|" + combined["run_date"].astype(str)
        + "|" + combined["track"].astype(str)
        + "|" + combined["distance"].astype(str)
        + "|" + combined["finish_pos"].astype(str)
    )

    combined = combined.drop_duplicates("_dedupe", keep="first").drop(columns=["_dedupe"])
    combined.to_csv(FORM_RUNS, index=False)

backfill.to_csv(OUT, index=False)
fetch_diag.to_csv(DIAG, index=False)

print("=" * 100)
print("EDGEIQ ACTIVE RA PROFILE BACKFILL V1")
print("=" * 100)
print(fetch_diag.to_string(index=False))
print()
print("ROWS PARSED:", len(backfill))
print("SAVED:", OUT)
print("SAVED:", DIAG)
print("PATCHED:", FORM_RUNS)
