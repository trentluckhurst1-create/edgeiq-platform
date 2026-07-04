from __future__ import annotations

import csv
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

WAREHOUSE = DATA / "racingcom_sectional_warehouse_v2.csv"
LAYOUT_B_DERIVED = DATA / "racingcom_layout_b_derived_metrics_v1.csv"

OUT = DATA / "edgeiq_sectional_profiles_v2.csv"
AUDIT_OUT = DATA / "edgeiq_sectional_profiles_v2_audit.csv"

PROFILE_COLUMNS = [
    "horse_key",
    "horse_name",
    "runs_with_sectionals",
    "layout_a_runs",
    "layout_b_runs",
    "avg_early_speed",
    "avg_mid_speed",
    "avg_late_speed",
    "avg_peak_speed",
    "avg_speed",
    "avg_early_split_time",
    "avg_mid_split_time",
    "avg_late_split_time",
    "avg_closing_rank",
    "avg_early_rank",
    "avg_late_vs_early_delta",
    "avg_split_consistency_score",
    "profile_depth_status",
    "sectional_archetype",
    "sectional_evidence_type",
]

AUDIT_COLUMNS = [
    "sectional_rows_loaded",
    "layout_b_derived_rows_loaded",
    "unique_horses_loaded",
    "profiles_output",
    "sample_too_small",
    "early_profiles",
    "strong_early_profiles",
    "dna_ready_profiles",
    "summary_speed_only_profiles",
    "split_timing_only_profiles",
    "mixed_profiles",
    "final_status",
]

SPEED_COLUMNS = ("early_speed", "mid_speed", "late_speed", "peak_speed", "avg_speed")
SPLIT_COLUMNS = (
    "early_split_time",
    "mid_split_time",
    "late_split_time",
    "closing_rank_within_race",
    "early_rank_within_race",
    "late_vs_early_delta",
    "split_consistency_score",
)


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-"} else re.sub(r"\s+", " ", text)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as handle:
            return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    tmp.replace(path)


def parse_float(value: Any) -> float | None:
    text = clean(value).replace(",", "")
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        parsed = float(match.group(0))
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def format_number(value: float | None) -> str:
    if value is None:
        return ""
    rounded = round(value, 2)
    if rounded.is_integer():
        return str(int(rounded))
    return f"{rounded:.2f}".rstrip("0").rstrip(".")


def avg(values: list[float]) -> float | None:
    return mean(values) if values else None


def race_key(row: dict[str, Any]) -> str:
    return "|".join([clean(row.get("meeting_date")), clean(row.get("track")).upper(), clean(row.get("race_no"))])


def depth_status(runs: int) -> str:
    if runs >= 10:
        return "DNA_READY"
    if runs >= 5:
        return "STRONG_EARLY_PROFILE"
    if runs >= 2:
        return "EARLY_PROFILE"
    return "SAMPLE_TOO_SMALL"


def evidence_type(layout_a_runs: int, layout_b_runs: int, has_summary: bool, has_split: bool) -> str:
    if has_summary and has_split:
        return "MIXED_SUMMARY_AND_SPLIT"
    if has_summary or layout_a_runs:
        return "SUMMARY_SPEED_ONLY"
    if has_split or layout_b_runs:
        return "SPLIT_TIMING_ONLY"
    return "INSUFFICIENT"


