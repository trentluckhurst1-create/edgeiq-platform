from __future__ import annotations

import csv
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUTS = {
    "quality": DATA / "edgeiq_sectional_payload_quality_v1.csv",
    "features": DATA / "edgeiq_real_sectional_physics_features_v1.csv",
    "validation": DATA / "edgeiq_temporal_physics_validation_v1.csv",
    "shadow_state": DATA / "edgeiq_shadow_environment_state_v1.csv",
    "fields": DATA / "edgeiq_vic_three_day_race_fields.csv",
}

OUT = DATA / "edgeiq_sectional_source_coverage_audit_v1.csv"
SUMMARY = DATA / "edgeiq_sectional_source_coverage_summary_v1.csv"
PRIORITY = DATA / "edgeiq_sectional_acquisition_priority_v1.csv"

AUDIT_FIELDS = [
    "coverage_type",
    "coverage_value",
    "total_rows",
    "high_trust_rows",
    "usable_rows",
    "partial_rows",
    "degraded_rows",
    "unsafe_rows",
    "safe_temporal_rows",
    "safe_shadow_rows",
    "quality_rate",
    "shadow_quality_rate",
    "dominant_blocker",
    "coverage_grade",
    "coverage_status",
    "recommended_action",
    "priority",
    "notes",
]

