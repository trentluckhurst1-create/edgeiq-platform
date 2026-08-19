# scrape_ra_horse_form_cards.py
# Dedicated Racing Australia horse form-card scraper
#
# Outputs:
#   1) horses_master.csv
#   2) horse_runs_ra.csv
#   3) upcoming_runner_ra_snapshot.csv
#
# Usage example:
#   python scrape_ra_horse_form_cards.py ^
#       --runners-csv data\upcoming\race_fields.csv ^
#       --out-dir outputs\ra_form_cards ^
#       --state VIC ^
#       --max-horses 0
#
# Notes:
# - This script scrapes Racing Australia "FreeFields/Form.aspx?Key=..."
# - It groups upcoming runners by meeting/date, loads the RA meeting form page,
#   then parses each horse block and every historical run shown for that horse.
# - It preserves raw text fields anywhere parsing is messy.
#
# Requirements:
#   pip install requests beautifulsoup4 pandas lxml

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Iterable
from urllib.parse import quote

import pandas as pd
import requests
from bs4 import BeautifulSoup


BASE_CAL_URL = "https://www.racingaustralia.horse/FreeFields/Calendar.aspx?State={state}"
BASE_FORM_URL = "https://www.racingaustralia.horse/FreeFields/Form.aspx?Key={key}&recentForm=Y"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


# ----------------------------
# Helpers
# ----------------------------

def clean_text(x: Optional[str]) -> str:
    if x is None:
        return ""
    x = x.replace("\xa0", " ")
    x = re.sub(r"[ \t]+", " ", x)
    x = re.sub(r"\s*\n\s*", "\n", x)
    return x.strip()


def slugify(s: str) -> str:
    s = clean_text(s).lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def horse_key(name: str) -> str:
    return slugify(name)


def meeting_key_hash(meeting_date: str, track: str) -> str:
    return hashlib.md5(f"{meeting_date}|{track}".encode("utf-8")).hexdigest()[:12]


def parse_money(s: str) -> Optional[float]:
    s = clean_text(s)
    m = re.search(r"\$([\d,]+(?:\.\d+)?)", s)
    if not m:
        return None
    return float(m.group(1).replace(",", ""))


def parse_float(s: str) -> Optional[float]:
    s = clean_text(s)
    if s == "":
        return None
    try:
        return float(s)
    except:
        return None


def parse_int(s: str) -> Optional[int]:
    s = clean_text(s)
    m = re.search(r"-?\d+", s)
    if not m:
        return None
    return int(m.group(0))


def coalesce_row_value(row: pd.Series, candidates: List[str]) -> Optional[str]:
    row_l = {str(c).lower(): c for c in row.index}
    for cand in candidates:
        if cand.lower() in row_l:
            v = row[row_l[cand.lower()]]
            if pd.notna(v):
                s = str(v).strip()
                if s != "":
                    return s
    return None


def normalize_date_to_ra_key_part(s: str) -> Optional[str]:
    """
    Convert common date values to Racing Australia key date format: 2026Mar18
    """
    if s is None or str(s).strip() == "":
        return None

    raw = str(s).strip()

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%Y%b%d")
        except:
            pass

    try:
        dt = pd.to_datetime(raw)
        if pd.isna(dt):
            return None
        return pd.Timestamp(dt).strftime("%Y%b%d")
    except:
        return None


def normalize_track_name(s: str) -> str:
    s = clean_text(s)
    s = s.replace("(Night)", "").strip()
    s = re.sub(r"\s+", " ", s)
    return s


def first_non_null(*vals):
    for v in vals:
        if v is not None and str(v).strip() != "":
            return v
    return None


# ----------------------------
# HTTP
# ----------------------------

class RAClient:
    def __init__(self, sleep_seconds: float = 0.8, timeout: int = 30):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.sleep_seconds = sleep_seconds
        self.timeout = timeout

    def get(self, url: str) -> requests.Response:
        time.sleep(self.sleep_seconds)
        r = self.session.get(url, timeout=self.timeout)
        r.raise_for_status()
        return r

    def get_soup(self, url: str) -> BeautifulSoup:
        r = self.get(url)
        return BeautifulSoup(r.text, "lxml")


# ----------------------------
# Parsing stats lines
# ----------------------------

STAT_TOKEN_RE = re.compile(r"([A-Za-z/()' .-]+):\s*([^:]+?)(?=(?:\s+[A-Za-z/()' .-]+:\s)|$)")


