from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from edgeiq_results_common_v1 import DATA, ROOT, csv_fieldnames, find_inventory_files, is_speed_candidate_column, numeric_float, read_csv, write_csv


OUT = DATA / "edgeiq_speed_column_inventory_v1.csv"
SUMMARY = DATA / "edgeiq_speed_column_inventory_summary_v1.csv"
CANDIDATES = DATA / "edgeiq_speed_candidate_columns_v1.csv"


def sample_join(values: list[str]) -> str:
    return " | ".join(values[:8])


def scan_file(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    rel = str(path.relative_to(ROOT))
    headers = csv_fieldnames(path)
    candidates = [col for col in headers if is_speed_candidate_column(col)]
    stats = {
        col: {"non_null": 0, "numeric": 0, "total": 0.0, "min": None, "max": None, "samples": []}
        for col in candidates
    }
    rows = 0
    error = ""
    try:
        for row in read_csv(path):
            rows += 1
            for col in candidates:
                value = row.get(col, "")
                if not value:
                    continue
                item = stats[col]
                item["non_null"] += 1
                if len(item["samples"]) < 8 and value not in item["samples"]:
                    item["samples"].append(value)
                num = numeric_float(value)
                if num is not None:
                    item["numeric"] += 1
                    item["total"] += num
                    item["min"] = num if item["min"] is None else min(item["min"], num)
                    item["max"] = num if item["max"] is None else max(item["max"], num)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    candidate_rows = []
    non_null_total = 0
    numeric_total = 0
    for col in candidates:
        item = stats[col]
        non_null_total += int(item["non_null"])
        numeric_total += int(item["numeric"])
        mean = round(float(item["total"]) / int(item["numeric"]), 4) if item["numeric"] else ""
        candidate_rows.append(
            {
                "file_path": rel,
                "rows": rows,
                "columns": len(headers),
                "candidate_column": col,
                "non_null_count": item["non_null"],
                "numeric_count": item["numeric"],
                "min": "" if item["min"] is None else item["min"],
                "max": "" if item["max"] is None else item["max"],
                "mean": mean,
                "sample_values": sample_join(item["samples"]),
            }
        )

    inventory = {
        "file_path": rel,
        "rows": rows,
        "columns": len(headers),
        "candidate_column_count": len(candidates),
        "candidate_columns": ";".join(candidates),
        "speed_like_non_null_values": non_null_total,
        "speed_like_numeric_values": numeric_total,
        "sample_values": sample_join([row["sample_values"] for row in candidate_rows if row["sample_values"]]),
        "error": error,
    }
    return inventory, candidate_rows


def main() -> None:
    inventory_rows = []
    candidate_rows = []
    for path in find_inventory_files():
        if path.suffix.lower() != ".csv":
            continue
        inventory, candidates = scan_file(path)
        inventory_rows.append(inventory)
        candidate_rows.extend(candidates)

    inventory_fields = ["file_path", "rows", "columns", "candidate_column_count", "candidate_columns", "speed_like_non_null_values", "speed_like_numeric_values", "sample_values", "error"]
    candidate_fields = ["file_path", "rows", "columns", "candidate_column", "non_null_count", "numeric_count", "min", "max", "mean", "sample_values"]
    write_csv(OUT, inventory_rows, inventory_fields)
    write_csv(CANDIDATES, candidate_rows, candidate_fields)

    files_with_candidates = sum(1 for row in inventory_rows if int(row["candidate_column_count"]) > 0)
    files_with_values = sum(1 for row in inventory_rows if int(row["speed_like_non_null_values"]) > 0)
    summary = {
        "files_scanned": len(inventory_rows),
        "files_with_candidate_columns": files_with_candidates,
        "files_with_speed_like_values": files_with_values,
        "candidate_column_rows": len(candidate_rows),
        "speed_like_non_null_values": sum(int(row["speed_like_non_null_values"]) for row in inventory_rows),
        "speed_like_numeric_values": sum(int(row["speed_like_numeric_values"]) for row in inventory_rows),
    }
    write_csv(SUMMARY, [summary], list(summary.keys()))
    print(f"Wrote speed column inventory for {len(inventory_rows)} CSV files")


if __name__ == "__main__":
    main()
