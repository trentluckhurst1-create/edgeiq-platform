from __future__ import annotations

from pathlib import Path

from edgeiq_results_common_v1 import DATA, ROOT, csv_fieldnames, find_inventory_files, read_csv, write_csv


OUT = DATA / "edgeiq_gear_source_audit_v1.csv"
SUMMARY = DATA / "edgeiq_gear_source_audit_summary_v1.csv"

TERMS = [
    "gear",
    "gear_change",
    "gear_changes",
    "new_gear",
    "removed_gear",
    "equipment",
    "blinkers",
    "visors",
    "winkers",
    "tongue_tie",
    "tongue",
    "cross_over_noseband",
    "noseband",
    "ear_muffs",
    "muffs",
    "pacifiers",
    "lugging_bit",
    "bar_plates",
    "synthetic_hoof_filler",
    "concussion_plates",
    "plates",
]


def candidate_columns(columns: list[str]) -> list[str]:
    out = []
    for col in columns:
        compact = col.lower().replace(" ", "_").replace("-", "_")
        if any(term in compact for term in TERMS):
            out.append(col)
    return out


def main() -> None:
    rows = []
    for path in find_inventory_files():
        if path.suffix.lower() != ".csv":
            continue
        columns = csv_fieldnames(path)
        candidates = candidate_columns(columns)
        if not candidates:
            continue
        rel = str(path.relative_to(ROOT))
        row_count = 0
        non_null = 0
        samples = []
        error = ""
        try:
            for row in read_csv(path):
                row_count += 1
                for col in candidates:
                    value = row.get(col, "")
                    if value:
                        non_null += 1
                        if len(samples) < 8 and value not in samples:
                            samples.append(value)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        rows.append(
            {
                "file_path": rel,
                "rows": row_count,
                "candidate_columns": ";".join(candidates),
                "candidate_column_count": len(candidates),
                "gear_non_null_values": non_null,
                "sample_values": " | ".join(samples),
                "error": error,
            }
        )
    rows.sort(key=lambda row: int(row["gear_non_null_values"]), reverse=True)
    fields = ["file_path", "rows", "candidate_columns", "candidate_column_count", "gear_non_null_values", "sample_values", "error"]
    write_csv(OUT, rows, fields)
    summary = {
        "files_with_gear_candidate_columns": len(rows),
        "files_with_gear_values": sum(1 for row in rows if int(row["gear_non_null_values"]) > 0),
        "gear_non_null_values": sum(int(row["gear_non_null_values"]) for row in rows),
        "best_source": rows[0]["file_path"] if rows else "",
        "best_source_values": rows[0]["gear_non_null_values"] if rows else 0,
    }
    write_csv(SUMMARY, [summary], list(summary.keys()))
    print(f"Wrote {OUT} ({len(rows)} sources)")


if __name__ == "__main__":
    main()