def parse_stat_line(line: str) -> Dict[str, str]:
    """
    Generic parser for lines like:
      Record: 15:1-1-0     Prizemoney:$27,435    1st Up: 3:1-0-0
      Track: 3:0-0-0       Dist: 8:0-1-0         Track/Dist: 3:0-0-0
      Firm: 0:0-0-0        Good: 7:0-1-0         Soft: 6:0-0-0
    """
    line = clean_text(line)
    out: Dict[str, str] = {}
    for m in STAT_TOKEN_RE.finditer(line):
        k = clean_text(m.group(1)).lower()
        v = clean_text(m.group(2))
        out[k] = v
    return out


def split_record_triplet(v: Optional[str], prefix: str) -> Dict[str, Optional[int]]:
    out = {
        f"{prefix}_starts": None,
        f"{prefix}_wins": None,
        f"{prefix}_seconds": None,
        f"{prefix}_thirds": None,
    }
    if not v:
        return out
    m = re.match(r"(\d+)\s*:\s*(\d+)\s*-\s*(\d+)\s*-\s*(\d+)", clean_text(v))
    if not m:
        return out
    out[f"{prefix}_starts"] = int(m.group(1))
    out[f"{prefix}_wins"] = int(m.group(2))
    out[f"{prefix}_seconds"] = int(m.group(3))
    out[f"{prefix}_thirds"] = int(m.group(4))
    return out


# ----------------------------
# Parsing run lines
# ----------------------------

RUN_LINE_RE = re.compile(
    r"""
    ^
    (?:(?P<prefix>[A-Z])\s+)?                             # T / J / etc optional
    (?P<finish>\d+)\s+of\s+(?P<field_size>\d+)\s+
    (?P<track>[A-Z ]{2,10})\s+
    (?P<date>\d{2}[A-Za-z]{3}\d{2})\s+
    (?P<distance>\d{3,4})m\s+
    (?P<going>[A-Za-z0-9\-]+(?:\s*[A-Za-z0-9\-]+)?)\s+
    (?P<race_class>.+?)\s+
    \$?(?P<prizemoney>[\d,]+)
    (?:\s+\(\$(?P<earnings>[\d,]+)\))?
    \s+(?P<jockey>.+?)\s+
    (?P<weight>\d+(?:\.\d+)?)kg
    (?:\s+\(cd\s+(?P<cd_weight>\d+(?:\.\d+)?)kg\))?
    \s+Barrier\s+(?P<barrier>\d+)
    (?:\s+Rtg\s+(?P<rating>\d+))?
    $
    """,
    re.VERBOSE,
)


def parse_run_header_line(line: str) -> Dict[str, object]:
    line = clean_text(line)
    out: Dict[str, object] = {"run_header_raw": line}

    m = RUN_LINE_RE.match(line)
    if not m:
        out["run_header_parse_ok"] = False
        return out

    d = m.groupdict()
    out["run_header_parse_ok"] = True
    out["run_prefix"] = d.get("prefix")
    out["finish_pos"] = parse_int(d.get("finish"))
    out["field_size"] = parse_int(d.get("field_size"))
    out["track_code"] = clean_text(d.get("track"))
    out["run_date_ra"] = clean_text(d.get("date"))
    out["distance_m"] = parse_int(d.get("distance"))
    out["going"] = clean_text(d.get("going"))
    out["race_class"] = clean_text(d.get("race_class"))
    out["race_prizemoney"] = parse_float((d.get("prizemoney") or "").replace(",", ""))
    out["earnings"] = parse_float((d.get("earnings") or "").replace(",", "")) if d.get("earnings") else None
    out["jockey"] = clean_text(d.get("jockey"))
    out["weight_kg"] = parse_float(d.get("weight"))
    out["cd_weight_kg"] = parse_float(d.get("cd_weight"))
    out["barrier"] = parse_int(d.get("barrier"))
    out["rating"] = parse_int(d.get("rating"))
    return out


