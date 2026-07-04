from __future__ import annotations

import csv
import math
from pathlib import Path
from statistics import pstdev
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CAL = DATA / "edgeiq_nexus_score_calibration_v1.csv"
LIVE = DATA / "edgeiq_live_nexus_contextual_feed_v2_1.csv"
SCORE = DATA / "edgeiq_nexus_contextual_score_v2_1.csv"
SUMMARY = DATA / "edgeiq_nexus_score_calibration_summary_v1.csv"
AUDIT = DATA / "edgeiq_nexus_score_calibration_audit_v1.csv"


def text(value: Any) -> str:
    return str(value or "").strip()


def num(value: Any) -> float | None:
    raw = text(value)
    if not raw:
        return None
    try:
        val = float(raw)
    except ValueError:
        return None
    return val if math.isfinite(val) else None


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def add(rows: list[dict[str, Any]], check: str, ok: bool, detail: Any, count: int = 0) -> None:
    rows.append({"check": check, "status": "PASS" if ok else "FAIL", "detail": detail, "count": count})


def main() -> None:
    rows = read_rows(CAL)
    live = read_rows(LIVE)
    score = read_rows(SCORE)
    summary = read_rows(SUMMARY)
    values = [num(row.get("nexus_context_score_calibrated")) for row in rows]
    values = [value for value in values if value is not None]
    populated_pct = len(values) / len(rows) * 100.0 if rows else 0.0
    spread = (max(values) - min(values)) if values else 0.0
    std = pstdev(values) if len(values) > 1 else 0.0
    band_counts: dict[str, int] = {}
    for row in rows:
        band = text(row.get("nexus_context_band_calibrated")) or "UNKNOWN"
        band_counts[band] = band_counts.get(band, 0) + 1
    max_band_pct = max(band_counts.values()) / len(rows) * 100.0 if rows and band_counts else 0.0
    neg_poor_pct = (band_counts.get("NEGATIVE", 0) + band_counts.get("POOR", 0)) / len(rows) * 100.0 if rows else 0.0
    audit_rows: list[dict[str, Any]] = []
    for path, name, data in [(CAL, "calibration", rows), (LIVE, "live_v2_1", live), (SCORE, "score_v2_1", score), (SUMMARY, "summary", summary)]:
        add(audit_rows, f"{name}_file_exists", path.exists(), path, len(data))
    add(audit_rows, "rows_gt_0", len(rows) > 0, len(rows), len(rows))
    add(audit_rows, "calibrated_score_populated_gt_95pct", populated_pct > 95.0, f"{populated_pct:.2f}%", len(values))
    add(audit_rows, "min_max_spread_ge_35", spread >= 35.0, f"spread={spread:.2f}", len(values))
    add(audit_rows, "std_ge_10", std >= 10.0, f"std={std:.2f}", len(values))
    add(audit_rows, "not_more_than_55pct_one_band", max_band_pct <= 55.0, f"max_band_pct={max_band_pct:.2f}; bands={band_counts}", len(band_counts))
    add(audit_rows, "negative_poor_combined_lte_45pct", neg_poor_pct <= 45.0, f"negative_poor_pct={neg_poor_pct:.2f}", len(rows))
    add(audit_rows, "top_10_visible_in_summary", sum(1 for row in summary if text(row.get("metric")).startswith("top_")) >= 10, "top rows present", len(summary))
    add(audit_rows, "bottom_10_visible_in_summary", sum(1 for row in summary if text(row.get("metric")).startswith("bottom_")) >= 10, "bottom rows present", len(summary))
    add(audit_rows, "raw_score_preserved", all("raw_nexus_context_score" in row and "raw_nexus_context_band" in row for row in rows[:10]), "raw columns present", len(rows))
    add(audit_rows, "required_columns_present", all(col in (rows[0].keys() if rows else []) for col in ["nexus_context_score_calibrated", "nexus_context_band_calibrated", "nexus_context_percentile", "nexus_context_rank_in_race", "nexus_context_field_rank", "calibration_method"]), "required columns", len(rows[0].keys()) if rows else 0)
    with AUDIT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail", "count"])
        writer.writeheader()
        writer.writerows(audit_rows)
    failures = [row for row in audit_rows if row["status"] == "FAIL"]
    print(f"Nexus score calibration audit: PASS={len(audit_rows)-len(failures)} FAIL={len(failures)}")
    if failures:
        for row in failures:
            print(f"FAIL {row['check']}: {row['detail']}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
