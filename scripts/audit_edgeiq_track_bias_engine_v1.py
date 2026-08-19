from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

ENGINE = DATA / "edgeiq_track_bias_engine_v1.csv"
LIVE = DATA / "edgeiq_live_track_bias_feed_v1.csv"
SUMMARY = DATA / "edgeiq_track_bias_engine_summary_v1.csv"
AUDIT = DATA / "edgeiq_track_bias_engine_audit_v1.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        writer.writerows(rows)


def check(name: str, status: str, detail: str) -> dict[str, str]:
    return {"check": name, "status": status, "detail": detail}


def has_cols(rows: list[dict[str, str]], cols: list[str]) -> tuple[bool, str]:
    if not rows:
        return False, "no rows available"
    missing = [col for col in cols if col not in rows[0]]
    return not missing, "missing=" + "|".join(missing) if missing else "all required columns present"


def as_int(value: str) -> int:
    try:
        return int(float(str(value or "0")))
    except ValueError:
        return 0


def main() -> int:
    engine = read_csv(ENGINE)
    live = read_csv(LIVE)
    summary = read_csv(SUMMARY)
    rows: list[dict[str, str]] = []

    rows.append(check("engine_file_exists", "PASS" if ENGINE.exists() else "FAIL", str(ENGINE.name)))
    rows.append(check("live_file_exists", "PASS" if LIVE.exists() else "FAIL", str(LIVE.name)))
    rows.append(check("summary_file_exists", "PASS" if SUMMARY.exists() else "FAIL", str(SUMMARY.name)))
    rows.append(check("engine_rows_positive", "PASS" if len(engine) > 0 else "FAIL", f"engine_rows={len(engine)}"))
    rows.append(check("live_rows_positive", "PASS" if len(live) > 0 else "FAIL", f"live_rows={len(live)}"))

    ok, detail = has_cols(engine, [
        "track_key",
        "distance_band",
        "condition_band",
        "field_size_band",
        "rail_bucket",
        "run_style",
        "context_sample",
        "style_sample",
        "bias_band",
        "confidence",
        "bias_summary",
    ])
    rows.append(check("engine_required_columns", "PASS" if ok else "FAIL", detail))

    ok, detail = has_cols(live, [
        "race_date",
        "track",
        "race_no",
        "distance_band",
        "condition_band",
        "field_size_band",
        "rail_bucket",
        "projected_pace",
        "preferred_styles",
        "risk_styles",
        "bias_band",
        "confidence",
        "evidence_sample",
        "fallback_level",
    ])
    rows.append(check("live_required_columns", "PASS" if ok else "FAIL", detail))

    bad_high_engine = [
        row for row in engine
        if row.get("confidence") == "HIGH" and (as_int(row.get("style_sample", "")) < 100 or as_int(row.get("context_sample", "")) < 200)
    ]
    rows.append(check(
        "engine_high_confidence_sample_gate",
        "PASS" if not bad_high_engine else "FAIL",
        f"bad_rows={len(bad_high_engine)}",
    ))

    bad_high_live = [
        row for row in live
        if row.get("confidence") == "HIGH" and as_int(row.get("evidence_sample", "")) < 200
    ]
    rows.append(check(
        "live_high_confidence_sample_gate",
        "PASS" if not bad_high_live else "FAIL",
        f"bad_rows={len(bad_high_live)}",
    ))

    fallback_rows = [row for row in live if row.get("fallback_level") not in {"", "NO_MATCH"}]
    rows.append(check(
        "live_context_matching_present",
        "PASS" if fallback_rows else "WARN",
        f"matched_live_rows={len(fallback_rows)}",
    ))

    summary_status = any(row.get("metric") == "status" and row.get("value") == "TRACK_BIAS_ENGINE_V1_BUILT" for row in summary)
    rows.append(check("summary_status_present", "PASS" if summary_status else "FAIL", "summary status row checked"))

    rail_values = {row.get("rail_bucket") for row in live}
    rows.append(check(
        "rail_context_reported",
        "PASS" if rail_values else "FAIL",
        f"rail_buckets={'|'.join(sorted(v for v in rail_values if v))}",
    ))

    write_csv(AUDIT, rows)
    fail_count = sum(1 for row in rows if row["status"] == "FAIL")
    warn_count = sum(1 for row in rows if row["status"] == "WARN")
    print(f"Track bias engine audit: PASS={len(rows) - fail_count - warn_count} WARN={warn_count} FAIL={fail_count}")
    return 1 if fail_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
