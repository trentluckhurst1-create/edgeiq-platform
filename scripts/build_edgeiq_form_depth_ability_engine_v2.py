from pathlib import Path
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_execution_board_live.csv"
TERMINAL = DATA / "edgeiq_execution_board_terminal.csv"
FORM_SUMMARY = DATA / "form_card_summary.csv"
FORM_RUNS = DATA / "form_card_runs.csv"
RACE_FIELDS = DATA / "race_fields.csv"
UNCERTAINTY = DATA / "edgeiq_uncertainty_engine_v1.csv"
FIRST_STARTER = DATA / "edgeiq_first_starter_engine_v1.csv"
TRAINER_JOCKEY = DATA / "edgeiq_trainer_jockey_intelligence_v1.csv"
ADAPTIVE_POLICY = DATA / "edgeiq_self_adaptive_policy_v2.csv"

OUT = DATA / "edgeiq_form_depth_ability_v2.csv"
DIAGNOSTICS = DATA / "edgeiq_form_depth_ability_diagnostics_v2.csv"

OUTPUT_COLUMNS = [
    "track",
    "race_no",
    "horse",
    "official_run_count",
    "total_form_runs",
    "recent_official_runs",
    "last3_rating_avg",
    "last5_rating_avg",
    "peak_rating",
    "rating_consistency_score",
    "exposed_ability_score",
    "form_depth_grade",
    "ability_confidence_grade",
    "distance_suitability_score",
    "class_suitability_score",
    "track_condition_suitability_score",
    "speed_map_suitability_score",
    "form_depth_reason",
    "form_depth_probability_adjustment",
    "form_depth_stake_adjustment",
]


def canonical(value):
    text = str(value or "").upper()
    text = re.sub(r"\(NZ\)|\(AUS\)|\(GB\)|\(IRE\)", "", text)
    return re.sub(r"[^A-Z0-9]", "", text).strip()


def track_key(value):
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def race_key(value):
    text = str(value or "").strip()
    if text.endswith(".0"):
        text = text[:-2]
    digits = re.sub(r"[^0-9]", "", text)
    return digits or text


def clean(value):
    return str(value or "").strip().upper()


def as_num(value, default=0.0):
    try:
        parsed = pd.to_numeric(value, errors="coerce")
        if pd.isna(parsed):
            return default
        return float(parsed)
    except Exception:
        return default


