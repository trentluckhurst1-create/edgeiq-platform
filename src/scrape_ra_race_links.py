from __future__ import annotations

import argparse
import csv
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)
TIMEOUT = 30
RA_BASE = "https://www.racingaustralia.horse/"
RA_ACCEPTANCES = "https://www.racingaustralia.horse/FreeFields/Acceptances.aspx"
RA_HORSE_FORM = "https://www.racingaustralia.horse/InteractiveForm/HorseAllForm.aspx"


# =========================================================
# SCRAPE RA RACE LINKS (FIXED)
# ---------------------------------------------------------
# Input:
#   data/upcoming/race_fields.csv
#   Must contain at least: race_date, state, track, race_no, horse
#
# Output dir:
#   outputs/ra_form/
#   writes: upcoming_runner_ra_links.csv
#
# Purpose:
#   For every upcoming runner, find the Racing Australia horse link
#   from the Acceptances page and extract:
#     - horse_code
#     - race_entry
#     - ra_all_form_url
# =========================================================


REQUIRED_COLUMNS = ["race_date", "state", "track", "race_no", "horse"]


def norm_text(value: object) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = str(value).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if text.lower() in {"nan", "none", "null", "na", "n/a"}:
        return ""
    return text



def safe_int(value: object) -> Optional[int]:
    text = norm_text(value)
    if not text:
        return None
    match = re.search(r"\d+", text)
    return int(match.group()) if match else None



def normalize_horse_name(value: object) -> str:
    text = norm_text(value).upper()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^A-Z0-9 ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text



def slugify_track(track: str) -> str:
    text = norm_text(track)
    text = re.sub(r"\s+", " ", text).strip()
    return text



def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-AU,en;q=0.9",
            "Referer": RA_BASE,
        }
    )
    return s



def fetch_html(session: requests.Session, url: str, sleep_seconds: float = 0.0) -> str:
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)
    response = session.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    return response.text



def build_acceptances_url(race_date: str, state: str, track: str) -> str:
    dt = pd.to_datetime(race_date).strftime("%Y%b%d")
    track_part = slugify_track(track).replace(" ", "%20")
    key = f"{dt},{state.upper()},{track_part}"
    return f"{RA_ACCEPTANCES}?Key={key}"



def extract_ra_params(url: str) -> Tuple[str, str]:
    parsed = urlparse(norm_text(url).replace("&amp;", "&"))
    qs_raw = parse_qs(parsed.query)
    qs = {k.lower(): v for k, v in qs_raw.items()}
    horse_code = norm_text(qs.get("horsecode", [""])[0])
    race_entry = norm_text(qs.get("raceentry", [""])[0])
    return horse_code, race_entry



def build_ra_all_form_url(horse_code: str, race_entry: str) -> str:
    return f"{RA_HORSE_FORM}?HorseCode={horse_code}&src=horseform&raceEntry={race_entry}"

def choose_race_fields(df: pd.DataFrame) -> pd.DataFrame:
    # ---------- AUTO DETECT COLUMNS ----------
    def find_col(options):
        for opt in options:
            for col in df.columns:
                if col.lower() == opt.lower():
                    return col
        return None

    col_race_date = find_col(["race_date", "date"])
    col_state = find_col(["state"])
    col_track = find_col(["track"])
    col_race_no = find_col(["race_no", "race", "race_number"])
    col_horse = find_col(["horse", "runner", "horse_name"])

    missing = []
    if not col_race_date: missing.append("race_date/date")
    if not col_state: missing.append("state")
    if not col_track: missing.append("track")
    if not col_race_no: missing.append("race_no/race")
    if not col_horse: missing.append("horse/runner")

    if missing:
        raise ValueError(f"Missing required columns: {missing}\nAvailable: {list(df.columns)}")

    # ---------- BUILD CLEAN DF ----------
    out = pd.DataFrame({
        "race_date": pd.to_datetime(df[col_race_date], errors="coerce").dt.strftime("%Y-%m-%d"),
        "state": df[col_state].map(norm_text),
        "track": df[col_track].map(norm_text),
        "race_no": df[col_race_no].apply(safe_int),
        "horse": df[col_horse].map(norm_text),
    })

    # Optional extras if exist
    optional_cols = [
        "barrier", "weight", "jockey", "trainer", "race_name", "race_class"
    ]

    for c in optional_cols:
        if c in df.columns:
            out[c] = df[c]

    out = out.dropna(subset=["race_date", "race_no"])
    out = out[out["horse"] != ""].copy()

    return out.reset_index(drop=True)


def discover_meeting_horse_links(session: requests.Session, meeting_url: str, sleep_seconds: float) -> pd.DataFrame:
    html_text = fetch_html(session, meeting_url, sleep_seconds=sleep_seconds)
    soup = BeautifulSoup(html_text, "html.parser")

    discovered: List[Dict[str, object]] = []
    for a in soup.find_all("a", href=True):
        href = norm_text(a.get("href"))
        text = norm_text(a.get_text(" "))
        if not href:
            continue
        full_url = urljoin(meeting_url, href)
        if "HorseFullForm.aspx" not in full_url and "HorseAllForm.aspx" not in full_url:
            continue

        horse_code, race_entry = extract_ra_params(full_url)
        if not horse_code:
            continue

        # Try to infer race number from nearby context if present in parent row.
        race_no = None
        parent_text = ""
        parent = a.parent
        for _ in range(4):
            if parent is None:
                break
            parent_text = norm_text(parent.get_text(" "))
            match = re.search(r"\bR(?:ACE)?\s*(\d{1,2})\b", parent_text, flags=re.I)
            if match:
                race_no = int(match.group(1))
                break
            parent = parent.parent

        discovered.append(
            {
                "horse_link_text": text,
                "horse_norm": normalize_horse_name(text),
                "horse_code": horse_code,
                "race_entry": race_entry,
                "source_form_url": full_url,
                "ra_all_form_url": build_ra_all_form_url(horse_code, race_entry),
                "context_text": parent_text,
                "context_race_no": race_no,
            }
        )

    out = pd.DataFrame(discovered)
    if out.empty:
        return out

    out = out.drop_duplicates(subset=["horse_norm", "horse_code", "race_entry"]).reset_index(drop=True)
    return out



