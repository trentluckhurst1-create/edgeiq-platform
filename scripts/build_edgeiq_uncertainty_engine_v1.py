from pathlib import Path
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_execution_board_live.csv"
TERMINAL = DATA / "edgeiq_execution_board_terminal.csv"
RESULTS = DATA / "edgeiq_results_master.csv"
PROBABILITY = DATA / "edgeiq_probability_engine_v2.csv"
BAYESIAN = DATA / "edgeiq_bayesian_blending_v1.csv"
ENVIRONMENT = DATA / "edgeiq_environment_classification_v1.csv"
MICROSTRUCTURE = DATA / "edgeiq_market_microstructure_v1.csv"
TIMING = DATA / "edgeiq_temporal_execution_intelligence_v1.csv"
FORM_SUMMARY = DATA / "form_card_summary.csv"
FORM_RUNS = DATA / "form_card_runs.csv"
RACE_FIELDS = DATA / "race_fields.csv"

OUT = DATA / "edgeiq_uncertainty_engine_v1.csv"
DIAGNOSTICS = DATA / "edgeiq_uncertainty_diagnostics_v1.csv"


OUTPUT_COLUMNS = [
    "track",
    "race_no",
    "horse",
    "uncertainty_score",
    "uncertainty_band",
    "uncertainty_reason",
    "sample_depth_score",
    "exposed_form_score",
    "lightly_raced_flag",
    "first_starter_flag",
    "no_official_runs_flag",
    "recent_form_stability",
    "price_variance_risk",
    "environment_uncertainty_penalty",
    "microstructure_uncertainty_penalty",
    "timing_uncertainty_penalty",
    "recommended_probability_shrinkage",
    "recommended_stake_multiplier",
    "uncertainty_adjusted_probability",
    "uncertainty_adjusted_fair_price",
    "uncertainty_adjusted_overlay_pct",
    "uncertainty_original_execution_action",
    "uncertainty_adjusted_execution_action",
    "uncertainty_applied",
    "uncertainty_protected_edge_flag",
]


def canonical(value):
    text = str(value or "").upper()
    text = re.sub(r"\(NZ\)|\(AUS\)|\(GB\)|\(IRE\)", "", text)
    text = re.sub(r"[^A-Z0-9]", "", text)
    return text.strip()


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


def as_num(value, default=None):
    try:
        parsed = pd.to_numeric(value, errors="coerce")
        if pd.isna(parsed):
            return default
        return float(parsed)
    except Exception:
        return default


