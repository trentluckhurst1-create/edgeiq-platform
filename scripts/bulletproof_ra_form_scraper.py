from __future__ import annotations

import re
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import pandas as pd
import requests
from bs4 import BeautifulSoup

DATA = ROOT / "public" / "data"
FIELDS = DATA / "race_fields.csv"
FULL = DATA / "full_career_form.csv"
RUNS = DATA / "form_card_runs.csv"

OUT_REPORT = DATA / "form_scrape_bulletproof_report.csv"
OUT_MISSING = DATA / "form_scrape_still_missing.csv"
DEBUG_DIR = DATA / "debug_ra_form_pages"

DEBUG_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

COUNTRY_RE = re.compile(r"\([A-Z]{2,4}\)")
NON_ALNUM_RE = re.compile(r"[^A-Z0-9]")


def compact(x) -> str:
    if pd.isna(x):
        return ""
    s = str(x).upper().strip()
    s = COUNTRY_RE.sub("", s)
    s = NON_ALNUM_RE.sub("", s)
    return s


def clean(x) -> str:
    if pd.isna(x):
        return ""
    s = str(x).strip()
    return "" if s.lower() in {"nan", "none", "null"} else s


def first_present(row, names):
    lower = {str(c).lower().strip(): c for c in row.index}
    for name in names:
        c = lower.get(name.lower())
        if c is not None:
            return row.get(c)
    return ""


def normalise_col(c) -> str:
    s = str(c).strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    return s


def classify_run_type(row) -> str:
    blob = " ".join(clean(v).upper() for v in row.values)
    if "JUMP" in blob:
        return "JUMPOUT"
    if "TRIAL" in blob:
        return "TRIAL"
    return "RACE"


def extract_horse_code(url: str) -> str:
    try:
        q = parse_qs(urlparse(url).query)
        return q.get("HorseCode", [""])[0]
    except Exception:
        return ""


def fetch_html(url: str, tries: int = 3) -> str:
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=25)
            if r.status_code == 200 and len(r.text) > 500:
                return r.text
            last = f"status={r.status_code} len={len(r.text)}"
        except Exception as e:
            last = repr(e)
        time.sleep(1.5 + i)
    raise RuntimeError(last or "fetch failed")


def parse_tables(html: str):
    try:
        return pd.read_html(html)
    except Exception:
        return []


def choose_form_table(tables):
    best = None
    best_score = -1

    wanted = ["date", "track", "dist", "class", "jockey", "margin", "finish", "pos", "sp"]

    for t in tables:
        if t is None or t.empty:
            continue

        flat_cols = []
        for c in t.columns:
            if isinstance(c, tuple):
                flat_cols.append(" ".join(str(x) for x in c if str(x) != "nan"))
            else:
                flat_cols.append(str(c))

        t = t.copy()
        t.columns = [normalise_col(c) for c in flat_cols]
        blob = " ".join(t.columns).lower()

        score = sum(1 for w in wanted if w in blob)
        score += min(len(t), 30) / 100

        if score > best_score:
            best = t
            best_score = score

    if best is None or best_score < 2:
        return None

    return best


def parse_form_rows(horse: str, horse_key: str, url: str, html: str) -> list[dict]:
    tables = parse_tables(html)
    table = choose_form_table(tables)

    if table is None or table.empty:
        return []

    rows = []

    for _, r in table.iterrows():
        vals = [clean(v) for v in r.values]
        blob = " ".join(vals)

        if not blob or blob.lower() in {"nan", "none"}:
            continue

        date = first_present(r, ["date", "run_date", "race_date"])
        track = first_present(r, ["track", "trk"])
        dist = first_present(r, ["dist", "distance"])
        race_class = first_present(r, ["class", "race_class", "class_name"])
        cond = first_present(r, ["condition", "track_condition", "going"])
        fin = first_present(r, ["fin", "finish", "finish_pos", "place", "pos"])
        margin = first_present(r, ["margin", "mgn"])
        jockey = first_present(r, ["jockey", "rider"])
        barrier = first_present(r, ["barrier", "bar"])
        weight = first_present(r, ["weight", "wgt", "weight_carried"])
        sp = first_present(r, ["sp", "starting_price", "price"])
        winner = first_present(r, ["winner"])
        pos800 = first_present(r, ["800", "pos_800", "800m"])
        pos400 = first_present(r, ["400", "pos_400", "400m"])

        if not clean(date) or not clean(track):
            continue

        run_type = classify_run_type(r)

        rows.append({
            "horse": horse,
            "horse_key": horse_key,
            "run_date": clean(date),
            "track": clean(track),
            "distance": clean(dist),
            "race_class": clean(race_class),
            "track_condition": clean(cond),
            "finish_pos": clean(fin),
            "field_size": "",
            "margin": clean(margin),
            "jockey": clean(jockey),
            "trainer": "",
            "barrier": clean(barrier),
            "weight_carried": clean(weight),
            "sp_text": clean(sp),
            "starting_price": clean(sp),
            "official_time": "",
            "winner": clean(winner),
            "second": "",
            "pos_800": clean(pos800),
            "pos_400": clean(pos400),
            "in_run_positions": "",
            "run_type": run_type,
            "run_rating": "",
            "rating_display": "—" if run_type != "RACE" else "",
            "source_url": url,
        })

    return rows


