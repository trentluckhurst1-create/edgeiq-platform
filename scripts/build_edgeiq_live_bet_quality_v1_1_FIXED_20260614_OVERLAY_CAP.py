import json
import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUT_CSV = DATA / "edgeiq_live_bet_quality_v1_1.csv"
OUT_SUMMARY = DATA / "edgeiq_live_bet_quality_v1_1_summary.csv"
OUT_JSON = DATA / "edgeiq_live_bet_quality_v1_1.json"

LIVE_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
V8_DISPLAY = DATA / "edgeiq_live_v8_candidate_display_feed_v1.csv"
RELIABILITY = DATA / "edgeiq_live_race_reliability_v1_feed.csv"
RELIABILITY_FALLBACK = DATA / "edgeiq_race_reliability_v1.csv"
SECTIONALS = DATA / "edgeiq_sectional_profiles_v2.csv"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str).fillna("")


def norm_text(x):
    return str(x or "").strip()


def norm_upper(x):
    return norm_text(x).upper()


def horse_key(x):
    return "".join(ch for ch in norm_upper(x) if ch.isalnum())


def num(x, default=math.nan):
    try:
        if x is None:
            return default
        s = str(x).strip()
        if s == "":
            return default
        return float(s)
    except Exception:
        return default


def first_existing(row, cols, default=""):
    for c in cols:
        if c in row.index:
            v = row.get(c)
            if str(v).strip() != "":
                return v
    return default


def find_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None


def safe_round(x, nd=4):
    try:
        if pd.isna(x) or math.isnan(float(x)):
            return ""
        return round(float(x), nd)
    except Exception:
        return ""


def overlay_score(overlay_pct):
    x = num(overlay_pct, 0)
    if x <= 0:
        return 0.0

    if x <= 6:
        return max(0.0, x * 1.2)
    if x <= 12:
        return 7.2 + ((x - 6) * 1.1)
    if x <= 25:
        return 13.8 + ((x - 12) * 0.7)
    if x <= 60:
        return 22.9 + ((x - 25) * 0.2)
    if x <= 150:
        return 25.0

    return 18.0


def interaction_score(v8_row):
    if v8_row is None:
        return 0.0

    match_level = norm_upper(v8_row.get("brc_match_level_v8", ""))
    badge = norm_upper(v8_row.get("v8_candidate_badge", ""))
    status = norm_upper(v8_row.get("v8_candidate_display_status", ""))

    score = 0.0

    if match_level == "EXACT":
        score += 10.0
    elif match_level == "TRACK_DISTANCE_RAIL_CONDITION":
        score += 7.0
    elif match_level == "TRACK_DISTANCE_RAIL_CONDITION_WIDE":
        score += 4.0

    if "POSITIVE" in badge or "SHORTEN" in badge or "UP" in badge:
        score += 10.0
    elif "NEUTRAL" in badge:
        score += 5.0
    elif "NEGATIVE" in badge or "LENGTHEN" in badge or "DOWN" in badge:
        score += 1.0

    if "OBSERVATION" in status or "ACTIVE" in status or "CANDIDATE" in status:
        score += 5.0

    return max(0.0, min(25.0, score))


def reliability_score(row):
    raw = first_existing(
        row,
        [
            "race_reliability_score_v1",
            "race_reliability_score",
            "reliability_score",
            "reliability_score_v1",
        ],
        "",
    )
    v = num(raw, math.nan)

    if not math.isnan(v):
        if v <= 20:
            return max(0.0, min(20.0, v))
        return max(0.0, min(20.0, v / 5.0))

    band = norm_upper(
        first_existing(
            row,
            [
                "race_reliability_band_v1",
                "race_reliability_band",
                "reliability_band",
            ],
            "",
        )
    )

    if "ELITE" in band:
        return 20.0
    if "STRONG" in band or "HIGH" in band:
        return 16.0
    if "SOLID" in band or "MEDIUM" in band:
        return 12.0
    if "WEAK" in band or "LOW" in band:
        return 6.0
    return 8.0


