from __future__ import annotations

import csv
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from edgeiq_memory_safe_io import stream_csv_rows, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUTS = {
    "physics": DATA / "edgeiq_real_sectional_physics_features_v1.csv",
    "validation": DATA / "edgeiq_temporal_physics_validation_v1.csv",
    "identity_memory": DATA / "edgeiq_temporal_identity_memory_v1.csv",
    "results_truth": DATA / "edgeiq_canonical_results_truth_v1.csv",
    "regime": DATA / "edgeiq_temporal_research_regime_engine_v1.csv",
    "evidence": DATA / "edgeiq_temporal_evidence_accumulator_v1.csv",
    "fields": DATA / "edgeiq_vic_three_day_race_fields.csv",
    "market_entity": DATA / "edgeiq_canonical_market_entity_graph_v1.csv",
}

OUT = DATA / "edgeiq_research_coverage_audit_v1.csv"
SUMMARY = DATA / "edgeiq_research_coverage_summary_v1.csv"
BACKFILL = DATA / "edgeiq_research_backfill_priority_v1.csv"

AUDIT_FIELDS = [
    "coverage_type",
    "coverage_value",
    "total_rows",
    "validated_rows",
    "unique_horses",
    "unique_races",
    "coverage_grade",
    "coverage_status",
    "coverage_gap",
    "recommended_action",
    "research_priority",
    "trusted_for_live_modelling",
    "trusted_for_live_execution",
    "notes",
]

