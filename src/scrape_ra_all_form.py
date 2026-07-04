from __future__ import annotations

import argparse
import csv
import html
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup


BASE_FORM_URL = "https://www.racingaustralia.horse/InteractiveForm/HorseAllForm.aspx"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)
TIMEOUT = 30


@dataclass
class HorseProfile:
    horse_name: str = ""
    horse_code: str = ""
    source_url: str = ""
    race_entry: str = ""
    age_sex_colour: str = ""
    dob: str = ""
    sire: str = ""
    dam: str = ""
    status: str = ""
    owners: str = ""
    stewards_embargoes: str = ""
    last_gear_change: str = ""
    trainer: str = ""
    trainer_location: str = ""
    racing_colours: str = ""
    career_summary_raw: str = ""
    career_starts: Optional[int] = None
    career_wins: Optional[int] = None
    career_seconds: Optional[int] = None
    career_thirds: Optional[int] = None
    prizemoney: Optional[float] = None
    min_win_distance: Optional[int] = None
    max_win_distance: Optional[int] = None
    first_up_raw: str = ""
    second_up_raw: str = ""
    track_stats_raw: str = ""
    dist_stats_raw: str = ""
    track_dist_stats_raw: str = ""
    firm_stats_raw: str = ""
    good_stats_raw: str = ""
    soft_stats_raw: str = ""
    heavy_stats_raw: str = ""
    synthetic_stats_raw: str = ""
    scraped_at_utc: str = ""


@dataclass
class HorseRun:
    horse_name: str = ""
    horse_code: str = ""
    source_url: str = ""
    race_entry: str = ""
    run_index: Optional[int] = None
    run_type_code: str = ""
    run_type: str = ""
    is_official_run: int = 0
    is_trial: int = 0
    is_jumpout: int = 0
    finish_pos: Optional[int] = None
    field_size: Optional[int] = None
    track_code: str = ""
    run_date: str = ""
    distance: Optional[int] = None
    track_condition: str = ""
    race_name: str = ""
    race_class_raw: str = ""
    prizemoney_race: Optional[float] = None
    prizemoney_earned: Optional[float] = None
    jockey: str = ""
    weight: Optional[float] = None
    barrier: Optional[int] = None
    run_rating_raw: Optional[float] = None
    winner_name: str = ""
    second_name: str = ""
    third_name: str = ""
    winner_weight: Optional[float] = None
    second_weight: Optional[float] = None
    third_weight: Optional[float] = None
    race_time: str = ""
    sectional_600: Optional[float] = None
    margin: Optional[float] = None
    in_run_positions_raw: str = ""
    price_raw: str = ""
    sp: Optional[float] = None
    raw_run_text: str = ""


def norm_text(value: object) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = html.unescape(str(value))
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if text.lower() in {"nan", "none", "null", "na", "n/a"}:
        return ""
    return text


def safe_float(value: object) -> Optional[float]:
    text = norm_text(value).replace(",", "")
    if not text:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def safe_int(value: object) -> Optional[int]:
    x = safe_float(value)
    return None if x is None else int(round(x))


def parse_margin_token(token: str) -> Optional[float]:
    token = norm_text(token).upper()
    mapping = {
        "NOSE": 0.05,
        "NSE": 0.05,
        "SHORT HEAD": 0.10,
        "HEAD": 0.20,
        "LONG HEAD": 0.25,
        "NK": 0.30,
    }
    if token in mapping:
        return mapping[token]
    return safe_float(token)


def extract_all_money(text: str) -> List[float]:
    vals: List[float] = []
    for x in re.findall(r"\$([\d,]+(?:\.\d+)?)", norm_text(text)):
        num = safe_float(x)
        if num is not None:
            vals.append(num)
    return vals


def now_utc_iso() -> str:
    return pd.Timestamp.now("UTC").isoformat()


def extract_ra_params(url: str) -> Tuple[str, str]:
    parsed = urlparse(norm_text(url).replace("&amp;", "&"))
    raw_qs = parse_qs(parsed.query)
    qs = {k.lower(): v for k, v in raw_qs.items()}
    horse_code = norm_text(qs.get("horsecode", [""])[0])
    race_entry = norm_text(qs.get("raceentry", [""])[0])
    return horse_code, race_entry


