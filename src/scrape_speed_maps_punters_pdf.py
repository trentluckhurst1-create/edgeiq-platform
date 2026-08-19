from __future__ import annotations

import argparse
import re
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 30


# ============================================================
# SCRAPE SPEED MAPS (REWRITE)
# ------------------------------------------------------------
# Goal:
#   Build a cleaner speed_map_report.csv that can actually join to
#   your worksheet UI.
#
# Key fixes over old version:
#   - horse names cleaned to match race_fields / ratings universe
#   - race_date / track / race_no preserved from race_fields
#   - speed_map_group inferred even when source only provides text
#   - no useless raw values like "1. Lucky Chance (5)"
#
# Input:
#   race_fields.csv
#
# Output:
#   speed_map_report.csv
# ============================================================


def norm_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return "" if text.lower() in {"nan", "none", "null"} else text



def normalize_horse_name(value: object) -> str:
    text = norm_text(value).upper()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^A-Z0-9 ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text



def clean_horse_display(value: object) -> str:
    text = norm_text(value)
    text = re.sub(r"^\d+\.\s*", "", text)
    text = re.sub(r"\s*\((\d+)\)\s*$", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text



def clean_track_name(value: object) -> str:
    text = norm_text(value)
    text = re.sub(r"^(bet365|Ladbrokes|Sportsbet)\s+", "", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()



def slugify_track(value: object) -> str:
    text = norm_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text



def safe_int(value: object) -> Optional[int]:
    m = re.search(r"\d+", norm_text(value))
    return int(m.group()) if m else None



def build_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-AU,en;q=0.9",
        }
    )
    return s



def load_fields(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)

    def find_col(options: list[str]) -> str | None:
        lower_map = {str(c).lower(): c for c in df.columns}
        for opt in options:
            if opt.lower() in lower_map:
                return lower_map[opt.lower()]
        return None

    col_race_date = find_col(["race_date", "date"])
    col_track = find_col(["track", "meeting", "venue"])
    col_race_no = find_col(["race_no", "race", "race_number"])
    col_horse = find_col(["horse", "runner", "horse_name"])

    missing = []
    if not col_race_date:
        missing.append("race_date/date")
    if not col_track:
        missing.append("track/meeting/venue")
    if not col_race_no:
        missing.append("race_no/race/race_number")
    if not col_horse:
        missing.append("horse/runner/horse_name")

    if missing:
        raise ValueError(f"Input CSV missing required columns: {missing}. Available: {list(df.columns)}")

    out = df.copy()
    out["race_date"] = pd.to_datetime(out[col_race_date], errors="coerce").dt.strftime("%Y-%m-%d")
    out["track"] = out[col_track].map(norm_text)
    out["race_no"] = out[col_race_no].apply(safe_int)
    out["horse"] = out[col_horse].map(norm_text)
    out["horse_norm"] = out["horse"].map(normalize_horse_name)

    return out



def build_speedmap_url(race_date: str, track: str, race_no: int) -> str:
    date_part = pd.to_datetime(race_date).strftime("%Y-%m-%d")
    track_slug = slugify_track(track)
    return f"https://www.racing.com/form/{date_part}/{track_slug}/race/{race_no}/speedmap"



