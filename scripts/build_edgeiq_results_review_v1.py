import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RESULTS = DATA / "edgeiq_racingcom_results_warehouse_v1.csv"
LIVE_BET_QUALITY = DATA / "edgeiq_live_bet_quality_v1_1.csv"
V8 = DATA / "edgeiq_live_v8_candidate_display_feed_v1.csv"
LIVE_RUNNER_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
RACE_SECTIONAL_READ = DATA / "edgeiq_race_sectional_read_v1.csv"

OUT_CSV = DATA / "edgeiq_results_review_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_results_review_v1_summary.csv"
OUT_JSON = DATA / "edgeiq_results_review_v1.json"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str).fillna("")


def clean(x):
    return str(x or "").strip()


def key_text(x):
    return "".join(ch for ch in clean(x).upper() if ch.isalnum())


def race_key(row):
    d = clean(row.get("meeting_date")) or clean(row.get("race_date"))
    t = clean(row.get("track"))
    rn = clean(row.get("race_no"))
    return f"{d}|{t.upper()}|{rn}"


def runner_key(row):
    horse = clean(row.get("horse")) or clean(row.get("horseName")) or clean(row.get("horse_name"))
    return f"{race_key(row)}|{key_text(horse)}"


def n(x, default=None):
    try:
        s = str(x).strip()
        if s == "":
            return default
        return float(s)
    except Exception:
        return default


def finish_pos(row):
    for c in ["finishPosition", "finish_position", "position", "pos"]:
        v = clean(row.get(c))
        if v:
            try:
                return int(float(v))
            except Exception:
                if v.upper() == "SCR":
                    return 999
    return 999


def main():
    results = read_csv(RESULTS)
    bet = read_csv(LIVE_BET_QUALITY)
    v8 = read_csv(V8)
    live = read_csv(LIVE_RUNNER_BOARD)
    sectional_read = read_csv(RACE_SECTIONAL_READ)

    if results.empty:
        print("[RESULTS_REVIEW_V1] NO RESULTS WAREHOUSE FOUND")
        pd.DataFrame().to_csv(OUT_CSV, index=False)
        return

    maps = {}

    for name, df in [("bet", bet), ("v8", v8), ("live", live)]:
        m = {}
        if not df.empty:
            for _, r in df.iterrows():
                m[runner_key(r)] = r
        maps[name] = m

    read_map = {}
    if not sectional_read.empty:
        for _, r in sectional_read.iterrows():
            read_map[race_key(r)] = r

    rows = []

    for _, r in results.iterrows():
        rk = runner_key(r)
        rrk = race_key(r)

        b = maps["bet"].get(rk)
        v = maps["v8"].get(rk)
        l = maps["live"].get(rk)
        sr = read_map.get(rrk)

        horse = clean(r.get("horseName")) or clean(r.get("horse")) or clean(r.get("horse_name"))

        rows.append(
            {
                "meeting_date": clean(r.get("meeting_date")) or clean(r.get("race_date")),
                "track": clean(r.get("track")),
                "race_no": clean(r.get("race_no")),
                "finish_position": finish_pos(r),
                "horse": horse,
                "jockey": clean(r.get("jockey")),
                "trainer": clean(r.get("trainer")),
                "barrier": clean(r.get("barrier")),
                "sp": clean(r.get("sp")) or clean(r.get("SP")),
                "stab": clean(r.get("stab")),
                "margin": clean(r.get("margin")),
                "race_time": clean(r.get("raceTime")) or clean(r.get("race_time")),
                "edgeiq_fair_price_v1": clean(l.get("fair_price")) if l is not None else "",
                "edgeiq_market_price_v1": clean(l.get("live_price")) if l is not None else "",
                "edgeiq_pre_race_edge_pct_v1": clean(l.get("edge_pct")) if l is not None else "",
                "bet_quality_score_v1_1": clean(b.get("bet_quality_score_v1_1")) if b is not None else "",
                "bet_quality_grade_v1_1": clean(b.get("bet_quality_grade_v1_1")) if b is not None else "",
                "v8_fair_price_v1": clean(v.get("v8_candidate_price_display")) if v is not None else "",
                "v8_confidence_v1": clean(v.get("brc_match_level_v8")) if v is not None else "",
                "sectional_race_summary_v1": clean(sr.get("sectional_race_summary")) if sr is not None else "",
                "sectional_read_status_v1": clean(sr.get("sectional_read_status")) if sr is not None else "PENDING_SECTIONALS",
                "results_review_note_v1": "",
            }
        )

    out = pd.DataFrame(rows)
    out = out.sort_values(["meeting_date", "track", "race_no", "finish_position", "horse"])
    out.to_csv(OUT_CSV, index=False)

    summary = {
        "status": "COMPLETE",
        "rows": int(len(out)),
        "races": int(out[["meeting_date", "track", "race_no"]].drop_duplicates().shape[0]),
        "sectional_read_matched_rows": int((out["sectional_race_summary_v1"].astype(str).str.strip() != "").sum()),
        "bet_quality_matched_rows": int((out["bet_quality_score_v1_1"].astype(str).str.strip() != "").sum()),
        "v8_matched_rows": int((out["v8_fair_price_v1"].astype(str).str.strip() != "").sum()),
        "verdict": "RESULTS_REVIEW_V1_BUILT",
    }

    pd.DataFrame([{"metric": k, "value": v} for k, v in summary.items()]).to_csv(OUT_SUMMARY, index=False)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("[RESULTS_REVIEW_V1] COMPLETE")
    for k, v in summary.items():
        print(f"{k}={v}")


if __name__ == "__main__":
    main()
