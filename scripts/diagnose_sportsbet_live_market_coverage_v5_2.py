from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUTPUTS = ROOT / "outputs"
AUDIT_DIR = OUTPUTS / "audits"

FAIR_PRICES = DATA / "edgeiq_current_fair_prices_review_v5_2.csv"
SPORTSBET_MARKET = DATA / "sportsbet_live_market_v1.csv"
REQUESTED_NEXT_EVENTS = OUTPUTS / "sportsbet_live_real" / "sportsbet_next_events.json"
RAW_EVENTS_SAMPLE = DATA / "sportsbet_live_market_raw_events_sample_v1.json"
SPORTSBET_STATUS = DATA / "sportsbet_live_market_status_v1.csv"
SPORTSBET_CAPTURE_LOG = DATA / "sportsbet_live_market_capture_log_v1.csv"

OUT = AUDIT_DIR / "sportsbet_live_market_coverage_v5_2.csv"
AUDIT_TXT = AUDIT_DIR / "sportsbet_live_market_coverage_v5_2_audit.txt"


def norm(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).upper().strip().split())


def horse_key(value: object) -> str:
    text = norm(value)
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def clean_race_no(value: object) -> str:
    text = str(value).strip()
    return text[:-2] if text.endswith(".0") else text


def read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def extract_events(payload: Any) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if payload is None:
        return events

    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        return events

    for key in ["selected_events", "events", "nextEvents", "raw_events"]:
        for item in as_list(payload.get(key)):
            if isinstance(item, dict):
                events.append(item)

    raw_excerpt = payload.get("raw_excerpt")
    if isinstance(raw_excerpt, str) and raw_excerpt.strip().startswith("[") and raw_excerpt.strip().endswith("]"):
        try:
            for item in json.loads(raw_excerpt):
                if isinstance(item, dict):
                    events.append(item)
        except json.JSONDecodeError:
            pass

    for sample_key in ["racecard_sample_1", "racecard_sample_2", "racecard_sample_3", "racecard_sample_4"]:
        sample = payload.get(sample_key)
        if isinstance(sample, dict) and isinstance(sample.get("event"), dict):
            events.append(sample["event"])

    return events


def extract_racecard_sample_keys(payload: Any) -> dict[tuple[str, str, str], list[str]]:
    found: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    if not isinstance(payload, dict):
        return found

    for key, sample in payload.items():
        if not key.startswith("racecard_sample_") or not isinstance(sample, dict):
            continue
        event = sample.get("event")
        if isinstance(event, dict):
            found[event_key(event)].append(key)
    return found


def event_id(event: dict[str, Any]) -> str:
    return str(event.get("event_id") or event.get("id") or "").strip()


def event_race_no(event: dict[str, Any]) -> str:
    return clean_race_no(event.get("race_no") or event.get("raceNumber") or "")


def event_track(event: dict[str, Any]) -> str:
    return norm(event.get("track") or event.get("competitionName") or event.get("meeting_name") or "")


def event_date(event: dict[str, Any]) -> str:
    explicit = str(event.get("race_date") or event.get("date") or "").strip()
    if explicit:
        return explicit[:10]
    race_time = str(event.get("race_time") or event.get("startTimeIso") or "").strip()
    if len(race_time) >= 10 and race_time[4:5] == "-":
        return race_time[:10]
    return ""


def event_name(event: dict[str, Any]) -> str:
    return str(event.get("event_name") or event.get("name") or event.get("displayName") or "").strip()


def event_key(event: dict[str, Any]) -> tuple[str, str, str]:
    return (event_date(event), event_track(event), event_race_no(event))


def find_racecard_files() -> list[Path]:
    if not OUTPUTS.exists():
        return []
    return sorted(
        path
        for path in OUTPUTS.rglob("*")
        if path.is_file() and re.search(r"sportsbet.*racecard|racecard.*sportsbet|racecard", path.name, re.IGNORECASE)
    )