BACKFILL_FIELDS = [
    "priority",
    "coverage_type",
    "coverage_value",
    "coverage_gap",
    "current_validated_rows",
    "target_validated_rows",
    "required_data_source",
    "recommended_backfill_action",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

TRACK_ALIASES = {
    "BET365 YARRA VALLEY": "YARRA VALLEY",
    "SPORTSBET WANGARATTA": "WANGARATTA",
    "SOUTHSIDE PAKENHAM": "PAKENHAM",
    "SPORTSBET PAKENHAM": "PAKENHAM",
    "PAKENHAM SYNTHETIC": "PAKENHAM",
    "BALLARAT SYNTHETIC": "BALLARAT",
    "GEELONG SYNTHETIC": "GEELONG",
    "THE VALLEY": "MOONEE VALLEY",
    "SANDOWN HILLSIDE": "SANDOWN",
    "SANDOWN LAKESIDE": "SANDOWN",
    "CAULFIELD HEATH": "CAULFIELD HEATH",
}


def clean(value: object) -> str:
    text = str(value or "").strip()
    if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"}:
        return ""
    return text


def normalise_text(value: object) -> str:
    text = clean(value).upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.replace("&", " AND ")
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"['`’‘]", "", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalise_track(value: object) -> str:
    track = normalise_text(value)
    track = re.sub(r"\bRACING\b", "", track)
    track = re.sub(r"\bCLUB\b", "", track)
    track = re.sub(r"\s+", " ", track).strip()
    return TRACK_ALIASES.get(track, track)


def normalise_date(value: object) -> str:
    text = clean(value)
    if not text:
        return ""
    text = text.replace("/", "-")
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d-%m-%y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    match = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", text)
    if match:
        year, month, day = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return text[:10]


def normalise_race_no(value: object) -> str:
    text = clean(value).upper()
    match = re.search(r"\d+", text)
    return str(int(match.group(0))) if match else ""


def horse_key(value: object) -> str:
    return normalise_text(value)


def race_key(row: dict[str, object]) -> str:
    date = normalise_date(row.get("race_date"))
    track = normalise_track(row.get("track"))
    race_no = normalise_race_no(row.get("race_no"))
    return f"{date}|{track}|{race_no}" if date and track and race_no else ""


def runner_key(row: dict[str, object]) -> str:
    key = race_key(row)
    horse = horse_key(row.get("horse"))
    return f"{key}|{horse}" if key and horse else ""


def to_float(value: object) -> float:
    text = clean(value)
    if not text:
        return math.nan
    try:
        return float(re.sub(r"[^0-9.\-]", "", text))
    except ValueError:
        return math.nan


def to_int(value: object) -> int:
    number = to_float(value)
    if math.isnan(number):
        return 0
    return int(round(number))


def yes(value: object) -> bool:
    return clean(value).upper() in {"YES", "Y", "TRUE", "1", "SAFE", "TRUSTED_RESULT"}


def distance_bucket(value: object) -> str:
    distance = to_float(value)
    if math.isnan(distance):
        return "UNKNOWN"
    if distance <= 1200:
        return "SPRINT"
    if distance <= 1600:
        return "MILE"
    if distance <= 2000:
        return "MIDDLE"
    return "STAYING"


def field_size_bucket(value: int) -> str:
    if value <= 0:
        return "UNKNOWN"
    if value <= 7:
        return "SMALL"
    if value <= 11:
        return "MEDIUM"
    return "LARGE"


def repeat_bucket(starts: int) -> str:
    if starts <= 1:
        return "1_START"
    if starts == 2:
        return "2_START"
    if starts <= 4:
        return "3_TO_4_STARTS"
    return "5_PLUS_STARTS"


def grade_density(validated_rows: int, total_rows: int = 0) -> str:
    if validated_rows >= 500:
        return "A"
    if validated_rows >= 250:
        return "B"
    if validated_rows >= 100:
        return "C"
    if validated_rows >= 20:
        return "D"
    if total_rows >= 500 and validated_rows <= 0:
        return "F"
    return "F"


def status_for_grade(grade: str) -> str:
    return {
        "A": "STRONG_VALIDATED_DENSITY",
        "B": "USABLE_RESEARCH_DENSITY",
        "C": "EMERGING_RESEARCH_DENSITY",
        "D": "WEAK_RESEARCH_DENSITY",
        "F": "CRITICALLY_INSUFFICIENT",
    }.get(grade, "CRITICALLY_INSUFFICIENT")


def target_for_type(coverage_type: str) -> int:
    if coverage_type in {"RESULT_MATCH_RATE", "HORSE_REPEAT_STARTS"}:
        return 250
    if coverage_type in {"TRACK", "TEMPORAL_PATTERN", "ENERGY_CURVE"}:
        return 100
    return 50


def priority_for(coverage_type: str, grade: str, total_rows: int, validated_rows: int, coverage_value: str) -> str:
    if grade in {"A", "B"}:
        return "LOW"
    if coverage_type in {"HORSE_REPEAT_STARTS", "RESULT_MATCH_RATE"}:
        return "HIGH"
    if total_rows >= 250 and validated_rows < 20:
        return "HIGH"
    if coverage_type == "TRACK" and total_rows >= 100 and validated_rows < 20:
        return "HIGH"
    if coverage_type in {"DISTANCE_BUCKET", "FIELD_SIZE_BUCKET", "TEMPORAL_PATTERN", "ENERGY_CURVE"}:
        return "MEDIUM"
    if coverage_value == "UNKNOWN":
        return "MEDIUM"
    return "LOW"


def gap_text(coverage_type: str, validated_rows: int, total_rows: int, extra: str = "") -> str:
    target = target_for_type(coverage_type)
    if validated_rows >= target:
        return "No immediate coverage gap for current research threshold."
    if total_rows <= 0:
        return "No rows available for this coverage slice."
    base = f"Validated density below target: {validated_rows}/{target}."
    return f"{base} {extra}".strip()


def action_for(coverage_type: str, priority: str) -> str:
    if coverage_type == "RESULT_MATCH_RATE":
        return "Backfill settled finish-position truth and rerun temporal validation."
    if coverage_type == "HORSE_REPEAT_STARTS":
        return "Increase repeat-start linkage through canonical horse identity and older settled sectional history."
    if coverage_type == "TRACK":
        return "Prioritise trusted sectional/result joins for high-row tracks with low validation density."
    if coverage_type == "TEMPORAL_PATTERN":
        return "Continue evidence accumulation until each pattern reaches minimum validated sample."
    if coverage_type == "ENERGY_CURVE":
        return "Balance energy-curve validation samples before promotion review."
    if coverage_type == "SECTIONAL_SOURCE":
        return "Improve source lineage and results matching for under-covered sectional sources."
    if priority == "LOW":
        return "Monitor; descriptive gap only at current maturity."
    return "Backfill validated temporal/result evidence for this slice."


class BucketStats:
    def __init__(self) -> None:
        self.total_rows = 0
        self.validated_rows = 0
        self.horses: set[str] = set()
        self.validated_horses: set[str] = set()
        self.races: set[str] = set()
        self.validated_races: set[str] = set()

    def add(self, row: dict[str, str], validated: bool) -> None:
        self.total_rows += 1
        key = race_key(row)
        horse = horse_key(row.get("horse"))
        if key:
            self.races.add(key)
        if horse:
            self.horses.add(horse)
        if validated:
            self.validated_rows += 1
            if key:
                self.validated_races.add(key)
            if horse:
                self.validated_horses.add(horse)


def safe_input_rows(path: Path):
    try:
        yield from stream_csv_rows(path)
    except Exception:
        return


def build_race_context() -> tuple[dict[str, dict[str, object]], dict[str, int]]:
    contexts: dict[str, dict[str, object]] = {}
    field_counts: Counter[str] = Counter()
    for row in safe_input_rows(INPUTS["fields"]):
        key = race_key(row)
        if not key:
            continue
        field_counts[key] += 1
        contexts.setdefault(
            key,
            {
                "distance": clean(row.get("distance")),
                "distance_bucket": distance_bucket(row.get("distance")),
                "track_condition": clean(row.get("track_condition")) or "UNKNOWN",
                "track": normalise_track(row.get("track")),
            },
        )
    for key, count in field_counts.items():
        contexts.setdefault(key, {})
        contexts[key]["field_size"] = count
        contexts[key]["field_size_bucket"] = field_size_bucket(count)
    return contexts, dict(field_counts)


def build_safe_result_keys() -> set[str]:
    keys: set[str] = set()
    for row in safe_input_rows(INPUTS["results_truth"]):
        if yes(row.get("safe_for_model_validation")) and clean(row.get("finish_position")):
            key = runner_key(row)
            if key:
                keys.add(key)
    return keys


def is_validation_row_validated(row: dict[str, str], safe_results: set[str]) -> bool:
    if clean(row.get("finish_position")):
        return True
    key = runner_key(row)
    return bool(key and key in safe_results)


def add_bucket(
    buckets: dict[tuple[str, str], BucketStats],
    coverage_type: str,
    coverage_value: str,
    row: dict[str, str],
    validated: bool,
) -> None:
    value = clean(coverage_value) or "UNKNOWN"
    buckets[(coverage_type, value)].add(row, validated)


def build_coverage_buckets(race_context: dict[str, dict[str, object]], safe_results: set[str]) -> dict[tuple[str, str], BucketStats]:
    buckets: dict[tuple[str, str], BucketStats] = defaultdict(BucketStats)

    for row in safe_input_rows(INPUTS["physics"]):
        key = race_key(row)
        context = race_context.get(key, {})
        enriched = dict(row)
        add_bucket(buckets, "TRACK", normalise_track(row.get("track")) or "UNKNOWN", enriched, False)
        add_bucket(buckets, "DISTANCE_BUCKET", str(context.get("distance_bucket") or "UNKNOWN"), enriched, False)
        add_bucket(buckets, "FIELD_SIZE_BUCKET", str(context.get("field_size_bucket") or "UNKNOWN"), enriched, False)
        add_bucket(buckets, "SECTIONAL_SOURCE", clean(row.get("source_file")) or "UNKNOWN", enriched, False)
        if "track_condition" in context:
            add_bucket(buckets, "TRACK_CONDITION", str(context.get("track_condition") or "UNKNOWN"), enriched, False)

    for row in safe_input_rows(INPUTS["validation"]):
        key = race_key(row)
        context = race_context.get(key, {})
        validated = is_validation_row_validated(row, safe_results)
        add_bucket(buckets, "TRACK", normalise_track(row.get("track")) or "UNKNOWN", row, validated)
        add_bucket(buckets, "DISTANCE_BUCKET", str(context.get("distance_bucket") or "UNKNOWN"), row, validated)
        add_bucket(buckets, "FIELD_SIZE_BUCKET", str(context.get("field_size_bucket") or "UNKNOWN"), row, validated)
        add_bucket(buckets, "TEMPORAL_PATTERN", clean(row.get("phase_transition_pattern")) or "UNKNOWN", row, validated)
        add_bucket(buckets, "ENERGY_CURVE", clean(row.get("energy_curve_type")) or "UNKNOWN", row, validated)
        if "track_condition" in context:
            add_bucket(buckets, "TRACK_CONDITION", str(context.get("track_condition") or "UNKNOWN"), row, validated)

    for row in safe_input_rows(INPUTS["identity_memory"]):
        starts = to_int(row.get("starts_tracked"))
        validated_starts = to_int(row.get("validated_result_starts"))
        bucket = repeat_bucket(starts)
        pseudo = {"horse": row.get("horse", ""), "race_date": "", "track": "", "race_no": ""}
        stat = buckets[("HORSE_REPEAT_STARTS", bucket)]
        stat.total_rows += 1
        horse = horse_key(row.get("horse"))
        if horse:
            stat.horses.add(horse)
        if validated_starts > 0:
            stat.validated_rows += 1
            stat.validated_horses.add(horse)
        _ = pseudo

    return buckets


def build_audit_rows(buckets: dict[tuple[str, str], BucketStats]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for (coverage_type, coverage_value), stats in sorted(buckets.items()):
        grade = grade_density(stats.validated_rows, stats.total_rows)
        priority = priority_for(coverage_type, grade, stats.total_rows, stats.validated_rows, coverage_value)
        gap = gap_text(coverage_type, stats.validated_rows, stats.total_rows)
        rows.append(
            {
                "coverage_type": coverage_type,
                "coverage_value": coverage_value,
                "total_rows": stats.total_rows,
                "validated_rows": stats.validated_rows,
                "unique_horses": len(stats.horses),
                "unique_races": len(stats.races),
                "coverage_grade": grade,
                "coverage_status": status_for_grade(grade),
                "coverage_gap": gap,
                "recommended_action": action_for(coverage_type, priority),
                "research_priority": priority,
                "trusted_for_live_modelling": "NO",
                "trusted_for_live_execution": "NO",
                "notes": "Research coverage audit only; no modelling, pricing, or execution trust granted.",
            }
        )
    return rows


def build_result_match_row(safe_results: set[str]) -> dict[str, object]:
    total = 0
    validated = 0
    horses: set[str] = set()
    races: set[str] = set()
    for row in safe_input_rows(INPUTS["validation"]):
        total += 1
        if horse_key(row.get("horse")):
            horses.add(horse_key(row.get("horse")))
        if race_key(row):
            races.add(race_key(row))
        if is_validation_row_validated(row, safe_results):
            validated += 1
    grade = grade_density(validated, total)
    priority = priority_for("RESULT_MATCH_RATE", grade, total, validated, "TEMPORAL_VALIDATION")
    rate = 0.0 if total <= 0 else (validated / total) * 100.0
    return {
        "coverage_type": "RESULT_MATCH_RATE",
        "coverage_value": "TEMPORAL_VALIDATION",
        "total_rows": total,
        "validated_rows": validated,
        "unique_horses": len(horses),
        "unique_races": len(races),
        "coverage_grade": grade,
        "coverage_status": status_for_grade(grade),
        "coverage_gap": f"Temporal validation match rate is {rate:.2f}%; validated evidence remains below promotion-grade density.",
        "recommended_action": action_for("RESULT_MATCH_RATE", priority),
        "research_priority": priority,
        "trusted_for_live_modelling": "NO",
        "trusted_for_live_execution": "NO",
        "notes": "Uses canonical results truth where available; no predictive claims.",
    }


def build_backfill_rows(audit_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in audit_rows:
        priority = clean(row.get("research_priority"))
        grade = clean(row.get("coverage_grade"))
        if priority == "LOW" and grade in {"A", "B"}:
            continue
        coverage_type = clean(row.get("coverage_type"))
        target = target_for_type(coverage_type)
        current = to_int(row.get("validated_rows"))
        rows.append(
            {
                "priority": priority or "LOW",
                "coverage_type": coverage_type,
                "coverage_value": clean(row.get("coverage_value")),
                "coverage_gap": clean(row.get("coverage_gap")),
                "current_validated_rows": current,
                "target_validated_rows": target,
                "required_data_source": required_source_for(coverage_type),
                "recommended_backfill_action": clean(row.get("recommended_action")),
                "notes": "Offline research backfill queue; does not alter live worker, execution, prices, or ratings.",
            }
        )
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    rows.sort(key=lambda item: (priority_order.get(str(item["priority"]), 3), str(item["coverage_type"]), str(item["coverage_value"])))
    return rows


def required_source_for(coverage_type: str) -> str:
    return {
        "RESULT_MATCH_RATE": "canonical settled results truth plus temporal validation joins",
        "HORSE_REPEAT_STARTS": "historical sectional identity memory and canonical horse aliases",
        "TRACK": "trusted sectionals and settled results by Victorian track",
        "DISTANCE_BUCKET": "trusted sectionals and settled results by distance",
        "FIELD_SIZE_BUCKET": "race fields plus trusted sectionals and settled results",
        "TEMPORAL_PATTERN": "temporal physics validation rows",
        "ENERGY_CURVE": "temporal physics validation rows",
        "SECTIONAL_SOURCE": "sectional lineage, payload reconstruction, and result truth",
        "TRACK_CONDITION": "race field condition plus trusted sectionals and settled results",
    }.get(coverage_type, "research evidence backfill")


def missing_inputs() -> list[str]:
    return [path.name for path in INPUTS.values() if not path.exists()]


def count_market_links() -> tuple[int, int]:
    total = 0
    safe = 0
    for row in safe_input_rows(INPUTS["market_entity"]):
        total += 1
        if yes(row.get("safe_for_market_comparison")):
            safe += 1
    return total, safe


def build_summary(audit_rows: list[dict[str, object]], backfills: list[dict[str, object]], safe_results: set[str]) -> list[dict[str, object]]:
    validated_total = 0
    total_validation = 0
    for row in safe_input_rows(INPUTS["validation"]):
        total_validation += 1
        if is_validation_row_validated(row, safe_results):
            validated_total += 1
    match_rate = 0.0 if total_validation <= 0 else (validated_total / total_validation) * 100.0
    horses_5_plus = 0
    for row in safe_input_rows(INPUTS["identity_memory"]):
        if to_int(row.get("starts_tracked")) >= 5:
            horses_5_plus += 1
    tracks_under = sum(1 for row in audit_rows if row["coverage_type"] == "TRACK" and row["coverage_grade"] in {"D", "F"})
    patterns_under = sum(1 for row in audit_rows if row["coverage_type"] == "TEMPORAL_PATTERN" and row["coverage_grade"] in {"D", "F"})
    market_total, market_safe = count_market_links()
    values: list[dict[str, object]] = [
        {"metric": "audit_rows", "value": len(audit_rows)},
        {"metric": "high_priority_backfills", "value": sum(1 for row in backfills if row["priority"] == "HIGH")},
        {"metric": "medium_priority_backfills", "value": sum(1 for row in backfills if row["priority"] == "MEDIUM")},
        {"metric": "low_priority_backfills", "value": sum(1 for row in backfills if row["priority"] == "LOW")},
        {"metric": "validated_rows_total", "value": validated_total},
        {"metric": "validated_match_rate", "value": f"{match_rate:.2f}"},
        {"metric": "horses_with_5_plus_starts", "value": horses_5_plus},
        {"metric": "tracks_under_minimum_density", "value": tracks_under},
        {"metric": "patterns_under_minimum_density", "value": patterns_under},
        {"metric": "market_entity_rows", "value": market_total},
        {"metric": "safe_market_comparison_rows", "value": market_safe},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "research_pipeline_offline_only", "value": "YES"},
    ]
    for filename in missing_inputs():
        values.append({"metric": f"missing_input::{filename}", "value": "YES"})
    return values


def main() -> None:
    race_context, _ = build_race_context()
    safe_results = build_safe_result_keys()
    buckets = build_coverage_buckets(race_context, safe_results)
    audit_rows = build_audit_rows(buckets)
    audit_rows.append(build_result_match_row(safe_results))
    audit_rows.sort(key=lambda item: (str(item["coverage_type"]), str(item["coverage_value"])))
    backfills = build_backfill_rows(audit_rows)
    summary = build_summary(audit_rows, backfills, safe_results)
    write_csv_atomic(OUT, audit_rows, AUDIT_FIELDS)
    write_csv_atomic(BACKFILL, backfills, BACKFILL_FIELDS)
    write_csv_atomic(SUMMARY, summary, SUMMARY_FIELDS)
    print(f"Wrote {OUT}")
    print(f"Wrote {SUMMARY}")
    print(f"Wrote {BACKFILL}")
    print(f"audit_rows={len(audit_rows)} backfill_rows={len(backfills)}")


if __name__ == "__main__":
    main()