def sectional_score(row):
    depth = norm_upper(row.get("profile_depth_status", ""))
    archetype = norm_upper(row.get("sectional_archetype", ""))

    runs = num(row.get("runs_with_sectionals", ""), 0)
    avg_peak = num(row.get("avg_peak_speed", ""), math.nan)
    avg_late = num(row.get("avg_late_speed", ""), math.nan)
    avg_speed = num(row.get("avg_speed", ""), math.nan)

    score = 0.0

    if runs >= 8:
        score += 5.0
    elif runs >= 4:
        score += 4.0
    elif runs >= 2:
        score += 2.0

    if "DNA" in depth or "READY" in depth:
        score += 4.0
    elif "PROFILE" in depth:
        score += 2.0

    if any(k in archetype for k in ["ELITE", "STRONG", "FAST", "LATE", "PEAK"]):
        score += 4.0
    elif archetype:
        score += 2.0

    speed_vals = [x for x in [avg_peak, avg_late, avg_speed] if not math.isnan(x)]
    if speed_vals:
        score += 2.0

    return max(0.0, min(15.0, score))


def market_score(live_price, fair_price, overlay_pct, market_state, execution_action):
    live = num(live_price, math.nan)
    fair = num(fair_price, math.nan)
    edge = num(overlay_pct, 0)

    if math.isnan(live) or live <= 0:
        return 0.0

    score = 0.0

    if edge >= 18:
        score += 6.0
    elif edge >= 10:
        score += 4.0
    elif edge >= 6:
        score += 2.0
    elif edge > 0:
        score += 1.0

    state = norm_upper(market_state)
    action = norm_upper(execution_action)

    if "FIRM" in state or "SHORT" in state:
        score += 2.0
    elif "STABLE" in state:
        score += 1.0

    if "EXECUTE" in action:
        score += 2.0
    elif "WATCH" in action:
        score += 1.0

    return max(0.0, min(10.0, score))


def grade(score):
    s = num(score, 0)
    if s >= 85:
        return "A+"
    if s >= 75:
        return "A"
    if s >= 65:
        return "B"
    if s >= 55:
        return "C"
    if s >= 45:
        return "D"
    return "PASS"


def score_band(score):
    s = num(score, 0)
    if s >= 90:
        return "90_PLUS"
    if s >= 80:
        return "80_89"
    if s >= 70:
        return "70_79"
    if s >= 60:
        return "60_69"
    if s >= 50:
        return "50_59"
    return "UNDER_50"


