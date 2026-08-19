from __future__ import annotations

import csv
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "public" / "data"

LIVE_FEED_PATH = DATA_DIR / "edgeiq_vic_live_terminal_feed_v1.csv"
REAL_SPEED_MAP_PATH = DATA_DIR / "edgeiq_real_speed_map_positions.csv"
HORSE_DNA_PATH = DATA_DIR / "edgeiq_horse_dna_v1.csv"
SECTIONAL_FEATURE_PATH = DATA_DIR / "edgeiq_sectional_feature_engine_v2.csv"
SECTIONAL_INTELLIGENCE_PATH = DATA_DIR / "edgeiq_sectional_intelligence_v2.csv"

OUTPUT_PATH = DATA_DIR / "edgeiq_tactical_speed_bucket_v1.csv"
AUDIT_PATH = DATA_DIR / "edgeiq_tactical_speed_bucket_v1_audit.csv"

TACTICAL_ORDER = ["LEADER", "ON_PACE", "MIDFIELD", "OFF_PACE", "BACKMARKER"]
FORWARD_DNA_ARCHETYPES = {"PRESSURE_LEADER", "FRONT_RUNNING_CONTROLLER"}
REARWARD_DNA_ARCHETYPES = {"STRONG_CLOSER"}

OUTPUT_COLUMNS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key",
    "barrier",
    "map_x_pct",
    "settling_band",
    "sectional_archetype",
    "dna_confidence",
    "early_speed_score",
    "late_strength_score",
    "tactical_speed_bucket",
    "tactical_position_group",
    "tempo_pressure_role",
    "bucket_confidence",
    "bucket_reason",
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
    raw = re.sub(r"^(SPORTSBET|SPORTS BET|BET365|LADBROKES|TABTOUCH|TAB)\s+", "", raw).strip()
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


def to_float(value: Any) -> float | None:
    raw = text(value)
    if not raw or raw.upper() in {"-", "NA", "N/A", "NULL", "NONE"}:
        return None
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return None


def format_number(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.2f}"


def canonical_settling_band(value: str | None) -> str:
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
    return ""


def bucket_from_map_x(map_x_pct: float | None) -> str:
    if map_x_pct is None:
        return "UNKNOWN"
    if map_x_pct <= 30:
        return "LEADER"
    if map_x_pct <= 45:
        return "ON_PACE"
    if map_x_pct <= 65:
        return "MIDFIELD"
    if map_x_pct <= 80:
        return "OFF_PACE"
    return "BACKMARKER"


def position_group(bucket: str) -> str:
    if bucket in {"LEADER", "ON_PACE"}:
        return "FORWARD"
    if bucket == "MIDFIELD":
        return "MIDFIELD"
    if bucket in {"OFF_PACE", "BACKMARKER"}:
        return "REARWARD"
    return "UNKNOWN"


def groups_agree(bucket: str, settling_band: str) -> bool:
    if not bucket or bucket == "UNKNOWN" or not settling_band:
        return False
    if bucket == settling_band:
        return True
    return position_group(bucket) == position_group(settling_band)


def near_forward_boundary(map_x_pct: float | None, bucket: str) -> bool:
    if map_x_pct is None:
        return False
    if bucket == "ON_PACE":
        return map_x_pct <= 34
    if bucket == "MIDFIELD":
        return map_x_pct <= 50
    if bucket == "OFF_PACE":
        return map_x_pct <= 69
    if bucket == "BACKMARKER":
        return map_x_pct <= 83
    return False


def near_rear_boundary(map_x_pct: float | None, bucket: str) -> bool:
    if map_x_pct is None:
        return False
    if bucket == "LEADER":
        return map_x_pct >= 27
    if bucket == "ON_PACE":
        return map_x_pct >= 42
    if bucket == "MIDFIELD":
        return map_x_pct >= 62
    if bucket == "OFF_PACE":
        return map_x_pct >= 77
    return False


def shift_bucket(bucket: str, direction: int) -> str:
    if bucket not in TACTICAL_ORDER:
        return bucket
    index = TACTICAL_ORDER.index(bucket)
    return TACTICAL_ORDER[max(0, min(len(TACTICAL_ORDER) - 1, index + direction))]