def racecard_metadata(path: Path) -> dict[str, str]:
    meta = {
        "path": str(path),
        "event_id": "",
        "race_date": "",
        "track": "",
        "race_no": "",
        "event_name": "",
    }
    try:
        payload = read_json(path)
    except (OSError, json.JSONDecodeError):
        payload = None

    if isinstance(payload, dict):
        meta["event_id"] = str(payload.get("event_id") or payload.get("id") or "")
        meta["race_no"] = event_race_no(payload)
        meta["track"] = event_track(payload)
        meta["race_date"] = event_date(payload)
        meta["event_name"] = event_name(payload)

    if not meta["event_id"]:
        match = re.search(r"(\d{6,})", path.name)
        if match:
            meta["event_id"] = match.group(1)
    return meta


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not FAIR_PRICES.exists():
        raise FileNotFoundError(f"Missing fair-price input: {FAIR_PRICES}")
    if not SPORTSBET_MARKET.exists():
        raise FileNotFoundError(f"Missing Sportsbet market input: {SPORTSBET_MARKET}")

    fair = pd.read_csv(FAIR_PRICES, dtype=str, keep_default_na=False, low_memory=False)
    sportsbet = pd.read_csv(SPORTSBET_MARKET, dtype=str, keep_default_na=False, low_memory=False)

    fair_required = {"race_date", "track", "race_no", "race_time", "horse", "horse_key"}
    sportsbet_required = {"race_date", "track", "race_no", "horse", "horse_key", "sportsbet_price", "event_id"}
    missing = {
        "fair_prices": sorted(fair_required.difference(fair.columns)),
        "sportsbet_market": sorted(sportsbet_required.difference(sportsbet.columns)),
    }
    missing = {name: columns for name, columns in missing.items() if columns}
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    fair["race_no"] = fair["race_no"].map(clean_race_no)
    sportsbet["race_no"] = sportsbet["race_no"].map(clean_race_no)
    fair["track_norm"] = fair["track"].map(norm)
    sportsbet["track_norm"] = sportsbet["track"].map(norm)
    fair["horse_key_match"] = fair.apply(lambda row: horse_key(row.get("horse_key", "")) or horse_key(row.get("horse", "")), axis=1)
    sportsbet["horse_key_match"] = sportsbet.apply(lambda row: horse_key(row.get("horse_key", "")) or horse_key(row.get("horse", "")), axis=1)
    return fair, sportsbet


def build_event_indexes(events: list[dict[str, Any]]) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    out: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        out[event_key(event)].append(event)
    return out


def racecard_evidence(
    race_key: tuple[str, str, str],
    event_ids: list[str],
    racecard_by_event_id: dict[str, list[dict[str, str]]],
    racecard_by_key: dict[tuple[str, str, str], list[dict[str, str]]],
    sample_keys_by_race: dict[tuple[str, str, str], list[str]],
    has_market_rows: bool,
) -> tuple[str, str]:
    evidence: list[str] = []

    for event_id_value in event_ids:
        for item in racecard_by_event_id.get(event_id_value, []):
            evidence.append(item["path"])

    for item in racecard_by_key.get(race_key, []):
        evidence.append(item["path"])

    for sample_key in sample_keys_by_race.get(race_key, []):
        evidence.append(f"{RAW_EVENTS_SAMPLE.name}:{sample_key}")

    if has_market_rows:
        evidence.append(f"{SPORTSBET_MARKET.name}:market_rows")

    unique = sorted(set(evidence))
    if unique:
        return "YES", "; ".join(unique)
    return "NO", ""