def build_ra_url(horse_code: str, race_entry: str = "", src: str = "horseform") -> str:
    params = {"HorseCode": horse_code, "src": src}
    if race_entry:
        params["raceEntry"] = race_entry
    return f"{BASE_FORM_URL}?{urlencode(params)}"


def detect_first_existing(df: pd.DataFrame, names: Iterable[str]) -> Optional[str]:
    lower_map = {c.lower(): c for c in df.columns}
    for name in names:
        if name.lower() in lower_map:
            return lower_map[name.lower()]
    return None


def looks_like_ra_horse_code(text: str) -> bool:
    text = norm_text(text)
    return bool(text) and bool(re.fullmatch(r"[A-Za-z0-9%+/=]+", text)) and len(text) >= 8


def build_input_horses(df: pd.DataFrame) -> pd.DataFrame:
    url_col = detect_first_existing(
        df,
        ["ra_all_form_url", "horse_form_url", "ra_form_url", "horse_url", "form_url", "source_url"],
    )
    horse_name_col = detect_first_existing(df, ["horse", "horse_name", "runner"])
    horse_code_col = detect_first_existing(df, ["horse_code", "ra_horse_code"])
    race_entry_col = detect_first_existing(df, ["race_entry", "ra_race_entry"])

    rows: List[Dict[str, object]] = []
    for _, row in df.iterrows():
        source_url = norm_text(row.get(url_col)) if url_col else ""
        horse_name = norm_text(row.get(horse_name_col)) if horse_name_col else ""
        horse_code = norm_text(row.get(horse_code_col)) if horse_code_col else ""
        race_entry = norm_text(row.get(race_entry_col)) if race_entry_col else ""

        if source_url:
            hc, re_ = extract_ra_params(source_url)
            horse_code = horse_code or hc
            race_entry = race_entry or re_

        if horse_code and not looks_like_ra_horse_code(horse_code):
            horse_code = ""

        if not source_url and horse_code:
            source_url = build_ra_url(horse_code, race_entry)

        if not source_url and not horse_code:
            continue

        rows.append(
            {
                "horse_name_input": horse_name,
                "horse_code": horse_code,
                "race_entry": race_entry,
                "source_url": source_url,
            }
        )

    out = pd.DataFrame(rows)
    if out.empty:
        raise ValueError("No Racing Australia horse references found in input CSV.")

    out["horse_code_norm"] = out["horse_code"].astype(str).str.strip()
    out["source_url_norm"] = out["source_url"].astype(str).str.strip()
    out = out.drop_duplicates(subset=["horse_code_norm", "source_url_norm"])
    return out.reset_index(drop=True)


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-AU,en;q=0.9",
            "Referer": "https://www.racingaustralia.horse/",
        }
    )
    return s


def fetch_html(session: requests.Session, url: str, sleep_seconds: float = 0.0) -> str:
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)
    response = session.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    return response.text


def soup_lines(soup: BeautifulSoup) -> List[str]:
    lines: List[str] = []
    for raw in soup.get_text("\n").splitlines():
        line = norm_text(raw)
        if line:
            lines.append(line)
    return lines


