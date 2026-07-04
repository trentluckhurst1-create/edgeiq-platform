from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SPLITS = DATA / "racingcom_rendered_speed_data_splits_v1.csv"
WAREHOUSE = DATA / "racingcom_sectional_warehouse_v2.csv"

OUT = DATA / "racingcom_layout_b_derived_metrics_v1.csv"
AUDIT_OUT = DATA / "racingcom_layout_b_derived_metrics_v1_audit.csv"

OUTPUT_COLUMNS = [
    "meeting_date",
    "track",
    "race_no",
    "source_url",
    "horse_name",
    "horse_key",
    "position",
    "split_count",
    "early_split_time",
    "mid_split_time",
    "late_split_time",
    "fastest_split_time",
    "slowest_split_time",
    "late_vs_early_delta",
    "early_rank_within_race",
    "closing_rank_within_race",
    "split_consistency_score",
    "derived_status",
]

AUDIT_COLUMNS = [
    "split_rows_loaded",
    "layout_b_horse_race_rows",
    "derived_rows_output",
    "rows_with_early_mid_late",
    "rows_with_closing_rank",
    "rows_with_consistency_score",
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


def parse_time_seconds(value: Any) -> float | None:
    text = clean(value)
    if not text:
        return None
    match = re.search(r"(?:(\d+):)?(\d+(?:\.\d+)?)", text)
    if not match:
        return None
    minutes = int(match.group(1) or 0)
    seconds = float(match.group(2))
    total = minutes * 60 + seconds
    return total if math.isfinite(total) else None


def split_order(metric_name: str) -> tuple[int, int, str] | None:
    name = clean(metric_name).upper()
    match = re.fullmatch(r"(\d+)M-(\d+)M", name)
    if match:
        start, end = int(match.group(1)), int(match.group(2))
        return start, end, name
    match = re.fullmatch(r"(\d+)M-FINISH", name)
    if match:
        return int(match.group(1)), 0, name
    return None


def format_number(value: float | None) -> str:
    if value is None:
        return ""
    rounded = round(value, 2)
    if rounded.is_integer():
        return str(int(rounded))
    return f"{rounded:.2f}".rstrip("0").rstrip(".")


def race_key(row: dict[str, Any]) -> str:
    return "|".join([clean(row.get("meeting_date")), clean(row.get("track")).upper(), clean(row.get("race_no"))])


def horse_race_key(row: dict[str, Any]) -> str:
    return "|".join([race_key(row), clean(row.get("horse_key"))])


def rank_by_lowest(rows: list[dict[str, Any]], value_column: str, output_column: str) -> None:
    race_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        value = row.get(value_column)
        if isinstance(value, (int, float)):
            race_groups[race_key(row)].append(row)
    for group in race_groups.values():
        ordered = sorted(group, key=lambda row: float(row[value_column]))
        previous_value: float | None = None
        previous_rank = 0
        for index, row in enumerate(ordered, start=1):
            value = float(row[value_column])
            rank = previous_rank if previous_value is not None and value == previous_value else index
            row[output_column] = rank
            previous_value = value
            previous_rank = rank


def consistency_score(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    spread = pstdev(values)
    return max(0.0, min(100.0, 100.0 - (spread * 25.0)))


def derive_rows(split_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in split_rows:
        if clean(row.get("metric_type")) not in {"SECTIONAL_SPLIT_TIME", "OVERALL_TIME"}:
            continue
        key = horse_race_key(row)
        if not key.replace("|", ""):
            continue
        item = grouped.setdefault(
            key,
            {
                "meeting_date": clean(row.get("meeting_date")),
                "track": clean(row.get("track")),
                "race_no": clean(row.get("race_no")),
                "source_url": clean(row.get("source_url")),
                "horse_name": clean(row.get("horse_name")),
                "horse_key": clean(row.get("horse_key")),
                "position": clean(row.get("position")),
                "splits": [],
                "overall_time": None,
            },
        )
        if clean(row.get("metric_type")) == "OVERALL_TIME":
            item["overall_time"] = parse_time_seconds(row.get("metric_value"))
            continue
        parsed_order = split_order(row.get("metric_name"))
        parsed_time = parse_time_seconds(row.get("metric_value"))
        if parsed_order is None or parsed_time is None:
            continue
        item["splits"].append(
            {
                "metric_name": clean(row.get("metric_name")),
                "metric_value": clean(row.get("metric_value")),
                "time": parsed_time,
                "order": parsed_order[0],
            }
        )

    output: list[dict[str, Any]] = []
    for item in grouped.values():
        splits = sorted(item["splits"], key=lambda split: split["order"], reverse=True)
        if not splits:
            continue
        split_times = [float(split["time"]) for split in splits]
        split_count = len(split_times)
        early = split_times[0]
        late = split_times[-1]
        if split_count >= 3:
            middle_values = split_times[1:-1]
            mid = mean(middle_values) if middle_values else None
        else:
            mid = None
        consistency = consistency_score(split_times)
        output.append(
            {
                "meeting_date": item["meeting_date"],
                "track": item["track"],
                "race_no": item["race_no"],
                "source_url": item["source_url"],
                "horse_name": item["horse_name"],
                "horse_key": item["horse_key"],
                "position": item["position"],
                "split_count": split_count,
                "early_split_time": early,
                "mid_split_time": mid,
                "late_split_time": late,
                "fastest_split_time": min(split_times),
                "slowest_split_time": max(split_times),
                "late_vs_early_delta": late - early,
                "early_rank_within_race": "",
                "closing_rank_within_race": "",
                "split_consistency_score": consistency,
                "derived_status": "DERIVED_SPLIT_METRICS" if split_count >= 3 else "DERIVED_LIMITED_SPLITS",
            }
        )

    rank_by_lowest(output, "early_split_time", "early_rank_within_race")
    rank_by_lowest(output, "late_split_time", "closing_rank_within_race")
    output.sort(key=lambda row: (clean(row.get("meeting_date")), clean(row.get("track")), int(clean(row.get("race_no")) or 0), int(re.search(r"\d+", clean(row.get("position")) or "999").group(0))))
    return output


def serialise(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    serialised: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        for column in (
            "early_split_time",
            "mid_split_time",
            "late_split_time",
            "fastest_split_time",
            "slowest_split_time",
            "late_vs_early_delta",
            "split_consistency_score",
        ):
            item[column] = format_number(item.get(column))
        serialised.append(item)
    return serialised


def main() -> None:
    split_rows = read_csv(SPLITS)
    _warehouse_rows = read_csv(WAREHOUSE)
    derived = derive_rows(split_rows)
    serialised = serialise(derived)
    rows_with_early_mid_late = sum(1 for row in serialised if clean(row.get("early_split_time")) and clean(row.get("mid_split_time")) and clean(row.get("late_split_time")))
    rows_with_closing_rank = sum(1 for row in serialised if clean(row.get("closing_rank_within_race")))
    rows_with_consistency = sum(1 for row in serialised if clean(row.get("split_consistency_score")))
    final_status = "LAYOUT_B_DERIVED_METRICS_BUILT" if serialised else ("NO_SPLITS_FOUND" if not split_rows else "NO_DERIVED_ROWS_OUTPUT")

    audit = [
        {
            "split_rows_loaded": len(split_rows),
            "layout_b_horse_race_rows": len(derived),
            "derived_rows_output": len(serialised),
            "rows_with_early_mid_late": rows_with_early_mid_late,
            "rows_with_closing_rank": rows_with_closing_rank,
            "rows_with_consistency_score": rows_with_consistency,
            "final_status": final_status,
        }
    ]

    write_csv(OUT, serialised, OUTPUT_COLUMNS)
    write_csv(AUDIT_OUT, audit, AUDIT_COLUMNS)

    row = audit[0]
    print("Racing.com Layout B derived metrics V1 built")
    print(f"split_rows_loaded={row['split_rows_loaded']}")
    print(f"layout_b_horse_race_rows={row['layout_b_horse_race_rows']}")
    print(f"derived_rows_output={row['derived_rows_output']}")
    print(f"rows_with_early_mid_late={row['rows_with_early_mid_late']}")
    print(f"rows_with_closing_rank={row['rows_with_closing_rank']}")
    print(f"rows_with_consistency_score={row['rows_with_consistency_score']}")
    print(f"final_status={row['final_status']}")


if __name__ == "__main__":
    main()