def parse_run_detail_line(line: str) -> Dict[str, object]:
    """
    Example:
      1st Better Breakout 59.5kg, 3rd March Madness 54kg 1:10.92, 1.55L, 3rd@800m, 1st@400m, $9.50/$10/$11/$10

    Or:
      1st She's A Sweet Star 55kg, 2nd Niven 58.5kg 1:11.23 (600m 36.03), 12.91L $3.10EF
    """
    line = clean_text(line)
    out: Dict[str, object] = {"run_detail_raw": line}

    if not line:
        return out

    # Winner / second section
    m = re.match(
        r"1st\s+(?P<winner>.+?)\s+(?P<winner_wt>\d+(?:\.\d+)?)kg,\s+"
        r"2nd\s+(?P<second>.+?)\s+(?P<second_wt>\d+(?:\.\d+)?)kg\s+"
        r"(?P<tail>.+)$",
        line
    )
    if m:
        out["winner_name"] = clean_text(m.group("winner"))
        out["winner_weight_kg"] = parse_float(m.group("winner_wt"))
        out["second_name"] = clean_text(m.group("second"))
        out["second_weight_kg"] = parse_float(m.group("second_wt"))
        tail = clean_text(m.group("tail"))
    else:
        # Alternate "1st ..., 3rd ..."
        m = re.match(
            r"1st\s+(?P<winner>.+?)\s+(?P<winner_wt>\d+(?:\.\d+)?)kg,\s+"
            r"3rd\s+(?P<third>.+?)\s+(?P<third_wt>\d+(?:\.\d+)?)kg\s+"
            r"(?P<tail>.+)$",
            line
        )
        if m:
            out["winner_name"] = clean_text(m.group("winner"))
            out["winner_weight_kg"] = parse_float(m.group("winner_wt"))
            out["third_name"] = clean_text(m.group("third"))
            out["third_weight_kg"] = parse_float(m.group("third_wt"))
            tail = clean_text(m.group("tail"))
        else:
            tail = line

    out["detail_tail"] = tail

    # Time
    m_time = re.search(r"(\d+:\d+\.\d+)", tail)
    if m_time:
        out["race_time"] = m_time.group(1)

    # Sectional in parentheses
    m_sec = re.search(r"\(([^)]+)\)", tail)
    if m_sec:
        out["sectional_text"] = clean_text(m_sec.group(1))

    # Margin
    m_margin = re.search(r"(\d+(?:\.\d+)?)L", tail)
    if m_margin:
        out["margin_l"] = parse_float(m_margin.group(1))

    # In-run positions
    positions = re.findall(r"(\d+(?:st|nd|rd|th)@\d+m)", tail)
    if positions:
        out["in_run_positions"] = " | ".join(positions)

    # Odds
    # Example: $9.50/$10/$11/$10 or $3.10EF
    m_odds = re.search(r"(\$[0-9./A-Za-z]+(?:/[0-9.$A-Za-z]+)*)$", tail)
    if m_odds:
        out["odds_text"] = clean_text(m_odds.group(1))

    return out


# ----------------------------
# Meeting page parsing
# ----------------------------

