import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


MIN_YEAR = 2021
MAX_YEAR = 2024
FORBIDDEN_TERMS = ("sp", "bsp", "starting_price", "odds", "price", "market", "bet", "stake", "return")

LAB026_COLUMNS = ["canonical_race_id", "canonical_horse_id", "race_date", "finish_position"]
LAB031_COLUMNS = [
    "canonical_performance_id",
    "canonical_race_id",
    "canonical_horse_id",
    "race_date",
    "current_weight_kg",
    "weight_change_kg",
    "distance_change_metres",
    "abs_distance_change_metres",
    "prior_same_class_starts",
    "prior_exact_distance_starts_031",
]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--perf026-source", required=True)
    p.add_argument("--lab031-source", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--min-year", type=int, default=MIN_YEAR)
    p.add_argument("--max-year", type=int, default=MAX_YEAR)
    return p.parse_args()


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def forbidden_columns(columns):
    bad = []
    for col in columns:
        lc = col.lower()
        tokens = lc.replace("-", "_").split("_")
        if "sp" in tokens or "bsp" in tokens:
            bad.append(col)
        elif any(term in lc for term in FORBIDDEN_TERMS if term not in {"sp", "bsp"}):
            bad.append(col)
    return bad


def write_partition(source, output, columns, min_year, max_year):
    source = Path(source)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    header = list(pd.read_csv(source, nrows=0).columns)
    missing = [c for c in columns if c not in header]
    if missing:
        raise RuntimeError(f"STOP_SOURCE_COLUMNS_MISSING_{source.name}: {missing}")

    bad = forbidden_columns(columns)
    if bad:
        raise RuntimeError(f"STOP_FORBIDDEN_EXPORT_COLUMNS_{source.name}: {bad}")

    rows = 0
    year_counts = {}
    unique_races = set()
    unique_horses = set()
    min_date = None
    max_date = None
    wrote_header = False

    if output.exists():
        output.unlink()

    for chunk in pd.read_csv(source, usecols=columns, chunksize=250000):
        chunk["race_date"] = pd.to_datetime(chunk["race_date"], errors="coerce")
        chunk = chunk[chunk["race_date"].notna()].copy()
        years = chunk["race_date"].dt.year
        chunk = chunk[years.between(min_year, max_year)].copy()
        if chunk.empty:
            continue

        years = chunk["race_date"].dt.year
        for year, count in years.value_counts().sort_index().items():
            year_counts[str(int(year))] = year_counts.get(str(int(year)), 0) + int(count)
        if "canonical_race_id" in chunk.columns:
            unique_races.update(chunk["canonical_race_id"].dropna().astype(str).unique().tolist())
        if "canonical_horse_id" in chunk.columns:
            unique_horses.update(chunk["canonical_horse_id"].dropna().astype(str).unique().tolist())

        cmin = chunk["race_date"].min()
        cmax = chunk["race_date"].max()
        min_date = cmin if min_date is None or cmin < min_date else min_date
        max_date = cmax if max_date is None or cmax > max_date else max_date
        rows += len(chunk)
        chunk["race_date"] = chunk["race_date"].dt.strftime("%Y-%m-%d")
        chunk.to_csv(output, index=False, mode="a", header=not wrote_header)
        wrote_header = True

    if rows == 0:
        raise RuntimeError(f"STOP_EMPTY_PARTITION_{source.name}")
    if set(year_counts) - {str(y) for y in range(min_year, max_year + 1)}:
        raise RuntimeError(f"STOP_OUT_OF_SCOPE_YEAR_COUNTS_{source.name}: {year_counts}")
    if min_date.year < min_year or max_date.year > max_year:
        raise RuntimeError(f"STOP_OUT_OF_SCOPE_DATE_BOUNDS_{source.name}: {min_date} {max_date}")

    output_columns = list(pd.read_csv(output, nrows=0).columns)
    manifest = {
        "status": "PASS",
        "purpose": "CODEX_ISSUE5_SEALED_YEAR_FREE_SOURCE_PARTITION",
        "source_path": str(source),
        "source_sha256": sha256_file(source),
        "output_path": str(output),
        "output_sha256": sha256_file(output),
        "output_bytes": output.stat().st_size,
        "output_rows": rows,
        "output_unique_race_count": len(unique_races) if "canonical_race_id" in output_columns else None,
        "output_unique_horse_count": len(unique_horses) if "canonical_horse_id" in output_columns else None,
        "min_race_date": min_date.strftime("%Y-%m-%d"),
        "max_race_date": max_date.strftime("%Y-%m-%d"),
        "year_counts": {str(y): int(year_counts.get(str(y), 0)) for y in range(min_year, max_year + 1)},
        "assert_no_rows_after_2024_12_31": max_date.strftime("%Y-%m-%d") <= "2024-12-31",
        "columns": output_columns,
        "required_columns": columns,
        "forbidden_column_scan": {
            "forbidden_terms": list(FORBIDDEN_TERMS),
            "flagged_columns": forbidden_columns(output_columns),
            "status": "PASS" if not forbidden_columns(output_columns) else "FAIL",
        },
        "lineage": "Partitioned by authorised upstream source repair for Issue #5; model fitting/scoring not performed by this export.",
    }
    if manifest["forbidden_column_scan"]["status"] != "PASS":
        raise RuntimeError(f"STOP_FORBIDDEN_COLUMNS_IN_OUTPUT_{source.name}")
    return manifest


def main():
    args = parse_args()
    if args.min_year != MIN_YEAR or args.max_year != MAX_YEAR:
        raise RuntimeError("STOP_UNAPPROVED_YEAR_WINDOW")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    lab026_out = out / "CODEX_ISSUE5_LAB026_CLEAN_PLACING_2021_2024.csv"
    lab031_out = out / "CODEX_ISSUE5_LAB031_CONTEXT_2021_2024.csv"

    lab026_manifest = write_partition(args.perf026_source, lab026_out, LAB026_COLUMNS, args.min_year, args.max_year)
    lab031_manifest = write_partition(args.lab031_source, lab031_out, LAB031_COLUMNS, args.min_year, args.max_year)

    lab026_manifest_path = out / "CODEX_ISSUE5_LAB026_CLEAN_PLACING_2021_2024.manifest.json"
    lab031_manifest_path = out / "CODEX_ISSUE5_LAB031_CONTEXT_2021_2024.manifest.json"
    lab026_manifest_path.write_text(json.dumps(lab026_manifest, indent=2), encoding="utf-8")
    lab031_manifest_path.write_text(json.dumps(lab031_manifest, indent=2), encoding="utf-8")

    audit = {
        "status": "PASS",
        "model_fitting": "NO",
        "model_scoring": "NO",
        "market_access": "NO",
        "source_repair_scope": "ONE_TIME_UPSTREAM_PARTITION_EXPORT",
        "partitions": {
            "lab026_clean_placing": str(lab026_manifest_path),
            "lab031_context": str(lab031_manifest_path),
        },
    }
    audit_path = out / "CODEX_ISSUE5_SOURCE_PARTITION_AUDIT_20261010.json"
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print("CODEX_ISSUE5_SOURCE_PARTITION_EXPORT=PASS")
    print(f"LAB026_MANIFEST={lab026_manifest_path}")
    print(f"LAB031_MANIFEST={lab031_manifest_path}")


if __name__ == "__main__":
    main()