def read_csv(path):
    if not path.exists():
        print(f"[form_depth_v2] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"[form_depth_v2] read {path.name}: {len(df)} rows")
        return df
    except Exception as exc:
        print(f"[form_depth_v2] failed {path.name}: {exc}")
        return pd.DataFrame()


def add_runner_keys(df):
    if df.empty:
        return df
    out = df.copy()
    out["_horse_key"] = out.get("horse", "").map(canonical) if "horse" in out.columns else ""
    out["_track_key"] = out.get("track", "").map(track_key) if "track" in out.columns else ""
    if "race_no" in out.columns:
        out["_race_key"] = out["race_no"].map(race_key)
    elif "race_number" in out.columns:
        out["_race_key"] = out["race_number"].map(race_key)
    else:
        out["_race_key"] = ""
    return out


def merge_by_runner(base, extra, columns, prefix):
    if base.empty or extra.empty:
        return base
    extra = add_runner_keys(extra)
    keys = ["_horse_key", "_track_key", "_race_key"]
    available = [col for col in columns if col in extra.columns]
    if not available or not set(keys).issubset(extra.columns):
        return base
    right = extra[keys + available].drop_duplicates(keys, keep="last")
    right = right.rename(columns={col: f"{prefix}_{col}" for col in available})
    return base.merge(right, on=keys, how="left")


def prepare_summary(summary):
    if summary.empty:
        return pd.DataFrame()
    out = add_runner_keys(summary)
    renames = {
        "1LS": "summary_1ls",
        "2LS": "summary_2ls",
        "3LS": "summary_3ls",
        "4LS": "summary_4ls",
        "5LS": "summary_5ls",
        "3LSA": "summary_3lsa",
        "5LSA": "summary_5lsa",
        "PEAK": "summary_peak",
        "official_run_count": "summary_official_run_count",
    }
    out = out.rename(columns={k: v for k, v in renames.items() if k in out.columns})
    keep = ["_horse_key", "_track_key", "_race_key"] + [v for v in renames.values() if v in out.columns]
    return out[keep].drop_duplicates(["_horse_key", "_track_key", "_race_key"], keep="last")


def prepare_runs(runs):
    if runs.empty:
        return runs
    out = runs.copy()
    out["_horse_key"] = out.get("horse", "").map(canonical) if "horse" in out.columns else ""
    official = out.get("is_official_race", True)
    if isinstance(official, bool):
        out["_is_official"] = official
    else:
        out["_is_official"] = official.astype(str).str.upper().isin({"TRUE", "1", "YES"})
    out["_rating"] = pd.to_numeric(out.get("run_rating", out.get("rating", "")), errors="coerce")
    out["_distance"] = pd.to_numeric(out.get("distance", "").astype(str).str.extract(r"(\d+)")[0], errors="coerce") if "distance" in out.columns else pd.NA
    out["_date"] = pd.to_datetime(out.get("run_date", out.get("date", "")), errors="coerce")
    return out.sort_values("_date", ascending=False)


def runner_runs(prepared_runs, horse_key):
    if prepared_runs.empty or not horse_key:
        return pd.DataFrame()
    return prepared_runs[prepared_runs["_horse_key"].eq(horse_key)].copy()


def official_count(row):
    candidates = [
        row.get("official_run_count"),
        row.get("summary_official_run_count"),
        row.get("official_run_count_v5"),
        row.get("summary_official_run_count"),
    ]
    for value in candidates:
        parsed = as_num(value, -1)
        if parsed >= 0:
            return int(parsed)
    return 0


def rating_values(row, runs_for_horse):
    official = runs_for_horse[runs_for_horse["_is_official"].eq(True)].copy() if not runs_for_horse.empty else pd.DataFrame()
    ratings = official["_rating"].dropna().astype(float).tolist() if not official.empty else []
    last3 = as_num(row.get("last3_flat_avg"), 0) or as_num(row.get("summary_3lsa"), 0)
    last5 = as_num(row.get("last5_flat_avg"), 0) or as_num(row.get("summary_5lsa"), 0)
    peak = as_num(row.get("peak_rating"), 0) or as_num(row.get("summary_peak"), 0)
    if not last3 and ratings:
        last3 = sum(ratings[:3]) / min(3, len(ratings))
    if not last5 and ratings:
        last5 = sum(ratings[:5]) / min(5, len(ratings))
    if not peak and ratings:
        peak = max(ratings)
    recent = ratings[:5]
    consistency = 0.0
    if len(recent) >= 2:
        spread = pd.Series(recent).std()
        consistency = max(0.0, min(100.0, 100.0 - spread * 4.0))
    elif len(recent) == 1:
        consistency = 45.0
    return last3, last5, peak, consistency, len(official), len(runs_for_horse)


def suitability_scores(row, runs_for_horse):
    distance_now = as_num(row.get("distance"), 0)
    official = runs_for_horse[runs_for_horse["_is_official"].eq(True)].copy() if not runs_for_horse.empty else pd.DataFrame()
    distance_score = 50.0
    class_score = 50.0
    condition_score = 50.0
    speed_score = 50.0

    if not official.empty and distance_now:
        distances = official["_distance"].dropna()
        if len(distances):
            avg_distance = float(distances.head(5).mean())
            gap = abs(distance_now - avg_distance)
            distance_score = max(20.0, min(80.0, 75.0 - gap / 20.0))

    race_class = clean(row.get("race_class") or row.get("race_class_clean"))
    if race_class and not official.empty and "race_class" in official.columns:
        class_matches = official["race_class"].astype(str).map(clean).eq(race_class).sum()
        class_score = min(80.0, 45.0 + class_matches * 8.0)

    condition = clean(row.get("track_condition"))
    if condition and not official.empty and "track_condition" in official.columns:
        cond_base = re.sub(r"[^A-Z]", "", condition)
        matches = official["track_condition"].astype(str).map(lambda v: re.sub(r"[^A-Z]", "", clean(v))).eq(cond_base).sum()
        condition_score = min(80.0, 45.0 + matches * 7.0)

    speed_bucket = clean(row.get("speed_map_bucket"))
    if speed_bucket:
        if speed_bucket in {"LEADER", "ONPACE", "ON_PACE", "MAP_ADVANTAGE"}:
            speed_score = 62.0
        elif speed_bucket in {"FIRST START", "UNKNOWN", "BACKMARKER"}:
            speed_score = 45.0

    return distance_score, class_score, condition_score, speed_score


def grade_and_adjust(row, last3, last5, peak, consistency, official_runs, total_runs, suitability):
    uncertainty = clean(row.get("uncertainty_band") or row.get("uncertainty_uncertainty_band"))
    first_flag = clean(row.get("first_starter_engine_flag") or row.get("first_first_starter_engine_flag")) == "TRUE"
    no_form = clean(row.get("no_official_form_engine_flag") or row.get("first_no_official_form_engine_flag")) == "TRUE"
    lightly = clean(row.get("lightly_raced_engine_flag") or row.get("first_lightly_raced_engine_flag")) == "TRUE"

    reasons = []
    if no_form or first_flag or official_runs <= 0:
        grade = "NO_OFFICIAL_FORM"
        confidence = "LOW"
        ability = 0.0
        adjustment = 0.0
        stake = 1.0
        reasons.append("no official exposed race evidence")
        return grade, confidence, ability, adjustment, stake, " | ".join(reasons)

    recent_base = last3 or last5 or 0
    peak_gap = max(0.0, peak - recent_base) if peak and recent_base else 0.0
    suitability_avg = sum(suitability) / len(suitability)
    ability = 0.0
    if recent_base:
        ability += (recent_base - 60.0) * 1.2
        reasons.append(f"recent rating {recent_base:.1f}")
    if last3 and last5:
        trend = last3 - last5
        ability += max(-8.0, min(8.0, trend * 0.8))
        reasons.append(f"last3-last5 {trend:.1f}")
    if peak_gap > 12:
        ability -= 4.0
        reasons.append("peak materially above recent form")
    elif peak and recent_base and peak_gap <= 6:
        ability += 2.0
    ability += (consistency - 50.0) * 0.08
    ability += (suitability_avg - 50.0) * 0.08

    if official_runs >= 5 and consistency >= 65 and recent_base >= 68:
        grade = "STRONG_EXPOSED_FORM"
        confidence = "HIGH"
    elif official_runs >= 4 and recent_base >= 62:
        grade = "SOLID_EXPOSED_FORM"
        confidence = "MEDIUM"
    elif official_runs <= 3 or lightly:
        grade = "LIGHTLY_RACED"
        confidence = "LOW"
    elif recent_base and recent_base < 55:
        grade = "WEAK_RECENT_FORM"
        confidence = "MEDIUM"
    else:
        grade = "MIXED_EXPOSED_FORM"
        confidence = "MEDIUM"

    adjustment = max(-0.075, min(0.075, ability / 1000.0))
    if lightly and adjustment > 0.025:
        adjustment = 0.025
        reasons.append("lightly raced cap")
    if uncertainty == "EXTREME" and adjustment > 0.01:
        adjustment = 0.01
        reasons.append("EXTREME uncertainty positive cap")
    if consistency < 45 and adjustment > 0:
        adjustment *= 0.4
        reasons.append("poor consistency dampened positive signal")

    if adjustment >= 0.035:
        stake = 1.05
    elif adjustment <= -0.035:
        stake = 0.90
    elif adjustment <= -0.01:
        stake = 0.96
    else:
        stake = 1.0
    if uncertainty == "EXTREME":
        stake = min(stake, 1.0)

    return grade, confidence, round(ability, 2), round(adjustment, 4), round(stake, 4), " | ".join(reasons[:6]) or "neutral exposed form profile"


def build_rows(live, summary, runs):
    rows = []
    summary = prepare_summary(summary)
    base = add_runner_keys(live)
    if not summary.empty:
        base = base.merge(summary, on=["_horse_key", "_track_key", "_race_key"], how="left", suffixes=("", "_summary"))
    prepared_runs = prepare_runs(runs)

    for _, row in base.iterrows():
        r_runs = runner_runs(prepared_runs, row.get("_horse_key", ""))
        last3, last5, peak, consistency, recent_official, total_runs = rating_values(row, r_runs)
        official_runs = official_count(row) or recent_official
        suitability = suitability_scores(row, r_runs)
        grade, confidence, ability, adjustment, stake, reason = grade_and_adjust(
            row, last3, last5, peak, consistency, official_runs, total_runs, suitability
        )
        rows.append({
            "track": row.get("track", ""),
            "race_no": row.get("race_no", ""),
            "horse": row.get("horse", ""),
            "official_run_count": int(official_runs),
            "total_form_runs": int(total_runs),
            "recent_official_runs": int(recent_official),
            "last3_rating_avg": round(last3, 2) if last3 else "",
            "last5_rating_avg": round(last5, 2) if last5 else "",
            "peak_rating": round(peak, 2) if peak else "",
            "rating_consistency_score": round(consistency, 2) if consistency else "",
            "exposed_ability_score": ability,
            "form_depth_grade": grade,
            "ability_confidence_grade": confidence,
            "distance_suitability_score": round(suitability[0], 2),
            "class_suitability_score": round(suitability[1], 2),
            "track_condition_suitability_score": round(suitability[2], 2),
            "speed_map_suitability_score": round(suitability[3], 2),
            "form_depth_reason": reason,
            "form_depth_probability_adjustment": adjustment,
            "form_depth_stake_adjustment": stake,
        })
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def patch_board(path, rows):
    board = read_csv(path)
    if board.empty or rows.empty:
        return 0
    board = add_runner_keys(board)
    keyed = add_runner_keys(rows)
    patch_cols = [c for c in OUTPUT_COLUMNS if c not in {"track", "race_no", "horse"}]
    patch = keyed[["_horse_key", "_track_key", "_race_key"] + patch_cols].drop_duplicates(["_horse_key", "_track_key", "_race_key"], keep="last")
    merged = board.merge(patch, on=["_horse_key", "_track_key", "_race_key"], how="left", suffixes=("", "_form_depth_new"))
    for col in patch_cols:
        extra = f"{col}_form_depth_new"
        if extra in merged.columns:
            current = merged[col].map(lambda v: str(v).strip()) if col in merged.columns else pd.Series([""] * len(merged), index=merged.index)
            merged[col] = merged[col].where(current != "", merged[extra]) if col in merged.columns else merged[extra]
            merged = merged.drop(columns=[extra])
    merged = merged.drop(columns=["_horse_key", "_track_key", "_race_key"], errors="ignore")
    merged.to_csv(path, index=False)
    return len(merged)


def diagnostics(rows):
    if rows.empty:
        return pd.DataFrame([{"diagnostic_type": "OVERALL", "rows": 0, "value": "", "reason": "No live rows available"}])
    dist = rows["form_depth_grade"].value_counts().to_dict()
    exposed = int(rows["official_run_count"].gt(0).sum())
    high_conf = int(rows["ability_confidence_grade"].eq("HIGH").sum())
    low_no_form = int(rows["form_depth_grade"].isin(["NO_OFFICIAL_FORM", "LIGHTLY_RACED"]).sum())
    avg_adj = rows["form_depth_probability_adjustment"].map(lambda v: as_num(v, 0)).mean()
    strongest = rows.sort_values("exposed_ability_score", ascending=False).head(1)
    weakest = rows.sort_values("exposed_ability_score", ascending=True).head(1)

    def row_value(df, cols):
        if df.empty:
            return ""
        row = df.iloc[0]
        return " | ".join(str(row.get(col, "")) for col in cols)

    return pd.DataFrame([
        {"diagnostic_type": "OVERALL", "rows": len(rows), "value": len(rows), "reason": "Form depth rows processed"},
        {"diagnostic_type": "FORM_DEPTH_DISTRIBUTION", "rows": len(rows), "value": ";".join(f"{k}:{v}" for k, v in dist.items()), "reason": "Live form depth grade distribution"},
        {"diagnostic_type": "EXPOSED_ABILITY_COVERAGE", "rows": exposed, "value": f"{exposed}/{len(rows)}", "reason": "Rows with official exposed form"},
        {"diagnostic_type": "AVERAGE_ADJUSTMENT", "rows": len(rows), "value": f"{avg_adj:.4f}", "reason": "Average capped probability adjustment"},
        {"diagnostic_type": "HIGH_CONFIDENCE_EXPOSED_RUNNERS", "rows": high_conf, "value": high_conf, "reason": "High-confidence exposed form runners"},
        {"diagnostic_type": "LOW_CONFIDENCE_NO_FORM_RUNNERS", "rows": low_no_form, "value": low_no_form, "reason": "No-form/lightly-raced runners"},
        {"diagnostic_type": "STRONGEST_EXPOSED_ABILITY", "rows": 1 if len(strongest) else 0, "value": row_value(strongest, ["horse", "form_depth_grade", "exposed_ability_score"]), "reason": row_value(strongest, ["form_depth_reason"])},
        {"diagnostic_type": "WEAKEST_EXPOSED_ABILITY", "rows": 1 if len(weakest) else 0, "value": row_value(weakest, ["horse", "form_depth_grade", "exposed_ability_score"]), "reason": row_value(weakest, ["form_depth_reason"])},
    ])


def main():
    print("=" * 100)
    print("EDGEIQ FORM DEPTH / ABILITY ENGINE V2")
    print("=" * 100)
    live = read_csv(LIVE)
    if live.empty:
        pd.DataFrame(columns=OUTPUT_COLUMNS).to_csv(OUT, index=False)
        diagnostics(pd.DataFrame(columns=OUTPUT_COLUMNS)).to_csv(DIAGNOSTICS, index=False)
        print("[form_depth_v2] rows processed: 0")
        return

    base = add_runner_keys(live)
    base = merge_by_runner(base, read_csv(UNCERTAINTY), ["uncertainty_band"], "uncertainty")
    base = merge_by_runner(base, read_csv(FIRST_STARTER), ["first_starter_engine_flag", "lightly_raced_engine_flag", "no_official_form_engine_flag", "debut_risk_grade"], "first")
    base = merge_by_runner(base, read_csv(TRAINER_JOCKEY), ["trainer_jockey_signal_grade", "trainer_jockey_probability_adjustment"], "tj")
    base = merge_by_runner(base, read_csv(ADAPTIVE_POLICY), ["adaptive_policy_v2", "adaptive_execution_permission"], "adaptive")

    read_csv(RACE_FIELDS)
    rows = build_rows(base, read_csv(FORM_SUMMARY), read_csv(FORM_RUNS))
    rows.to_csv(OUT, index=False)
    diagnostics(rows).to_csv(DIAGNOSTICS, index=False)

    live_rows = patch_board(LIVE, rows)
    terminal_rows = patch_board(TERMINAL, rows)
    dist = rows["form_depth_grade"].value_counts().to_dict()
    exposed = int(rows["official_run_count"].gt(0).sum())
    high_conf = int(rows["ability_confidence_grade"].eq("HIGH").sum())
    avg_adj = rows["form_depth_probability_adjustment"].mean()

    print(f"[form_depth_v2] rows processed: {len(rows)}")
    print(f"[form_depth_v2] live board rows patched: {live_rows}")
    print(f"[form_depth_v2] terminal rows patched: {terminal_rows}")
    print(f"[form_depth_v2] form depth distribution: {dist}")
    print(f"[form_depth_v2] exposed ability coverage: {exposed}/{len(rows)}")
    print(f"[form_depth_v2] high-confidence exposed runners: {high_conf}")
    print(f"[form_depth_v2] average adjustment: {avg_adj:.4f}")
    print(f"[form_depth_v2] wrote {OUT}")
    print(f"[form_depth_v2] wrote {DIAGNOSTICS}")
    print("=" * 100)


if __name__ == "__main__":
    main()