def build_rows(
    fair: pd.DataFrame,
    sportsbet: pd.DataFrame,
    next_events: list[dict[str, Any]],
    raw_events: list[dict[str, Any]],
    racecard_files: list[dict[str, str]],
    sample_keys_by_race: dict[tuple[str, str, str], list[str]],
) -> list[dict[str, object]]:
    next_by_key = build_event_indexes(next_events)
    raw_by_key = build_event_indexes(raw_events)

    racecard_by_event_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    racecard_by_key: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for item in racecard_files:
        if item["event_id"]:
            racecard_by_event_id[item["event_id"]].append(item)
        key = (item["race_date"], item["track"], item["race_no"])
        if any(key):
            racecard_by_key[key].append(item)

    rows: list[dict[str, object]] = []
    for key, group in fair.groupby(["race_date", "track_norm", "race_no"], dropna=False):
        race_date, track_norm, race_no = key
        expected_horses = set(group["horse_key_match"])
        sportsbet_race = sportsbet[
            sportsbet["race_date"].eq(race_date)
            & sportsbet["track_norm"].eq(track_norm)
            & sportsbet["race_no"].eq(race_no)
        ].copy()
        sportsbet_horses = set(sportsbet_race["horse_key_match"])

        matched_horses = expected_horses.intersection(sportsbet_horses)
        missing_horses = expected_horses.difference(sportsbet_horses)
        extra_horses = sportsbet_horses.difference(expected_horses)

        next_matches = next_by_key.get((race_date, track_norm, race_no), [])
        raw_matches = raw_by_key.get((race_date, track_norm, race_no), [])
        sportsbet_event_ids = sorted({str(value) for value in sportsbet_race["event_id"] if str(value).strip()})
        event_ids = sorted(
            {
                event_id(event)
                for event in [*next_matches, *raw_matches]
                if event_id(event)
            }.union(sportsbet_event_ids)
        )

        capture_exists, capture_files = racecard_evidence(
            (race_date, track_norm, race_no),
            event_ids,
            racecard_by_event_id,
            racecard_by_key,
            sample_keys_by_race,
            has_market_rows=not sportsbet_race.empty,
        )

        if sportsbet_race.empty:
            if not next_matches and not raw_matches:
                reason = "missing from selected/available Sportsbet event metadata; no racecard requested"
            elif capture_exists == "NO":
                reason = "event metadata found but no racecard capture evidence found"
            else:
                reason = "racecard capture evidence exists but no rows reached sportsbet_live_market_v1.csv"
        elif missing_horses:
            reason = "partial market coverage; Sportsbet rows exist but runner count is short"
        else:
            reason = "covered"

        rows.append(
            {
                "race_date": race_date,
                "track": group["track"].iloc[0],
                "race_no": race_no,
                "race_time": group["race_time"].iloc[0],
                "expected_runner_count": len(group),
                "expected_horses": "; ".join(group["horse"].tolist()),
                "sportsbet_matched_race": "YES" if not sportsbet_race.empty else "NO",
                "sportsbet_runner_rows": len(sportsbet_race),
                "matched_runner_count": len(matched_horses),
                "missing_runner_count": len(missing_horses),
                "missing_horses": "; ".join(group[group["horse_key_match"].isin(missing_horses)]["horse"].tolist()),
                "extra_sportsbet_runner_count": len(extra_horses),
                "sportsbet_event_ids": "; ".join(sportsbet_event_ids),
                "available_event_ids": "; ".join(event_ids),
                "next_events_file_exists": "YES" if REQUESTED_NEXT_EVENTS.exists() else "NO",
                "next_events_contains_race": "YES" if next_matches else "NO",
                "raw_events_sample_file_exists": "YES" if RAW_EVENTS_SAMPLE.exists() else "NO",
                "raw_events_sample_contains_race": "YES" if raw_matches else "NO",
                "racecard_capture_exists": capture_exists,
                "racecard_capture_files": capture_files,
                "reason_missing": reason,
            }
        )
    return rows