def read_csv(path):
    if not path.exists():
        print(f"[uncertainty] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
        print(f"[uncertainty] read {path.name}: {len(df)} rows")
        return df
    except Exception as exc:
        print(f"[uncertainty] failed {path.name}: {exc}")
        return pd.DataFrame()


def add_keys(df):
    if df.empty:
        return df
    out = df.copy()
    out["_horse_key"] = out.get("horse", "").map(canonical) if "horse" in out.columns else ""
    out["_track_key"] = out.get("track", "").map(track_key) if "track" in out.columns else ""
    out["_race_key"] = out.get("race_no", out.get("race_number", "")).map(race_key) if any(c in out.columns for c in ["race_no", "race_number"]) else ""
    return out


def merge_by_runner(base, other, columns, prefix):
    if base.empty or other.empty:
        return base

    other = add_keys(other)
    keys = ["_horse_key", "_track_key", "_race_key"]
    if not set(keys).issubset(other.columns):
        return base

    available = [c for c in columns if c in other.columns]
    if not available:
        return base

    lookup = other[keys + available].drop_duplicates(keys, keep="last")
    rename = {c: f"{prefix}_{c}" for c in available}
    return base.merge(lookup.rename(columns=rename), on=keys, how="left")


def merge_form_summary(base, summary):
    if base.empty or summary.empty:
        return base

    summary = add_keys(summary)
    available = [c for c in ["official_run_count", "1LS", "2LS", "3LS", "4LS", "5LS", "3LSA", "5LSA", "PEAK", "gap"] if c in summary.columns]
    if not available:
        return base

    horse_lookup = summary[["_horse_key"] + available].drop_duplicates(["_horse_key"], keep="last")
    return base.merge(horse_lookup.rename(columns={c: f"summary_{c}" for c in available}), on="_horse_key", how="left")


def form_runs_depth(runs):
    if runs.empty or "horse" not in runs.columns:
        return pd.DataFrame(columns=["_horse_key", "form_runs_count", "form_recent_rating_std"])

    runs = runs.copy()
    runs["_horse_key"] = runs["horse"].map(canonical)
    rating_col = next((c for c in ["run_rating", "rating"] if c in runs.columns), None)
    official = runs
    if "is_official_race" in official.columns:
        official = official[official["is_official_race"].astype(str).str.upper().isin(["TRUE", "1", "YES"])]

    grouped = official.groupby("_horse_key", dropna=False)
    counts = grouped.size().rename("form_runs_count")
    if rating_col:
        std = grouped[rating_col].apply(lambda s: pd.to_numeric(s, errors="coerce").tail(5).std()).rename("form_recent_rating_std")
    else:
        std = pd.Series(dtype=float, name="form_recent_rating_std")

    return pd.concat([counts, std], axis=1).reset_index()


def get_first(row, names, default=None):
    for name in names:
        if name in row.index:
            value = row.get(name)
            if pd.notna(value) and str(value).strip() != "":
                return value
    return default


def sample_depth_score(row):
    official = as_num(get_first(row, [
        "official_run_count",
        "summary_official_run_count",
        "summary_official_run_count_x",
        "summary_official_run_count_y",
        "form_runs_count",
    ]), None)
    if official is None:
        return 0
    if official <= 0:
        return 0
    if official == 1:
        return 20
    if official == 2:
        return 35
    if official <= 4:
        return 55
    if official <= 8:
        return 75
    return 90


def exposed_form_score(row):
    latest = as_num(get_first(row, ["latest_flat_rating", "summary_1LS", "summary_1LS_x", "summary_1LS_y"]), None)
    last3 = as_num(get_first(row, ["last3_flat_avg", "summary_3LSA", "summary_3LSA_x", "summary_3LSA_y"]), None)
    last5 = as_num(get_first(row, ["last5_flat_avg", "summary_5LSA", "summary_5LSA_x", "summary_5LSA_y"]), None)
    peak = as_num(get_first(row, ["peak_rating", "summary_PEAK", "summary_PEAK_x", "summary_PEAK_y"]), None)
    values = [v for v in [latest, last3, last5, peak] if v is not None]
    if len(values) >= 3:
        return 85
    if len(values) == 2:
        return 70
    if len(values) == 1:
        return 45
    return 10


def recent_stability(row):
    explicit_std = as_num(row.get("form_recent_rating_std"), None)
    if explicit_std is not None:
        if explicit_std <= 3:
            return 85
        if explicit_std <= 7:
            return 65
        if explicit_std <= 12:
            return 45
        return 25

    last3 = as_num(get_first(row, ["last3_flat_avg", "summary_3LSA", "summary_3LSA_x", "summary_3LSA_y"]), None)
    last5 = as_num(get_first(row, ["last5_flat_avg", "summary_5LSA", "summary_5LSA_x", "summary_5LSA_y"]), None)
    if last3 is not None and last5 is not None:
        gap = abs(last3 - last5)
        if gap <= 3:
            return 80
        if gap <= 7:
            return 60
        if gap <= 12:
            return 40
        return 25
    return 20


def price_variance_risk(row):
    velocity = as_num(row.get("movement_velocity"), 0)
    stability = as_num(row.get("movement_stability"), 50)
    fluctuations = str(row.get("recent_odds_fluctuations", "") or "")
    risk = 0
    if velocity >= 5:
        risk += 25
    elif velocity >= 2:
        risk += 15
    if stability <= 20:
        risk += 25
    elif stability <= 45:
        risk += 12
    if fluctuations.count(",") >= 5:
        risk += 10
    return min(risk, 40)


def protected_edge(row):
    return (
        clean(row.get("environment_type")) == "PROTECTED_EDGE"
        or "PROTECT" in clean(row.get("matched_interaction_recommendation"))
        or "PROTECT" in clean(row.get("blending_reason"))
        or clean(row.get("overlay_realism_grade")) == "REALISTIC"
    )


def classify_band(score):
    if score >= 80:
        return "EXTREME"
    if score >= 60:
        return "HIGH"
    if score >= 35:
        return "MEDIUM"
    return "LOW"


def adjusted_action(original, band, is_protected):
    original = clean(original)
    if band == "EXTREME":
        if original in {"MAX_BET", "PRIORITY_EXECUTE", "EXECUTE", "REDUCED_EXECUTE"} and not is_protected:
            return "SUPPRESS"
        if original in {"MAX_BET", "PRIORITY_EXECUTE"} and is_protected:
            return "WATCH"
    if band == "HIGH":
        if original in {"MAX_BET", "PRIORITY_EXECUTE"}:
            return "EXECUTE"
        if original == "EXECUTE" and not is_protected:
            return "REDUCED_EXECUTE"
    return original


def compute_row(row):
    reasons = []
    sample = sample_depth_score(row)
    exposed = exposed_form_score(row)
    stability = recent_stability(row)

    official_runs = as_num(get_first(row, [
        "official_run_count",
        "summary_official_run_count",
        "form_runs_count",
    ]), None)

    speed_bucket = clean(row.get("speed_map_bucket"))
    risk_flags = clean(row.get("risk_flags"))
    rating_notes = clean(row.get("rating_notes"))
    first = "FIRST" in speed_bucket or "FIRST START" in rating_notes
    no_runs = official_runs is None or official_runs <= 0 or "NO_OFFICIAL_FORM" in risk_flags
    lightly = official_runs is not None and 0 < official_runs <= 3

    score = 100 - (sample * 0.35) - (exposed * 0.25) - (stability * 0.15)

    if first:
        score += 28
        reasons.append("first starter profile")
    if no_runs:
        score += 35
        reasons.append("no official race-run sample")
    elif lightly:
        score += 18
        reasons.append("lightly raced sample")

    variance = price_variance_risk(row)
    score += variance
    if variance >= 20:
        reasons.append("price variance/tape instability")

    env = clean(row.get("environment_type"))
    env_penalty = 0
    if env in {"CHAOTIC", "PUBLIC_TRAP", "VOLATILE"}:
        env_penalty = 18
        reasons.append(f"{env} environment")
    elif env == "PROTECTED_EDGE":
        env_penalty = -8
        reasons.append("protected-edge environment")
    score += env_penalty

    micro = clean(row.get("microstructure_type"))
    micro_penalty = 0
    if micro in {"VOLATILITY_CLUSTER", "FALSE_STEAM", "PUBLIC_STEAM", "PANIC_DRIFT"}:
        micro_penalty = 16
        reasons.append(f"{micro} microstructure")
    elif micro in {"CONTROLLED_FIRMING", "SHARP_STEAM"}:
        micro_penalty = -6
        reasons.append(f"{micro} confirmation")
    score += micro_penalty

    timing = clean(row.get("timing_environment"))
    transition = clean(row.get("transition_type"))
    timing_penalty = 0
    if timing in {"TRAP_WINDOW", "CHAOTIC_LATE", "PUBLIC_OVERREACTION"}:
        timing_penalty += 14
        reasons.append(f"{timing} timing")
    if transition == "EXECUTE_WINDOW_TO_AVOID":
        timing_penalty += 18
        reasons.append("execution window deteriorating")
    score += timing_penalty

    is_protected = protected_edge(row)
    if is_protected:
        score -= 8

    score = max(0, min(100, round(score, 2)))
    band = classify_band(score)
    if (first or no_runs) and band in {"LOW", "MEDIUM"}:
        band = "HIGH"
    if no_runs and score >= 75:
        band = "EXTREME"

    if band == "EXTREME":
        shrink = 0.55
        stake = 0.25
    elif band == "HIGH":
        shrink = 0.72
        stake = 0.5
    elif band == "MEDIUM":
        shrink = 0.88
        stake = 0.75
    else:
        shrink = 1.0
        stake = 1.0

    if is_protected and band != "LOW":
        shrink = min(1.0, shrink + 0.08)
        if band != "EXTREME":
            stake = min(1.0, stake + 0.1)

    raw_probability = as_num(get_first(row, ["v2_probability", "blended_probability", "shrunk_probability", "raw_model_probability", "rated_probability"]), None)
    market_price = as_num(get_first(row, ["sportsbet_price", "market_price", "current_price"]), None)
    adjusted_probability = None if raw_probability is None else max(0.0025, min(0.75, raw_probability * shrink))
    adjusted_fair = None if not adjusted_probability else round(1 / adjusted_probability, 4)
    adjusted_overlay = None
    if market_price and adjusted_fair:
        adjusted_overlay = round(((market_price / adjusted_fair) - 1) * 100, 2)

    original = clean(get_first(row, ["execution_action", "final_execution_state", "post_v2_execution_action"], "PASS"))
    final = adjusted_action(original, band, is_protected)
    applied = final != original

    if not reasons:
        reasons.append("sufficient exposed form and stable market context")

    return {
        "track": row.get("track", ""),
        "race_no": row.get("race_no", ""),
        "horse": row.get("horse", ""),
        "uncertainty_score": score,
        "uncertainty_band": band,
        "uncertainty_reason": " | ".join(reasons[:6]),
        "sample_depth_score": round(sample, 2),
        "exposed_form_score": round(exposed, 2),
        "lightly_raced_flag": str(bool(lightly)).upper(),
        "first_starter_flag": str(bool(first)).upper(),
        "no_official_runs_flag": str(bool(no_runs)).upper(),
        "recent_form_stability": round(stability, 2),
        "price_variance_risk": round(variance, 2),
        "environment_uncertainty_penalty": round(env_penalty, 2),
        "microstructure_uncertainty_penalty": round(micro_penalty, 2),
        "timing_uncertainty_penalty": round(timing_penalty, 2),
        "recommended_probability_shrinkage": round(shrink, 4),
        "recommended_stake_multiplier": round(stake, 4),
        "uncertainty_adjusted_probability": round(adjusted_probability, 6) if adjusted_probability is not None else "",
        "uncertainty_adjusted_fair_price": adjusted_fair if adjusted_fair is not None else "",
        "uncertainty_adjusted_overlay_pct": adjusted_overlay if adjusted_overlay is not None else "",
        "uncertainty_original_execution_action": original,
        "uncertainty_adjusted_execution_action": final,
        "uncertainty_applied": str(applied).upper(),
        "uncertainty_protected_edge_flag": str(bool(is_protected)).upper(),
    }


def patch_board(path, uncertainty):
    board = read_csv(path)
    if board.empty or uncertainty.empty:
        return 0, 0

    board = add_keys(board)
    uncertainty = add_keys(uncertainty)
    patch_cols = [c for c in OUTPUT_COLUMNS if c not in {"track", "race_no", "horse", "recommended_stake_multiplier"}]
    patch = uncertainty[["_horse_key", "_track_key", "_race_key", "recommended_stake_multiplier"] + patch_cols].copy()
    patch = patch.rename(columns={"recommended_stake_multiplier": "uncertainty_recommended_stake_multiplier"})
    patch = patch.drop_duplicates(["_horse_key", "_track_key", "_race_key"], keep="last")

    original_cols = set(board.columns)
    merged = board.merge(patch, on=["_horse_key", "_track_key", "_race_key"], how="left", suffixes=("", "_uncertainty_new"))

    for col in patch.columns:
        if col.startswith("_"):
            continue
        new_col = f"{col}_uncertainty_new"
        if new_col in merged.columns:
            merged[col] = merged[new_col].combine_first(merged.get(col))
            merged = merged.drop(columns=[new_col])

    if "uncertainty_adjusted_execution_action" in merged.columns:
        mask = merged["uncertainty_adjusted_execution_action"].astype(str).str.strip().ne("")
        merged.loc[mask, "execution_action"] = merged.loc[mask, "uncertainty_adjusted_execution_action"]
        merged.loc[mask, "final_execution_state"] = merged.loc[mask, "uncertainty_adjusted_execution_action"]

    added_cols = [c for c in merged.columns if c not in original_cols and not c.startswith("_")]
    merged = merged.drop(columns=["_horse_key", "_track_key", "_race_key"], errors="ignore")
    merged.to_csv(path, index=False)
    return len(merged), len(added_cols)


def diagnostics(rows):
    if rows.empty:
        return pd.DataFrame([{
            "diagnostic_type": "OVERALL",
            "rows": 0,
            "value": "",
            "reason": "No live rows available",
        }])

    band_counts = rows["uncertainty_band"].value_counts().to_dict()
    highest = rows.sort_values("uncertainty_score", ascending=False).iloc[0]
    avg_score = rows["uncertainty_score"].mean()
    avg_shrink = rows["recommended_probability_shrinkage"].mean()
    first_count = int((rows["first_starter_flag"] == "TRUE").sum())
    no_runs_count = int((rows["no_official_runs_flag"] == "TRUE").sum())

    records = [
        {
            "diagnostic_type": "OVERALL",
            "rows": len(rows),
            "value": round(avg_score, 2),
            "reason": f"Average uncertainty score; avg shrinkage {avg_shrink:.3f}",
        },
        {
            "diagnostic_type": "DISTRIBUTION",
            "rows": len(rows),
            "value": ";".join(f"{k}:{v}" for k, v in band_counts.items()),
            "reason": "Live uncertainty band distribution",
        },
        {
            "diagnostic_type": "HIGHEST_UNCERTAINTY_RUNNER",
            "rows": 1,
            "value": highest.get("horse", ""),
            "reason": highest.get("uncertainty_reason", ""),
        },
        {
            "diagnostic_type": "FIRST_STARTERS",
            "rows": first_count,
            "value": first_count,
            "reason": "First starter profiles default to high uncertainty unless strongly confirmed",
        },
        {
            "diagnostic_type": "NO_OFFICIAL_RUNS",
            "rows": no_runs_count,
            "value": no_runs_count,
            "reason": "No official run sample requires defensive probability shrinkage",
        },
        {
            "diagnostic_type": "AVERAGE_RECOMMENDED_SHRINKAGE",
            "rows": len(rows),
            "value": round(avg_shrink, 4),
            "reason": "Mean probability multiplier recommended by uncertainty model",
        },
    ]

    structures = rows.groupby(["uncertainty_band", "first_starter_flag", "no_official_runs_flag"], dropna=False).size().reset_index(name="rows")
    if len(structures):
        top = structures.sort_values("rows", ascending=False).iloc[0]
        records.append({
            "diagnostic_type": "HIGHEST_RISK_STRUCTURE",
            "rows": int(top["rows"]),
            "value": f"{top['uncertainty_band']} first={top['first_starter_flag']} no_runs={top['no_official_runs_flag']}",
            "reason": "Most common current uncertainty structure",
        })

    return pd.DataFrame(records)


def main():
    print("=" * 100)
    print("EDGEIQ UNCERTAINTY ENGINE V1")
    print("=" * 100)

    live = read_csv(LIVE)
    if live.empty:
        empty = pd.DataFrame(columns=OUTPUT_COLUMNS)
        empty.to_csv(OUT, index=False)
        diagnostics(empty).to_csv(DIAGNOSTICS, index=False)
        print("[uncertainty] rows processed: 0")
        return

    base = add_keys(live)
    base = merge_by_runner(base, read_csv(PROBABILITY), ["v2_probability", "v2_fair_price", "v2_overlay_pct", "v2_probability_realism_grade"], "prob")
    base = merge_by_runner(base, read_csv(BAYESIAN), ["model_weight", "market_weight", "blended_probability", "blending_reason"], "bayes")
    base = merge_by_runner(base, read_csv(ENVIRONMENT), ["environment_type", "environment_risk_grade", "matched_interaction_recommendation"], "env")
    base = merge_by_runner(base, read_csv(MICROSTRUCTURE), ["microstructure_type", "microstructure_risk_grade", "movement_velocity", "movement_stability"], "micro")
    base = merge_form_summary(base, read_csv(FORM_SUMMARY))
    depth = form_runs_depth(read_csv(FORM_RUNS))
    if not depth.empty:
        base = base.merge(depth, on="_horse_key", how="left")
    base = merge_by_runner(base, read_csv(RACE_FIELDS), ["race_class", "distance", "track_condition"], "field")

    rows = pd.DataFrame([compute_row(row) for _, row in base.iterrows()], columns=OUTPUT_COLUMNS)
    rows.to_csv(OUT, index=False)
    diagnostics(rows).to_csv(DIAGNOSTICS, index=False)

    live_rows, _ = patch_board(LIVE, rows)
    terminal_rows, _ = patch_board(TERMINAL, rows)

    distribution = rows["uncertainty_band"].value_counts().to_dict()
    changed = rows["uncertainty_original_execution_action"] != rows["uncertainty_adjusted_execution_action"]
    suppressed = int((changed & (rows["uncertainty_adjusted_execution_action"] == "SUPPRESS")).sum())
    reduced = int((changed & rows["uncertainty_adjusted_execution_action"].isin(["WATCH", "REDUCED_EXECUTE", "EXECUTE"])).sum())

    print(f"[uncertainty] rows processed: {len(rows)}")
    print(f"[uncertainty] live board rows patched: {live_rows}")
    print(f"[uncertainty] terminal rows patched: {terminal_rows}")
    print(f"[uncertainty] uncertainty distribution: {distribution}")
    print(f"[uncertainty] runners suppressed: {suppressed}")
    print(f"[uncertainty] runners reduced: {reduced}")
    print(f"[uncertainty] average recommended shrinkage: {rows['recommended_probability_shrinkage'].mean():.4f}")
    print(f"[uncertainty] wrote {OUT}")
    print(f"[uncertainty] wrote {DIAGNOSTICS}")
    print("=" * 100)


if __name__ == "__main__":
    main()
