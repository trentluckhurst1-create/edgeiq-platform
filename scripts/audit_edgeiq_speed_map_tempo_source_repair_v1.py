from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "public" / "data"

LIVE_FEED_PATH = DATA_DIR / "edgeiq_vic_live_terminal_feed_v1.csv"
REAL_SPEED_MAP_PATH = DATA_DIR / "edgeiq_real_speed_map_positions.csv"
MEETING_UNIVERSE_PATH = DATA_DIR / "edgeiq_vic_three_day_meeting_universe.csv"
CURRENT_PROJECTION_PATH = DATA_DIR / "edgeiq_current_field_projection_v5_2.csv"
RACE_SHAPE_FIT_PATH = DATA_DIR / "edgeiq_race_shape_fit_v1.csv"

OUTPUT_PATH = DATA_DIR / "edgeiq_speed_map_tempo_source_repair_v1.csv"
SUMMARY_PATH = DATA_DIR / "edgeiq_speed_map_tempo_source_repair_v1_summary.csv"

SOURCE_NAME_PATTERN = re.compile(r"(speed|pace|map|shape|tempo|sectional)", re.IGNORECASE)
DERIVED_OR_AUDIT_SOURCES = {
    "edgeiq_race_shape_fit_v1.csv",
    "edgeiq_race_shape_fit_v1_audit.csv",
    "edgeiq_race_shape_fit_coverage_v1.csv",
    "edgeiq_race_shape_fit_coverage_v1_summary.csv",
    "edgeiq_speed_map_tempo_source_repair_v1.csv",
    "edgeiq_speed_map_tempo_source_repair_v1_summary.csv",
}
VALID_TACTICAL_BUCKETS = {"LEADER", "ON_PACE", "MIDFIELD", "OFF_PACE", "BACKMARKER"}

FIELD_ALIASES = {
    "track": ["track"],
    "race_no": ["race_no", "race_number"],
    "horse_key": ["horse_key"],
    "pace_profile": ["pace_profile"],
    "speed_map_bucket": ["speed_map_bucket"],
    "run_style": ["run_style"],
    "settling_band": ["settling_band"],
    "map_style": ["map_style", "map_position"],
    "projected_tempo": ["projected_tempo", "projected_tempo_shape", "projected_race_shape", "expected_tempo"],
    "race_shape": ["race_shape", "projected_race_shape", "race_shape_bias", "pace_setup_label"],
    "pace_pressure": ["pace_pressure", "pace_pressure_score", "pace_collapse_risk"],
}