PRIORITY_FIELDS = [
    "priority",
    "target_type",
    "target_value",
    "current_quality_grade",
    "dominant_blocker",
    "affected_rows",
    "safe_shadow_rows",
    "recommended_acquisition_action",
    "target_source_hint",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

TRACK_ALIASES = {
    "THE VALLEY": "MOONEE VALLEY",
    "SPORTSBET PAKENHAM": "PAKENHAM",
    "SOUTHSIDE PAKENHAM": "PAKENHAM",
    "PAKENHAM SYNTHETIC": "PAKENHAM",
    "BALLARAT SYNTHETIC": "BALLARAT",
    "GEELONG SYNTHETIC": "GEELONG",
    "SANDOWN HILLSIDE": "SANDOWN",
    "SANDOWN LAKESIDE": "SANDOWN",
}

METRO_TRACKS = {"FLEMINGTON", "CAULFIELD", "CAULFIELD HEATH", "MOONEE VALLEY", "SANDOWN"}
PROVINCIAL_TRACKS = {"PAKENHAM", "CRANBOURNE", "BALLARAT", "BENDIGO", "GEELONG", "SEYMOUR", "SALE", "MORNINGTON", "WERRIBEE", "WODONGA", "WANGARATTA"}
WATCH_VALUES = {
    ("TRACK", "HORSHAM"),
    ("TRACK_FAMILY", "COUNTRY"),
    ("DISTANCE_BUCKET", "MILE"),
    ("RACE_CLASS", "BM56"),
    ("SHADOW_ENVIRONMENT", "track:HORSHAM"),
    ("SHADOW_ENVIRONMENT", "track_family:COUNTRY"),
    ("SHADOW_ENVIRONMENT", "tempo_bucket:MEDIUM"),
    ("SHADOW_ENVIRONMENT", "race_class:BM56"),
    ("SHADOW_ENVIRONMENT", "distance_bucket:MILE"),
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
    track = re.sub(r"\bRACING\b|\bCLUB\b", "", track)
    track = re.sub(r"\s+", " ", track).strip()
    return TRACK_ALIASES.get(track, track)


def normalise_date(value: object) -> str:
    text = clean(value).replace("/", "-")
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d-%m-%y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    match = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", text)
    if match:
        y, m, d = match.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"
    return text[:10]


def normalise_race_no(value: object) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def runner_key(row: dict[str, object]) -> str:
    date = normalise_date(row.get("race_date"))
    track = normalise_track(row.get("track"))
    race_no = normalise_race_no(row.get("race_no"))
    horse = normalise_text(row.get("horse"))
    return f"{date}|{track}|{race_no}|{horse}" if date and track and race_no and horse else ""


def race_key(row: dict[str, object]) -> str:
    date = normalise_date(row.get("race_date"))
    track = normalise_track(row.get("track"))
    race_no = normalise_race_no(row.get("race_no"))
    return f"{date}|{track}|{race_no}" if date and track and race_no else ""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{int(datetime.now().timestamp() * 1000)}.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def to_float(value: object) -> float:
    try:
        return float(clean(value))
    except ValueError:
        return math.nan


def to_int(value: object) -> int:
    try:
        return int(float(clean(value)))
    except ValueError:
        return 0


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


def track_family(track: str) -> str:
    if track in METRO_TRACKS:
        return "METRO"
    if track in PROVINCIAL_TRACKS:
        return "PROVINCIAL"
    if track:
        return "COUNTRY"
    return "UNKNOWN"


def yes(value: object) -> bool:
    return clean(value).upper() in {"YES", "Y", "TRUE", "1"}


def fmt(value: float) -> str:
    return f"{max(0.0, min(100.0, value)):.2f}"


def build_field_context() -> dict[str, dict[str, str]]:
    context: dict[str, dict[str, str]] = {}
    for row in read_csv(INPUTS["fields"]):
        key = race_key(row)
        if not key:
            continue
        track = normalise_track(row.get("track"))
        context.setdefault(
            key,
            {
                "distance_bucket": distance_bucket(row.get("distance")),
                "race_class": normalise_text(row.get("race_class")) or "UNKNOWN",
                "track_family": track_family(track),
            },
        )
    return context


def build_phase_index() -> dict[str, str]:
    return {
        runner_key(row): clean(row.get("phase_transition_pattern")) or "UNKNOWN"
        for row in read_csv(INPUTS["validation"])
        if runner_key(row)
    }


def active_shadow_environments() -> set[str]:
    envs: set[str] = set()
    for row in read_csv(INPUTS["shadow_state"]):
        if clean(row.get("current_status")) in {"ACTIVE_STABLE_RESEARCH", "DECAYING_RESEARCH", "SAMPLE_GROWTH_PHASE"}:
            env = clean(row.get("environment_key"))
            if env:
                envs.add(env)
    return envs


class Stats:
    def __init__(self) -> None:
        self.total = 0
        self.grades = Counter()
        self.blockers = Counter()
        self.safe_temporal = 0
        self.safe_shadow = 0

    def add(self, row: dict[str, str]) -> None:
        self.total += 1
        self.grades[clean(row.get("source_quality_grade")) or "UNKNOWN"] += 1
        self.blockers[clean(row.get("quality_blocker")) or "UNKNOWN"] += 1
        self.safe_temporal += 1 if yes(row.get("safe_for_temporal_research")) else 0
        self.safe_shadow += 1 if yes(row.get("safe_for_shadow_research")) else 0


def add_bucket(buckets: dict[tuple[str, str], Stats], coverage_type: str, coverage_value: str, row: dict[str, str]) -> None:
    buckets[(coverage_type, clean(coverage_value) or "UNKNOWN")].add(row)


def build_buckets() -> dict[tuple[str, str], Stats]:
    context = build_field_context()
    phase_index = build_phase_index()
    active_envs = active_shadow_environments()
    buckets: dict[tuple[str, str], Stats] = defaultdict(Stats)
    for row in read_csv(INPUTS["quality"]):
        track = normalise_track(row.get("track")) or "UNKNOWN"
        ctx = context.get(race_key(row), {})
        phase = phase_index.get(runner_key(row), "UNKNOWN")
        family = ctx.get("track_family") or track_family(track)
        add_bucket(buckets, "TRACK", track, row)
        add_bucket(buckets, "TRACK_FAMILY", family, row)
        add_bucket(buckets, "DISTANCE_BUCKET", ctx.get("distance_bucket") or "UNKNOWN", row)
        add_bucket(buckets, "RACE_CLASS", ctx.get("race_class") or "UNKNOWN", row)
        add_bucket(buckets, "SOURCE_FILE", clean(row.get("source_file")) or "UNKNOWN", row)
        add_bucket(buckets, "PHASE_PATTERN", phase, row)
        add_bucket(buckets, "QUALITY_BLOCKER", clean(row.get("quality_blocker")) or "UNKNOWN", row)
        candidate_envs = {
            f"track:{track}",
            f"track_family:{family}",
            f"distance_bucket:{ctx.get('distance_bucket') or 'UNKNOWN'}",
            f"race_class:{ctx.get('race_class') or 'UNKNOWN'}",
        }
        if track == "HORSHAM":
            candidate_envs.add("tempo_bucket:MEDIUM")
        for env in candidate_envs:
            if env in active_envs or (env in {"track:HORSHAM", "track_family:COUNTRY", "tempo_bucket:MEDIUM", "race_class:BM56", "distance_bucket:MILE"}):
                add_bucket(buckets, "SHADOW_ENVIRONMENT", env, row)
    return buckets


def grade_coverage(stats: Stats) -> tuple[str, str]:
    if stats.total <= 0:
        return "F", "NO_COVERAGE"
    usable = stats.grades.get("A", 0) + stats.grades.get("B", 0)
    quality_rate = usable / stats.total
    shadow_rate = stats.safe_shadow / stats.total
    unsafe_rate = stats.grades.get("F", 0) / stats.total
    degraded_rate = (stats.grades.get("D", 0) + stats.grades.get("F", 0)) / stats.total
    if quality_rate >= 0.45 and shadow_rate >= 0.25:
        return "A", "STRONG_HIGH_TRUST_OR_USABLE_COVERAGE"
    if quality_rate >= 0.20 or shadow_rate >= 0.10:
        return "B", "USABLE_COVERAGE"
    if stats.safe_temporal / stats.total >= 0.45 or stats.grades.get("C", 0) / stats.total >= 0.45:
        return "C", "PARTIAL_RESEARCH_USABLE_COVERAGE"
    if degraded_rate >= 0.35 or stats.blockers.get("WEAK_PHASE_CONFIDENCE", 0) > stats.total * 0.35:
        return "D", "DEGRADED_OR_WEAK_PHASE_CONFIDENCE"
    if unsafe_rate >= 0.25:
        return "F", "UNSAFE_OR_UNUSABLE_COVERAGE"
    return "D", "WEAK_COVERAGE"


def recommended_action(coverage_type: str, value: str, blocker: str, grade: str) -> str:
    if grade in {"A", "B"}:
        return "Monitor existing source; no urgent acquisition required."
    if blocker == "WEAK_PHASE_CONFIDENCE":
        return "Repair early/mid/late phase extraction and validate phase confidence before shadow use."
    if blocker == "LOW_SPLIT_COMPLETENESS":
        return "Harvest fuller sectional splits from direct source payloads."
    if blocker == "UNSAFE_RECONSTRUCTION_RISK":
        return "Prioritise direct source payload over reconstructed-only rows and improve lineage."
    if coverage_type == "SHADOW_ENVIRONMENT":
        return "Target VIC country BM56/BM64 mile and medium-tempo races first with fuller split payloads."
    return "Improve source lineage, split depth, and physics validation for this coverage slice."


def priority_for(coverage_type: str, value: str, stats: Stats, grade: str, blocker: str) -> str:
    quality_rate = (stats.grades.get("A", 0) + stats.grades.get("B", 0)) / max(1, stats.total)
    shadow_rate = stats.safe_shadow / max(1, stats.total)
    if (coverage_type, value) in WATCH_VALUES:
        return "HIGH" if grade in {"C", "D", "F"} or shadow_rate < 0.20 else "MEDIUM"
    if coverage_type == "SHADOW_ENVIRONMENT" and (grade in {"C", "D", "F"} or shadow_rate < 0.20):
        return "HIGH"
    if stats.total >= 500 and shadow_rate < 0.10:
        return "HIGH"
    if blocker in {"WEAK_PHASE_CONFIDENCE", "LOW_SPLIT_COMPLETENESS"} and stats.total >= 100:
        return "HIGH"
    if blocker == "UNSAFE_RECONSTRUCTION_RISK" and stats.total >= 100:
        return "MEDIUM"
    if grade in {"C", "D"}:
        return "MEDIUM"
    if quality_rate >= 0.20:
        return "LOW"
    return "LOW"


def build_audit_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for (coverage_type, value), stats in sorted(build_buckets().items()):
        high = stats.grades.get("A", 0)
        usable = stats.grades.get("B", 0)
        partial = stats.grades.get("C", 0)
        degraded = stats.grades.get("D", 0)
        unsafe = stats.grades.get("F", 0)
        quality_rate = ((high + usable) / max(1, stats.total)) * 100.0
        shadow_rate = (stats.safe_shadow / max(1, stats.total)) * 100.0
        blocker = stats.blockers.most_common(1)[0][0] if stats.blockers else "UNKNOWN"
        grade, status = grade_coverage(stats)
        priority = priority_for(coverage_type, value, stats, grade, blocker)
        rows.append(
            {
                "coverage_type": coverage_type,
                "coverage_value": value,
                "total_rows": stats.total,
                "high_trust_rows": high,
                "usable_rows": usable,
                "partial_rows": partial,
                "degraded_rows": degraded,
                "unsafe_rows": unsafe,
                "safe_temporal_rows": stats.safe_temporal,
                "safe_shadow_rows": stats.safe_shadow,
                "quality_rate": fmt(quality_rate),
                "shadow_quality_rate": fmt(shadow_rate),
                "dominant_blocker": blocker,
                "coverage_grade": grade,
                "coverage_status": status,
                "recommended_action": recommended_action(coverage_type, value, blocker, grade),
                "priority": priority,
                "notes": "Sectional source coverage audit only. Offline research; no live modelling, overlays, ratings, or execution.",
            }
        )
    return rows


def build_priority_rows(audit_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for row in audit_rows:
        priority = clean(row.get("priority"))
        if priority not in {"HIGH", "MEDIUM", "LOW"}:
            continue
        if priority == "LOW" and clean(row.get("coverage_grade")) in {"A", "B"}:
            continue
        blocker = clean(row.get("dominant_blocker"))
        if clean(row.get("coverage_type")) == "SHADOW_ENVIRONMENT":
            hint = "VIC country BM56/BM64 mile and medium-tempo sectional payloads"
        elif blocker == "UNSAFE_RECONSTRUCTION_RISK":
            hint = "direct official sectional payload source, not reconstructed exports"
        else:
            hint = "Racing.com/Racing Australia sectional source lineage with fuller split ladders"
        out.append(
            {
                "priority": priority,
                "target_type": clean(row.get("coverage_type")),
                "target_value": clean(row.get("coverage_value")),
                "current_quality_grade": clean(row.get("coverage_grade")),
                "dominant_blocker": blocker,
                "affected_rows": clean(row.get("total_rows")),
                "safe_shadow_rows": clean(row.get("safe_shadow_rows")),
                "recommended_acquisition_action": clean(row.get("recommended_action")),
                "target_source_hint": hint,
                "notes": "Acquisition priority is research-only and does not authorise modelling or execution.",
            }
        )
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    out.sort(key=lambda item: (order.get(str(item["priority"]), 9), -to_int(item["affected_rows"]), str(item["target_type"]), str(item["target_value"])))
    return out


def grade_lookup(audit_rows: list[dict[str, object]], coverage_type: str, value: str) -> str:
    for row in audit_rows:
        if row["coverage_type"] == coverage_type and row["coverage_value"] == value:
            return str(row["coverage_grade"])
    return "UNKNOWN"


def build_summary(audit_rows: list[dict[str, object]], priorities: list[dict[str, object]]) -> list[dict[str, object]]:
    priority_counts = Counter(str(row["priority"]) for row in priorities)
    weak_tracks = sum(1 for row in audit_rows if row["coverage_type"] == "TRACK" and row["coverage_grade"] in {"D", "F"})
    unsafe_sources = sum(1 for row in audit_rows if row["coverage_type"] == "SOURCE_FILE" and row["dominant_blocker"] == "UNSAFE_RECONSTRUCTION_RISK")
    weak_shadow = sum(1 for row in audit_rows if row["coverage_type"] == "SHADOW_ENVIRONMENT" and row["coverage_grade"] in {"C", "D", "F"})
    values: list[dict[str, object]] = [
        {"metric": "audit_rows", "value": len(audit_rows)},
        {"metric": "high_priority_acquisition_targets", "value": priority_counts.get("HIGH", 0)},
        {"metric": "medium_priority_acquisition_targets", "value": priority_counts.get("MEDIUM", 0)},
        {"metric": "low_priority_acquisition_targets", "value": priority_counts.get("LOW", 0)},
        {"metric": "tracks_with_weak_quality", "value": weak_tracks},
        {"metric": "sources_with_unsafe_reconstruction", "value": unsafe_sources},
        {"metric": "shadow_environments_with_weak_quality", "value": weak_shadow},
        {"metric": "horsham_quality_grade", "value": grade_lookup(audit_rows, "TRACK", "HORSHAM")},
        {"metric": "country_quality_grade", "value": grade_lookup(audit_rows, "TRACK_FAMILY", "COUNTRY")},
        {"metric": "medium_tempo_quality_grade", "value": grade_lookup(audit_rows, "SHADOW_ENVIRONMENT", "tempo_bucket:MEDIUM")},
        {"metric": "bm56_quality_grade", "value": grade_lookup(audit_rows, "RACE_CLASS", "BM56")},
        {"metric": "mile_quality_grade", "value": grade_lookup(audit_rows, "DISTANCE_BUCKET", "MILE")},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "offline_research_only", "value": "YES"},
    ]
    for path in INPUTS.values():
        if not path.exists():
            values.append({"metric": f"missing_input::{path.name}", "value": "YES"})
    return values


def main() -> None:
    audit_rows = build_audit_rows()
    priority_rows = build_priority_rows(audit_rows)
    summary = build_summary(audit_rows, priority_rows)
    write_csv(OUT, audit_rows, AUDIT_FIELDS)
    write_csv(PRIORITY, priority_rows, PRIORITY_FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    print("=" * 88)
    print("EDGEIQ SECTIONAL SOURCE COVERAGE AUDIT V1")
    print("=" * 88)
    print(f"audit rows: {len(audit_rows)}")
    print(f"priority rows: {len(priority_rows)}")
    for row in summary:
        if row["metric"] in {"high_priority_acquisition_targets", "tracks_with_weak_quality", "shadow_environments_with_weak_quality", "horsham_quality_grade", "country_quality_grade", "medium_tempo_quality_grade", "bm56_quality_grade", "mile_quality_grade", "live_modelling_yes", "live_execution_yes"}:
            print(f"{row['metric']}: {row['value']}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {PRIORITY}")


if __name__ == "__main__":
    main()
