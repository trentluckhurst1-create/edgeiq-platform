from pathlib import Path
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_execution_board_live.csv"
TERMINAL = DATA / "edgeiq_execution_board_terminal.csv"
UNCERTAINTY = DATA / "edgeiq_uncertainty_engine_v1.csv"
FORM_SUMMARY = DATA / "form_card_summary.csv"
FORM_RUNS = DATA / "form_card_runs.csv"
RACE_FIELDS = DATA / "race_fields.csv"
ENVIRONMENT = DATA / "edgeiq_environment_classification_v1.csv"
MICROSTRUCTURE = DATA / "edgeiq_market_microstructure_v1.csv"
TIMING = DATA / "edgeiq_temporal_execution_intelligence_v1.csv"

OUT = DATA / "edgeiq_first_starter_engine_v1.csv"
DIAGNOSTICS = DATA / "edgeiq_first_starter_diagnostics_v1.csv"

OUTPUT_COLUMNS = [
    "track",
    "race_no",
    "horse",
    "first_starter_engine_flag",
    "lightly_raced_engine_flag",
    "no_official_form_engine_flag",
    "official_run_count",
    "trial_run_count",
    "jumpout_run_count",
    "debut_profile_grade",
    "exposed_form_grade",
    "debut_market_confirmation",
    "debut_environment_quality",
    "debut_risk_grade",
    "first_starter_reason",
    "first_starter_probability_multiplier",
    "first_starter_stake_multiplier",
    "first_starter_action_impact",
    "first_starter_original_execution_action",
    "first_starter_adjusted_execution_action",
    "first_starter_applied",
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
        print(f"[first_starter] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"[first_starter] read {path.name}: {len(df)} rows")
        return df
    except Exception as exc:
        print(f"[first_starter] failed {path.name}: {exc}")
        return pd.DataFrame()


def add_keys(df):
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
    extra = add_keys(extra)
    keys = ["_horse_key", "_track_key", "_race_key"]
    available = [col for col in columns if col in extra.columns]
    if not available or not set(keys).issubset(extra.columns):
        return base
    right = extra[keys + available].drop_duplicates(keys, keep="last")
    right = right.rename(columns={col: f"{prefix}_{col}" for col in available})
    return base.merge(right, on=keys, how="left")


def merge_form_summary(base, summary):
    if base.empty or summary.empty:
        return base
    summary = add_keys(summary)
    available = [col for col in ["official_run_count", "1LS", "2LS", "3LS", "5LSA", "PEAK"] if col in summary.columns]
    if not available:
        return base
    right = summary[["_horse_key"] + available].drop_duplicates("_horse_key", keep="last")
    right = right.rename(columns={col: f"summary_{col}" for col in available})
    return base.merge(right, on="_horse_key", how="left")


def form_counts(runs):
    if runs.empty or "horse" not in runs.columns:
        return pd.DataFrame(columns=["_horse_key", "form_official_run_count", "trial_run_count", "jumpout_run_count"])

    df = runs.copy()
    df["_horse_key"] = df["horse"].map(canonical)
    run_type = df["run_type"].map(clean) if "run_type" in df.columns else pd.Series([""] * len(df), index=df.index)
    raw_text = df["raw_text"].map(clean) if "raw_text" in df.columns else pd.Series([""] * len(df), index=df.index)
    official = df["is_official_race"].astype(str).str.upper().isin(["TRUE", "1", "YES"]) if "is_official_race" in df.columns else run_type.eq("RACE")
    trial = run_type.str.contains("TRIAL", na=False) | raw_text.str.contains("TRIAL", na=False)
    jumpout = run_type.str.contains("JUMP", na=False) | raw_text.str.contains("JUMP", na=False)

    grouped = pd.DataFrame({
        "_horse_key": df["_horse_key"],
        "official": official.astype(int),
        "trial": trial.astype(int),
        "jumpout": jumpout.astype(int),
    }).groupby("_horse_key", dropna=False).sum().reset_index()
    return grouped.rename(columns={
        "official": "form_official_run_count",
        "trial": "trial_run_count",
        "jumpout": "jumpout_run_count",
    })


def first_value(row, names, default=None):
    for name in names:
        if name in row.index:
            value = row.get(name)
            if pd.notna(value) and str(value).strip() != "":
                return value
    return default


def official_runs(row):
    return as_num(first_value(row, [
        "official_run_count",
        "summary_official_run_count",
        "form_official_run_count",
        "summary_official_run_count_x",
        "summary_official_run_count_y",
        "uncertainty_official_run_count",
    ]), 0)


def exposed_form_grade(row, official_count):
    values = [
        as_num(first_value(row, ["latest_flat_rating", "summary_1LS"]), None),
        as_num(first_value(row, ["last3_flat_avg", "summary_3LS"]), None),
        as_num(first_value(row, ["last5_flat_avg", "summary_5LSA"]), None),
        as_num(first_value(row, ["peak_rating", "summary_PEAK"]), None),
    ]
    observed = len([v for v in values if v is not None])
    if official_count <= 0:
        return "NO_EXPOSED_FORM"
    if official_count <= 3:
        return "LIGHT_SAMPLE"
    if observed >= 3:
        return "EXPOSED_STABLE"
    if observed >= 1:
        return "EXPOSED_LIMITED"
    return "EXPOSED_UNKNOWN"


def debut_profile_grade(first_flag, no_form, official_count, trials, jumpouts):
    if not first_flag and official_count > 3:
        return "EXPOSED_RUNNER"
    if no_form and trials + jumpouts >= 2:
        return "DEBUT_WITH_TRIAL_HINTS"
    if no_form and trials + jumpouts == 1:
        return "DEBUT_MINIMAL_TRIAL_HINT"
    if no_form:
        return "UNKNOWN_DEBUT_PROFILE"
    if official_count <= 3:
        return "LIGHTLY_RACED_PROFILE"
    return "EXPOSED_RUNNER"


def market_confirmation(row):
    price = as_num(first_value(row, ["sportsbet_price", "market_price", "current_price"]), None)
    mover = clean(first_value(row, ["market_mover", "movement_signal"], ""))
    micro = clean(first_value(row, ["microstructure_type", "micro_microstructure_type"], ""))
    env = clean(first_value(row, ["environment_type", "env_environment_type"], ""))
    model_weight = as_num(first_value(row, ["model_weight", "bayes_model_weight"], 0), 0)
    market_weight = as_num(first_value(row, ["market_weight", "bayes_market_weight"], 0), 0)

    score = 0
    reasons = []
    if price is not None and price <= 4:
        score += 30
        reasons.append("short market price")
    elif price is not None and price <= 8:
        score += 20
        reasons.append("some market support")
    elif price is not None and price >= 26:
        score -= 10
        reasons.append("rough market price")
    if "FIRM" in mover or "STEAM" in mover or micro in {"CONTROLLED_FIRMING", "SHARP_STEAM"}:
        score += 20
        reasons.append("positive tape confirmation")
    if env == "PROTECTED_EDGE":
        score += 10
        reasons.append("protected-edge context")
    if market_weight > model_weight and market_weight >= 0.6:
        score += 8
        reasons.append("market-led blend")

    if score >= 40:
        return "CONFIRMED", reasons
    if score >= 20:
        return "PARTIAL", reasons
    return "UNCONFIRMED", reasons or ["no strong market confirmation"]


def environment_quality(row):
    env = clean(first_value(row, ["environment_type", "env_environment_type"], ""))
    micro = clean(first_value(row, ["microstructure_type", "micro_microstructure_type"], ""))
    timing = clean(first_value(row, ["timing_environment"], ""))
    transition = clean(first_value(row, ["transition_type"], ""))

    bad = env in {"CHAOTIC", "PUBLIC_TRAP", "VOLATILE"} or micro in {"VOLATILITY_CLUSTER", "FALSE_STEAM", "PUBLIC_STEAM", "PANIC_DRIFT"} or timing in {"TRAP_WINDOW", "PUBLIC_OVERREACTION", "CHAOTIC_LATE"} or transition == "EXECUTE_WINDOW_TO_AVOID"
    good = env == "PROTECTED_EDGE" or micro in {"CONTROLLED_FIRMING", "SHARP_STEAM"}

    if bad:
        return "POOR"
    if good:
        return "SUPPORTIVE"
    return "NEUTRAL"


def action_rule(original, first_flag, no_form, lightly, confirmation, uncertainty_band):
    original = clean(original) or "PASS"
    impact = "NO_CHANGE"
    final = original

    if no_form:
        if original in {"MAX_BET", "PRIORITY_EXECUTE", "EXECUTE", "REDUCED_EXECUTE"} and confirmation != "CONFIRMED":
            final = "SUPPRESS"
            impact = "SUPPRESS_NO_OFFICIAL_FORM"
        elif original in {"MAX_BET", "PRIORITY_EXECUTE"}:
            final = "WATCH"
            impact = "WATCH_ONLY_DEBUT_PROFILE"
    elif first_flag and confirmation == "UNCONFIRMED":
        if original in {"MAX_BET", "PRIORITY_EXECUTE", "EXECUTE"}:
            final = "SUPPRESS"
            impact = "SUPPRESS_UNCONFIRMED_DEBUT"
    elif lightly and uncertainty_band not in {"LOW", "MEDIUM"}:
        if original in {"MAX_BET", "PRIORITY_EXECUTE"}:
            final = "EXECUTE"
            impact = "REDUCE_LIGHTLY_RACED"
        elif original == "EXECUTE":
            final = "REDUCED_EXECUTE"
            impact = "REDUCE_LIGHTLY_RACED"

    return final, impact


def compute_row(row):
    official = official_runs(row)
    trials = int(as_num(row.get("trial_run_count"), 0) or 0)
    jumpouts = int(as_num(row.get("jumpout_run_count"), 0) or 0)
    risk_flags = clean(row.get("risk_flags"))
    speed_bucket = clean(row.get("speed_map_bucket"))
    notes = clean(row.get("rating_notes"))
    uncertainty_band = clean(row.get("uncertainty_band"))

    no_form = official <= 0 or "NO_OFFICIAL_FORM" in risk_flags
    first_flag = no_form or "FIRST" in speed_bucket or "FIRST START" in notes
    lightly = 0 < official <= 3
    confirmation, confirmation_reasons = market_confirmation(row)
    env_quality = environment_quality(row)
    debut_grade = debut_profile_grade(first_flag, no_form, official, trials, jumpouts)
    form_grade = exposed_form_grade(row, official)

    risk_score = 20
    reasons = []
    if no_form:
        risk_score += 55
        reasons.append("no official race-run sample")
    elif first_flag:
        risk_score += 45
        reasons.append("first-starter/debut profile")
    elif lightly:
        risk_score += 28
        reasons.append("lightly raced profile")

    if trials + jumpouts:
        risk_score -= min(12, (trials + jumpouts) * 5)
        reasons.append("trial/jumpout evidence present")

    if confirmation == "CONFIRMED":
        risk_score -= 14
        reasons.append("market confirmation")
    elif confirmation == "PARTIAL":
        risk_score -= 6
        reasons.append("partial market confirmation")
    else:
        risk_score += 8
        reasons.append("unconfirmed by market")

    if env_quality == "POOR":
        risk_score += 16
        reasons.append("poor debut environment")
    elif env_quality == "SUPPORTIVE":
        risk_score -= 8
        reasons.append("supportive market environment")

    if uncertainty_band == "EXTREME":
        risk_score += 10
        reasons.append("extreme uncertainty")
    elif uncertainty_band == "LOW":
        risk_score -= 8

    if no_form:
        risk_score = max(risk_score, 75)
    if first_flag:
        risk_score = max(risk_score, 60)

    risk_score = max(0, min(100, risk_score))
    if risk_score >= 80:
        risk_grade = "EXTREME"
        prob_mult = 0.6
        stake_mult = 0.2 if no_form else 0.25
    elif risk_score >= 60:
        risk_grade = "HIGH"
        prob_mult = 0.75
        stake_mult = 0.4
    elif risk_score >= 35:
        risk_grade = "MEDIUM"
        prob_mult = 0.9
        stake_mult = 0.7
    else:
        risk_grade = "LOW"
        prob_mult = 1.0
        stake_mult = 1.0

    if first_flag and risk_grade == "LOW":
        risk_grade = "MEDIUM"
    if no_form:
        stake_mult = min(stake_mult, 0.2)

    original = clean(first_value(row, ["execution_action", "final_execution_state"], "PASS"))
    final, impact = action_rule(original, first_flag, no_form, lightly, confirmation, uncertainty_band)
    applied = final != original

    reason = " | ".join((reasons + confirmation_reasons)[:7])
    return {
        "track": row.get("track", ""),
        "race_no": row.get("race_no", ""),
        "horse": row.get("horse", ""),
        "first_starter_engine_flag": str(bool(first_flag)).upper(),
        "lightly_raced_engine_flag": str(bool(lightly)).upper(),
        "no_official_form_engine_flag": str(bool(no_form)).upper(),
        "official_run_count": int(official),
        "trial_run_count": trials,
        "jumpout_run_count": jumpouts,
        "debut_profile_grade": debut_grade,
        "exposed_form_grade": form_grade,
        "debut_market_confirmation": confirmation,
        "debut_environment_quality": env_quality,
        "debut_risk_grade": risk_grade,
        "first_starter_reason": reason or "exposed runner",
        "first_starter_probability_multiplier": round(prob_mult, 4),
        "first_starter_stake_multiplier": round(stake_mult, 4),
        "first_starter_action_impact": impact,
        "first_starter_original_execution_action": original,
        "first_starter_adjusted_execution_action": final,
        "first_starter_applied": str(applied).upper(),
    }


def patch_board(path, rows):
    board = read_csv(path)
    if board.empty or rows.empty:
        return 0
    board = add_keys(board)
    rows = add_keys(rows)
    patch_cols = [c for c in OUTPUT_COLUMNS if c not in {"track", "race_no", "horse"}]
    patch = rows[["_horse_key", "_track_key", "_race_key"] + patch_cols].drop_duplicates(["_horse_key", "_track_key", "_race_key"], keep="last")
    merged = board.merge(patch, on=["_horse_key", "_track_key", "_race_key"], how="left", suffixes=("", "_fs_new"))

    for col in patch_cols:
        extra = f"{col}_fs_new"
        if extra in merged.columns:
            current = merged[col].map(lambda v: str(v).strip()) if col in merged.columns else pd.Series([""] * len(merged), index=merged.index)
            merged[col] = merged[col].where(current != "", merged[extra]) if col in merged.columns else merged[extra]
            merged = merged.drop(columns=[extra])

    mask = merged.get("first_starter_adjusted_execution_action", pd.Series([""] * len(merged))).astype(str).str.strip().ne("")
    merged.loc[mask, "execution_action"] = merged.loc[mask, "first_starter_adjusted_execution_action"]
    merged.loc[mask, "final_execution_state"] = merged.loc[mask, "first_starter_adjusted_execution_action"]
    merged = merged.drop(columns=["_horse_key", "_track_key", "_race_key"], errors="ignore")
    merged.to_csv(path, index=False)
    return len(merged)


def diagnostics(rows):
    if rows.empty:
        return pd.DataFrame([{
            "diagnostic_type": "OVERALL",
            "rows": 0,
            "value": "",
            "reason": "No live rows available",
        }])

    first_count = int((rows["first_starter_engine_flag"] == "TRUE").sum())
    light_count = int((rows["lightly_raced_engine_flag"] == "TRUE").sum())
    no_form_count = int((rows["no_official_form_engine_flag"] == "TRUE").sum())
    risk_distribution = rows["debut_risk_grade"].value_counts().to_dict()
    avg_prob = rows["first_starter_probability_multiplier"].mean()
    avg_stake = rows["first_starter_stake_multiplier"].mean()
    reason_counts = rows["first_starter_reason"].astype(str).str.split("|").str[0].str.strip().value_counts()
    common_reason = reason_counts.index[0] if len(reason_counts) else ""

    return pd.DataFrame([
        {
            "diagnostic_type": "OVERALL",
            "rows": len(rows),
            "value": len(rows),
            "reason": "First starter and lightly raced engine rows processed",
        },
        {
            "diagnostic_type": "RISK_DISTRIBUTION",
            "rows": len(rows),
            "value": ";".join(f"{k}:{v}" for k, v in risk_distribution.items()),
            "reason": "Distribution by debut risk",
        },
        {
            "diagnostic_type": "FIRST_STARTERS",
            "rows": first_count,
            "value": first_count,
            "reason": "First starter or no official form profiles",
        },
        {
            "diagnostic_type": "LIGHTLY_RACED",
            "rows": light_count,
            "value": light_count,
            "reason": "Official run count from 1 to 3",
        },
        {
            "diagnostic_type": "NO_OFFICIAL_FORM",
            "rows": no_form_count,
            "value": no_form_count,
            "reason": "No official race-run sample",
        },
        {
            "diagnostic_type": "AVERAGE_MULTIPLIERS",
            "rows": len(rows),
            "value": f"prob={avg_prob:.4f};stake={avg_stake:.4f}",
            "reason": "Average first-starter probability and stake multipliers",
        },
        {
            "diagnostic_type": "MOST_COMMON_REASON",
            "rows": int(reason_counts.iloc[0]) if len(reason_counts) else 0,
            "value": common_reason,
            "reason": "Most common current limited-evidence reason",
        },
    ])


def main():
    print("=" * 100)
    print("EDGEIQ FIRST STARTER / LIGHTLY RACED ENGINE V1")
    print("=" * 100)

    live = read_csv(LIVE)
    if live.empty:
        pd.DataFrame(columns=OUTPUT_COLUMNS).to_csv(OUT, index=False)
        diagnostics(pd.DataFrame(columns=OUTPUT_COLUMNS)).to_csv(DIAGNOSTICS, index=False)
        print("[first_starter] rows processed: 0")
        return

    base = add_keys(live)
    base = merge_by_runner(base, read_csv(UNCERTAINTY), ["uncertainty_band", "no_official_runs_flag", "first_starter_flag"], "uncertainty")
    base = merge_form_summary(base, read_csv(FORM_SUMMARY))
    counts = form_counts(read_csv(FORM_RUNS))
    if not counts.empty:
        base = base.merge(counts, on="_horse_key", how="left")
    base = merge_by_runner(base, read_csv(RACE_FIELDS), ["race_class", "distance", "track_condition"], "field")
    base = merge_by_runner(base, read_csv(ENVIRONMENT), ["environment_type", "matched_interaction_recommendation"], "env")
    base = merge_by_runner(base, read_csv(MICROSTRUCTURE), ["microstructure_type", "movement_velocity", "movement_stability"], "micro")

    rows = pd.DataFrame([compute_row(row) for _, row in base.iterrows()], columns=OUTPUT_COLUMNS)
    rows.to_csv(OUT, index=False)
    diagnostics(rows).to_csv(DIAGNOSTICS, index=False)

    live_rows = patch_board(LIVE, rows)
    terminal_rows = patch_board(TERMINAL, rows)

    distribution = rows["debut_risk_grade"].value_counts().to_dict()
    first_count = int((rows["first_starter_engine_flag"] == "TRUE").sum())
    lightly_count = int((rows["lightly_raced_engine_flag"] == "TRUE").sum())
    no_form_count = int((rows["no_official_form_engine_flag"] == "TRUE").sum())

    print(f"[first_starter] rows processed: {len(rows)}")
    print(f"[first_starter] live board rows patched: {live_rows}")
    print(f"[first_starter] terminal rows patched: {terminal_rows}")
    print(f"[first_starter] first starters: {first_count}")
    print(f"[first_starter] lightly raced: {lightly_count}")
    print(f"[first_starter] no official form: {no_form_count}")
    print(f"[first_starter] risk distribution: {distribution}")
    print(f"[first_starter] average probability multiplier: {rows['first_starter_probability_multiplier'].mean():.4f}")
    print(f"[first_starter] average stake multiplier: {rows['first_starter_stake_multiplier'].mean():.4f}")
    print(f"[first_starter] wrote {OUT}")
    print(f"[first_starter] wrote {DIAGNOSTICS}")
    print("=" * 100)


if __name__ == "__main__":
    main()
