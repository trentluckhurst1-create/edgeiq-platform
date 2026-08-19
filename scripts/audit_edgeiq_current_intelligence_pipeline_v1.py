from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

BASE_FEED = DATA / "edgeiq_form_guide_enriched_v2.json"

SOURCE_AUDIT_JSON = DATA / "edgeiq_current_intelligence_source_contract_audit.json"
SOURCE_AUDIT_CSV = DATA / "edgeiq_current_intelligence_source_contract_audit.csv"
SOURCE_AUDIT_TXT = DATA / "edgeiq_current_intelligence_source_contract_audit.txt"

JOIN_AUDIT_JSON = DATA / "edgeiq_form_guide_current_intelligence_join_audit.json"
JOIN_AUDIT_CSV = DATA / "edgeiq_form_guide_current_intelligence_join_audit.csv"
JOIN_AUDIT_TXT = DATA / "edgeiq_form_guide_current_intelligence_join_audit.txt"

COVERAGE_JSON = DATA / "edgeiq_form_guide_current_intelligence_coverage.json"
COVERAGE_CSV = DATA / "edgeiq_form_guide_current_intelligence_coverage.csv"
COVERAGE_TXT = DATA / "edgeiq_form_guide_current_intelligence_coverage.txt"


SOURCE_CONTRACTS: dict[str, dict[str, Any]] = {
    "EPI": {
        "file": DATA / "edgeiq_live_runner_board_governed_v1.csv",
        "builders": ["scripts/build_edgeiq_live_runner_board_governed_v1.py"],
        "date_fields": ["race_date", "date"],
        "track_fields": ["track", "meeting", "meeting_name"],
        "race_fields": ["race_no", "race_number", "race"],
        "runner_fields": ["horse", "runner", "runner_name", "horse_name", "horse_canon", "horse_key"],
        "metric_fields": [
            "projected_rating_v5_2",
            "projected_rating_V6_1_RESERCH",
            "projected_rating",
            "total_rating_points",
        ],
    },
    "EDGEiQ Price": {
        "file": DATA / "edgeiq_live_runner_board_governed_v1.csv",
        "builders": ["scripts/build_edgeiq_probability_engine_v3.py", "scripts/build_edgeiq_live_runner_board_governed_v1.py", "src/services/marketPricingService.ts"],
        "date_fields": ["race_date", "date"],
        "track_fields": ["track", "meeting", "meeting_name"],
        "race_fields": ["race_no", "race_number", "race"],
        "runner_fields": ["horse", "runner", "runner_name", "horse_name", "horse_canon", "horse_key"],
        "metric_fields": [
            "edgeiq_v7_2_preview_display_fair_price",
            "edgeiq_display_fair_price_v7_2",
            "ui_fair_price",
            "display_fair_price",
            "display_fair_price_governed",
            "fair_price_display",
            "fair_price",
            "fair_price_v7_2",
            "rated_price",
        ],
    },
    "Early Speed": {
        "file": DATA / "edgeiq_live_runner_board_governed_v1.csv",
        "builders": ["scripts/build_edgeiq_live_runner_board_governed_v1.py", "src/services/runnerMetricsService.ts"],
        "date_fields": ["race_date", "date"],
        "track_fields": ["track", "meeting", "meeting_name"],
        "race_fields": ["race_no", "race_number", "race"],
        "runner_fields": ["horse", "runner", "runner_name", "horse_name", "horse_canon", "horse_key"],
        "metric_fields": ["projected_speed", "projected_spd", "early_speed_rating"],
    },
    "Late Speed": {
        "file": DATA / "live_speed_map_v3.csv",
        "builders": ["scripts/build_live_speed_map_engine_v3.py", "scripts/build_edgeiq_live_runner_board_governed_v1.py", "src/services/runnerMetricsService.ts"],
        "date_fields": ["race_date", "date"],
        "track_fields": ["track", "meeting", "meeting_name"],
        "race_fields": ["race_no", "race_number", "race"],
        "runner_fields": ["horse_key", "horse", "runner", "runner_name", "horse_canon"],
        "metric_fields": ["late_speed", "late_power_index", "late_power_score"],
    },
    "Race Shape": {
        "file": DATA / "live_speed_map_v3.csv",
        "builders": [
            "scripts/add_current_race_shape.py",
            "scripts/add_race_shape_state.py",
            "scripts/wire_live_speed_map_v3.py",
        ],
        "date_fields": ["race_date", "date"],
        "track_fields": ["track", "meeting", "meeting_name"],
        "race_fields": ["race_no", "race_number", "race"],
        "runner_fields": ["horse_key", "horse", "runner", "runner_name"],
        "metric_fields": ["tempo_fit", "pace_fit", "pace_fit_band", "speed_map_bucket", "settling_position", "run_style", "lane"],
    },
    "Suitability": {
        "file": DATA / "edgeiq_runner_dna_drawer_feed_v2.csv",
        "builders": ["scripts/wire_edgeiq_live_dna_explainability_v1.py", "src/edgeiq-os/services/adapters/RunnerDNAAdapter.ts"],
        "date_fields": ["race_date", "date"],
        "track_fields": ["track", "meeting", "meeting_name"],
        "race_fields": ["race_no", "race_number", "race"],
        "runner_fields": ["horse_key", "horse", "runner", "runner_name"],
        "metric_fields": ["today_suitability", "suitability", "runner_dna_v6_1_score", "dna_score"],
    },
    "Form Momentum": {
        "file": None,
        "builders": [],
        "date_fields": ["race_date", "date"],
        "track_fields": ["track", "meeting", "meeting_name"],
        "race_fields": ["race_no", "race_number", "race"],
        "runner_fields": ["horse", "runner", "runner_name", "horse_name"],
        "metric_fields": ["form_momentum", "momentum", "trajectory", "form_trend", "projection_trend", "current_form", "campaign_trend"],
    },
}

