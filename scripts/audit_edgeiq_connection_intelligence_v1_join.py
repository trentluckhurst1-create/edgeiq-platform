from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_PATH = DATA / "edgeiq_live_runner_board_v1.csv"
CONNECTION_PATH = DATA / "edgeiq_connection_intelligence_v1.csv"
DETAIL_PATH = DATA / "edgeiq_connection_intelligence_v1_join_audit.csv"
SUMMARY_PATH = DATA / "edgeiq_connection_intelligence_v1_join_audit_summary.csv"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def upper_text(value: object) -> str:
    return safe_text(value).upper()


def normalize_horse(value: object) -> str:
    return "".join(ch for ch in upper_text(value) if ch.isalnum())


def is_scratched(row: pd.Series) -> bool:
    values = [
        upper_text(row.get("is_scratched")),
        upper_text(row.get("scratch_status")),
        upper_text(row.get("runner_status")),
    ]
    return any(value in {"TRUE", "YES", "Y", "1", "SCRATCHED", "LATE_SCRATCHED", "LATESCRATCHED"} for value in values)


def build_key(row: pd.Series) -> str:
    race_date = safe_text(row.get("race_date"))
    track = upper_text(row.get("track"))
    race_no = safe_text(row.get("race_no"))
    horse_key = upper_text(row.get("horse_key")) or normalize_horse(row.get("horse"))
    return "|".join([race_date, track, race_no, horse_key])


def main() -> None:
    built_at = now_iso()
    if not LIVE_PATH.exists():
        raise FileNotFoundError(f"Missing live runner board: {LIVE_PATH}")
    if not CONNECTION_PATH.exists():
        raise FileNotFoundError(f"Missing connection intelligence feed: {CONNECTION_PATH}")

    live_df = pd.read_csv(LIVE_PATH, dtype=str).fillna("")
    connection_df = pd.read_csv(CONNECTION_PATH, dtype=str).fillna("")

    live_active = live_df[~live_df.apply(is_scratched, axis=1)].copy()
    live_active["join_key"] = live_active.apply(build_key, axis=1)
    connection_df["join_key"] = connection_df.apply(build_key, axis=1)

    live_counts = live_active["join_key"].value_counts(dropna=False).to_dict()
    connection_counts = connection_df["join_key"].value_counts(dropna=False).to_dict()

    all_keys = sorted(set(live_counts.keys()) | set(connection_counts.keys()))
    detail_rows: list[dict[str, object]] = []
    matched_rows = 0
    missing_rows = 0
    extra_rows = 0

    live_lookup = {
        row["join_key"]: row
        for row in live_active[["join_key", "race_date", "track", "race_no", "horse", "horse_key"]].to_dict("records")
    }
    connection_lookup = {
        row["join_key"]: row
        for row in connection_df[["join_key", "race_date", "track", "race_no", "horse", "horse_key"]].to_dict("records")
    }

    for join_key in all_keys:
        live_count = int(live_counts.get(join_key, 0))
        connection_count = int(connection_counts.get(join_key, 0))
        live_row = live_lookup.get(join_key, {})
        connection_row = connection_lookup.get(join_key, {})

        if live_count > 0 and connection_count > 0:
            issue_type = "MATCHED"
            matched_rows += 1
        elif live_count > 0:
            issue_type = "MISSING_IN_CONNECTION"
            missing_rows += 1
        else:
            issue_type = "EXTRA_IN_CONNECTION"
            extra_rows += 1

        detail_rows.append(
            {
                "race_date": safe_text(live_row.get("race_date") or connection_row.get("race_date")),
                "track": safe_text(live_row.get("track") or connection_row.get("track")),
                "race_no": safe_text(live_row.get("race_no") or connection_row.get("race_no")),
                "horse": safe_text(live_row.get("horse") or connection_row.get("horse")),
                "horse_key": safe_text(live_row.get("horse_key") or connection_row.get("horse_key")),
                "join_key": join_key,
                "live_count": live_count,
                "connection_count": connection_count,
                "issue_type": issue_type,
                "built_at": built_at,
            }
        )

    duplicate_connection_keys = sum(1 for value in connection_counts.values() if value > 1)
    duplicate_live_keys = sum(1 for value in live_counts.values() if value > 1)
    distinct_live_keys = len(live_counts)
    distinct_connection_keys = len(connection_counts)
    join_rate_pct = round((matched_rows / distinct_live_keys) * 100.0, 4) if distinct_live_keys else 0.0

    summary_row = {
        "status": "PASS" if join_rate_pct == 100.0 and duplicate_connection_keys == 0 and duplicate_live_keys == 0 and extra_rows == 0 else "FAIL",
        "active_live_rows": len(live_active),
        "distinct_live_keys": distinct_live_keys,
        "connection_rows": len(connection_df),
        "distinct_connection_keys": distinct_connection_keys,
        "matched_rows": matched_rows,
        "missing_in_connection_rows": missing_rows,
        "extra_connection_rows": extra_rows,
        "duplicate_live_keys": duplicate_live_keys,
        "duplicate_connection_keys": duplicate_connection_keys,
        "join_rate_pct": join_rate_pct,
        "built_at": built_at,
    }

    pd.DataFrame(detail_rows).to_csv(DETAIL_PATH, index=False)
    pd.DataFrame([summary_row]).to_csv(SUMMARY_PATH, index=False)

    print("[EDGEIQ_CONNECTION_INTELLIGENCE_V1_JOIN_AUDIT] COMPLETE")
    print(f"status={summary_row['status']}")
    print(f"active_live_rows={summary_row['active_live_rows']}")
    print(f"connection_rows={summary_row['connection_rows']}")
    print(f"matched_rows={summary_row['matched_rows']}")
    print(f"missing_in_connection_rows={summary_row['missing_in_connection_rows']}")
    print(f"duplicate_connection_keys={summary_row['duplicate_connection_keys']}")
    print(f"join_rate_pct={summary_row['join_rate_pct']}")
    print(f"wrote={DETAIL_PATH}")
    print(f"summary={SUMMARY_PATH}")


if __name__ == "__main__":
    main()
