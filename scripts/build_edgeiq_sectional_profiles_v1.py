from __future__ import annotations

import csv
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

WAREHOUSE = DATA / "racingcom_sectional_warehouse_v2.csv"
READINESS = DATA / "racingcom_sectional_warehouse_readiness_v1.csv"

OUT = DATA / "edgeiq_sectional_profiles_v1.csv"
AUDIT_OUT = DATA / "edgeiq_sectional_profiles_v1_audit.csv"

SPEED_COLUMNS = ("early_speed", "mid_speed", "late_speed", "peak_speed", "avg_speed")

PROFILE_COLUMNS = [
    "horse_key",
    "horse_name",
    "runs_with_sectionals",
    "avg_early_speed",
    "avg_mid_speed",
    "avg_late_speed",
    "avg_peak_speed",
    "avg_speed",
    "best_early_speed",
    "best_mid_speed",
    "best_late_speed",
    "best_peak_speed",
    "late_minus_early",
    "peak_minus_avg",
    "speed_consistency_score",
    "profile_depth_status",
    "sectional_archetype",
]

AUDIT_COLUMNS = [
    "sectional_rows_loaded",
    "unique_horses_loaded",
    "profiles_output",
    "sample_too_small",
    "early_profiles",
    "strong_early_profiles",
    "dna_ready_profiles",
    "final_status",
]


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


def depth_status(runs: int) -> str:
    if runs >= 10:
        return "DNA_READY"
    if runs >= 5:
        return "STRONG_EARLY_PROFILE"
    if runs >= 3:
        return "EARLY_PROFILE"
    if runs >= 2:
        return "EARLY_PROFILE"
    return "SAMPLE_TOO_SMALL"


def consistency_score(avg_speeds: list[float]) -> float | None:
    if len(avg_speeds) < 2:
        return None
    spread = pstdev(avg_speeds)
    return max(0.0, min(100.0, 100.0 - (spread * 8.0)))


def classify_archetype(
    runs: int,
    early: float | None,
    mid: float | None,
    late: float | None,
    peak: float | None,
    average_speed: float | None,
    late_minus_early: float | None,
    peak_minus_avg: float | None,
    consistency: float | None,
) -> str:
    if runs < 2:
        return "INSUFFICIENT_SAMPLE"
    if any(value is None for value in (early, mid, late, peak, average_speed)):
        return "INSUFFICIENT_SAMPLE"
    assert early is not None
    assert mid is not None
    assert late is not None
    assert peak is not None
    assert average_speed is not None

    late_delta = late_minus_early if late_minus_early is not None else late - early
    peak_delta = peak_minus_avg if peak_minus_avg is not None else peak - average_speed
    consistency_value = consistency if consistency is not None else 0

    if early >= mid + 0.8 and early >= late + 0.8:
        return "FAST_STARTER"
    if late_delta >= 1.0 and late >= mid:
        return "STRONG_CLOSER"
    if peak_delta >= 4.0:
        return "PEAK_SPEED_HORSE"
    if consistency_value >= 88 and abs(late_delta) <= 0.7:
        return "SUSTAINED_CRUISER"
    return "ONE_PACE_GRINDER"


def readiness_lookup() -> dict[str, dict[str, str]]:
    return {clean(row.get("horse_key")): row for row in read_csv(READINESS) if clean(row.get("horse_key"))}