FORM_MOMENTUM_CANDIDATES = [
    DATA / "edgeiq_live_runner_board_v1.csv",
    DATA / "edgeiq_live_runner_board_governed_v1.csv",
    DATA / "edgeiq_command_enrichment_feed_v2.csv",
    DATA / "edgeiq_runner_projection_feed_v1.csv",
    DATA / "edgeiq_campaign_intelligence_feed_v1.csv",
    DATA / "edgeiq_factor_scorecard_feed_v1.csv",
]


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def canonical_date(value: Any) -> str:
    raw = clean_text(value)
    if not raw:
        return ""
    raw = raw.split("T", 1)[0].split(" ", 1)[0]
    raw = raw.replace("/", "-")
    parts = raw.split("-")
    if len(parts) == 3:
        if len(parts[0]) == 4:
            y, m, d = parts
        else:
            d, m, y = parts
        try:
            return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
        except ValueError:
            return ""
    return ""


TRACK_ALIASES = {
    "CAULFIELD HEATH": "CAULFIELD HEATH",
    "CAULFIELD": "CAULFIELD",
    "GEELONG SYNTHETIC": "GEELONG",
    "GEELONG": "GEELONG",
    "DONALD": "DONALD",
    "BALLARAT SYNTHETIC": "BALLARAT",
    "BALLARAT": "BALLARAT",
    "HAMILTON": "HAMILTON",
}