def match_runners_for_meeting(meeting_runners: pd.DataFrame, discovered_links: pd.DataFrame, meeting_url: str) -> pd.DataFrame:
    if discovered_links.empty:
        out = meeting_runners.copy()
        out["meeting_url"] = meeting_url
        out["horse_code"] = ""
        out["race_entry"] = ""
        out["ra_all_form_url"] = ""
        out["source_form_url"] = ""
        out["horse_link_text"] = ""
        out["link_found"] = 0
        out["link_error"] = "no_horse_links_found"
        return out

    links = discovered_links.copy()

    rows: List[Dict[str, object]] = []
    for _, runner in meeting_runners.iterrows():
        horse = norm_text(runner["horse"])
        horse_norm = normalize_horse_name(horse)
        race_no = safe_int(runner["race_no"])

        candidates = links[links["horse_norm"] == horse_norm].copy()

        if race_no is not None and not candidates.empty:
            exact_race = candidates[candidates["context_race_no"] == race_no]
            if not exact_race.empty:
                candidates = exact_race

        row = runner.to_dict()
        row["meeting_url"] = meeting_url

        if candidates.empty:
            row.update(
                {
                    "horse_code": "",
                    "race_entry": "",
                    "ra_all_form_url": "",
                    "source_form_url": "",
                    "horse_link_text": "",
                    "link_found": 0,
                    "link_error": "horse_link_not_matched",
                }
            )
        else:
            best = candidates.iloc[0]
            row.update(
                {
                    "horse_code": best.get("horse_code", ""),
                    "race_entry": best.get("race_entry", ""),
                    "ra_all_form_url": best.get("ra_all_form_url", ""),
                    "source_form_url": best.get("source_form_url", ""),
                    "horse_link_text": best.get("horse_link_text", ""),
                    "link_found": 1,
                    "link_error": "",
                }
            )
        rows.append(row)

    return pd.DataFrame(rows)



def run_discovery(input_csv: Path, output_dir: Path, max_meetings: Optional[int], sleep_seconds: float) -> Dict[str, Path]:
    source_df = pd.read_csv(input_csv, low_memory=False)
    fields = choose_race_fields(source_df)

    meetings = (
        fields[["race_date", "state", "track"]]
        .drop_duplicates()
        .sort_values(["race_date", "state", "track"])
        .reset_index(drop=True)
    )
    if max_meetings is not None and max_meetings > 0:
        meetings = meetings.head(max_meetings).copy()

    session = make_session()
    matched_frames: List[pd.DataFrame] = []

    total = len(meetings)
    for i, (_, meeting) in enumerate(meetings.iterrows(), start=1):
        race_date = meeting["race_date"]
        state = meeting["state"]
        track = meeting["track"]
        meeting_url = build_acceptances_url(race_date, state, track)

        print(f"[{i}/{total}] {race_date} {state} {track}")
        print(f"  meeting_url: {meeting_url}")

        meeting_runners = fields[
            (fields["race_date"] == race_date)
            & (fields["state"] == state)
            & (fields["track"] == track)
        ].copy()

        try:
            discovered = discover_meeting_horse_links(session, meeting_url, sleep_seconds=sleep_seconds)
            print(f"  horse links discovered: {len(discovered)}")
        except Exception as exc:
            print(f"  [ERROR] discovery failed: {exc}")
            discovered = pd.DataFrame()

        matched = match_runners_for_meeting(meeting_runners, discovered, meeting_url)
        found = int(matched["link_found"].fillna(0).sum()) if not matched.empty else 0
        print(f"  matched: {found}/{len(matched)}")
        matched_frames.append(matched)

    output_dir.mkdir(parents=True, exist_ok=True)

    runner_links = pd.concat(matched_frames, ignore_index=True) if matched_frames else pd.DataFrame()
    links_csv = output_dir / "upcoming_runner_ra_links.csv"
    runner_links.to_csv(links_csv, index=False, quoting=csv.QUOTE_MINIMAL)

    return {"runner_links": links_csv}



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover Racing Australia horse links for every runner in race_fields.csv")
    parser.add_argument("--input-csv", required=True, help="Path to race_fields.csv")
    parser.add_argument("--output-dir", required=True, help="Directory to write upcoming_runner_ra_links.csv")
    parser.add_argument("--max-meetings", type=int, default=0, help="Optional cap for testing")
    parser.add_argument("--sleep-seconds", type=float, default=0.5, help="Sleep between requests")
    return parser.parse_args()



def main() -> None:
    args = parse_args()
    input_csv = Path(args.input_csv)
    output_dir = Path(args.output_dir)

    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv.resolve()}")

    print("=== SCRAPE RA RACE LINKS (FIXED) ===")
    print(f"Input:  {input_csv.resolve()}")
    print(f"Output: {output_dir.resolve()}")
    print(f"Max meetings: {args.max_meetings or 'ALL'}")
    print(f"Sleep: {args.sleep_seconds}s")

    paths = run_discovery(
        input_csv=input_csv,
        output_dir=output_dir,
        max_meetings=args.max_meetings if args.max_meetings > 0 else None,
        sleep_seconds=args.sleep_seconds,
    )

    print("\n✅ Completed")
    for key, path in paths.items():
        print(f"  {key}: {path.resolve()}")


if __name__ == "__main__":
    main()
