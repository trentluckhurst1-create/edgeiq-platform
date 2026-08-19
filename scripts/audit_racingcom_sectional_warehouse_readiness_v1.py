from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

WAREHOUSE = DATA / "racingcom_sectional_warehouse_v2.csv"
OUT = DATA / "racingcom_sectional_warehouse_readiness_v1.csv"
AUDIT_OUT = DATA / "racingcom_sectional_warehouse_readiness_v1_audit.csv"

HORSE_COLUMNS = [
    "horse_key",
    "horse_name",
    "runs_with_sectionals",
    "latest_run_date",
    "earliest_run_date",
]

AUDIT_COLUMNS = [
    "unique_horses",
    "horses_with_1_run",
    "horses_with_2_runs",
    "horses_with_3_runs",
    "horses_with_3_plus_runs",
    "horses_with_5_plus_runs",
    "horses_with_10_plus_runs",
    "avg_runs_per_horse",
    "median_runs_per_horse",
    "max_runs_per_horse",
    "unique_races",
    "layout_a_rows",
    "layout_b_rows",
    "dna_v3_ready_flag",
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


def race_key(row: dict[str, str]) -> str:
    return "|".join(
        [
            clean(row.get("meeting_date")),
            clean(row.get("track")).upper(),
            clean(row.get("race_no")),
        ]
    )


def format_number(value: float | None) -> str:
    if value is None:
        return ""
    rounded = round(value, 2)
    if rounded.is_integer():
        return str(int(rounded))
    return f"{rounded:.2f}".rstrip("0").rstrip(".")


def readiness_flag(unique_horses: int, three_plus: int, five_plus: int, ten_plus: int) -> str:
    if unique_horses >= 1000 and five_plus >= 100 and ten_plus >= 10:
        return "DNA_V3_READY"
    if unique_horses >= 500 and three_plus >= 100:
        return "EARLY_PROFILE_READY"
    return "NOT_READY"


def main() -> None:
    rows = read_csv(WAREHOUSE)
    horse_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        horse_key = clean(row.get("horse_key"))
        if horse_key:
            horse_groups[horse_key].append(row)

    horse_rows: list[dict[str, Any]] = []
    run_counts: list[int] = []
    for horse_key, group in horse_groups.items():
        dates = sorted({clean(row.get("meeting_date")) for row in group if clean(row.get("meeting_date"))})
        names = Counter(clean(row.get("horse_name")) for row in group if clean(row.get("horse_name")))
        run_count = len({race_key(row) for row in group if race_key(row).replace("|", "")})
        run_counts.append(run_count)
        horse_rows.append(
            {
                "horse_key": horse_key,
                "horse_name": names.most_common(1)[0][0] if names else "",
                "runs_with_sectionals": run_count,
                "latest_run_date": dates[-1] if dates else "",
                "earliest_run_date": dates[0] if dates else "",
            }
        )

    horse_rows.sort(key=lambda row: (-int(row["runs_with_sectionals"]), clean(row.get("horse_name"))))

    unique_races = len({race_key(row) for row in rows if race_key(row).replace("|", "")})
    layout_a_rows = sum(1 for row in rows if clean(row.get("layout_type")).upper() == "LAYOUT_A_SUMMARY_SPEED")
    layout_b_rows = sum(1 for row in rows if clean(row.get("layout_type")).upper() == "LAYOUT_B_SPLIT_TIMING")
    horses_with_1 = sum(1 for value in run_counts if value == 1)
    horses_with_2 = sum(1 for value in run_counts if value == 2)
    horses_with_3 = sum(1 for value in run_counts if value == 3)
    horses_with_3_plus = sum(1 for value in run_counts if value >= 3)
    horses_with_5_plus = sum(1 for value in run_counts if value >= 5)
    horses_with_10_plus = sum(1 for value in run_counts if value >= 10)
    flag = readiness_flag(len(horse_groups), horses_with_3_plus, horses_with_5_plus, horses_with_10_plus)

    audit_rows = [
        {
            "unique_horses": len(horse_groups),
            "horses_with_1_run": horses_with_1,
            "horses_with_2_runs": horses_with_2,
            "horses_with_3_runs": horses_with_3,
            "horses_with_3_plus_runs": horses_with_3_plus,
            "horses_with_5_plus_runs": horses_with_5_plus,
            "horses_with_10_plus_runs": horses_with_10_plus,
            "avg_runs_per_horse": format_number(mean(run_counts) if run_counts else None),
            "median_runs_per_horse": format_number(median(run_counts) if run_counts else None),
            "max_runs_per_horse": max(run_counts) if run_counts else 0,
            "unique_races": unique_races,
            "layout_a_rows": layout_a_rows,
            "layout_b_rows": layout_b_rows,
            "dna_v3_ready_flag": flag,
            "final_status": "SECTIONAL_WAREHOUSE_READINESS_AUDITED" if rows else "NO_WAREHOUSE_ROWS_FOUND",
        }
    ]

    write_csv(OUT, horse_rows, HORSE_COLUMNS)
    write_csv(AUDIT_OUT, audit_rows, AUDIT_COLUMNS)

    audit = audit_rows[0]
    print("Racing.com sectional warehouse readiness V1 built")
    print(f"unique_horses={audit['unique_horses']}")
    print(f"unique_races={audit['unique_races']}")
    print(f"horses_with_3_plus_runs={audit['horses_with_3_plus_runs']}")
    print(f"horses_with_5_plus_runs={audit['horses_with_5_plus_runs']}")
    print(f"horses_with_10_plus_runs={audit['horses_with_10_plus_runs']}")
    print(f"dna_v3_ready_flag={audit['dna_v3_ready_flag']}")


if __name__ == "__main__":
    main()