def classify_archetype(
    runs: int,
    summary: dict[str, float | None],
    split: dict[str, float | None],
    evidence: str,
) -> str:
    if runs < 2:
        return "INSUFFICIENT_SAMPLE"

    early = summary.get("early_speed")
    mid = summary.get("mid_speed")
    late = summary.get("late_speed")
    peak = summary.get("peak_speed")
    avg_speed_value = summary.get("avg_speed")

    if all(value is not None for value in (early, mid, late, peak, avg_speed_value)):
        assert early is not None
        assert mid is not None
        assert late is not None
        assert peak is not None
        assert avg_speed_value is not None
        late_delta = late - early
        peak_delta = peak - avg_speed_value
        if early >= mid + 0.8 and early >= late + 0.8:
            return "FAST_STARTER"
        if late_delta >= 1.0 and late >= mid:
            return "STRONG_CLOSER"
        if peak_delta >= 4.0:
            return "PEAK_SPEED_HORSE"
        if abs(late_delta) <= 0.7:
            return "SUSTAINED_CRUISER"
        return "ONE_PACE_GRINDER"

    early_split = split.get("early_split_time")
    late_split = split.get("late_split_time")
    closing_rank = split.get("closing_rank")
    early_rank = split.get("early_rank")
    consistency = split.get("split_consistency_score")
    late_delta = split.get("late_vs_early_delta")

    if evidence in {"SPLIT_TIMING_ONLY", "MIXED_SUMMARY_AND_SPLIT"} and all(value is not None for value in (early_split, late_split)):
        assert early_split is not None
        assert late_split is not None
        if closing_rank is not None and closing_rank <= 3 and late_split < early_split:
            return "SPLIT_TIMING_CLOSER"
        if early_rank is not None and early_rank <= 3 and early_split <= late_split:
            return "SPLIT_TIMING_SPEED"
        if consistency is not None and consistency >= 90:
            return "CONSISTENT_SECTIONALIST"
        if late_delta is not None and late_delta < -0.25:
            return "SPLIT_TIMING_CLOSER"
        return "ONE_PACE_GRINDER"

    return "INSUFFICIENT_SAMPLE"


def build_profiles() -> tuple[list[dict[str, Any]], int, int]:
    warehouse_rows = read_csv(WAREHOUSE)
    layout_b_rows = read_csv(LAYOUT_B_DERIVED)
    names: dict[str, Counter[str]] = defaultdict(Counter)
    races: dict[str, set[str]] = defaultdict(set)
    layout_a_races: dict[str, set[str]] = defaultdict(set)
    layout_b_races: dict[str, set[str]] = defaultdict(set)
    summary_values: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    split_values: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    for row in warehouse_rows:
        horse_key = clean(row.get("horse_key"))
        if not horse_key:
            continue
        names[horse_key][clean(row.get("horse_name"))] += 1
        races[horse_key].add(race_key(row))
        layout = clean(row.get("layout_type")).upper()
        if layout == "LAYOUT_A_SUMMARY_SPEED":
            layout_a_races[horse_key].add(race_key(row))
        elif layout == "LAYOUT_B_SPLIT_TIMING":
            layout_b_races[horse_key].add(race_key(row))
        for column in SPEED_COLUMNS:
            value = parse_float(row.get(column))
            if value is not None:
                summary_values[horse_key][column].append(value)

    for row in layout_b_rows:
        horse_key = clean(row.get("horse_key"))
        if not horse_key:
            continue
        names[horse_key][clean(row.get("horse_name"))] += 1
        races[horse_key].add(race_key(row))
        layout_b_races[horse_key].add(race_key(row))
        mapping = {
            "early_split_time": "early_split_time",
            "mid_split_time": "mid_split_time",
            "late_split_time": "late_split_time",
            "closing_rank": "closing_rank_within_race",
            "early_rank": "early_rank_within_race",
            "late_vs_early_delta": "late_vs_early_delta",
            "split_consistency_score": "split_consistency_score",
        }
        for output_name, input_name in mapping.items():
            value = parse_float(row.get(input_name))
            if value is not None:
                split_values[horse_key][output_name].append(value)

    profiles: list[dict[str, Any]] = []
    for horse_key in sorted(races):
        run_count = len({key for key in races[horse_key] if clean(key).replace("|", "")})
        layout_a_count = len(layout_a_races[horse_key])
        layout_b_count = len(layout_b_races[horse_key])
        summary_avg = {column: avg(summary_values[horse_key][column]) for column in SPEED_COLUMNS}
        split_avg = {column: avg(split_values[horse_key][column]) for column in ("early_split_time", "mid_split_time", "late_split_time", "closing_rank", "early_rank", "late_vs_early_delta", "split_consistency_score")}
        has_summary = any(value is not None for value in summary_avg.values())
        has_split = any(value is not None for value in split_avg.values())
        evidence = evidence_type(layout_a_count, layout_b_count, has_summary, has_split)
        status = depth_status(run_count)
        archetype = classify_archetype(run_count, summary_avg, split_avg, evidence)
        horse_name = names[horse_key].most_common(1)[0][0] if names[horse_key] else ""

        profiles.append(
            {
                "horse_key": horse_key,
                "horse_name": horse_name,
                "runs_with_sectionals": run_count,
                "layout_a_runs": layout_a_count,
                "layout_b_runs": layout_b_count,
                "avg_early_speed": format_number(summary_avg["early_speed"]),
                "avg_mid_speed": format_number(summary_avg["mid_speed"]),
                "avg_late_speed": format_number(summary_avg["late_speed"]),
                "avg_peak_speed": format_number(summary_avg["peak_speed"]),
                "avg_speed": format_number(summary_avg["avg_speed"]),
                "avg_early_split_time": format_number(split_avg["early_split_time"]),
                "avg_mid_split_time": format_number(split_avg["mid_split_time"]),
                "avg_late_split_time": format_number(split_avg["late_split_time"]),
                "avg_closing_rank": format_number(split_avg["closing_rank"]),
                "avg_early_rank": format_number(split_avg["early_rank"]),
                "avg_late_vs_early_delta": format_number(split_avg["late_vs_early_delta"]),
                "avg_split_consistency_score": format_number(split_avg["split_consistency_score"]),
                "profile_depth_status": status,
                "sectional_archetype": archetype,
                "sectional_evidence_type": evidence,
            }
        )

    profiles.sort(key=lambda row: (-int(row["runs_with_sectionals"]), clean(row.get("horse_name"))))
    return profiles, len(warehouse_rows), len(layout_b_rows)