def main() -> None:
    warehouse_rows = read_csv(WAREHOUSE)
    readiness = readiness_lookup()
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in warehouse_rows:
        horse_key = clean(row.get("horse_key"))
        if horse_key:
            grouped[horse_key].append(row)

    profiles: list[dict[str, Any]] = []
    for horse_key, rows in grouped.items():
        ready_row = readiness.get(horse_key, {})
        run_count = int(clean(ready_row.get("runs_with_sectionals")) or "0") if ready_row else 0
        if not run_count:
            run_count = len({f"{clean(row.get('meeting_date'))}|{clean(row.get('track'))}|{clean(row.get('race_no'))}" for row in rows})

        names = Counter(clean(row.get("horse_name")) for row in rows if clean(row.get("horse_name")))
        horse_name = clean(ready_row.get("horse_name")) or (names.most_common(1)[0][0] if names else "")
        metrics: dict[str, list[float]] = {
            column: [value for value in (parse_float(row.get(column)) for row in rows) if value is not None]
            for column in SPEED_COLUMNS
        }

        avg_early = avg(metrics["early_speed"])
        avg_mid = avg(metrics["mid_speed"])
        avg_late = avg(metrics["late_speed"])
        avg_peak = avg(metrics["peak_speed"])
        avg_speed = avg(metrics["avg_speed"])
        late_delta = (avg_late - avg_early) if avg_late is not None and avg_early is not None else None
        peak_delta = (avg_peak - avg_speed) if avg_peak is not None and avg_speed is not None else None
        consistency = consistency_score(metrics["avg_speed"])
        status = depth_status(run_count)
        archetype = classify_archetype(
            run_count,
            avg_early,
            avg_mid,
            avg_late,
            avg_peak,
            avg_speed,
            late_delta,
            peak_delta,
            consistency,
        )

        profiles.append(
            {
                "horse_key": horse_key,
                "horse_name": horse_name,
                "runs_with_sectionals": run_count,
                "avg_early_speed": format_number(avg_early),
                "avg_mid_speed": format_number(avg_mid),
                "avg_late_speed": format_number(avg_late),
                "avg_peak_speed": format_number(avg_peak),
                "avg_speed": format_number(avg_speed),
                "best_early_speed": format_number(max(metrics["early_speed"]) if metrics["early_speed"] else None),
                "best_mid_speed": format_number(max(metrics["mid_speed"]) if metrics["mid_speed"] else None),
                "best_late_speed": format_number(max(metrics["late_speed"]) if metrics["late_speed"] else None),
                "best_peak_speed": format_number(max(metrics["peak_speed"]) if metrics["peak_speed"] else None),
                "late_minus_early": format_number(late_delta),
                "peak_minus_avg": format_number(peak_delta),
                "speed_consistency_score": format_number(consistency),
                "profile_depth_status": status,
                "sectional_archetype": archetype,
            }
        )

    profiles.sort(key=lambda row: (-int(row["runs_with_sectionals"]), clean(row.get("horse_name"))))
    status_counts = Counter(clean(row.get("profile_depth_status")) for row in profiles)
    final_status = "SECTIONAL_PROFILES_BUILT" if profiles else ("NO_SECTIONAL_WAREHOUSE_FOUND" if not warehouse_rows else "NO_PROFILES_OUTPUT")
    audit = [
        {
            "sectional_rows_loaded": len(warehouse_rows),
            "unique_horses_loaded": len(grouped),
            "profiles_output": len(profiles),
            "sample_too_small": status_counts.get("SAMPLE_TOO_SMALL", 0),
            "early_profiles": status_counts.get("EARLY_PROFILE", 0),
            "strong_early_profiles": status_counts.get("STRONG_EARLY_PROFILE", 0),
            "dna_ready_profiles": status_counts.get("DNA_READY", 0),
            "final_status": final_status,
        }
    ]

    write_csv(OUT, profiles, PROFILE_COLUMNS)
    write_csv(AUDIT_OUT, audit, AUDIT_COLUMNS)

    row = audit[0]
    print("EDGEiQ sectional profiles V1 built")
    print(f"sectional_rows_loaded={row['sectional_rows_loaded']}")
    print(f"unique_horses_loaded={row['unique_horses_loaded']}")
    print(f"profiles_output={row['profiles_output']}")
    print(f"sample_too_small={row['sample_too_small']}")
    print(f"early_profiles={row['early_profiles']}")
    print(f"strong_early_profiles={row['strong_early_profiles']}")
    print(f"dna_ready_profiles={row['dna_ready_profiles']}")
    print(f"final_status={row['final_status']}")


if __name__ == "__main__":
    main()
