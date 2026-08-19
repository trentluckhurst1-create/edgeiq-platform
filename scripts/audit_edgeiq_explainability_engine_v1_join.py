from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_live_runner_board_v1.csv"

FEEDS = {
    "race_shape": DATA / "edgeiq_race_shape_story_v1.csv",
    "runner_explainability": DATA / "edgeiq_runner_explainability_v1.csv",
    "confidence_breakdown": DATA / "edgeiq_confidence_breakdown_v1.csv",
    "runner_trend": DATA / "edgeiq_runner_trend_engine_v1.csv",
}

OUT = DATA / "edgeiq_explainability_engine_v1_join_audit.csv"
SUMMARY = DATA / "edgeiq_explainability_engine_v1_join_audit_summary.csv"


def clean(v):
    return "" if v is None else str(v).strip()


def upper(v):
    return clean(v).upper()


def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def horse(row):
    return clean(row.get("horse")) or clean(row.get("_horse"))


def horse_key(row):
    return upper(row.get("horse_key")) or upper(horse(row))


def runner_key(row):
    return (
        clean(row.get("race_date")) or clean(row.get("_date")),
        upper(row.get("track")) or upper(row.get("_track")),
        clean(row.get("race_no")) or clean(row.get("_race")),
        horse_key(row),
    )


def race_key(row):
    return (
        clean(row.get("race_date")) or clean(row.get("_date")),
        upper(row.get("track")) or upper(row.get("_track")),
        clean(row.get("race_no")) or clean(row.get("_race")),
    )


def is_scratched(row):
    vals = [
        upper(row.get("is_scratched")),
        upper(row.get("scratch_status")),
        upper(row.get("runner_status")),
    ]
    return any(v in {"TRUE", "YES", "Y", "SCRATCHED", "LATE_SCRATCHING"} for v in vals)


def duplicate_count(keys):
    c = Counter(keys)
    return sum(1 for _, n in c.items() if n > 1)


def main():
    built_at = datetime.now(timezone.utc).isoformat()

    live_rows_all = read_csv(LIVE)
    live_rows = [r for r in live_rows_all if not is_scratched(r)]

    live_runner_keys = [runner_key(r) for r in live_rows if all(runner_key(r))]
    live_race_keys = [race_key(r) for r in live_rows if all(race_key(r))]

    live_runner_set = set(live_runner_keys)
    live_race_set = set(live_race_keys)

    audit_rows = []
    summary_rows = [
        {"metric": "status", "value": "EXPLAINABILITY_ENGINE_V1_JOIN_AUDIT_BUILT"},
        {"metric": "live_rows_all", "value": len(live_rows_all)},
        {"metric": "live_active_rows", "value": len(live_rows)},
        {"metric": "live_unique_runner_keys", "value": len(live_runner_set)},
        {"metric": "live_unique_race_keys", "value": len(live_race_set)},
        {"metric": "built_at", "value": built_at},
    ]

    all_pass = True

    for name, path in FEEDS.items():
        rows = read_csv(path)
        is_race_feed = name == "race_shape"

        if is_race_feed:
            keys = [race_key(r) for r in rows if all(race_key(r))]
            key_set = set(keys)
            expected_set = live_race_set
        else:
            keys = [runner_key(r) for r in rows if all(runner_key(r))]
            key_set = set(keys)
            expected_set = live_runner_set

        matched = len(expected_set & key_set)
        missing = len(expected_set - key_set)
        extra = len(key_set - expected_set)
        duplicates = duplicate_count(keys)
        join_rate = round((matched / len(expected_set)) * 100, 2) if expected_set else 0

        verdict = "PASS"
        if missing > 0 or duplicates > 0 or join_rate < 99:
            verdict = "WARN"
            all_pass = False

        audit_rows.append({
            "feed": name,
            "path": str(path),
            "feed_rows": len(rows),
            "feed_unique_keys": len(key_set),
            "expected_keys": len(expected_set),
            "matched_keys": matched,
            "missing_from_feed": missing,
            "extra_in_feed": extra,
            "duplicate_keys": duplicates,
            "join_rate_pct": join_rate,
            "verdict": verdict,
            "built_at": built_at,
        })

        summary_rows.extend([
            {"metric": f"{name}_rows", "value": len(rows)},
            {"metric": f"{name}_join_rate_pct", "value": join_rate},
            {"metric": f"{name}_missing", "value": missing},
            {"metric": f"{name}_duplicates", "value": duplicates},
            {"metric": f"{name}_verdict", "value": verdict},
        ])

    summary_rows.insert(1, {
        "metric": "overall_verdict",
        "value": "PASS" if all_pass else "WARN_REVIEW_REQUIRED",
    })

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        fields = [
            "feed", "path", "feed_rows", "feed_unique_keys", "expected_keys",
            "matched_keys", "missing_from_feed", "extra_in_feed",
            "duplicate_keys", "join_rate_pct", "verdict", "built_at",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(audit_rows)

    with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary_rows)

    print("[EXPLAINABILITY_ENGINE_V1_JOIN_AUDIT] COMPLETE")
    print(f"output={OUT}")
    print(f"summary={SUMMARY}")


if __name__ == "__main__":
    main()