def main() -> None:
    profiles, warehouse_count, layout_b_count = build_profiles()
    depth_counts = Counter(clean(row.get("profile_depth_status")) for row in profiles)
    evidence_counts = Counter(clean(row.get("sectional_evidence_type")) for row in profiles)
    final_status = "SECTIONAL_PROFILES_V2_BUILT" if profiles else "NO_PROFILES_OUTPUT"
    audit = [
        {
            "sectional_rows_loaded": warehouse_count,
            "layout_b_derived_rows_loaded": layout_b_count,
            "unique_horses_loaded": len(profiles),
            "profiles_output": len(profiles),
            "sample_too_small": depth_counts.get("SAMPLE_TOO_SMALL", 0),
            "early_profiles": depth_counts.get("EARLY_PROFILE", 0),
            "strong_early_profiles": depth_counts.get("STRONG_EARLY_PROFILE", 0),
            "dna_ready_profiles": depth_counts.get("DNA_READY", 0),
            "summary_speed_only_profiles": evidence_counts.get("SUMMARY_SPEED_ONLY", 0),
            "split_timing_only_profiles": evidence_counts.get("SPLIT_TIMING_ONLY", 0),
            "mixed_profiles": evidence_counts.get("MIXED_SUMMARY_AND_SPLIT", 0),
            "final_status": final_status,
        }
    ]
    write_csv(OUT, profiles, PROFILE_COLUMNS)
    write_csv(AUDIT_OUT, audit, AUDIT_COLUMNS)

    row = audit[0]
    print("EDGEiQ sectional profiles V2 built")
    print(f"sectional_rows_loaded={row['sectional_rows_loaded']}")
    print(f"layout_b_derived_rows_loaded={row['layout_b_derived_rows_loaded']}")
    print(f"unique_horses_loaded={row['unique_horses_loaded']}")
    print(f"profiles_output={row['profiles_output']}")
    print(f"sample_too_small={row['sample_too_small']}")
    print(f"early_profiles={row['early_profiles']}")
    print(f"strong_early_profiles={row['strong_early_profiles']}")
    print(f"dna_ready_profiles={row['dna_ready_profiles']}")
    print(f"final_status={row['final_status']}")


if __name__ == "__main__":
    main()
