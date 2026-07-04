from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

AUDIT_OUT = DATA / "edgeiq_nexus_feature_engine_audit_v1.csv"

FILES = {
    "trainer_recent_form": DATA / "edgeiq_trainer_recent_form_engine_v1.csv",
    "jockey_recent_form": DATA / "edgeiq_jockey_recent_form_engine_v1.csv",
    "jockey_run_style": DATA / "edgeiq_jockey_run_style_engine_v1.csv",
    "trainer_run_style": DATA / "edgeiq_trainer_run_style_engine_v1.csv",
    "partnership": DATA / "edgeiq_trainer_jockey_partnership_engine_v1.csv",
    "live_nexus": DATA / "edgeiq_live_nexus_feature_feed_v1.csv",
    "summary": DATA / "edgeiq_nexus_feature_engine_summary_v1.csv",
}

REQUIRED_COLUMNS = {
    "trainer_recent_form": [
        "trainer_canonical",
        "trainer_name",
        "last_25_starts",
        "last_25_wins",
        "last_25_places",
        "last_25_win_pct",
        "last_25_place_pct",
        "last_25_roi_pct",
        "last_25_ae",
        "last_25_avg_sp",
        "last_25_momentum_band",
        "last_50_starts",
        "last_100_starts",
    ],
    "jockey_recent_form": [
        "jockey_canonical",
        "jockey_name",
        "last_25_starts",
        "last_25_wins",
        "last_25_places",
        "last_25_win_pct",
        "last_25_place_pct",
        "last_25_roi_pct",
        "last_25_ae",
        "last_25_avg_sp",
        "last_25_momentum_band",
        "last_50_starts",
        "last_100_starts",
    ],
    "jockey_run_style": [
        "jockey_canonical",
        "jockey_name",
        "run_style_band",
        "starts",
        "wins",
        "places",
        "win_pct",
        "place_pct",
        "roi_pct",
        "ae",
        "avg_sp",
    ],
    "trainer_run_style": [
        "trainer_canonical",
        "trainer_name",
        "run_style_band",
        "starts",
        "wins",
        "places",
        "win_pct",
        "place_pct",
        "roi_pct",
        "ae",
        "avg_sp",
    ],
    "partnership": [
        "trainer_canonical",
        "jockey_canonical",
        "combo_canonical",
        "lifetime_starts",
        "lifetime_win_pct",
        "lifetime_place_pct",
        "lifetime_roi_pct",
        "lifetime_ae",
        "last_12_months_starts",
        "track_combo_starts",
        "distance_combo_starts",
        "class_combo_starts",
    ],
    "live_nexus": [
        "race_date",
        "track",
        "race_no",
        "horse",
        "trainer",
        "jockey",
        "trainer_last25_starts",
        "trainer_last25_momentum_band",
        "jockey_last25_starts",
        "jockey_last25_momentum_band",
        "trainer_run_style_starts",
        "jockey_run_style_rides",
        "combo_lifetime_starts",
        "combo_last12m_starts",
        "nexus_feature_coverage_count",
        "nexus_feature_status",
    ],
}


def read_header_and_count(path: Path) -> tuple[list[str], int]:
    if not path.exists():
        return [], 0
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
        return header, sum(1 for _ in reader)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = ["check", "status", "file", "detail", "rows"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    audit_rows: list[dict[str, Any]] = []
    headers: dict[str, list[str]] = {}
    counts: dict[str, int] = {}

    for name, path in FILES.items():
        header, count = read_header_and_count(path)
        headers[name] = header
        counts[name] = count
        audit_rows.append({
            "check": f"{name}_file_exists",
            "status": "PASS" if path.exists() else "FAIL",
            "file": str(path),
            "detail": "exists" if path.exists() else "missing",
            "rows": count,
        })
        if name != "summary":
            audit_rows.append({
                "check": f"{name}_rows_gt_0",
                "status": "PASS" if count > 0 else "FAIL",
                "file": str(path),
                "detail": "rows > 0" if count > 0 else "no rows",
                "rows": count,
            })

    for name, required in REQUIRED_COLUMNS.items():
        header_set = set(headers.get(name, []))
        missing = [col for col in required if col not in header_set]
        audit_rows.append({
            "check": f"{name}_key_columns_exist",
            "status": "PASS" if not missing else "FAIL",
            "file": str(FILES[name]),
            "detail": "OK" if not missing else "missing: " + ", ".join(missing),
            "rows": counts.get(name, 0),
        })

    live_path = FILES["live_nexus"]
    live_feature_rows = 0
    if live_path.exists():
        with live_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            for row in csv.DictReader(handle):
                try:
                    if int(float(row.get("nexus_feature_coverage_count") or 0)) > 0:
                        live_feature_rows += 1
                except ValueError:
                    pass
    audit_rows.append({
        "check": "live_nexus_rows_with_feature_data_gt_0",
        "status": "PASS" if live_feature_rows > 0 else "FAIL",
        "file": str(live_path),
        "detail": f"{live_feature_rows} live rows have at least one Nexus feature family",
        "rows": live_feature_rows,
    })

    write_csv(AUDIT_OUT, audit_rows)
    failures = [row for row in audit_rows if row["status"] == "FAIL"]
    print(f"EDGEiQ Nexus feature audit: {len(audit_rows) - len(failures)}/{len(audit_rows)} PASS")
    if failures:
        for row in failures:
            print(f"FAIL {row['check']}: {row['detail']}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