def apply_dna_adjustment(
    base_bucket: str,
    map_x_pct: float | None,
    settling_band: str,
    sectional_archetype: str,
    dna_confidence: str,
) -> tuple[str, str]:
    if base_bucket == "UNKNOWN":
        return base_bucket, "no usable map_x_pct; DNA adjustment skipped"

    archetype = sectional_archetype.upper()
    confidence = dna_confidence.upper()
    if confidence == "INSUFFICIENT" or not archetype:
        return base_bucket, "map_x_pct primary; no usable DNA adjustment"

    if archetype in FORWARD_DNA_ARCHETYPES:
        if base_bucket not in {"LEADER"} and (near_forward_boundary(map_x_pct, base_bucket) or position_group(settling_band) == "FORWARD"):
            adjusted = shift_bucket(base_bucket, -1)
            return adjusted, f"map_x_pct primary; {archetype} lifted borderline bucket forward from {base_bucket}"
        return base_bucket, f"map_x_pct primary; {archetype} confirmed without bucket shift"

    if archetype in REARWARD_DNA_ARCHETYPES:
        if base_bucket not in {"BACKMARKER"} and (near_rear_boundary(map_x_pct, base_bucket) or position_group(settling_band) == "REARWARD"):
            adjusted = shift_bucket(base_bucket, 1)
            return adjusted, f"map_x_pct primary; {archetype} shifted borderline bucket back from {base_bucket}"
        return base_bucket, f"map_x_pct primary; {archetype} confirmed without bucket shift"

    if archetype == "ONE_PACE_GRINDER":
        return base_bucket, "map_x_pct primary; ONE_PACE_GRINDER left neutral"

    return base_bucket, f"map_x_pct primary; {archetype} did not trigger tactical shift"


def confidence_for_bucket(map_x_pct: float | None, settling_band: str, bucket: str, dna_confidence: str) -> str:
    has_map = map_x_pct is not None
    has_settling = bool(settling_band)
    if not has_map and not has_settling:
        return "INSUFFICIENT"
    if has_map and has_settling and groups_agree(bucket, settling_band) and dna_confidence.upper() in {"HIGH", "MEDIUM"}:
        return "HIGH"
    if has_map:
        return "MEDIUM" if has_settling else "LOW"
    return "LOW"


def role_for_bucket(bucket: str, early_score: float | None, late_score: float | None, sectional_archetype: str, confidence: str) -> str:
    if bucket == "UNKNOWN" or confidence == "INSUFFICIENT":
        return "UNKNOWN"
    archetype = sectional_archetype.upper()
    if bucket in {"LEADER", "ON_PACE"}:
        if (early_score is not None and early_score >= 70) or archetype == "PRESSURE_LEADER":
            return "PRIMARY_PRESSURE"
        return "PACE_PRESENCE"
    if bucket == "MIDFIELD":
        return "NEUTRAL"
    if bucket in {"OFF_PACE", "BACKMARKER"}:
        if late_score is not None and late_score >= 70:
            return "CLOSING_PROFILE"
        return "REARWARD"
    return "UNKNOWN"


def build_lookup(rows: list[dict[str, str]], key_column: str = "horse_key") -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for row in rows:
        key = normalise_key(row.get(key_column) or row.get("horse"))
        if key:
            lookup[key] = row
    return lookup


def build_runner_lookup(rows: list[dict[str, str]]) -> dict[tuple[str, str, str, str], dict[str, str]]:
    lookup: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in rows:
        key = runner_key(row)
        if key[-1]:
            lookup[key] = row
    return lookup