def main():
    live = read_csv(LIVE_BOARD)
    v8 = read_csv(V8_DISPLAY)
    reliability = read_csv(RELIABILITY)
    if reliability.empty:
        reliability = read_csv(RELIABILITY_FALLBACK)
    sectionals = read_csv(SECTIONALS)

    if live.empty:
        raise SystemExit("[LIVE_BET_QUALITY_V1_1] ERROR missing live board")

    for df in [live, v8, reliability, sectionals]:
        if not df.empty:
            if "horse_key" not in df.columns:
                horse_col = find_col(df, ["horse", "runner", "horse_name", "horseName"])
                if horse_col:
                    df["horse_key"] = df[horse_col].map(horse_key)

    live["horse_key"] = live["horse_key"].map(horse_key) if "horse_key" in live.columns else live.get("horse", "").map(horse_key)

    def race_key_from_row(r):
        track = first_existing(r, ["track", "meeting_name", "venue", "join_track"], "")
        race_no = first_existing(r, ["race_no", "race_number", "join_race_no"], "")
        return f"{norm_upper(track)}|{norm_upper(race_no)}"

    def horse_key_from_row(r):
        return horse_key(
            first_existing(
                r,
                ["horse", "runner", "horse_name", "horseName", "horse_key", "join_horse"],
                "",
            )
        )

    for df in [live, v8, reliability]:
        if not df.empty:
            df["_join_race_key"] = df.apply(race_key_from_row, axis=1)
            df["_join_horse_key"] = df.apply(horse_key_from_row, axis=1)

    if not sectionals.empty:
        sectionals["_join_horse_key"] = sectionals["horse_key"].map(horse_key) if "horse_key" in sectionals.columns else ""

    v8_map = {}
    if not v8.empty:
        for _, r in v8.iterrows():
            v8_map[(r.get("_join_race_key", ""), r.get("_join_horse_key", ""))] = r

    rel_map = {}
    if not reliability.empty:
        for _, r in reliability.iterrows():
            rel_map[r.get("_join_race_key", "")] = r

    sec_map = {}
    if not sectionals.empty:
        for _, r in sectionals.iterrows():
            sec_map[r.get("_join_horse_key", "")] = r

    rows = []

    for _, r in live.iterrows():
        race_key = r.get("_join_race_key", "")
        hk = r.get("_join_horse_key", "")

        v8r = v8_map.get((race_key, hk))
        relr = rel_map.get(race_key)
        secr = sec_map.get(hk)

        live_price = first_existing(
            r,
            ["live_price", "ui_price", "sportsbet_price", "market_price", "fixed_win", "tab_fixed_win"],
            "",
        )

        official_fair = first_existing(
            r,
            ["fair_price", "edgeiq_fair_price", "official_fair_price", "fair_price_replay_v1"],
            "",
        )

        v8_fair = ""
        if v8r is not None:
            v8_fair = first_existing(
                v8r,
                [
                    "v8_candidate_price_display",
                    "v8_adjusted_fair_price_v1",
                    "v8_candidate_fair_price",
                    "interaction_fair",
                ],
                "",
            )

        fair_for_score = official_fair

        live_num = num(live_price, math.nan)
        fair_num = num(fair_for_score, math.nan)

        if not math.isnan(live_num) and not math.isnan(fair_num) and fair_num > 0:
            overlay_pct = ((live_num / fair_num) - 1.0) * 100.0
        else:
            overlay_pct = num(first_existing(r, ["edge_pct", "overlay_pct", "v8_adjusted_overlay_pct_v1"], ""), 0)

        os = overlay_score(overlay_pct)
        ins = interaction_score(v8r)

        rel_source = relr if relr is not None else r
        rs = reliability_score(rel_source)

        live_sectional_weapon = num(r.get("sectional_weapon_score", ""), math.nan)
        live_late_power = num(r.get("late_power_index", ""), math.nan)
        live_projected_spd = num(r.get("projected_spd", ""), math.nan)

        if not math.isnan(live_sectional_weapon) or not math.isnan(live_late_power):
            ss = 0.0

            if not math.isnan(live_sectional_weapon):
                if live_sectional_weapon >= 85:
                    ss += 8.0
                elif live_sectional_weapon >= 75:
                    ss += 6.0
                elif live_sectional_weapon >= 65:
                    ss += 4.0
                elif live_sectional_weapon >= 55:
                    ss += 2.0

            if not math.isnan(live_late_power):
                if live_late_power >= 85:
                    ss += 5.0
                elif live_late_power >= 75:
                    ss += 4.0
                elif live_late_power >= 65:
                    ss += 3.0
                elif live_late_power >= 55:
                    ss += 2.0

            if not math.isnan(live_projected_spd):
                if 3.0 <= live_projected_spd <= 8.0:
                    ss += 2.0
                else:
                    ss += 1.0

            ss = max(0.0, min(15.0, ss))
        else:
            sec_source = secr if secr is not None else r
            ss = sectional_score(sec_source)

        ms = market_score(
            live_price,
            fair_for_score,
            overlay_pct,
            first_existing(r, ["market_state", "price_state", "firming_state"], ""),
            first_existing(r, ["execution_action", "decision", "action"], ""),
        )

        total = max(0.0, min(100.0, os + ins + rs + ss + ms))
        g = grade(total)
        band = score_band(total)

        brc_match = ""
        v8_badge = ""
        v8_status = ""
        v8_delta = ""
        if v8r is not None:
            brc_match = first_existing(v8r, ["brc_match_level_v8"], "")
            v8_badge = first_existing(v8r, ["v8_candidate_badge"], "")
            v8_status = first_existing(v8r, ["v8_candidate_display_status"], "")
            v8_delta = first_existing(v8r, ["v8_delta_display", "v8_adjusted_fair_price_delta_v1"], "")

        out = r.to_dict()

        out.update({
            "bet_quality_score_v1_1": safe_round(total, 2),
            "bet_quality_grade_v1_1": g,
            "bet_quality_score_band_v1_1": band,
            "bet_quality_status_v1_1": "OBSERVATION_ONLY",
            "overlay_score_v1_1": safe_round(os, 2),
            "interaction_score_component_v1_1": safe_round(ins, 2),
            "reliability_score_component_v1_1": safe_round(rs, 2),
            "sectional_score_component_v1_1": safe_round(ss, 2),
            "market_score_component_v1_1": safe_round(ms, 2),
            "bet_quality_overlay_pct_v1_1": safe_round(overlay_pct, 4),
            "bet_quality_positive_overlay_flag_v1_1": str(overlay_pct > 0),
            "bet_quality_fair_price_used_v1_1": safe_round(fair_num, 4),
            "bet_quality_live_price_used_v1_1": safe_round(live_num, 4),
            "v8_candidate_price_display": v8_fair,
            "v8_delta_display": v8_delta,
            "v8_candidate_badge": v8_badge,
            "brc_match_level_v8": brc_match,
            "v8_candidate_display_status": v8_status,
            "official_fair_price_replaced": "NO",
            "edge_execution_staking_changed": "NO",
        })

        rows.append(out)

    out_df = pd.DataFrame(rows)

    drop_cols = [c for c in out_df.columns if c.startswith("_join_")]
    out_df = out_df.drop(columns=drop_cols, errors="ignore")

    out_df.to_csv(OUT_CSV, index=False)

    summary = {
        "status": "COMPLETE",
        "rows": int(len(out_df)),
        "scored_rows": int((pd.to_numeric(out_df["bet_quality_score_v1_1"], errors="coerce") > 0).sum()),
        "a_plus_rows": int((out_df["bet_quality_grade_v1_1"] == "A+").sum()),
        "a_rows": int((out_df["bet_quality_grade_v1_1"] == "A").sum()),
        "b_rows": int((out_df["bet_quality_grade_v1_1"] == "B").sum()),
        "c_rows": int((out_df["bet_quality_grade_v1_1"] == "C").sum()),
        "d_rows": int((out_df["bet_quality_grade_v1_1"] == "D").sum()),
        "pass_rows": int((out_df["bet_quality_grade_v1_1"] == "PASS").sum()),
        "v8_matched_rows": int((out_df["v8_candidate_price_display"].astype(str).str.strip() != "").sum()),
        "avg_bet_quality_score": safe_round(pd.to_numeric(out_df["bet_quality_score_v1_1"], errors="coerce").mean(), 4),
        "max_bet_quality_score": safe_round(pd.to_numeric(out_df["bet_quality_score_v1_1"], errors="coerce").max(), 4),
        "official_fair_price_replaced": "NO",
        "edge_execution_staking_changed": "NO",
        "verdict": "LIVE_BET_QUALITY_V1_1_BUILT_OBSERVATION_ONLY",
    }

    pd.DataFrame([{"metric": k, "value": v} for k, v in summary.items()]).to_csv(OUT_SUMMARY, index=False)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("[LIVE_BET_QUALITY_V1_1] COMPLETE")
    for k, v in summary.items():
        print(f"{k}={v}")
    print(f"wrote={OUT_CSV}")
    print(f"summary={OUT_SUMMARY}")
    print(f"json={OUT_JSON}")


if __name__ == "__main__":
    main()