def read_optional_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_text_audit(
    rows: list[dict[str, object]],
    fair: pd.DataFrame,
    sportsbet: pd.DataFrame,
    next_events: list[dict[str, Any]],
    raw_events: list[dict[str, Any]],
    racecard_files: list[dict[str, str]],
) -> None:
    status_rows = read_optional_csv(SPORTSBET_STATUS)
    log_rows = read_optional_csv(SPORTSBET_CAPTURE_LOG)

    expected_races = len(rows)
    matched_races = sum(1 for row in rows if row["sportsbet_matched_race"] == "YES")
    missing_races = expected_races - matched_races
    expected_runners = len(fair)
    sportsbet_rows = len(sportsbet)
    missing_runner_count = sum(int(row["missing_runner_count"]) for row in rows)
    available_event_ids = sorted(
        {
            event_id(event)
            for event in [*next_events, *raw_events]
            if event_id(event)
        }.union({str(value) for value in sportsbet["event_id"] if str(value).strip()})
    )

    lines = [
        "EDGEIQ SPORTSBET LIVE MARKET COVERAGE V5.2",
        "=" * 90,
        f"built_at={datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"fair_price_file={FAIR_PRICES}",
        f"sportsbet_market_file={SPORTSBET_MARKET}",
        f"requested_next_events_file={REQUESTED_NEXT_EVENTS}",
        f"requested_next_events_file_exists={REQUESTED_NEXT_EVENTS.exists()}",
        f"raw_events_sample_file={RAW_EVENTS_SAMPLE}",
        f"raw_events_sample_file_exists={RAW_EVENTS_SAMPLE.exists()}",
        "",
        "SUMMARY",
        f"expected_races={expected_races}",
        f"expected_runners={expected_runners}",
        f"sportsbet_rows={sportsbet_rows}",
        f"sportsbet_matched_races={matched_races}",
        f"missing_races={missing_races}",
        f"missing_runner_count={missing_runner_count}",
        f"next_events_parsed={len(next_events)}",
        f"raw_events_sample_events_parsed={len(raw_events)}",
        f"racecard_capture_files_found={len(racecard_files)}",
        f"available_sportsbet_event_ids={'; '.join(available_event_ids)}",
        "",
        "CAPTURE STATUS",
    ]

    for row in status_rows:
        lines.append("; ".join(f"{key}={value}" for key, value in row.items()))

    lines.append("")
    lines.append("CAPTURE LOG")
    for row in log_rows:
        lines.append("; ".join(f"{key}={value}" for key, value in row.items()))

    lines.append("")
    lines.append("RACECARD FILES FOUND")
    for item in racecard_files:
        lines.append("; ".join(f"{key}={value}" for key, value in item.items()))

    lines.append("")
    lines.append("PER RACE DIAGNOSIS")
    for row in rows:
        lines.append(
            (
                f"R{row['race_no']} {row['race_time']} {row['track']}: "
                f"expected={row['expected_runner_count']}, sportsbet_rows={row['sportsbet_runner_rows']}, "
                f"missing={row['missing_runner_count']}, event_ids={row['available_event_ids'] or '-'}, "
                f"next_events_contains={row['next_events_contains_race']}, raw_sample_contains={row['raw_events_sample_contains_race']}, "
                f"racecard_capture={row['racecard_capture_exists']}, reason={row['reason_missing']}"
            )
        )

    AUDIT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def sort_rows(out: pd.DataFrame) -> pd.DataFrame:
    out = out.copy()
    out["_race_sort"] = pd.to_numeric(out["race_no"], errors="coerce").fillna(999).astype(int)
    return out.sort_values(["race_date", "track", "_race_sort"]).drop(columns=["_race_sort"])


def main() -> None:
    print("=" * 90)
    print("EDGEIQ SPORTSBET LIVE MARKET COVERAGE DIAGNOSIS V5.2")
    print("=" * 90)

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    fair, sportsbet = load_inputs()

    next_payload = read_json(REQUESTED_NEXT_EVENTS)
    raw_payload = read_json(RAW_EVENTS_SAMPLE)
    next_events = extract_events(next_payload)
    raw_events = extract_events(raw_payload)
    racecard_sample_keys = extract_racecard_sample_keys(raw_payload)
    racecard_files = [racecard_metadata(path) for path in find_racecard_files()]

    rows = build_rows(fair, sportsbet, next_events, raw_events, racecard_files, racecard_sample_keys)
    out = sort_rows(pd.DataFrame(rows))
    out.to_csv(OUT, index=False)

    write_text_audit(rows, fair, sportsbet, next_events, raw_events, racecard_files)

    print(f"wrote: {OUT}")
    print(f"wrote: {AUDIT_TXT}")
    print()
    print(
        out[
            [
                "race_date",
                "track",
                "race_no",
                "race_time",
                "expected_runner_count",
                "sportsbet_runner_rows",
                "missing_runner_count",
                "available_event_ids",
                "next_events_contains_race",
                "raw_events_sample_contains_race",
                "racecard_capture_exists",
                "reason_missing",
            ]
        ].to_string(index=False)
    )
    print("=" * 90)


if __name__ == "__main__":
    main()