def build_tactical_speed_bucket() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    live_rows = read_csv(LIVE_FEED_PATH)
    speed_rows = read_csv(REAL_SPEED_MAP_PATH)
    dna_rows = read_csv(HORSE_DNA_PATH)
    feature_rows = read_csv(SECTIONAL_FEATURE_PATH)
    intelligence_rows = read_csv(SECTIONAL_INTELLIGENCE_PATH)

    speed_lookup = build_runner_lookup(speed_rows)
    dna_lookup = build_lookup(dna_rows)

    output_rows: list[dict[str, Any]] = []
    dna_matched_count = 0
    map_missing_count = 0
    settling_missing_count = 0

    for live_row in live_rows:
        key = runner_key(live_row)
        if not key[-1]:
            continue

        speed_row = speed_lookup.get(key, {})
        dna_row = dna_lookup.get(key[-1], {})
        if dna_row:
            dna_matched_count += 1

        map_x_pct = to_float(speed_row.get("map_x_pct")) if speed_row else None
        if map_x_pct is None:
            map_x_pct = to_float(live_row.get("map_x_pct"))
        if map_x_pct is None:
            map_missing_count += 1

        settling_band = canonical_settling_band(speed_row.get("settling_band") if speed_row else "")
        if not settling_band:
            settling_band = canonical_settling_band(live_row.get("settling_band"))
        if not settling_band:
            settling_missing_count += 1

        base_bucket = bucket_from_map_x(map_x_pct)
        if base_bucket == "UNKNOWN" and settling_band:
            base_bucket = settling_band

        sectional_archetype = text(dna_row.get("sectional_archetype")) or "UNKNOWN_INSUFFICIENT_DATA"
        dna_confidence = text(dna_row.get("dna_confidence")) or "INSUFFICIENT"
        early_speed_score = to_float(dna_row.get("early_speed_score"))
        late_strength_score = to_float(dna_row.get("late_strength_score"))

        tactical_bucket, dna_reason = apply_dna_adjustment(
            base_bucket,
            map_x_pct,
            settling_band,
            sectional_archetype,
            dna_confidence,
        )

        bucket_confidence = confidence_for_bucket(map_x_pct, settling_band, tactical_bucket, dna_confidence)
        tempo_pressure_role = role_for_bucket(
            tactical_bucket,
            early_speed_score,
            late_strength_score,
            sectional_archetype,
            bucket_confidence,
        )

        agreement_note = "settling agrees" if groups_agree(tactical_bucket, settling_band) else "settling mixed"
        if not settling_band:
            agreement_note = "settling missing"
        if map_x_pct is None:
            agreement_note = "map_x_pct missing"

        output_rows.append(
            {
                "race_date": text(live_row.get("race_date")),
                "track": text(live_row.get("track")),
                "race_no": text(live_row.get("race_no")),
                "horse": text(live_row.get("horse")),
                "horse_key": key[-1],
                "barrier": text(speed_row.get("barrier")) or text(live_row.get("barrier")),
                "map_x_pct": format_number(map_x_pct),
                "settling_band": settling_band,
                "sectional_archetype": sectional_archetype,
                "dna_confidence": dna_confidence,
                "early_speed_score": format_number(early_speed_score),
                "late_strength_score": format_number(late_strength_score),
                "tactical_speed_bucket": tactical_bucket,
                "tactical_position_group": position_group(tactical_bucket),
                "tempo_pressure_role": tempo_pressure_role,
                "bucket_confidence": bucket_confidence,
                "bucket_reason": f"{dna_reason}; base={base_bucket}; {agreement_note}",
            }
        )

    bucket_counts = Counter(row["tactical_speed_bucket"] for row in output_rows)
    confidence_counts = Counter(row["bucket_confidence"] for row in output_rows)
    role_counts = Counter(row["tempo_pressure_role"] for row in output_rows)

    audit = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "live_terminal_rows_loaded": len(live_rows),
        "real_speed_map_rows_loaded": len(speed_rows),
        "horse_dna_rows_loaded": len(dna_rows),
        "sectional_feature_rows_loaded": len(feature_rows),
        "sectional_intelligence_rows_loaded": len(intelligence_rows),
        "output_rows": len(output_rows),
        "buckets_count": "; ".join(f"{name}:{count}" for name, count in sorted(bucket_counts.items())),
        "confidence_count": "; ".join(f"{name}:{count}" for name, count in sorted(confidence_counts.items())),
        "tempo_pressure_role_count": "; ".join(f"{name}:{count}" for name, count in sorted(role_counts.items())),
        "map_x_pct_missing_count": map_missing_count,
        "settling_band_missing_count": settling_missing_count,
        "dna_matched_count": dna_matched_count,
        "dna_unmatched_count": len(output_rows) - dna_matched_count,
        "status": "TACTICAL_SPEED_BUCKET_BUILT" if output_rows and map_missing_count < len(output_rows) else "TACTICAL_SPEED_BUCKET_INSUFFICIENT_INPUTS",
        "method_note": "map_x_pct primary; settling_band confirms; Horse DNA only nudges borderline cases and assigns pressure/closing roles.",
    }

    return output_rows, audit


def main() -> None:
    output_rows, audit = build_tactical_speed_bucket()
    write_csv(OUTPUT_PATH, output_rows, OUTPUT_COLUMNS)
    write_csv(AUDIT_PATH, [audit], list(audit.keys()))

    print(f"Tactical speed bucket rows written: {len(output_rows)}")
    print(f"Audit written: {AUDIT_PATH}")
    print(f"Status: {audit['status']}")
    print(f"Buckets: {audit['buckets_count']}")
    print(f"Confidence: {audit['confidence_count']}")
    print(f"Roles: {audit['tempo_pressure_role_count']}")


if __name__ == "__main__":
    main()
