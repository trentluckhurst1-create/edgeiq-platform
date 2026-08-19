from __future__ import annotations

from datetime import datetime, date
from pathlib import Path
import math
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "public" / "data"
INPUT_PATH = DATA_DIR / "edgeiq_live_runner_board_v1.csv"
DETAIL_PATH = DATA_DIR / "edgeiq_race_probability_integrity_v1.csv"
SUMMARY_PATH = DATA_DIR / "edgeiq_race_probability_integrity_v1_summary.csv"


def text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def as_float(value: object) -> float | None:
    raw = text(value).replace("$", "").replace("%", "").replace(",", "")
    if not raw:
        return None
    try:
        number = float(raw)
    except ValueError:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def as_bool(value: object) -> bool:
    raw = text(value).upper()
    return raw in {"1", "TRUE", "YES", "Y", "SCRATCHED", "LATESCRATCHED"}


def is_active_runner(row: pd.Series) -> bool:
    status_text = " ".join(
        [
            text(row.get("runner_status")),
            text(row.get("scratch_status")),
            text(row.get("tab_fixed_betting_status")),
            text(row.get("is_scratched")),
        ]
    ).upper()
    if "SCRATCH" in status_text:
        return False
    if as_bool(row.get("is_scratched")):
        return False
    return True


def future_flag(row: pd.Series, today: date) -> bool:
    day_bucket = text(row.get("day_bucket")).upper()
    if day_bucket in {"TOMORROW", "DAY+2", "DAY +2"}:
        return True
    race_date = text(row.get("race_date") or row.get("meeting_date"))
    if not race_date:
        return False
    try:
        parsed = datetime.strptime(race_date, "%Y-%m-%d").date()
    except ValueError:
        return False
    return parsed > today


def status_for_race(
    *,
    active_runner_count: int,
    rows_missing_win_pct: int,
    rows_missing_fair_price: int,
    win_pct_sum: float,
    bad_fair_rows: int,
    future_rows_present: bool,
) -> str:
    if active_runner_count == 0:
        return "NO_ACTIVE_RUNNERS"
    if future_rows_present and (rows_missing_win_pct > 0 or rows_missing_fair_price > 0):
        return "WARNING_PARTIAL_FUTURE"
    if rows_missing_win_pct > 0:
        return "FAIL_MISSING_PROB"
    if bad_fair_rows > 0:
        return "FAIL_BAD_FAIR"
    if win_pct_sum < 95:
        return "FAIL_PROB_SUM_LOW"
    if win_pct_sum > 105:
        return "FAIL_PROB_SUM_HIGH"
    if 99 <= win_pct_sum <= 101:
        return "PASS"
    return "WARN_PROB_SUM_NEAR_TARGET"