def parse_profile(lines: List[str], source_url: str, horse_code: str, race_entry: str) -> HorseProfile:
    profile = HorseProfile(
        source_url=source_url,
        horse_code=horse_code,
        race_entry=race_entry,
        scraped_at_utc=now_utc_iso(),
    )

    for i, line in enumerate(lines[:80]):
        if re.search(r"\byo\b", line, re.I):
            if i > 0:
                profile.horse_name = norm_text(lines[i - 1])
            profile.age_sex_colour = line
            break

    i = 0
    while i < len(lines):
        line = lines[i]

        if line == "D.O.B:" and i + 1 < len(lines):
            profile.dob = norm_text(lines[i + 1])
            i += 2
            continue

        if line.lower().startswith("by "):
            m = re.match(r"by\s+(.*?)\s+from\s+(.*)$", line, flags=re.I)
            if m:
                profile.sire = norm_text(m.group(1))
                profile.dam = norm_text(m.group(2))

        if line == "Status" and i + 1 < len(lines):
            profile.status = norm_text(lines[i + 1])
            i += 2
            continue

        if line.startswith("Owner’s Details") or line.startswith("Owner's Details"):
            if i + 1 < len(lines):
                profile.owners = norm_text(lines[i + 1])
            i += 2
            continue

        if line == "Stewards Embargoes" and i + 1 < len(lines):
            profile.stewards_embargoes = norm_text(lines[i + 1])
            i += 2
            continue

        if line.startswith("Last Gear Change") and i + 1 < len(lines):
            profile.last_gear_change = norm_text(lines[i + 1])
            i += 2
            continue

        if line == "Trainer" and i + 1 < len(lines):
            profile.trainer = norm_text(lines[i + 1])
            if i + 2 < len(lines) and lines[i + 2].startswith("("):
                profile.trainer_location = norm_text(lines[i + 2]).strip("()")
                i += 3
            else:
                i += 2
            continue

        if line == "Racing Colours" and i + 1 < len(lines):
            profile.racing_colours = norm_text(lines[i + 1])
            i += 2
            continue

        if line == "Career" and i + 2 < len(lines) and lines[i + 1] == "Summary:":
            parts: List[str] = []
            j = i + 2
            while j < len(lines):
                if re.match(r"^(?:T|J)$", lines[j]):
                    break
                if re.match(r"^\d+(?:st|nd|rd|th)\s+of\s+\d+$", lines[j], flags=re.I):
                    break
                parts.append(lines[j])
                j += 1
            parse_career_block(profile, parts)
            i = j
            continue

        i += 1

    return profile


def parse_career_block(profile: HorseProfile, lines: List[str]) -> None:
    profile.career_summary_raw = " | ".join(lines)

    for idx, line in enumerate(lines):
        nxt = lines[idx + 1] if idx + 1 < len(lines) else ""

        m = re.match(r"^(\d+)-(\d+):(\d+):(\d+)$", line)
        if m:
            profile.career_starts = safe_int(m.group(1))
            profile.career_wins = safe_int(m.group(2))
            profile.career_seconds = safe_int(m.group(3))
            profile.career_thirds = safe_int(m.group(4))

        if line == "Prizemoney:" and nxt:
            profile.prizemoney = safe_float(nxt)
        elif line == "Min/Max-Dist-Win:" and nxt:
            mm = re.search(r"(\d+)/(\d+)", nxt)
            if mm:
                profile.min_win_distance = safe_int(mm.group(1))
                profile.max_win_distance = safe_int(mm.group(2))
        elif line == "1st Up:" and nxt:
            profile.first_up_raw = nxt
        elif line == "2nd Up:" and nxt:
            profile.second_up_raw = nxt
        elif line == "Track:" and nxt:
            profile.track_stats_raw = nxt
        elif line == "Dist:" and nxt:
            profile.dist_stats_raw = nxt
        elif line == "Track/Dist:" and nxt:
            profile.track_dist_stats_raw = nxt
        elif line == "Firm:" and nxt:
            profile.firm_stats_raw = nxt
        elif line == "Good:" and nxt:
            profile.good_stats_raw = nxt
        elif line == "Soft:" and nxt:
            profile.soft_stats_raw = nxt
        elif line == "Heavy:" and nxt:
            profile.heavy_stats_raw = nxt
        elif line == "Synthetic:" and nxt:
            profile.synthetic_stats_raw = nxt