def extract_text_lines_from_form_page(html: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")

    # Prefer body visible text. Keep line breaks.
    text = soup.get_text("\n", strip=False)
    lines = [clean_text(x) for x in text.split("\n")]
    lines = [x for x in lines if x]
    return lines


def find_horse_block_starts(lines: List[str]) -> List[int]:
    starts = []
    for i, line in enumerate(lines):
        if line.startswith("Trainer: ") and i >= 1:
            starts.append(i - 1)  # previous line is usually horse header/name block
    return starts


def parse_horse_name_from_header_line(line: str) -> str:
    """
    Very defensive. On RA pages the horse name is typically the line immediately before Trainer:
    """
    line = clean_text(line)

    # Remove leading numeric saddlecloth fragments if present.
    line = re.sub(r"^\d+\s+", "", line).strip()

    # Remove short last-5 form strings if present at front.
    line = re.sub(r"^[0-9xsptj\-]{1,8}\s+", "", line, flags=re.I).strip()

    return line


def split_horse_blocks(lines: List[str]) -> List[List[str]]:
    starts = find_horse_block_starts(lines)
    if not starts:
        return []

    blocks: List[List[str]] = []
    for idx, start in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else len(lines)
        blocks.append(lines[start:end])
    return blocks


def parse_trainer_jockey_barrier_line(line: str) -> Dict[str, object]:
    """
    Example:
      Trainer: Rodney Miller (Cairns) Jockey: Jackson Murphy 58.5kg Barrier:3
    """
    line = clean_text(line)
    out = {"trainer_jockey_barrier_raw": line}

    m = re.search(
        r"Trainer:\s*(?P<trainer>.+?)\s*\((?P<trainer_loc>.*?)\)\s*"
        r"Jockey:\s*(?P<jockey>.+?)\s+(?P<jockey_weight>\d+(?:\.\d+)?)kg\s*"
        r"Barrier:?\s*(?P<barrier>\d+)",
        line,
    )
    if m:
        out["trainer"] = clean_text(m.group("trainer"))
        out["trainer_location"] = clean_text(m.group("trainer_loc"))
        out["jockey"] = clean_text(m.group("jockey"))
        out["jockey_weight_kg"] = parse_float(m.group("jockey_weight"))
        out["barrier"] = parse_int(m.group("barrier"))
    else:
        # fallback partials
        m_tr = re.search(r"Trainer:\s*(.+?)(?:\s+Jockey:|$)", line)
        m_jk = re.search(r"Jockey:\s*(.+?)(?:\s+Barrier:?|$)", line)
        m_ba = re.search(r"Barrier:?\s*(\d+)", line)
        if m_tr:
            tr = clean_text(m_tr.group(1))
            loc_m = re.match(r"(.+?)\s*\((.*?)\)$", tr)
            if loc_m:
                out["trainer"] = clean_text(loc_m.group(1))
                out["trainer_location"] = clean_text(loc_m.group(2))
            else:
                out["trainer"] = tr
        if m_jk:
            out["jockey"] = clean_text(m_jk.group(1))
        if m_ba:
            out["barrier"] = parse_int(m_ba.group(1))

    return out


def parse_horse_block(block_lines: List[str], source_url: str) -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    horse_row: Dict[str, object] = {}
    run_rows: List[Dict[str, object]] = []

    horse_header = clean_text(block_lines[0]) if block_lines else ""
    horse_name = parse_horse_name_from_header_line(horse_header)

    horse_row["horse_name"] = horse_name
    horse_row["horse_key"] = horse_key(horse_name)
    horse_row["horse_header_raw"] = horse_header
    horse_row["source_url"] = source_url

    if len(block_lines) >= 2:
        horse_row.update(parse_trainer_jockey_barrier_line(block_lines[1]))

    # Parse known stat lines
    for line in block_lines[2:6]:
        stats = parse_stat_line(line)
        if not stats:
            continue
        for k, v in stats.items():
            horse_row[f"stat_{slugify(k)}_raw"] = v

    # Expand common stat tokens
    horse_row.update(split_record_triplet(horse_row.get("stat_record_raw"), "career"))
    horse_row["prizemoney"] = parse_money(str(horse_row.get("stat_prizemoney_raw", "")))

    horse_row.update(split_record_triplet(horse_row.get("stat_1st_up_raw"), "first_up"))
    horse_row.update(split_record_triplet(horse_row.get("stat_2nd_up_raw"), "second_up"))

    horse_row.update(split_record_triplet(horse_row.get("stat_track_raw"), "track"))
    horse_row.update(split_record_triplet(horse_row.get("stat_dist_raw"), "distance"))
    horse_row.update(split_record_triplet(horse_row.get("stat_track_dist_raw"), "track_distance"))

    horse_row.update(split_record_triplet(horse_row.get("stat_firm_raw"), "firm"))
    horse_row.update(split_record_triplet(horse_row.get("stat_good_raw"), "good"))
    horse_row.update(split_record_triplet(horse_row.get("stat_soft_raw"), "soft"))
    horse_row.update(split_record_triplet(horse_row.get("stat_heavy_raw"), "heavy"))
    horse_row.update(split_record_triplet(horse_row.get("stat_synthetic_raw"), "synthetic"))

    horse_row["distance_wins_raw"] = horse_row.get("stat_distance_s_won_raw")

    # Historical runs follow as alternating header/detail lines, but not always perfect.
    i = 2
    while i < len(block_lines):
        line = block_lines[i]

        # A run header usually contains "of", date token, distance, Barrier
        if re.search(r"\bof\b", line) and re.search(r"\d{2}[A-Za-z]{3}\d{2}", line) and "Barrier" in line:
            run = {
                "horse_name": horse_name,
                "horse_key": horse_key(horse_name),
                "source_url": source_url,
            }
            run.update(parse_run_header_line(line))

            next_line = block_lines[i + 1] if i + 1 < len(block_lines) else ""
            if next_line.startswith("1st "):
                run.update(parse_run_detail_line(next_line))
                i += 1

            run_rows.append(run)

        i += 1

    horse_row["historical_runs_count_scraped"] = len(run_rows)
    horse_row["block_raw"] = "\n".join(block_lines)

    return horse_row, run_rows


# ----------------------------
# Find meeting form key
# ----------------------------

def discover_form_key_from_calendar(client: RAClient, state: str, target_date_ra: str, track_name: str) -> Optional[str]:
    """
    Visit state calendar, try to find a FreeFields/Form.aspx?Key=... link matching date and track.
    """
    url = BASE_CAL_URL.format(state=quote(state))
    soup = client.get_soup(url)

    track_norm = normalize_track_name(track_name).lower()

    # Try direct href search
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = clean_text(a.get_text(" ", strip=True))
        href_full = href

        if "FreeFields/Form.aspx?Key=" not in href_full:
            continue

        if target_date_ra not in href_full:
            continue

        text_norm = normalize_track_name(text).lower()
        if track_norm in text_norm or text_norm in track_norm:
            m = re.search(r"Key=([^&]+)", href_full)
            if m:
                return m.group(1)

    # Fallback: any key for date + track in href
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "FreeFields/Form.aspx?Key=" not in href:
            continue
        if target_date_ra not in href:
            continue
        if quote(track_name) in href or track_name.replace(" ", "%20") in href or track_norm.replace(" ", "").lower() in href.lower().replace("%20", ""):
            m = re.search(r"Key=([^&]+)", href)
            if m:
                return m.group(1)

    return None


# ----------------------------
# Upcoming runners preparation
# ----------------------------

def standardize_upcoming_runners(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tries to support common column names from your pipeline.
    """
    rows = []
    for _, r in df.iterrows():
        race_date = coalesce_row_value(r, ["race_date", "meeting_date", "date"])
        track = coalesce_row_value(r, ["track", "meeting", "venue", "track_name"])
        race_no = coalesce_row_value(r, ["race_no", "race_number", "race"])
        horse = coalesce_row_value(r, ["horse", "runner", "horse_name"])
        trainer = coalesce_row_value(r, ["trainer"])
        jockey = coalesce_row_value(r, ["jockey"])
        weight = coalesce_row_value(r, ["weight", "allocated_weight", "wt"])
        barrier = coalesce_row_value(r, ["barrier", "gate"])

        if not race_date or not track or not horse:
            continue

        rows.append({
            "race_date": str(race_date).strip(),
            "track": normalize_track_name(str(track)),
            "race_no": parse_int(str(race_no)) if race_no is not None else None,
            "horse_name": clean_text(str(horse)),
            "horse_key": horse_key(str(horse)),
            "trainer_upcoming": clean_text(str(trainer)) if trainer is not None else None,
            "jockey_upcoming": clean_text(str(jockey)) if jockey is not None else None,
            "weight_upcoming": parse_float(str(weight)) if weight is not None else None,
            "barrier_upcoming": parse_int(str(barrier)) if barrier is not None else None,
        })

    out = pd.DataFrame(rows)
    if out.empty:
        raise ValueError("Could not infer required columns from runners CSV.")
    return out


# ----------------------------
# Main scrape flow
# ----------------------------

def scrape_ra_form_cards(
    runners_csv: str,
    out_dir: str,
    state: str,
    max_horses: int = 0,
    sleep_seconds: float = 0.8,
) -> None:
    os.makedirs(out_dir, exist_ok=True)

    client = RAClient(sleep_seconds=sleep_seconds)

    upcoming_raw = pd.read_csv(runners_csv)
    upcoming = standardize_upcoming_runners(upcoming_raw)

    # Deduplicate meetings
    meetings = (
        upcoming[["race_date", "track"]]
        .drop_duplicates()
        .sort_values(["race_date", "track"])
        .reset_index(drop=True)
    )

    horses_master_rows: List[Dict[str, object]] = []
    horse_runs_rows: List[Dict[str, object]] = []
    meeting_horse_lookup: Dict[Tuple[str, str], Dict[str, Dict[str, object]]] = {}

    for _, mrow in meetings.iterrows():
        race_date = str(mrow["race_date"])
        track = str(mrow["track"])
        target_date_ra = normalize_date_to_ra_key_part(race_date)

        if not target_date_ra:
            print(f"[WARN] Could not parse race_date for meeting: {race_date} {track}")
            continue

        form_key = discover_form_key_from_calendar(client, state=state, target_date_ra=target_date_ra, track_name=track)

        if not form_key:
            print(f"[WARN] Could not find RA form key for {race_date} | {track}")
            continue

        form_url = BASE_FORM_URL.format(key=form_key)
        print(f"[INFO] Scraping meeting form page: {race_date} | {track}")
        print(f"       {form_url}")

        html = client.get(form_url).text
        lines = extract_text_lines_from_form_page(html)
        horse_blocks = split_horse_blocks(lines)

        lookup: Dict[str, Dict[str, object]] = {}
        runs_count_before = len(horse_runs_rows)

        for block in horse_blocks:
            horse_row, run_rows = parse_horse_block(block, source_url=form_url)

            if not horse_row.get("horse_name"):
                continue

            horse_row["meeting_date_context"] = race_date
            horse_row["meeting_track_context"] = track
            horse_row["meeting_hash"] = meeting_key_hash(race_date, track)

            horses_master_rows.append(horse_row)
            horse_runs_rows.extend(run_rows)
            lookup[horse_key(horse_row["horse_name"])] = horse_row

            if max_horses and len(horses_master_rows) >= max_horses:
                break

        meeting_horse_lookup[(race_date, track)] = lookup
        print(
            f"[OK] {race_date} | {track} | horses={len(lookup)} "
            f"| runs_added={len(horse_runs_rows) - runs_count_before}"
        )

        if max_horses and len(horses_master_rows) >= max_horses:
            break

    horses_master = pd.DataFrame(horses_master_rows).drop_duplicates(subset=["horse_key"], keep="first")
    horse_runs = pd.DataFrame(horse_runs_rows)

    # Link upcoming runners back to horse profile
    snapshots = []
    for _, r in upcoming.iterrows():
        race_date = r["race_date"]
        track = r["track"]
        hk = r["horse_key"]
        profile = meeting_horse_lookup.get((race_date, track), {}).get(hk, {})

        snap = dict(r)
        snap["ra_profile_found"] = bool(profile)
        snap["ra_source_url"] = profile.get("source_url")
        snap["ra_trainer"] = profile.get("trainer")
        snap["ra_trainer_location"] = profile.get("trainer_location")
        snap["ra_jockey"] = profile.get("jockey")
        snap["ra_card_weight_kg"] = profile.get("jockey_weight_kg")
        snap["ra_barrier"] = profile.get("barrier")
        snap["ra_career_starts"] = profile.get("career_starts")
        snap["ra_career_wins"] = profile.get("career_wins")
        snap["ra_career_seconds"] = profile.get("career_seconds")
        snap["ra_career_thirds"] = profile.get("career_thirds")
        snap["ra_prizemoney"] = profile.get("prizemoney")
        snap["ra_historical_runs_count_scraped"] = profile.get("historical_runs_count_scraped")
        snapshots.append(snap)

    upcoming_snapshot = pd.DataFrame(snapshots)

    # Add run_id
    if not horse_runs.empty:
        horse_runs = horse_runs.copy()
        horse_runs["run_id"] = (
            horse_runs["horse_key"].astype(str)
            + "__"
            + horse_runs["run_date_ra"].fillna("").astype(str)
            + "__"
            + horse_runs["track_code"].fillna("").astype(str)
            + "__"
            + horse_runs["distance_m"].fillna("").astype(str)
        )

    horses_master_path = os.path.join(out_dir, "horses_master.csv")
    horse_runs_path = os.path.join(out_dir, "horse_runs_ra.csv")
    upcoming_snapshot_path = os.path.join(out_dir, "upcoming_runner_ra_snapshot.csv")

    horses_master.to_csv(horses_master_path, index=False)
    horse_runs.to_csv(horse_runs_path, index=False)
    upcoming_snapshot.to_csv(upcoming_snapshot_path, index=False)

    print("\n=== DONE ===")
    print(f"[OK] Wrote: {horses_master_path} | rows={len(horses_master)}")
    print(f"[OK] Wrote: {horse_runs_path} | rows={len(horse_runs)}")
    print(f"[OK] Wrote: {upcoming_snapshot_path} | rows={len(upcoming_snapshot)}")


# ----------------------------
# CLI
# ----------------------------

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Scrape Racing Australia horse form cards for upcoming runners")
    ap.add_argument("--runners-csv", required=True, help="CSV of upcoming runners")
    ap.add_argument("--out-dir", required=True, help="Output directory")
    ap.add_argument("--state", default="VIC", help="RA state calendar to use, e.g. VIC/NSW/QLD")
    ap.add_argument("--max-horses", type=int, default=0, help="Optional cap for testing; 0 = no cap")
    ap.add_argument("--sleep-seconds", type=float, default=0.8, help="Polite delay between requests")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    scrape_ra_form_cards(
        runners_csv=args.runners_csv,
        out_dir=args.out_dir,
        state=args.state,
        max_horses=args.max_horses,
        sleep_seconds=args.sleep_seconds,
    )


if __name__ == "__main__":
    main()