def canonical_track(value: Any) -> str:
    raw = clean_text(value).upper()
    raw = raw.replace("&", " AND ")
    raw = re.sub(r"[^A-Z0-9 ]+", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return TRACK_ALIASES.get(raw, raw)


def canonical_race_no(value: Any) -> str:
    raw = clean_text(value).upper()
    match = re.search(r"(\d+)", raw)
    return str(int(match.group(1))) if match else ""


def canonical_runner(value: Any) -> str:
    raw = clean_text(value).upper()
    raw = re.sub(r"\([^)]*\)", " ", raw)
    raw = raw.replace("’", "'").replace("`", "'")
    raw = re.sub(r"[^A-Z0-9]+", "", raw)
    return raw


def first_present(row: dict[str, Any], fields: list[str]) -> str:
    for field in fields:
        if field in row and clean_text(row.get(field)):
            return clean_text(row.get(field))
    return ""


def load_csv(path: Path | None) -> tuple[list[dict[str, str]], list[str]]:
    if not path or not path.exists():
        return [], []
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        reader = csv.DictReader(handle)
        return list(reader), reader.fieldnames or []


def load_form_runners() -> list[dict[str, Any]]:
    payload = json.loads(BASE_FEED.read_text(encoding="utf-8"))
    runners: list[dict[str, Any]] = []
    for race in payload.get("races", []):
        race_date = canonical_date(race.get("raceDate"))
        meeting = canonical_track(race.get("meeting"))
        race_no = canonical_race_no(race.get("raceNumber"))
        for runner in race.get("runners", []):
            runners.append(
                {
                    "race_date": race_date,
                    "meeting": meeting,
                    "race_number": race_no,
                    "runner_number": clean_text(runner.get("runnerNumber") or runner.get("number")),
                    "runner_name": clean_text(runner.get("runnerName") or runner.get("name")),
                    "runner_key": canonical_runner(runner.get("normalisedRunnerName") or runner.get("runnerName") or runner.get("name")),
                    "source_runner_id": clean_text(runner.get("id")),
                }
            )
    return runners


def row_key(row: dict[str, Any], contract: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        canonical_date(first_present(row, contract["date_fields"])),
        canonical_track(first_present(row, contract["track_fields"])),
        canonical_race_no(first_present(row, contract["race_fields"])),
        canonical_runner(first_present(row, contract["runner_fields"])),
    )


def race_key_from_row(row: dict[str, Any], contract: dict[str, Any]) -> tuple[str, str, str]:
    return row_key(row, contract)[:3]


def form_key(runner: dict[str, Any]) -> tuple[str, str, str, str]:
    return (runner["race_date"], runner["meeting"], runner["race_number"], runner["runner_key"])


def form_race_key(runner: dict[str, Any]) -> tuple[str, str, str]:
    return (runner["race_date"], runner["meeting"], runner["race_number"])


def has_metric(row: dict[str, Any], fields: list[str]) -> tuple[bool, str]:
    for field in fields:
        if field in row and clean_text(row.get(field)):
            return True, field
    return False, ""


def source_contract_for(metric: str, contract: dict[str, Any], form_runners: list[dict[str, Any]]) -> dict[str, Any]:
    path = contract.get("file")
    if path is None:
        candidate_rows: list[dict[str, str]] = []
        candidate_fields: list[str] = []
        selected = None
        for candidate in FORM_MOMENTUM_CANDIDATES:
            rows, fields = load_csv(candidate)
            if any(field in fields for field in contract["metric_fields"]):
                path = candidate
                candidate_rows = rows
                candidate_fields = fields
                selected = candidate.name
                break
        if path is None:
            return {
                "metric": metric,
                "source_filename": "",
                "builder": "",
                "exists": False,
                "row_count": 0,
                "latest_race_date": "",
                "date_coverage": "",
                "track_coverage": "",
                "unique_races": 0,
                "unique_runners": 0,
                "duplicate_keys": 0,
                "metric_columns_present": "",
                "nonblank_metric_rows": 0,
                "current_three_day_matched_rows": 0,
                "coverage_percentage": 0.0,
                "failure_reason": "NO_APPROVED_PRODUCTION_SOURCE",
                "sample_failures": "No current Form Momentum production source with approved metric columns located.",
            }
        rows, fields = candidate_rows, candidate_fields
    else:
        rows, fields = load_csv(path)
        selected = Path(path).name if path else ""

    if not path or not Path(path).exists():
        return {
            "metric": metric,
            "source_filename": str(path or ""),
            "builder": "|".join(contract.get("builders", [])),
            "exists": False,
            "row_count": 0,
            "latest_race_date": "",
            "date_coverage": "",
            "track_coverage": "",
            "unique_races": 0,
            "unique_runners": 0,
            "duplicate_keys": 0,
            "metric_columns_present": "",
            "nonblank_metric_rows": 0,
            "current_three_day_matched_rows": 0,
            "coverage_percentage": 0.0,
            "failure_reason": "SOURCE_FILE_MISSING",
            "sample_failures": "",
        }
    if not rows:
        return {
            "metric": metric,
            "source_filename": str(path),
            "builder": "|".join(contract.get("builders", [])),
            "exists": True,
            "row_count": 0,
            "latest_race_date": "",
            "date_coverage": "",
            "track_coverage": "",
            "unique_races": 0,
            "unique_runners": 0,
            "duplicate_keys": 0,
            "metric_columns_present": "",
            "nonblank_metric_rows": 0,
            "current_three_day_matched_rows": 0,
            "coverage_percentage": 0.0,
            "failure_reason": "SOURCE_FILE_EMPTY",
            "sample_failures": "",
        }

    keys = [row_key(row, contract) for row in rows]
    races = [key[:3] for key in keys if all(key[:3])]
    runners = [key for key in keys if all(key)]
    key_counts = Counter(runners)
    duplicate_keys = sum(1 for _, count in key_counts.items() if count > 1)
    dates = sorted({key[0] for key in keys if key[0]})
    tracks = sorted({key[1] for key in keys if key[1]})
    metric_columns_present = [field for field in contract["metric_fields"] if field in fields]
    nonblank_metric_rows = sum(1 for row in rows if has_metric(row, contract["metric_fields"])[0])
    form_keys = {form_key(runner) for runner in form_runners}
    matched = sum(1 for key in form_keys if key in key_counts and key_counts[key] == 1)
    failure = ""
    if not metric_columns_present:
        failure = "SOURCE_METRIC_COLUMN_MISSING"
    elif not set(r[0] for r in form_keys).intersection(dates):
        failure = "SOURCE_DATE_NOT_PRESENT"
    elif max(dates) < max(r[0] for r in form_keys):
        failure = "SOURCE_DATE_STALE"
    elif not set(r[1] for r in form_keys).intersection(tracks):
        failure = "SOURCE_TRACK_NOT_PRESENT"
    elif matched == 0:
        failure = "SOURCE_RUNNER_NOT_PRESENT"
    elif nonblank_metric_rows == 0:
        failure = "SOURCE_METRIC_VALUE_BLANK"
    elif duplicate_keys:
        failure = "SOURCE_DUPLICATE_KEY"
    else:
        failure = "OK"

    return {
        "metric": metric,
        "source_filename": str(path),
        "builder": "|".join(contract.get("builders", [])),
        "source_version": selected or Path(path).name,
        "generated_time": datetime.fromtimestamp(Path(path).stat().st_mtime, tz=timezone.utc).isoformat(),
        "exists": True,
        "row_count": len(rows),
        "latest_race_date": max(dates) if dates else "",
        "date_coverage": "|".join(dates[:20]) + ("..." if len(dates) > 20 else ""),
        "track_coverage": "|".join(tracks[:20]) + ("..." if len(tracks) > 20 else ""),
        "unique_races": len(set(races)),
        "unique_runners": len(set(runners)),
        "duplicate_keys": duplicate_keys,
        "metric_column": "|".join(metric_columns_present),
        "metric_columns_present": "|".join(metric_columns_present),
        "nonblank_metric_rows": nonblank_metric_rows,
        "matched_rows": matched,
        "unmatched_rows": len(form_runners) - matched,
        "current_three_day_matched_rows": matched,
        "coverage_percentage": round((matched / max(1, len(form_runners))) * 100, 2),
        "failure_reason": failure,
        "sample_failures": "",
    }


def join_failures_for(metric: str, contract: dict[str, Any], form_runners: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    path = contract.get("file")
    if path is None:
        return [
            {
                **runner,
                "metric": metric,
                "source_filename": "",
                "matched": "NO",
                "metric_column": "",
                "metric_nonblank": "NO",
                "failure_reason": "NO_APPROVED_PRODUCTION_SOURCE",
                "sample_source_dates": "",
            }
            for runner in form_runners
        ], {"NO_APPROVED_PRODUCTION_SOURCE": len(form_runners)}

    rows, fields = load_csv(path)
    if not Path(path).exists():
        return [
            {
                **runner,
                "metric": metric,
                "source_filename": str(path),
                "matched": "NO",
                "metric_column": "",
                "metric_nonblank": "NO",
                "failure_reason": "SOURCE_FILE_MISSING",
                "sample_source_dates": "",
            }
            for runner in form_runners
        ], {"SOURCE_FILE_MISSING": len(form_runners)}
    if not rows:
        return [
            {
                **runner,
                "metric": metric,
                "source_filename": str(path),
                "matched": "NO",
                "metric_column": "",
                "metric_nonblank": "NO",
                "failure_reason": "SOURCE_FILE_EMPTY",
                "sample_source_dates": "",
            }
            for runner in form_runners
        ], {"SOURCE_FILE_EMPTY": len(form_runners)}

    keys: defaultdict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    race_keys: defaultdict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    dates = set()
    tracks = set()
    metric_columns_present = [field for field in contract["metric_fields"] if field in fields]
    for row in rows:
        key = row_key(row, contract)
        keys[key].append(row)
        race_keys[key[:3]].append(row)
        if key[0]:
            dates.add(key[0])
        if key[1]:
            tracks.add(key[1])

    failure_counts: Counter[str] = Counter()
    out: list[dict[str, Any]] = []
    form_dates = {runner["race_date"] for runner in form_runners}
    sample_dates = "|".join(sorted(dates)[:10])
    for runner in form_runners:
        key = form_key(runner)
        race_key = form_race_key(runner)
        matched_rows = keys.get(key, [])
        metric_ok = False
        metric_col = ""
        reason = ""
        if not metric_columns_present:
            reason = "SOURCE_METRIC_COLUMN_MISSING"
        elif runner["race_date"] not in dates:
            reason = "SOURCE_DATE_NOT_PRESENT"
        elif runner["meeting"] not in tracks:
            reason = "SOURCE_TRACK_NOT_PRESENT"
        elif not race_keys.get(race_key):
            source_same_date_track = any(k[0] == runner["race_date"] and k[1] == runner["meeting"] for k in race_keys)
            reason = "SOURCE_RACE_NOT_PRESENT" if source_same_date_track else "SOURCE_TRACK_NOT_PRESENT"
        elif not matched_rows:
            reason = "SOURCE_RUNNER_NOT_PRESENT"
        elif len(matched_rows) > 1:
            reason = "SOURCE_DUPLICATE_KEY"
        else:
            metric_ok, metric_col = has_metric(matched_rows[0], contract["metric_fields"])
            reason = "OK" if metric_ok else "SOURCE_METRIC_VALUE_BLANK"
        failure_counts[reason] += 1
        out.append(
            {
                **runner,
                "metric": metric,
                "source_filename": str(path),
                "matched": "YES" if matched_rows else "NO",
                "metric_column": metric_col,
                "metric_nonblank": "YES" if metric_ok else "NO",
                "failure_reason": reason,
                "sample_source_dates": sample_dates,
                "source_has_form_date": "YES" if form_dates.intersection(dates) else "NO",
            }
        )
    return out, dict(failure_counts)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames: list[str] = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    form_runners = load_form_runners()
    form_dates = sorted({runner["race_date"] for runner in form_runners})
    form_tracks = sorted({runner["meeting"] for runner in form_runners})
    source_rows: list[dict[str, Any]] = []
    join_rows: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []
    failure_summary: dict[str, dict[str, int]] = {}

    for metric, contract in SOURCE_CONTRACTS.items():
        source_row = source_contract_for(metric, contract, form_runners)
        source_rows.append(source_row)
        metric_join_rows, failures = join_failures_for(metric, contract, form_runners)
        join_rows.extend(metric_join_rows)
        failure_summary[metric] = failures
        ok_count = sum(1 for row in metric_join_rows if row["failure_reason"] == "OK")
        coverage_rows.append(
            {
                "metric": metric,
                "form_runner_rows": len(form_runners),
                "populated_rows": ok_count,
                "coverage_percentage": round((ok_count / max(1, len(form_runners))) * 100, 2),
                "top_failure_reason": Counter(row["failure_reason"] for row in metric_join_rows).most_common(1)[0][0],
                "failure_counts": json.dumps(failures, sort_keys=True),
            }
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "form_runner_rows": len(form_runners),
        "form_dates": form_dates,
        "form_tracks": form_tracks,
        "sources": source_rows,
    }
    SOURCE_AUDIT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_csv(SOURCE_AUDIT_CSV, source_rows)
    SOURCE_AUDIT_TXT.write_text(
        "\n".join(
            [
                "EDGEiQ current intelligence source contract audit",
                f"generated_at={payload['generated_at']}",
                f"form_runner_rows={len(form_runners)}",
                f"form_dates={','.join(form_dates)}",
                f"form_tracks={','.join(form_tracks)}",
                "",
                *[
                    f"{row['metric']}: rows={row['row_count']} latest={row.get('latest_race_date','')} matched={row.get('matched_rows', row.get('current_three_day_matched_rows', 0))}/{len(form_runners)} reason={row['failure_reason']} source={row['source_filename']}"
                    for row in source_rows
                ],
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    JOIN_AUDIT_JSON.write_text(
        json.dumps(
            {
                "generated_at": payload["generated_at"],
                "form_runner_rows": len(form_runners),
                "failure_summary": failure_summary,
                "rows": join_rows[:2000],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_csv(JOIN_AUDIT_CSV, join_rows)
    JOIN_AUDIT_TXT.write_text(
        "\n".join(
            [
                "EDGEiQ Form Guide current intelligence join audit",
                f"generated_at={payload['generated_at']}",
                f"form_runner_rows={len(form_runners)}",
                "",
                *[f"{metric}: {json.dumps(counts, sort_keys=True)}" for metric, counts in failure_summary.items()],
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    COVERAGE_JSON.write_text(
        json.dumps(
            {
                "generated_at": payload["generated_at"],
                "form_runner_rows": len(form_runners),
                "coverage": coverage_rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_csv(COVERAGE_CSV, coverage_rows)
    COVERAGE_TXT.write_text(
        "\n".join(
            [
                "EDGEiQ Form Guide current intelligence coverage",
                f"generated_at={payload['generated_at']}",
                f"form_runner_rows={len(form_runners)}",
                "",
                *[
                    f"{row['metric']}: {row['populated_rows']}/{row['form_runner_rows']} ({row['coverage_percentage']}%) top_failure={row['top_failure_reason']}"
                    for row in coverage_rows
                ],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print("EDGEIQ_CURRENT_INTELLIGENCE_SOURCE_CONTRACT_AUDIT_COMPLETE")
    print(SOURCE_AUDIT_TXT)
    print(JOIN_AUDIT_TXT)
    print(COVERAGE_TXT)


if __name__ == "__main__":
    main()