def parse_runs(lines: List[str], horse_name: str, horse_code: str, source_url: str, race_entry: str) -> List[HorseRun]:
    runs: List[HorseRun] = []

    starts: List[int] = []
    for i, line in enumerate(lines):
        if line in {"T", "J"} and i + 1 < len(lines):
            if re.match(r"^\d+(?:st|nd|rd|th)\s+of\s+\d+$", lines[i + 1], flags=re.I):
                starts.append(i)
        elif re.match(r"^\d+(?:st|nd|rd|th)\s+of\s+\d+$", line, flags=re.I):
            starts.append(i)

    if not starts:
        return runs

    starts.append(len(lines))

    for idx in range(len(starts) - 1):
        start = starts[idx]
        end = starts[idx + 1]
        block = [norm_text(x) for x in lines[start:end] if norm_text(x)]
        if not block:
            continue

        run = HorseRun(
            horse_name=horse_name,
            horse_code=horse_code,
            source_url=source_url,
            race_entry=race_entry,
            run_index=idx + 1,
            raw_run_text=" | ".join(block),
        )

        body = block
        if block[0] == "T":
            run.run_type_code = "T"
            run.run_type = "trial"
            run.is_trial = 1
            body = block[1:]
        elif block[0] == "J":
            run.run_type_code = "J"
            run.run_type = "jumpout"
            run.is_jumpout = 1
            body = block[1:]
        else:
            run.run_type_code = "R"
            run.run_type = "race"
            run.is_official_run = 1

        if len(body) < 5:
            continue

        m = re.match(r"^(\d+)(?:st|nd|rd|th)\s+of\s+(\d+)$", body[0], flags=re.I)
        if m:
            run.finish_pos = safe_int(m.group(1))
            run.field_size = safe_int(m.group(2))

        m = re.match(r"^([A-Z0-9 ]+)\s+(\d{1,2}[A-Za-z]{3}\d{2})$", body[1])
        if m:
            run.track_code = norm_text(m.group(1))
            run.run_date = norm_text(m.group(2))

        m = re.match(r"^(\d{3,4})m\s+([A-Za-z]+\d*)\s+(.*)$", body[2])
        if m:
            run.distance = safe_int(m.group(1))
            run.track_condition = norm_text(m.group(2))
            run.race_name = norm_text(m.group(3))
            run.race_class_raw = run.race_name
            monies = extract_all_money(run.race_name)
            if monies:
                run.prizemoney_race = monies[0]
                run.prizemoney_earned = monies[1] if len(monies) > 1 else None

        run.jockey = body[3]

        wb = body[4]
        wt = re.search(r"(\d+(?:\.\d+)?)kg", wb)
        if wt:
            run.weight = safe_float(wt.group(1))
        bar = re.search(r"Barrier\s+(\d+)", wb, flags=re.I)
        if bar:
            run.barrier = safe_int(bar.group(1))
        rtg = re.search(r"Rtg\s+(\d+(?:\.\d+)?)", wb, flags=re.I)
        if rtg:
            run.run_rating_raw = safe_float(rtg.group(1))

        tail = " | ".join(body[5:])

        placements = list(re.finditer(r"(1st|2nd|3rd)\s+([^|]+?)\s+(\d+(?:\.\d+)?)kg", tail))
        for pm in placements:
            label = pm.group(1)
            pname = norm_text(pm.group(2)).rstrip(",")
            pwt = safe_float(pm.group(3))
            if label == "1st":
                run.winner_name = pname
                run.winner_weight = pwt
            elif label == "2nd":
                run.second_name = pname
                run.second_weight = pwt
            elif label == "3rd":
                run.third_name = pname
                run.third_weight = pwt

        time_match = re.search(r"(\d+:\d{2}\.\d{2}|\d{2}\.\d{2})", tail)
        if time_match:
            run.race_time = norm_text(time_match.group(1))

        sec_match = re.search(r"\(600m\s+(\d{2}\.\d{2})\)", tail)
        if sec_match:
            run.sectional_600 = safe_float(sec_match.group(1))

        margin_match = re.search(
            r",\s*([0-9]+(?:\.[0-9]+)?|Nose|Nse|Head|Nk|Long Head|Short Head)L\b",
            tail,
            flags=re.I,
        )
        if margin_match:
            run.margin = parse_margin_token(margin_match.group(1))

        in_run = re.findall(r"\d+(?:st|nd|rd|th)@\d+m", tail)
        if in_run:
            run.in_run_positions_raw = ", ".join(in_run)

        prices = re.findall(r"\$\d+(?:\.\d+)?", tail)
        if prices:
            run.price_raw = "/".join(prices)
            run.sp = safe_float(prices[-1])

        runs.append(run)

    return runs