def main() -> int:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_PATH}")

    df = pd.read_csv(INPUT_PATH, dtype=str, keep_default_na=False)
    if df.empty:
        raise ValueError(f"Input file is empty: {INPUT_PATH}")

    for required in ["race_date", "track", "race_no"]:
        if required not in df.columns:
            raise KeyError(f"Missing required column: {required}")

    df["__active__"] = df.apply(is_active_runner, axis=1)
    df["__future__"] = df.apply(lambda row: future_flag(row, date.today()), axis=1)
    df["__win_pct__"] = df["win_pct"].map(as_float) if "win_pct" in df.columns else None
    df["__fair_price__"] = df["fair_price"].map(as_float) if "fair_price" in df.columns else None
    df["__implied_prob__"] = df["__fair_price__"].map(lambda value: (100.0 / value) if value and value > 0 else None)

    detail_rows: list[dict[str, object]] = []

    grouped = df.groupby(["race_date", "track", "race_no"], dropna=False, sort=True)
    for (race_date, track, race_no), group in grouped:
        active = group[group["__active__"] == True].copy()
        active_runner_count = int(len(active))

        win_pcts = active["__win_pct__"].dropna().astype(float) if "__win_pct__" in active else pd.Series(dtype=float)
        fair_prices = active["__fair_price__"].dropna().astype(float) if "__fair_price__" in active else pd.Series(dtype=float)
        implied_probs = active["__implied_prob__"].dropna().astype(float) if "__implied_prob__" in active else pd.Series(dtype=float)

        rows_with_win_pct = int(win_pcts.shape[0])
        rows_with_fair_price = int(fair_prices.shape[0])
        rows_missing_win_pct = max(active_runner_count - rows_with_win_pct, 0)
        rows_missing_fair_price = max(active_runner_count - rows_with_fair_price, 0)

        win_pct_sum = float(win_pcts.sum()) if rows_with_win_pct else 0.0
        implied_prob_sum_from_fair_price = float(implied_probs.sum()) if rows_with_fair_price else 0.0
        min_win_pct = float(win_pcts.min()) if rows_with_win_pct else None
        max_win_pct = float(win_pcts.max()) if rows_with_win_pct else None

        top_horse = ""
        top_win_pct = None
        top_fair_price = None
        if rows_with_win_pct:
            active_sorted = active.sort_values("__win_pct__", ascending=False, na_position="last")
            top_row = active_sorted.iloc[0]
            top_horse = text(top_row.get("horse"))
            top_win_pct = as_float(top_row.get("win_pct"))
            top_fair_price = as_float(top_row.get("fair_price"))

        bad_fair_rows = 0
        for _, row in active.iterrows():
            wp = as_float(row.get("win_pct"))
            fair = as_float(row.get("fair_price"))
            if wp is None or fair is None or wp <= 0 or fair <= 0:
                continue
            expected_fair = 100.0 / wp
            abs_diff = abs(fair - expected_fair)
            rel_diff_pct = (abs_diff / expected_fair) * 100 if expected_fair else 0.0
            if abs_diff > 0.5 and rel_diff_pct > 2.5:
                bad_fair_rows += 1

        future_rows_present = bool(active["__future__"].any()) if active_runner_count else bool(group["__future__"].any())
        status = status_for_race(
            active_runner_count=active_runner_count,
            rows_missing_win_pct=rows_missing_win_pct,
            rows_missing_fair_price=rows_missing_fair_price,
            win_pct_sum=win_pct_sum,
            bad_fair_rows=bad_fair_rows,
            future_rows_present=future_rows_present,
        )

        detail_rows.append(
            {
                "race_date": race_date,
                "track": track,
                "race_no": race_no,
                "active_runner_count": active_runner_count,
                "rows_with_win_pct": rows_with_win_pct,
                "rows_with_fair_price": rows_with_fair_price,
                "rows_missing_win_pct": rows_missing_win_pct,
                "rows_missing_fair_price": rows_missing_fair_price,
                "win_pct_sum": round(win_pct_sum, 3),
                "implied_prob_sum_from_fair_price": round(implied_prob_sum_from_fair_price, 3),
                "min_win_pct": round(min_win_pct, 3) if min_win_pct is not None else "",
                "max_win_pct": round(max_win_pct, 3) if max_win_pct is not None else "",
                "top_horse": top_horse,
                "top_win_pct": round(top_win_pct, 3) if top_win_pct is not None else "",
                "top_fair_price": round(top_fair_price, 3) if top_fair_price is not None else "",
                "status": status,
            }
        )

    detail_df = pd.DataFrame(detail_rows)
    detail_df.to_csv(DETAIL_PATH, index=False)

    summary_row = {
        "built_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "input_file": INPUT_PATH.name,
        "races_audited": int(detail_df.shape[0]),
        "pass_races": int((detail_df["status"] == "PASS").sum()),
        "warning_partial_future_races": int((detail_df["status"] == "WARNING_PARTIAL_FUTURE").sum()),
        "warn_near_target_races": int((detail_df["status"] == "WARN_PROB_SUM_NEAR_TARGET").sum()),
        "fail_missing_prob_races": int((detail_df["status"] == "FAIL_MISSING_PROB").sum()),
        "fail_prob_sum_low_races": int((detail_df["status"] == "FAIL_PROB_SUM_LOW").sum()),
        "fail_prob_sum_high_races": int((detail_df["status"] == "FAIL_PROB_SUM_HIGH").sum()),
        "fail_bad_fair_races": int((detail_df["status"] == "FAIL_BAD_FAIR").sum()),
        "no_active_runner_races": int((detail_df["status"] == "NO_ACTIVE_RUNNERS").sum()),
    }
    pd.DataFrame([summary_row]).to_csv(SUMMARY_PATH, index=False)

    flemington = detail_df[
        (detail_df["race_date"] == "2026-06-20") & (detail_df["track"].astype(str).str.upper() == "FLEMINGTON")
    ].copy()

    print("[EDGEIQ_RACE_PROBABILITY_INTEGRITY_V1] COMPLETE")
    print(f"races_audited={summary_row['races_audited']}")
    print(f"pass_races={summary_row['pass_races']}")
    print(f"warning_partial_future_races={summary_row['warning_partial_future_races']}")
    print(f"fail_missing_prob_races={summary_row['fail_missing_prob_races']}")
    print(f"fail_prob_sum_low_races={summary_row['fail_prob_sum_low_races']}")
    print(f"fail_prob_sum_high_races={summary_row['fail_prob_sum_high_races']}")
    print(f"fail_bad_fair_races={summary_row['fail_bad_fair_races']}")
    print(f"wrote={DETAIL_PATH}")
    print(f"wrote={SUMMARY_PATH}")

    if not flemington.empty:
        print("\nFLEMINGTON 2026-06-20")
        display_cols = [
            "race_date",
            "track",
            "race_no",
            "active_runner_count",
            "win_pct_sum",
            "top_horse",
            "top_win_pct",
            "top_fair_price",
            "status",
        ]
        print(flemington[display_cols].to_string(index=False))

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover
        print(f"[EDGEIQ_RACE_PROBABILITY_INTEGRITY_V1] FAILED: {exc}", file=sys.stderr)
        raise
