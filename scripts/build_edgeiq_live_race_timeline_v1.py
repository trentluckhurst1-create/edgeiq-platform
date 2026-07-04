import json
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

ACTIVE_SELECTOR = DATA / "edgeiq_active_race_selector.csv"
LIVE_RUNNER_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"

OUT_CSV = DATA / "edgeiq_live_race_timeline_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_live_race_timeline_v1_summary.csv"
OUT_JSON = DATA / "edgeiq_live_race_timeline_v1.json"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str).fillna("")


def n(x, default=0):
    try:
        s = str(x).strip()
        if s == "":
            return default
        return float(s)
    except Exception:
        return default


def clean(x):
    return str(x or "").strip()


def parse_dt(date_s, time_s):
    date_s = clean(date_s)
    time_s = clean(time_s)
    if not date_s or not time_s:
        return None

    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(f"{date_s} {time_s}", fmt)
        except Exception:
            pass
    return None


def main():
    active = read_csv(ACTIVE_SELECTOR)
    live = read_csv(LIVE_RUNNER_BOARD)

    if active.empty:
        raise SystemExit("[RACE_TIMELINE_V1] ERROR missing active selector")

    now = datetime.now()

    live_counts = {}
    if not live.empty:
        for _, g in live.groupby(["race_date", "track", "race_no"], dropna=False):
            first = g.iloc[0]
            k = (clean(first.get("race_date")), clean(first.get("track")), clean(first.get("race_no")))
            live_counts[k] = {
                "runners": int(len(g)),
                "live_rows": int((g.get("live_price", pd.Series([""] * len(g))).astype(str).str.strip() != "").sum()),
                "fair_rows": int((g.get("fair_price", pd.Series([""] * len(g))).astype(str).str.strip() != "").sum()),
            }

    rows = []

    for _, r in active.iterrows():
        race_date = clean(r.get("race_date"))
        track = clean(r.get("track"))
        race_no = clean(r.get("race_no"))
        race_time = clean(r.get("race_time"))

        dt = parse_dt(race_date, race_time)
        minutes_to_jump = None
        if dt is not None:
            minutes_to_jump = round((dt - now).total_seconds() / 60, 1)

        k = (race_date, track, race_no)
        counts = live_counts.get(k, {"runners": 0, "live_rows": 0, "fair_rows": 0})

        if minutes_to_jump is None:
            status = "UNKNOWN_TIME"
        elif minutes_to_jump > 0:
            status = "UPCOMING"
        elif minutes_to_jump >= -20:
            status = "RECENTLY_JUMPED"
        else:
            status = "COMPLETED_OR_STALE"

        market_status = "LIVE_MARKET" if counts["live_rows"] > 0 else "NO_LIVE_MARKET"

        rows.append(
            {
                "race_key": clean(r.get("race_key")) or f"{race_date}_{track}_R{race_no}",
                "race_date": race_date,
                "track": track,
                "race_no": race_no,
                "race_time": race_time,
                "day_bucket": clean(r.get("day_bucket")),
                "priority_rank": clean(r.get("priority_rank")),
                "minutes_to_jump": minutes_to_jump if minutes_to_jump is not None else "",
                "timeline_status_v1": status,
                "market_status_v1": market_status,
                "runner_rows_v1": counts["runners"],
                "live_price_rows_v1": counts["live_rows"],
                "fair_price_rows_v1": counts["fair_rows"],
                "default_intelligence_focus_v1": "NO",
                "default_results_focus_v1": "NO",
            }
        )

    out = pd.DataFrame(rows)

    future = out[pd.to_numeric(out["minutes_to_jump"], errors="coerce") > 0].copy()
    future = future.sort_values(["minutes_to_jump", "race_date", "track", "race_no"])

    if len(future):
        idx = future.index[0]
        out.loc[idx, "default_intelligence_focus_v1"] = "YES"

    completed = out[pd.to_numeric(out["minutes_to_jump"], errors="coerce") <= 0].copy()
    completed = completed.sort_values(["race_date", "track", "race_no"])

    if len(completed):
        for idx in completed.index:
            out.loc[idx, "default_results_focus_v1"] = "YES"

    out.to_csv(OUT_CSV, index=False)

    summary = {
        "status": "COMPLETE",
        "rows": int(len(out)),
        "next_race": str(out[out["default_intelligence_focus_v1"] == "YES"]["race_key"].iloc[0]) if (out["default_intelligence_focus_v1"] == "YES").any() else "",
        "upcoming": int((out["timeline_status_v1"] == "UPCOMING").sum()),
        "recently_jumped": int((out["timeline_status_v1"] == "RECENTLY_JUMPED").sum()),
        "completed_or_stale": int((out["timeline_status_v1"] == "COMPLETED_OR_STALE").sum()),
        "live_market_races": int((out["market_status_v1"] == "LIVE_MARKET").sum()),
        "verdict": "RACE_TIMELINE_V1_BUILT",
    }

    pd.DataFrame([{"metric": k, "value": v} for k, v in summary.items()]).to_csv(OUT_SUMMARY, index=False)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("[RACE_TIMELINE_V1] COMPLETE")
    for k, v in summary.items():
        print(f"{k}={v}")


if __name__ == "__main__":
    main()
