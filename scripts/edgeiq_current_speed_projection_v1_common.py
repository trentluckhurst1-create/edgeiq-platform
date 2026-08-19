from __future__ import annotations

import csv
import json
import math
import re
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

CURRENT_RUNNERS = DATA / "race_fields.csv"
SPEED_MASTER = DATA / "edgeiq_speed_master_v1.csv"
SECTIONAL_PROFILE = DATA / "edgeiq_form_sectional_profile_feed_v1.csv"
SECTIONAL_TERMINAL = DATA / "edgeiq_form_sectional_terminal_feed_v1.csv"
PROFILE_STATS = DATA / "edgeiq_runner_profile_stats_v1.csv"
LIVE_SPEED_MAP = DATA / "live_speed_map_v3.csv"
ENRICHED = DATA / "edgeiq_form_guide_enriched_v2.json"

csv.field_size_limit(1024 * 1024 * 128)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean(value: Any) -> str:
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return "" if text.lower() in {"", "-", "none", "null", "n/a", "na", "unknown"} else text


def canon_runner(value: Any) -> str:
    text = clean(value).upper()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = text.replace("'", "").replace("\u2019", "").replace("&", "AND")
    return re.sub(r"[^A-Z0-9]+", "", text)


def canon_track(value: Any) -> str:
    text = clean(value).upper()
    text = re.sub(r"\b(BET365|SPORTSBET|LADBROKES|TAB|THE)\b", " ", text)
    text = re.sub(r"\b(RACECOURSE|RACING|TRACK)\b", " ", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def normalise_date(value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    text = text.split("T", 1)[0].split(" ", 1)[0].replace("/", "-")
    parts = text.split("-")
    if len(parts) != 3:
        return ""
    if len(parts[0]) == 4:
        y, m, d = parts
    else:
        d, m, y = parts
    try:
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    except ValueError:
        return ""


def parse_date(value: Any) -> date | None:
    text = normalise_date(value)
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def race_no(value: Any) -> str:
    match = re.search(r"\d+", clean(value).upper().replace("R", ""))
    return str(int(match.group(0))) if match else ""


def to_float(value: Any) -> float | None:
    text = clean(value).replace("$", "").replace(",", "").replace("kg", "")
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def round_or_none(value: float | None, digits: int = 1) -> float | None:
    return None if value is None else round(value, digits)


def band_from_score(value: float | None) -> str | None:
    if value is None:
        return None
    if value >= 75:
        return "LEADING"
    if value >= 65:
        return "ABOVE AVERAGE"
    if value >= 50:
        return "AVERAGE"
    return "BELOW AVERAGE"


def runner_identity(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        normalise_date(row.get("raceDate") or row.get("race_date")),
        canon_track(row.get("meeting") or row.get("track") or row.get("display_track")),
        race_no(row.get("raceNumber") or row.get("race_no") or row.get("race_number")),
        canon_runner(row.get("normalisedRunnerName") or row.get("normalized_runner") or row.get("horse_canon") or row.get("runnerName") or row.get("runner") or row.get("horse")),
    )


def load_current_runners() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not CURRENT_RUNNERS.exists():
        return rows
    with CURRENT_RUNNERS.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        for index, row in enumerate(csv.DictReader(handle), start=1):
            race_date = normalise_date(row.get("race_date"))
            runner_name = clean(row.get("horse") or row.get("runner"))
            norm = canon_runner(row.get("horse_canon") or runner_name)
            out = {
                "sourceIndex": index,
                "raceDate": race_date,
                "meeting": clean(row.get("display_track") or row.get("track")),
                "meetingKey": canon_track(row.get("track")),
                "raceNumber": int(race_no(row.get("race_no") or row.get("race_number")) or 0) or None,
                "raceNo": race_no(row.get("race_no") or row.get("race_number")),
                "raceKey": clean(row.get("race_key")),
                "runnerId": clean(row.get("runner_id")) or None,
                "runnerNumber": int(race_no(row.get("runner_number") or row.get("horse_no") or row.get("saddlecloth")) or 0) or None,
                "runnerName": runner_name,
                "normalizedRunner": norm,
                "distance": to_float(row.get("distance_m") or row.get("distance")),
                "barrier": to_float(row.get("barrier")),
                "fieldSize": to_float(row.get("field_size")),
                "isScratched": clean(row.get("is_scratched")).lower() in {"1", "true", "yes"} or clean(row.get("runner_status")).upper() == "SCRATCHED",
                "raw": row,
            }
            out["identity"] = runner_identity({**out, "track": row.get("track")})
            rows.append(out)
    return rows


def load_profile_starts() -> dict[str, int]:
    out: dict[str, int] = {}
    if not PROFILE_STATS.exists():
        return out
    with PROFILE_STATS.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        for row in csv.DictReader(handle):
            key = canon_runner(row.get("normalized_runner") or row.get("runner"))
            starts = int(to_float(row.get("career_starts")) or 0)
            if key:
                out[key] = starts
    return out


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_summary(path: Path, lines: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "min": None, "max": None, "mean": None, "median": None, "stddev": None, "unique": 0}
    return {
        "count": len(values),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "mean": round(mean(values), 2),
        "median": round(median(values), 2),
        "stddev": round(pstdev(values), 2) if len(values) > 1 else 0.0,
        "unique": len({round(v, 1) for v in values}),
    }


def race_key(row: dict[str, Any]) -> str:
    return f"{row.get('raceDate')}|{canon_track(row.get('meeting'))}|{race_no(row.get('raceNumber'))}"


def group_by_race(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[race_key(row)].append(row)
    return grouped


def source_inventory_rows() -> list[dict[str, Any]]:
    return [
        {
            "source_file": "public/data/edgeiq_speed_master_v1.csv",
            "builder": "speed master warehouse builders",
            "field": "early_raw",
            "unit_scale": "native speed-master 0-100 style score; observed max below 100",
            "date_coverage": "historical rows, as-of filter required",
            "race_coverage": "historical",
            "runner_coverage": "current runners by normalized_runner",
            "historical_current": "historical",
            "production_research_deprecated": "production evidence",
            "as_of_safe": "YES when race_date < selected race date",
            "selected_rejected": "selected",
            "reason": "Approved historical early-speed evidence; transformed only by as-of current-race projection aggregation.",
        },
        {
            "source_file": "public/data/edgeiq_speed_master_v1.csv",
            "builder": "speed master warehouse builders",
            "field": "late_raw",
            "unit_scale": "native speed-master 0-100 style score; higher stronger",
            "date_coverage": "historical rows, as-of filter required",
            "race_coverage": "historical",
            "runner_coverage": "current runners by normalized_runner",
            "historical_current": "historical",
            "production_research_deprecated": "production evidence",
            "as_of_safe": "YES when race_date < selected race date",
            "selected_rejected": "selected",
            "reason": "Approved historical late-speed profile fallback where benchmarked splits are unavailable.",
        },
        {
            "source_file": "public/data/edgeiq_form_sectional_profile_feed_v1.csv",
            "builder": "standardised sectional benchmark engine",
            "field": "split_labels, split_lengths",
            "unit_scale": "ESI lengths versus benchmark; negative is faster/inside standard",
            "date_coverage": "historical rows, as-of filter required",
            "race_coverage": "historical",
            "runner_coverage": "current runners by normalized_runner",
            "historical_current": "historical",
            "production_research_deprecated": "production evidence",
            "as_of_safe": "YES when race_date < selected race date",
            "selected_rejected": "selected",
            "reason": "Primary benchmark-adjusted late-sectional evidence when final 200/400/600 splits are present.",
        },
        {
            "source_file": "public/data/edgeiq_form_sectional_profile_feed_v1.csv",
            "builder": "standardised sectional benchmark engine",
            "field": "finish_len",
            "unit_scale": "ESI lengths versus benchmark; full-race performance context",
            "date_coverage": "historical rows, as-of filter required",
            "race_coverage": "historical",
            "runner_coverage": "current runners by normalized_runner",
            "historical_current": "historical",
            "production_research_deprecated": "source evidence only",
            "as_of_safe": "YES when race_date < selected race date",
            "selected_rejected": "rejected",
            "reason": "Not late-specific enough for current Late Speed score; retained for recent-form benchmark display only.",
        },
        {
            "source_file": "public/data/live_speed_map_v3.csv",
            "builder": "build_live_speed_map_engine_v3.py",
            "field": "speed_map_bucket, tempo_fit, late_power_index",
            "unit_scale": "current map labels plus historical/profile memory indices",
            "date_coverage": "current three-day rows",
            "race_coverage": "503 current rows",
            "runner_coverage": "current runner rows",
            "historical_current": "current shell with historical memory inputs",
            "production_research_deprecated": "production map evidence",
            "as_of_safe": "YES for map context, NO as a direct speed projection",
            "selected_rejected": "rejected",
            "reason": "V1.1 proved late_power_index and default map values are not approved direct Early/Late Speed projections.",
        },
        {
            "source_file": "public/data/edgeiq_runner_profile_stats_v1.csv",
            "builder": "build_edgeiq_runner_profile_stats_v1.py",
            "field": "career_starts and profile records",
            "unit_scale": "factual starts/wins/seconds/thirds",
            "date_coverage": "latest profile aggregate",
            "race_coverage": "runner profile rows",
            "runner_coverage": "current runners by normalized_runner",
            "historical_current": "historical aggregate",
            "production_research_deprecated": "profile evidence",
            "as_of_safe": "LIMITED; used only to classify first/no-history gap reasons",
            "selected_rejected": "selected",
            "reason": "Used for gap classification only, not as a speed score.",
        },
        {
            "source_file": "public/data/edgeiq_current_field_projection_v5_2.csv",
            "builder": "build_edgeiq_current_field_projection_v5_2.py",
            "field": "projected_rating_v5_2",
            "unit_scale": "EPI rating",
            "date_coverage": "current three-day rows",
            "race_coverage": "current races",
            "runner_coverage": "rated current runners",
            "historical_current": "current projection",
            "production_research_deprecated": "production",
            "as_of_safe": "YES for EPI only",
            "selected_rejected": "rejected",
            "reason": "Cannot be duplicated as Early or Late Speed.",
        },
    ]