def fetch_html(session: requests.Session, url: str) -> str:
    r = session.get(url, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.text



def infer_group_from_comment(comment: str, rank: int, field_size: int) -> str:
    c = norm_text(comment).lower()

    if any(x in c for x in ["leader", "lead", "front"]):
        return "Leader"
    if any(x in c for x in ["on pace", "forward", "prominent", "up there"]):
        return "On Pace"
    if any(x in c for x in ["midfield", "mid field", "middle"]):
        return "Midfield"
    if any(x in c for x in ["back", "rear", "backmarker", "get back"]):
        return "Backmarker"

    # Fallback from rank if source gives only ordering.
    if field_size <= 0:
        return "Unknown"
    if rank <= max(1, round(field_size * 0.2)):
        return "Leader"
    if rank <= max(2, round(field_size * 0.45)):
        return "On Pace"
    if rank <= max(3, round(field_size * 0.75)):
        return "Midfield"
    return "Backmarker"



def parse_speedmap_entries(html_text: str) -> list[dict]:
    soup = BeautifulSoup(html_text, "html.parser")
    rows: list[dict] = []

    # First pass: tabular-ish rows/cards containing horse-like text.
    candidates = soup.find_all(["tr", "li", "div", "article"])
    seen = set()
    rank = 0

    for node in candidates:
        text = node.get_text(" ", strip=True)
        if not text:
            continue
        if not re.search(r"\b\d+\.\s*[A-Za-z]", text):
            continue

        horse_raw_match = re.search(r"\b(\d+\.\s*[^|]+?)\s*(?:\||$)", text)
        horse_raw = horse_raw_match.group(1).strip() if horse_raw_match else text
        horse_clean = clean_horse_display(horse_raw)
        horse_norm = normalize_horse_name(horse_clean)
        if not horse_norm or horse_norm in seen:
            continue
        seen.add(horse_norm)

        barrier_match = re.search(r"\((\d+)\)\s*$", horse_raw)
        barrier = int(barrier_match.group(1)) if barrier_match else None

        group_text = ""
        for token in ["Leader", "On Pace", "Midfield", "Backmarker"]:
            if token.lower() in text.lower():
                group_text = token
                break

        rank += 1
        rows.append(
            {
                "horse": horse_clean,
                "horse_key": horse_norm,
                "barrier": barrier,
                "speed_map_group": group_text,
                "speed_map_rank": rank,
                "map_comment": text,
            }
        )

    field_size = len(rows)
    for row in rows:
        if not norm_text(row["speed_map_group"]):
            row["speed_map_group"] = infer_group_from_comment(
                comment=row["map_comment"],
                rank=int(row["speed_map_rank"]),
                field_size=field_size,
            )

    return rows



def scrape_race_speedmap(session: requests.Session, race_date: str, track: str, race_no: int, expected_horses: list[str], sleep_seconds: float) -> pd.DataFrame:
    url = build_speedmap_url(race_date, track, race_no)
    time.sleep(max(0.0, sleep_seconds))
    html_text = fetch_html(session, url)

    parsed = parse_speedmap_entries(html_text)
    if not parsed:
        return pd.DataFrame(columns=[
            "race_date", "track", "race_no", "horse", "horse_key", "barrier",
            "speed_map_group", "speed_map_rank", "map_comment", "source_url", "source"
        ])

    df = pd.DataFrame(parsed)
    df["race_date"] = race_date
    df["track"] = track
    df["race_no"] = race_no
    df["source_url"] = url
    df["source"] = "Racing.com"

    expected_norm = {normalize_horse_name(h) for h in expected_horses if normalize_horse_name(h)}
    if expected_norm:
        df = df[df["horse_key"].isin(expected_norm)].copy()

    return df[[
        "race_date", "track", "race_no", "horse", "horse_key", "barrier",
        "speed_map_group", "speed_map_rank", "map_comment", "source_url", "source"
    ]]



def run_scrape(input_csv: Path, output_csv: Path, sleep_seconds: float) -> Path:
    fields = load_fields(input_csv)
    session = build_session()
    collected: list[pd.DataFrame] = []

    races = (
        fields[["race_date", "track", "race_no"]]
        .drop_duplicates()
        .sort_values(["race_date", "track", "race_no"])
        .itertuples(index=False)
    )
    races = list(races)

    for idx, race in enumerate(races, start=1):
        race_date, track, race_no = race
        race_df = fields[
            (fields["race_date"] == race_date)
            & (fields["track"] == track)
            & (fields["race_no"] == race_no)
        ].copy()
        print(f"[{idx}/{len(races)}] {track} {race_date} R{race_no}")
        try:
            speed_df = scrape_race_speedmap(
                session=session,
                race_date=race_date,
                track=track,
                race_no=int(race_no),
                expected_horses=race_df["horse"].tolist(),
                sleep_seconds=sleep_seconds,
            )
            print(f"  matched: {len(speed_df)}/{len(race_df)}")
            collected.append(speed_df)
        except Exception as exc:
            print(f"  [ERROR] {exc}")

    final = pd.concat(collected, ignore_index=True) if collected else pd.DataFrame(columns=[
        "race_date", "track", "race_no", "horse", "horse_key", "barrier",
        "speed_map_group", "speed_map_rank", "map_comment", "source_url", "source"
    ])
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(output_csv, index=False)
    return output_csv



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rewrite speed map scraper")
    parser.add_argument("--input-csv", required=True, help="Path to race_fields.csv")
    parser.add_argument("--output-csv", required=True, help="Path to speed_map_report.csv")
    parser.add_argument("--sleep-seconds", type=float, default=0.5)
    return parser.parse_args()



def main() -> None:
    args = parse_args()
    input_csv = Path(args.input_csv)
    output_csv = Path(args.output_csv)

    print("=== SCRAPE SPEED MAPS (REWRITE) ===")
    print(f"Input:  {input_csv.resolve()}")
    print(f"Output: {output_csv.resolve()}")
    print(f"Sleep:  {args.sleep_seconds}s")

    written = run_scrape(input_csv=input_csv, output_csv=output_csv, sleep_seconds=args.sleep_seconds)

    print("\n✅ Completed")
    print(f"  output: {written.resolve()}")


if __name__ == "__main__":
    main()
