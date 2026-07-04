from __future__ import annotations

from collections import Counter, defaultdict

from edgeiq_results_common_v1 import DATA, SP_KEYS, canonical_from_row, first, has_value, key_for, now_iso, read_csv, source_paths, write_csv


def main() -> None:
    master_rows = list(read_csv(DATA / "edgeiq_results_master_v1.csv"))
    upstream_sp_keys: dict[str, str] = {}
    built_at = now_iso()
    for path, priority in source_paths():
        for row in read_csv(path):
            canonical = canonical_from_row(row, path.name, priority, built_at)
            if canonical is None:
                continue
            sp = first(row, SP_KEYS)
            if not has_value(sp):
                continue
            key = key_for(canonical["race_date"], canonical["track"], canonical["race_no"], canonical["runner"])
            upstream_sp_keys[key] = sp

    total = len(master_rows)
    with_runner = sum(1 for row in master_rows if has_value(row["runner"]))
    with_sp = sum(1 for row in master_rows if has_value(row["sp"]) or has_value(row["starting_price"]))
    missing = total - with_sp
    by_month = Counter()
    by_source = Counter()
    duplicate_keys = Counter()
    examples = []
    for row in master_rows:
        key = key_for(row["race_date"], row["track"], row["race_no"], row["runner"])
        duplicate_keys[key] += 1
        if has_value(row["sp"]) or has_value(row["starting_price"]):
            continue
        by_month[(row["year"], row["month"], row["track"])] += 1
        by_source[row["source_file"]] += 1
        if key in upstream_sp_keys and len(examples) < 200:
            examples.append({
                "race_date": row["race_date"],
                "track": row["track"],
                "race_no": row["race_no"],
                "runner": row["runner"],
                "source_file": row["source_file"],
                "upstream_sp": upstream_sp_keys[key],
                "downstream_sp": row["sp"],
            })

    audit_rows = [
        {
            "year": y,
            "month": m,
            "track": track,
            "missing_sp_rows": count,
        }
        for (y, m, track), count in by_month.most_common()
    ]
    write_csv(DATA / "edgeiq_results_sp_population_audit_v1.csv", audit_rows, ["year", "month", "track", "missing_sp_rows"])
    summary = [{
        "total_rows": total,
        "rows_with_runner": with_runner,
        "rows_with_sp": with_sp,
        "rows_missing_sp": missing,
        "sp_coverage_pct": round(with_sp / total * 100, 2) if total else 0,
        "missing_sp_by_source_file": ";".join(f"{k}:{v}" for k, v in by_source.most_common(20)),
        "duplicate_race_runner_rows": sum(1 for count in duplicate_keys.values() if count > 1),
        "examples_where_sp_exists_upstream_but_missing_downstream": len(examples),
    }]
    write_csv(DATA / "edgeiq_results_sp_population_audit_summary_v1.csv", summary, list(summary[0].keys()))
    write_csv(DATA / "edgeiq_results_sp_missing_examples_v1.csv", examples, ["race_date", "track", "race_no", "runner", "source_file", "upstream_sp", "downstream_sp"])
    print(f"SP coverage {summary[0]['sp_coverage_pct']}%")


if __name__ == "__main__":
    main()