def scrape_one_horse(session: requests.Session, row: pd.Series, sleep_seconds: float) -> Tuple[HorseProfile, List[HorseRun]]:
    source_url = norm_text(row.get("source_url"))
    horse_code = norm_text(row.get("horse_code"))
    race_entry = norm_text(row.get("race_entry"))

    if not source_url and horse_code:
        source_url = build_ra_url(horse_code, race_entry)
    if not source_url:
        raise ValueError("No valid Racing Australia URL or horse_code for this row")

    html_text = fetch_html(session, source_url, sleep_seconds=sleep_seconds)
    soup = BeautifulSoup(html_text, "html.parser")
    lines = soup_lines(soup)

    profile = parse_profile(lines, source_url=source_url, horse_code=horse_code, race_entry=race_entry)
    if not profile.horse_name:
        profile.horse_name = norm_text(row.get("horse_name_input"))

    runs = parse_runs(
        lines,
        horse_name=profile.horse_name,
        horse_code=horse_code,
        source_url=source_url,
        race_entry=race_entry,
    )
    return profile, runs


def merge_snapshot(input_horses: pd.DataFrame, profiles: pd.DataFrame) -> pd.DataFrame:
    snap = input_horses.copy()
    if profiles.empty:
        return snap
    profiles_small = profiles[["horse_code", "horse_name", "trainer", "source_url"]].drop_duplicates()
    return snap.merge(profiles_small, on="horse_code", how="left", suffixes=("_input", "_profile"))


def save_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if df.empty:
        pd.DataFrame().to_csv(path, index=False)
    else:
        df.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL)


def run_scrape(input_csv: Path, output_dir: Path, max_horses: Optional[int], sleep_seconds: float) -> Dict[str, Path]:
    source_df = pd.read_csv(input_csv, low_memory=False)
    input_horses = build_input_horses(source_df)

    if max_horses is not None and max_horses > 0:
        input_horses = input_horses.head(max_horses).copy()

    profiles: List[Dict[str, object]] = []
    runs: List[Dict[str, object]] = []

    session = make_session()
    total = len(input_horses)

    for i, (_, row) in enumerate(input_horses.iterrows(), start=1):
        print(f"[{i}/{total}] {row.get('horse_name_input', '') or row.get('horse_code', '')}")
        print(f"  {row.get('source_url', '')}")
        try:
            profile, horse_runs = scrape_one_horse(session, row, sleep_seconds=sleep_seconds)
            profiles.append(asdict(profile))
            runs.extend(asdict(x) for x in horse_runs)
            print(f"  [OK] profile + {len(horse_runs)} runs")
        except Exception as exc:
            print(f"  [ERROR] {exc}")

    profiles_df = pd.DataFrame(profiles)
    runs_df = pd.DataFrame(runs)
    snapshot_df = merge_snapshot(input_horses, profiles_df)

    out_paths = {
        "horses_master": output_dir / "horses_master.csv",
        "horse_runs": output_dir / "horse_runs_ra.csv",
        "snapshot": output_dir / "upcoming_runner_ra_snapshot.csv",
    }

    save_csv(profiles_df, out_paths["horses_master"])
    save_csv(runs_df, out_paths["horse_runs"])
    save_csv(snapshot_df, out_paths["snapshot"])
    return out_paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape Racing Australia horse All Form pages into master profile and run tables.")
    parser.add_argument("--input-csv", required=True, help="CSV containing RA horse URLs or horse_code values")
    parser.add_argument("--output-dir", required=True, help="Directory for horses_master.csv etc")
    parser.add_argument("--max-horses", type=int, default=0, help="Optional cap for test runs")
    parser.add_argument("--sleep-seconds", type=float, default=0.5, help="Sleep between requests")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_csv = Path(args.input_csv)
    output_dir = Path(args.output_dir)

    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv.resolve()}")

    print("=== SCRAPE RA ALL FORM ===")
    print(f"Input:  {input_csv.resolve()}")
    print(f"Output: {output_dir.resolve()}")
    print(f"Max horses: {args.max_horses or 'ALL'}")
    print(f"Sleep: {args.sleep_seconds}s")

    paths = run_scrape(
        input_csv=input_csv,
        output_dir=output_dir,
        max_horses=args.max_horses if args.max_horses > 0 else None,
        sleep_seconds=args.sleep_seconds,
    )

    print("\n✅ Completed")
    for key, path in paths.items():
        print(f"  {key}: {path.resolve()}")


if __name__ == "__main__":
    main()