OUTPUT_COLUMNS = [
    "audit_section",
    "file",
    "rows",
    "has_track",
    "has_race_no",
    "has_horse_key",
    "has_pace_profile",
    "has_speed_map_bucket",
    "has_run_style",
    "has_settling_band",
    "has_projected_tempo",
    "has_race_shape",
    "has_pace_pressure",
    "has_map_style",
    "nonblank_track",
    "nonblank_race_no",
    "nonblank_horse_key",
    "nonblank_pace_profile",
    "nonblank_speed_map_bucket",
    "nonblank_run_style",
    "nonblank_settling_band",
    "nonblank_projected_tempo",
    "nonblank_race_shape",
    "nonblank_pace_pressure",
    "nonblank_map_style",
    "current_runner_matches",
    "current_speed_map_bucket_matches",
    "current_projected_tempo_matches",
    "current_pace_pressure_matches",
    "source_speed_map_bucket_nonblank_count",
    "terminal_speed_map_bucket_nonblank_count",
    "source_pace_profile_nonblank_count",
    "terminal_pace_profile_nonblank_count",
    "source_run_style_nonblank_count",
    "terminal_run_style_nonblank_count",
    "source_settling_band_nonblank_count",
    "terminal_settling_band_nonblank_count",
    "rows_matched",
    "rows_unmatched",
    "race_date",
    "track",
    "race_no",
    "runners",
    "speed_bucket_rows",
    "leader_count",
    "on_pace_count",
    "midfield_count",
    "backmarker_count",
    "off_pace_count",
    "settling_leader_count",
    "settling_on_pace_count",
    "settling_midfield_count",
    "settling_backmarker_count",
    "settling_off_pace_count",
    "inferred_tempo_from_speed_bucket",
    "inferred_tempo_from_settling_band",
    "conflict_flag",
    "tempo_source_note",
    "recommendation",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def normalise_key(value: str | None) -> str:
    raw = (value or "").upper().strip()
    raw = re.sub(r"\([A-Z]{2,3}\)$", "", raw).strip()
    return re.sub(r"[^A-Z0-9]+", "", raw)


def normalise_track(value: str | None) -> str:
    raw = (value or "").upper().strip()
    raw = re.sub(r"\bVIC\b.*$", "", raw).strip()
    raw = re.sub(r"\s+-\s+PROFESSIONAL.*$", "", raw).strip()
    raw = re.sub(r"^(SPORTSBET|SPORTS BET|BET365|LADBROKES|TABTOUCH|TAB|MRC|VRC)\s+", "", raw).strip()
    raw = re.sub(r"[^A-Z0-9]+", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


def normalise_race_no(value: str | None) -> str:
    raw = text(value).upper()
    match = re.search(r"\d+", raw)
    return match.group(0) if match else raw


def runner_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        text(row.get("race_date")),
        normalise_track(row.get("track")),
        normalise_race_no(row.get("race_no")),
        normalise_key(row.get("horse_key") or row.get("horse")),
    )


def race_key(row: dict[str, str]) -> tuple[str, str, str]:
    key = runner_key(row)
    return key[:3]


def canonical_position(value: str | None) -> str:
    raw = re.sub(r"[_\-]+", " ", text(value).upper())
    raw = re.sub(r"\s+", " ", raw).strip()
    if not raw:
        return ""
    if "OFF PACE" in raw or "OFFPACE" in raw:
        return "OFF_PACE"
    if "BACK" in raw or "CLOSER" in raw or "REAR" in raw:
        return "BACKMARKER"
    if "LEADER" in raw or "FRONT" in raw:
        return "LEADER"
    if raw == "PACE" or "ON PACE" in raw or "ONPACE" in raw or "PRESS" in raw:
        return "ON_PACE"
    if "MID" in raw:
        return "MIDFIELD"
    return raw.replace(" ", "_")


def infer_tempo(leader_count: int, on_pace_count: int, has_source: bool) -> str:
    if not has_source:
        return "NO_SPEED_BUCKET_SOURCE"
    pace_count = leader_count + on_pace_count
    if pace_count >= 4:
        return "FAST"
    if pace_count >= 2:
        return "HONEST"
    return "CONTROLLED"


def is_valid_tactical_bucket(value: str | None) -> bool:
    return canonical_position(value) in VALID_TACTICAL_BUCKETS


def candidate_paths() -> list[Path]:
    paths = {
        LIVE_FEED_PATH,
        REAL_SPEED_MAP_PATH,
        MEETING_UNIVERSE_PATH,
        CURRENT_PROJECTION_PATH,
        RACE_SHAPE_FIT_PATH,
    }
    for path in DATA_DIR.glob("*.csv"):
        if SOURCE_NAME_PATTERN.search(path.name):
            paths.add(path)
    paths.discard(OUTPUT_PATH)
    paths.discard(SUMMARY_PATH)
    return sorted(paths, key=lambda item: item.name.lower())


def first_alias(fieldnames: list[str], aliases: list[str]) -> str | None:
    field_lookup = {field.lower(): field for field in fieldnames}
    for alias in aliases:
        if alias.lower() in field_lookup:
            return field_lookup[alias.lower()]
    return None


def value_from_alias(row: dict[str, str], aliases: list[str]) -> str:
    lower_lookup = {key.lower(): key for key in row.keys()}
    for alias in aliases:
        column = lower_lookup.get(alias.lower())
        if column:
            value = text(row.get(column))
            if value:
                return value
    return ""


def inspect_source_file(path: Path, current_keys: set[tuple[str, str, str, str]]) -> tuple[dict[str, Any], dict[tuple[str, str, str, str], dict[str, str]]]:
    row_count = 0
    nonblank_counts = Counter()
    current_matches = 0
    current_speed_bucket_matches = 0
    current_projected_tempo_matches = 0
    current_pace_pressure_matches = 0
    current_speed_rows: dict[tuple[str, str, str, str], dict[str, str]] = {}

    if not path.exists():
        return {"file": path.name, "rows": 0}, current_speed_rows

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        has_fields = {
            name: first_alias(fieldnames, aliases) is not None
            for name, aliases in FIELD_ALIASES.items()
        }

        for row in reader:
            row_count += 1
            for name, aliases in FIELD_ALIASES.items():
                if value_from_alias(row, aliases):
                    nonblank_counts[name] += 1

            key = runner_key(row)
            if key in current_keys:
                current_matches += 1
                speed_bucket = value_from_alias(row, FIELD_ALIASES["speed_map_bucket"])
                projected_tempo = value_from_alias(row, FIELD_ALIASES["projected_tempo"])
                pace_pressure = value_from_alias(row, FIELD_ALIASES["pace_pressure"])
                if speed_bucket and is_valid_tactical_bucket(speed_bucket):
                    current_speed_bucket_matches += 1
                if projected_tempo:
                    current_projected_tempo_matches += 1
                if pace_pressure:
                    current_pace_pressure_matches += 1
                if speed_bucket or projected_tempo or pace_pressure:
                    current_speed_rows[key] = {
                        "source_file": path.name,
                        "speed_map_bucket": speed_bucket,
                        "projected_tempo": projected_tempo,
                        "pace_pressure": pace_pressure,
                        "run_style": value_from_alias(row, FIELD_ALIASES["run_style"]),
                        "map_style": value_from_alias(row, FIELD_ALIASES["map_style"]),
                    }

    audit_row = {
        "audit_section": "FIELD_PRESENCE",
        "file": path.name,
        "rows": row_count,
        "has_track": "YES" if has_fields.get("track") else "NO",
        "has_race_no": "YES" if has_fields.get("race_no") else "NO",
        "has_horse_key": "YES" if has_fields.get("horse_key") else "NO",
        "has_pace_profile": "YES" if has_fields.get("pace_profile") else "NO",
        "has_speed_map_bucket": "YES" if has_fields.get("speed_map_bucket") else "NO",
        "has_run_style": "YES" if has_fields.get("run_style") else "NO",
        "has_settling_band": "YES" if has_fields.get("settling_band") else "NO",
        "has_projected_tempo": "YES" if has_fields.get("projected_tempo") else "NO",
        "has_race_shape": "YES" if has_fields.get("race_shape") else "NO",
        "has_pace_pressure": "YES" if has_fields.get("pace_pressure") else "NO",
        "has_map_style": "YES" if has_fields.get("map_style") else "NO",
        "nonblank_track": nonblank_counts.get("track", 0),
        "nonblank_race_no": nonblank_counts.get("race_no", 0),
        "nonblank_horse_key": nonblank_counts.get("horse_key", 0),
        "nonblank_pace_profile": nonblank_counts.get("pace_profile", 0),
        "nonblank_speed_map_bucket": nonblank_counts.get("speed_map_bucket", 0),
        "nonblank_run_style": nonblank_counts.get("run_style", 0),
        "nonblank_settling_band": nonblank_counts.get("settling_band", 0),
        "nonblank_projected_tempo": nonblank_counts.get("projected_tempo", 0),
        "nonblank_race_shape": nonblank_counts.get("race_shape", 0),
        "nonblank_pace_pressure": nonblank_counts.get("pace_pressure", 0),
        "nonblank_map_style": nonblank_counts.get("map_style", 0),
        "current_runner_matches": current_matches,
        "current_speed_map_bucket_matches": current_speed_bucket_matches,
        "current_projected_tempo_matches": current_projected_tempo_matches,
        "current_pace_pressure_matches": current_pace_pressure_matches,
    }
    return audit_row, current_speed_rows


def count_nonblank(rows: list[dict[str, str]], field_name: str) -> int:
    return sum(1 for row in rows if text(row.get(field_name)))


def build_loss_audit(live_rows: list[dict[str, str]], speed_rows: list[dict[str, str]]) -> dict[str, Any]:
    live_by_key = {runner_key(row): row for row in live_rows if runner_key(row)[-1]}
    speed_by_key = {runner_key(row): row for row in speed_rows if runner_key(row)[-1]}
    matched_keys = set(live_by_key) & set(speed_by_key)

    def source_count(field_name: str) -> int:
        return sum(1 for key in matched_keys if text(speed_by_key[key].get(field_name)))

    def terminal_count(field_name: str) -> int:
        return sum(1 for key in matched_keys if text(live_by_key[key].get(field_name)))

    return {
        "audit_section": "LIVE_FEED_LOSS_AUDIT",
        "file": f"{REAL_SPEED_MAP_PATH.name} -> {LIVE_FEED_PATH.name}",
        "source_speed_map_bucket_nonblank_count": source_count("speed_map_bucket"),
        "terminal_speed_map_bucket_nonblank_count": terminal_count("speed_map_bucket"),
        "source_pace_profile_nonblank_count": source_count("pace_profile"),
        "terminal_pace_profile_nonblank_count": terminal_count("pace_profile"),
        "source_run_style_nonblank_count": source_count("run_style"),
        "terminal_run_style_nonblank_count": terminal_count("run_style"),
        "source_settling_band_nonblank_count": source_count("settling_band"),
        "terminal_settling_band_nonblank_count": terminal_count("settling_band"),
        "rows_matched": len(matched_keys),
        "rows_unmatched": len((set(live_by_key) | set(speed_by_key)) - matched_keys),
        "tempo_source_note": "Real speed-map source has settling_band but no speed_map_bucket, pace_profile, or run_style columns.",
    }


def choose_best_speed_source(source_rows_by_file: dict[str, dict[tuple[str, str, str, str], dict[str, str]]]) -> tuple[str, dict[tuple[str, str, str, str], dict[str, str]]]:
    best_file = ""
    best_rows: dict[tuple[str, str, str, str], dict[str, str]] = {}
    best_count = 0
    priority = [
        "speed_map_report.csv",
        "live_speed_map_v3.csv",
        "live_speed_map_v2.csv",
        "edgeiq_race_shape_engine_v2.csv",
        "pace_pressure.csv",
    ]

    for filename, rows in source_rows_by_file.items():
        if filename in DERIVED_OR_AUDIT_SOURCES:
            continue
        count = sum(1 for row in rows.values() if is_valid_tactical_bucket(row.get("speed_map_bucket")))
        if count > best_count or (count == best_count and filename in priority and (best_file not in priority or priority.index(filename) < priority.index(best_file))):
            best_file = filename
            best_rows = rows
            best_count = count
    return best_file, best_rows


def build_race_tempo_rows(
    live_rows: list[dict[str, str]],
    real_speed_rows: list[dict[str, str]],
    best_speed_source_file: str,
    best_speed_rows: dict[tuple[str, str, str, str], dict[str, str]],
) -> list[dict[str, Any]]:
    speed_by_key = {runner_key(row): row for row in real_speed_rows if runner_key(row)[-1]}
    live_by_race: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in live_rows:
        key = runner_key(row)
        if key[-1]:
            live_by_race[key[:3]].append(row)

    output_rows: list[dict[str, Any]] = []
    for key in sorted(live_by_race, key=lambda item: (item[0], item[1], int(item[2]) if item[2].isdigit() else item[2])):
        rows = live_by_race[key]
        speed_bucket_counts: Counter[str] = Counter()
        settling_counts: Counter[str] = Counter()
        speed_bucket_rows = 0

        for row in rows:
            rkey = runner_key(row)
            speed_source_row = best_speed_rows.get(rkey, {})
            bucket = canonical_position(speed_source_row.get("speed_map_bucket"))
            if bucket in VALID_TACTICAL_BUCKETS:
                speed_bucket_counts[bucket] += 1
                speed_bucket_rows += 1

            real_speed_row = speed_by_key.get(rkey, {})
            settling = canonical_position(real_speed_row.get("settling_band") or row.get("settling_band"))
            if settling:
                settling_counts[settling] += 1

        speed_tempo = infer_tempo(
            speed_bucket_counts.get("LEADER", 0),
            speed_bucket_counts.get("ON_PACE", 0),
            speed_bucket_rows > 0,
        )
        settling_tempo = infer_tempo(
            settling_counts.get("LEADER", 0),
            settling_counts.get("ON_PACE", 0),
            bool(settling_counts),
        )
        if speed_tempo == "NO_SPEED_BUCKET_SOURCE":
            conflict_flag = "NO_SPEED_BUCKET_SOURCE"
        elif speed_tempo != settling_tempo:
            conflict_flag = "TEMPO_SOURCE_CONFLICT"
        else:
            conflict_flag = "NO_CONFLICT"

        output_rows.append(
            {
                "audit_section": "RACE_TEMPO_CANDIDATE",
                "file": best_speed_source_file,
                "race_date": key[0],
                "track": key[1],
                "race_no": key[2],
                "runners": len(rows),
                "speed_bucket_rows": speed_bucket_rows,
                "leader_count": speed_bucket_counts.get("LEADER", 0),
                "on_pace_count": speed_bucket_counts.get("ON_PACE", 0),
                "midfield_count": speed_bucket_counts.get("MIDFIELD", 0),
                "backmarker_count": speed_bucket_counts.get("BACKMARKER", 0),
                "off_pace_count": speed_bucket_counts.get("OFF_PACE", 0),
                "settling_leader_count": settling_counts.get("LEADER", 0),
                "settling_on_pace_count": settling_counts.get("ON_PACE", 0),
                "settling_midfield_count": settling_counts.get("MIDFIELD", 0),
                "settling_backmarker_count": settling_counts.get("BACKMARKER", 0),
                "settling_off_pace_count": settling_counts.get("OFF_PACE", 0),
                "inferred_tempo_from_speed_bucket": speed_tempo,
                "inferred_tempo_from_settling_band": settling_tempo,
                "conflict_flag": conflict_flag,
                "tempo_source_note": f"Speed bucket source={best_speed_source_file or 'NONE'}; settling source={REAL_SPEED_MAP_PATH.name}",
            }
        )

    return output_rows


def build_audit() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    live_rows = read_csv(LIVE_FEED_PATH)
    real_speed_rows = read_csv(REAL_SPEED_MAP_PATH)
    current_keys = {runner_key(row) for row in live_rows if runner_key(row)[-1]}

    output_rows: list[dict[str, Any]] = []
    source_rows_by_file: dict[str, dict[tuple[str, str, str, str], dict[str, str]]] = {}

    for path in candidate_paths():
        audit_row, matched_source_rows = inspect_source_file(path, current_keys)
        output_rows.append(audit_row)
        if matched_source_rows and path.name not in DERIVED_OR_AUDIT_SOURCES:
            source_rows_by_file[path.name] = matched_source_rows

    loss_row = build_loss_audit(live_rows, real_speed_rows)
    output_rows.append(loss_row)

    best_speed_source_file, best_speed_rows = choose_best_speed_source(source_rows_by_file)
    race_rows = build_race_tempo_rows(live_rows, real_speed_rows, best_speed_source_file, best_speed_rows)
    output_rows.extend(race_rows)

    terminal_speed_bucket_nonblank = count_nonblank(live_rows, "speed_map_bucket")
    terminal_pace_profile_nonblank = count_nonblank(live_rows, "pace_profile")
    terminal_run_style_nonblank = count_nonblank(live_rows, "run_style")
    terminal_settling_band_nonblank = count_nonblank(live_rows, "settling_band")
    real_speed_bucket_nonblank = count_nonblank(real_speed_rows, "speed_map_bucket")
    real_settling_band_nonblank = count_nonblank(real_speed_rows, "settling_band")
    best_speed_bucket_matches = sum(1 for row in best_speed_rows.values() if is_valid_tactical_bucket(row.get("speed_map_bucket")))
    tempo_conflicts = sum(1 for row in race_rows if row.get("conflict_flag") == "TEMPO_SOURCE_CONFLICT")
    no_speed_source_races = sum(1 for row in race_rows if row.get("conflict_flag") == "NO_SPEED_BUCKET_SOURCE")

    if terminal_speed_bucket_nonblank and terminal_pace_profile_nonblank:
        recommendation = "TEMPO_SOURCE_HEALTHY"
    elif best_speed_bucket_matches >= len(current_keys) * 0.8:
        recommendation = "REPAIR_LIVE_FEED_FIELD_PROPAGATION"
    elif best_speed_bucket_matches > 0:
        recommendation = "USE_ALTERNATIVE_TEMPO_SOURCE"
    else:
        recommendation = "TEMPO_SOURCE_NOT_AVAILABLE"

    candidate_files_with_speed_bucket = [
        row["file"]
        for row in output_rows
        if row.get("audit_section") == "FIELD_PRESENCE" and int(row.get("nonblank_speed_map_bucket") or 0) > 0
    ]
    candidate_files_with_projected_tempo = [
        row["file"]
        for row in output_rows
        if row.get("audit_section") == "FIELD_PRESENCE" and int(row.get("nonblank_projected_tempo") or 0) > 0
    ]

    summary = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "status": "SPEED_MAP_TEMPO_SOURCE_REPAIR_AUDITED",
        "candidate_files_inspected": sum(1 for row in output_rows if row.get("audit_section") == "FIELD_PRESENCE"),
        "live_terminal_rows": len(live_rows),
        "real_speed_map_rows": len(real_speed_rows),
        "current_runner_keys": len(current_keys),
        "terminal_speed_map_bucket_nonblank": terminal_speed_bucket_nonblank,
        "terminal_pace_profile_nonblank": terminal_pace_profile_nonblank,
        "terminal_run_style_nonblank": terminal_run_style_nonblank,
        "terminal_settling_band_nonblank": terminal_settling_band_nonblank,
        "real_speed_map_speed_map_bucket_nonblank": real_speed_bucket_nonblank,
        "real_speed_map_settling_band_nonblank": real_settling_band_nonblank,
        "best_speed_bucket_source": best_speed_source_file or "NONE",
        "best_speed_bucket_current_matches": best_speed_bucket_matches,
        "candidate_files_with_speed_map_bucket": "; ".join(candidate_files_with_speed_bucket) if candidate_files_with_speed_bucket else "NONE",
        "candidate_files_with_projected_tempo": "; ".join(candidate_files_with_projected_tempo) if candidate_files_with_projected_tempo else "NONE",
        "race_contexts_audited": len(race_rows),
        "tempo_conflict_races": tempo_conflicts,
        "no_speed_bucket_source_races": no_speed_source_races,
        "recommendation": recommendation,
        "diagnostic_note": "Terminal feed has blank pace_profile and speed_map_bucket. Real speed-map positions carry settling_band only; alternative speed bucket sources are partial/current-date dependent.",
    }

    for row in output_rows:
        row.setdefault("recommendation", recommendation if row.get("audit_section") == "LIVE_FEED_LOSS_AUDIT" else "")

    return output_rows, summary


def main() -> None:
    rows, summary = build_audit()
    write_csv(OUTPUT_PATH, rows, OUTPUT_COLUMNS)
    write_csv(SUMMARY_PATH, [summary], list(summary.keys()))

    print(f"Audit rows written: {len(rows)}")
    print(f"Summary written: {SUMMARY_PATH}")
    print(f"Status: {summary['status']}")
    print(f"Recommendation: {summary['recommendation']}")
    print(f"Best speed bucket source: {summary['best_speed_bucket_source']} ({summary['best_speed_bucket_current_matches']} current matches)")


if __name__ == "__main__":
    main()