def main():
    fields = pd.read_csv(FIELDS, low_memory=False)
    existing = pd.read_csv(FULL, low_memory=False) if FULL.exists() else pd.DataFrame()

    fields["horse_key_norm"] = fields.apply(lambda r: compact(r.get("horse_key") or r.get("horse")), axis=1)

    if not existing.empty:
        existing["horse_key_norm"] = existing.apply(lambda r: compact(r.get("horse_key") or r.get("horse")), axis=1)
        existing_keys = set(existing["horse_key_norm"].dropna().astype(str))
    else:
        existing_keys = set()

    targets = (
        fields[["horse", "horse_key", "horse_key_norm", "profile_url", "horse_url"]]
        .drop_duplicates("horse_key_norm")
        .copy()
    )

    targets["url"] = targets["profile_url"].fillna("").astype(str)
    targets.loc[targets["url"].str.strip().eq(""), "url"] = targets["horse_url"].fillna("").astype(str)

    missing = targets[
        ~targets["horse_key_norm"].isin(existing_keys)
        & targets["horse_key_norm"].ne("")
        & targets["url"].str.contains("HorseFullForm", case=False, na=False)
    ].copy()

    print("TOTAL RUNNERS:", len(targets))
    print("EXISTING FORM KEYS:", len(existing_keys))
    print("TO SCRAPE:", len(missing))

    new_rows = []
    report = []

    for i, r in missing.iterrows():
        horse = clean(r["horse"])
        horse_key = compact(r["horse_key"] or horse)
        url = clean(r["url"])

        print(f"[{len(report)+1}/{len(missing)}] {horse} {horse_key}")

        try:
            html = fetch_html(url)
            rows = parse_form_rows(horse, horse_key, url, html)

            if not rows:
                code = extract_horse_code(url) or horse_key
                (DEBUG_DIR / f"{horse_key}_{code}.html").write_text(html, encoding="utf-8", errors="ignore")

            new_rows.extend(rows)
            report.append({
                "horse": horse,
                "horse_key": horse_key,
                "url": url,
                "status": "OK" if rows else "NO_ROWS",
                "rows": len(rows),
            })

        except Exception as e:
            report.append({
                "horse": horse,
                "horse_key": horse_key,
                "url": url,
                "status": "ERROR",
                "rows": 0,
                "error": repr(e),
            })

        time.sleep(0.8)

    add = pd.DataFrame(new_rows)

    if not add.empty:
        base = existing.drop(columns=["horse_key_norm"], errors="ignore").copy() if not existing.empty else pd.DataFrame()
        combined = pd.concat([base, add], ignore_index=True)

        combined["horse_key_norm"] = combined.apply(lambda r: compact(r.get("horse_key") or r.get("horse")), axis=1)
        combined["_dedupe"] = (
            combined["horse_key_norm"].astype(str) + "|" +
            combined["run_date"].astype(str) + "|" +
            combined["track"].astype(str) + "|" +
            combined["distance"].astype(str) + "|" +
            combined["finish_pos"].astype(str) + "|" +
            combined["run_type"].astype(str)
        )

        combined = combined.drop_duplicates("_dedupe", keep="first")
        combined = combined.drop(columns=["horse_key_norm", "_dedupe"], errors="ignore")

        combined.to_csv(FULL, index=False)
        combined.to_csv(RUNS, index=False)

    rep = pd.DataFrame(report)
    rep.to_csv(OUT_REPORT, index=False)

    updated = pd.read_csv(FULL, low_memory=False)
    updated["horse_key_norm"] = updated.apply(lambda r: compact(r.get("horse_key") or r.get("horse")), axis=1)
    updated_keys = set(updated["horse_key_norm"].dropna().astype(str))

    still_missing = targets[~targets["horse_key_norm"].isin(updated_keys)].copy()
    still_missing.to_csv(OUT_MISSING, index=False)

    print()
    print("BULLETPROOF SCRAPE COMPLETE")
    print("NEW ROWS:", len(add))
    print("STILL MISSING:", len(still_missing))
    print("WROTE:", FULL)
    print("WROTE:", RUNS)
    print("WROTE:", OUT_REPORT)
    print("WROTE:", OUT_MISSING)


if __name__ == "__main__":
    main()
