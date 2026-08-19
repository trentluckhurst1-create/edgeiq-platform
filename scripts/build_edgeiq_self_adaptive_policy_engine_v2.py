from pathlib import Path
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_execution_board_live.csv"
TERMINAL = DATA / "edgeiq_execution_board_terminal.csv"
UNCERTAINTY = DATA / "edgeiq_uncertainty_engine_v1.csv"
FIRST_STARTER = DATA / "edgeiq_first_starter_engine_v1.csv"
ENVIRONMENT = DATA / "edgeiq_environment_classification_v1.csv"
MICROSTRUCTURE = DATA / "edgeiq_market_microstructure_v1.csv"
TIMING = DATA / "edgeiq_temporal_execution_intelligence_v1.csv"
TRANSITIONS = DATA / "edgeiq_market_state_transitions_v1.csv"
POLICY_RANKINGS = DATA / "edgeiq_policy_rankings_v1.csv"
RESULTS_SUMMARY = DATA / "edgeiq_results_summary.csv"

OUT = DATA / "edgeiq_self_adaptive_policy_v2.csv"
DIAGNOSTICS = DATA / "edgeiq_self_adaptive_policy_diagnostics_v2.csv"

OUTPUT_COLUMNS = [
    "track",
    "race_no",
    "horse",
    "adaptive_policy_v2",
    "adaptive_policy_reason",
    "adaptive_aggression_score",
    "adaptive_risk_score",
    "adaptive_model_trust",
    "adaptive_market_trust",
    "adaptive_stake_multiplier",
    "adaptive_execution_permission",
    "adaptive_action_impact",
    "adaptive_original_execution_action",
    "adaptive_adjusted_execution_action",
    "adaptive_policy_applied",
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
        print(f"[adaptive_v2] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"[adaptive_v2] read {path.name}: {len(df)} rows")
        return df
    except Exception as exc:
        print(f"[adaptive_v2] failed {path.name}: {exc}")
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


def merge_by_timing_window(base, timing):
    if base.empty or timing.empty or "timing_window" not in base.columns or "timing_window" not in timing.columns:
        return base
    cols = [
        "timing_window",
        "timing_environment",
        "timing_risk_grade",
        "recommended_wait_or_execute",
        "timing_reason",
    ]
    available = [col for col in cols if col in timing.columns]
    if len(available) <= 1:
        return base
    right = timing[available].drop_duplicates(["timing_window"], keep="last")
    merged = base.merge(right, on="timing_window", how="left", suffixes=("", "_timing_lookup"))
    for col in available:
        if col == "timing_window":
            continue
        lookup = f"{col}_timing_lookup"
        if lookup in merged.columns:
            current = merged[col].map(lambda v: str(v).strip()) if col in merged.columns else pd.Series([""] * len(merged), index=merged.index)
            merged[col] = merged[col].where(current != "", merged[lookup]) if col in merged.columns else merged[lookup]
            merged = merged.drop(columns=[lookup])
    return merged


def preferred_policy(policy_rankings):
    if policy_rankings.empty:
        return "DEFAULT", "policy rankings unavailable"
    rows = policy_rankings.copy()
    for ranking_type in ["RECOMMENDED_ACTIVE_POLICY", "SAFEST_POLICY", "BEST_DRAWDOWN_CONTROL"]:
        if "ranking_type" in rows.columns:
            found = rows[rows["ranking_type"].map(clean) == ranking_type]
            if len(found):
                row = found.iloc[0]
                value = str(row.get("policy_name") or row.get("recommended_active_policy") or "").strip()
                if value:
                    return value.upper(), f"historical ranking favours {value}"
    return "DEFAULT", "no decisive policy ranking"


def summary_bias(results_summary):
    if results_summary.empty:
        return 0, "no results summary"
    row = results_summary.iloc[0]
    roi = as_num(row.get("roi_pct"), 0)
    drawdown = abs(as_num(row.get("max_drawdown"), 0))
    if roi < -10 or drawdown > 20:
        return 12, "poor ROI/drawdown history"
    if roi < 0:
        return 6, "negative ROI history"
    return 0, "results summary does not force extra defence"


def protected_edge(row):
    return (
        clean(row.get("environment_type") or row.get("env_environment_type")) == "PROTECTED_EDGE"
        or "PROTECT" in clean(row.get("matched_interaction_recommendation") or row.get("env_matched_interaction_recommendation"))
        or clean(row.get("overlay_realism_grade")) == "REALISTIC"
    )


def current_action(row):
    return clean(row.get("execution_action") or row.get("final_execution_state") or row.get("post_v2_execution_action") or "PASS")


def choose_policy(row, historical_preference, historical_reason, results_penalty, results_reason):
    uncertainty = clean(row.get("uncertainty_band") or row.get("uncertainty_uncertainty_band"))
    first_risk = clean(row.get("debut_risk_grade") or row.get("first_debut_risk_grade"))
    first_flag = clean(row.get("first_starter_engine_flag") or row.get("first_first_starter_engine_flag")) == "TRUE"
    no_form = clean(row.get("no_official_form_engine_flag") or row.get("first_no_official_form_engine_flag")) == "TRUE"
    environment = clean(row.get("environment_type") or row.get("env_environment_type"))
    micro = clean(row.get("microstructure_type") or row.get("micro_microstructure_type"))
    timing = clean(row.get("timing_environment"))
    transition = clean(row.get("transition_type") or row.get("transition_transition_type"))
    confidence = clean(row.get("calibrated_confidence_label") or row.get("confidence_band_v1"))
    is_protected = protected_edge(row)

    risk = results_penalty
    aggression = 50
    reasons = []

    if results_penalty:
        reasons.append(results_reason)

    if uncertainty == "EXTREME":
        risk += 30
        aggression -= 25
        reasons.append("EXTREME uncertainty")
    elif uncertainty == "HIGH":
        risk += 18
        aggression -= 14
        reasons.append("HIGH uncertainty")
    elif uncertainty in {"LOW", "MEDIUM"}:
        aggression += 5

    if no_form or (first_flag and first_risk == "EXTREME"):
        risk += 25
        aggression -= 20
        reasons.append("first-starter/no-official-form extreme risk")
    elif first_flag or first_risk == "HIGH":
        risk += 16
        aggression -= 12
        reasons.append("limited exposed race evidence")

    if environment == "CHAOTIC":
        risk += 22
        aggression -= 18
        reasons.append("CHAOTIC environment")
    elif environment == "PUBLIC_TRAP":
        risk += 18
        aggression -= 12
        reasons.append("PUBLIC_TRAP environment")
    elif environment == "PROTECTED_EDGE":
        risk -= 12
        aggression += 14
        reasons.append("protected-edge environment")

    if micro == "VOLATILITY_CLUSTER":
        risk += 18
        aggression -= 14
        reasons.append("VOLATILITY_CLUSTER microstructure")
    elif micro in {"CONTROLLED_FIRMING", "SHARP_STEAM"}:
        risk -= 6
        aggression += 8
        reasons.append(f"{micro} tape support")

    if timing == "TRAP_WINDOW":
        risk += 16
        aggression -= 12
        reasons.append("TRAP_WINDOW timing")
    if transition == "EXECUTE_WINDOW_TO_AVOID":
        risk += 20
        aggression -= 18
        reasons.append("execution window deteriorating")

    if confidence in {"VERY_LOW", "LOW"}:
        risk += 10
        aggression -= 8
        reasons.append(f"{confidence} confidence")
    elif confidence in {"HIGH", "VERY_HIGH"}:
        risk -= 8
        aggression += 8

    if historical_preference == "SAFE_MODE" and not is_protected:
        risk += 8
        reasons.append(historical_reason)

    risk = max(0, min(100, round(risk, 2)))
    aggression = max(0, min(100, round(aggression, 2)))

    if is_protected and uncertainty in {"LOW", "MEDIUM"} and environment in {"PROTECTED_EDGE", "STABLE", "CLEAN"}:
        policy = "PROTECTED_EDGES_ONLY"
    elif no_form or first_risk == "EXTREME" or environment == "CHAOTIC":
        policy = "SAFE_MODE"
    elif uncertainty == "EXTREME" or transition == "EXECUTE_WINDOW_TO_AVOID":
        policy = "LOW_DRAWDOWN_MODE"
    elif confidence in {"HIGH", "VERY_HIGH"} and risk < 45:
        policy = "HIGH_CONFIDENCE_ONLY"
    elif historical_preference in {"SAFE_MODE", "LOW_DRAWDOWN_MODE"} and not is_protected:
        policy = historical_preference
    elif risk < 30 and aggression > 60:
        policy = "DEFAULT"
    else:
        policy = "SAFE_MODE" if risk >= 55 else "DEFAULT"

    if risk >= 75:
        permission = "DENY"
        stake = 0.2 if no_form or first_risk == "EXTREME" else 0.25
    elif risk >= 55:
        permission = "REDUCE"
        stake = 0.35
    elif risk >= 35:
        permission = "REDUCE"
        stake = 0.6
    else:
        permission = "ALLOW"
        stake = 1.0

    if is_protected and permission == "DENY" and not (no_form or uncertainty == "EXTREME"):
        permission = "REDUCE"
        stake = min(0.5, max(stake, 0.35))

    if policy == "EXPERIMENTAL_MODE":
        stake = min(stake, 0.25)

    model_trust = max(10, min(90, 60 - risk * 0.45 + aggression * 0.2))
    market_trust = max(10, min(90, 100 - model_trust))
    if no_form or first_risk in {"HIGH", "EXTREME"}:
        model_trust = min(model_trust, 30)
        market_trust = max(market_trust, 70)
    if is_protected and risk < 55:
        model_trust = min(70, model_trust + 10)
        market_trust = max(30, 100 - model_trust)

    return {
        "policy": policy,
        "reason": " | ".join(reasons[:7]) or "balanced live conditions",
        "risk": risk,
        "aggression": aggression,
        "model_trust": round(model_trust / 100, 4),
        "market_trust": round(market_trust / 100, 4),
        "stake": round(stake, 4),
        "permission": permission,
    }


def apply_action(original, permission):
    original = clean(original) or "PASS"
    if permission == "DENY":
        if original in {"MAX_BET", "PRIORITY_EXECUTE", "EXECUTE", "REDUCED_EXECUTE", "WATCH"}:
            return "SUPPRESS", "DENY_AGGRESSIVE_EXECUTION"
        return original, "DENY_NO_AGGRESSIVE_ACTION"
    if permission == "REDUCE":
        if original in {"MAX_BET", "PRIORITY_EXECUTE"}:
            return "EXECUTE", "REDUCE_PRIORITY"
        if original == "EXECUTE":
            return "REDUCED_EXECUTE", "REDUCE_EXECUTION"
        return original, "REDUCE_STAKE_ONLY"
    return original, "ALLOW_PRESERVE"


def compute_rows(live, historical_preference, historical_reason, results_penalty, results_reason):
    rows = []
    for _, row in live.iterrows():
        decision = choose_policy(row, historical_preference, historical_reason, results_penalty, results_reason)
        original = current_action(row)
        final, impact = apply_action(original, decision["permission"])
        rows.append({
            "track": row.get("track", ""),
            "race_no": row.get("race_no", ""),
            "horse": row.get("horse", ""),
            "adaptive_policy_v2": decision["policy"],
            "adaptive_policy_reason": decision["reason"],
            "adaptive_aggression_score": decision["aggression"],
            "adaptive_risk_score": decision["risk"],
            "adaptive_model_trust": decision["model_trust"],
            "adaptive_market_trust": decision["market_trust"],
            "adaptive_stake_multiplier": decision["stake"],
            "adaptive_execution_permission": decision["permission"],
            "adaptive_action_impact": impact,
            "adaptive_original_execution_action": original,
            "adaptive_adjusted_execution_action": final,
            "adaptive_policy_applied": str(final != original or decision["permission"] != "ALLOW").upper(),
        })
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def patch_board(path, rows):
    board = read_csv(path)
    if board.empty or rows.empty:
        return 0
    board = add_keys(board)
    rows = add_keys(rows)
    patch_cols = [c for c in OUTPUT_COLUMNS if c not in {"track", "race_no", "horse"}]
    patch = rows[["_horse_key", "_track_key", "_race_key"] + patch_cols].drop_duplicates(["_horse_key", "_track_key", "_race_key"], keep="last")
    merged = board.merge(patch, on=["_horse_key", "_track_key", "_race_key"], how="left", suffixes=("", "_adaptive_new"))
    for col in patch_cols:
        extra = f"{col}_adaptive_new"
        if extra in merged.columns:
            current = merged[col].map(lambda v: str(v).strip()) if col in merged.columns else pd.Series([""] * len(merged), index=merged.index)
            merged[col] = merged[col].where(current != "", merged[extra]) if col in merged.columns else merged[extra]
            merged = merged.drop(columns=[extra])
    mask = merged.get("adaptive_adjusted_execution_action", pd.Series([""] * len(merged))).astype(str).str.strip().ne("")
    merged.loc[mask, "execution_action"] = merged.loc[mask, "adaptive_adjusted_execution_action"]
    merged.loc[mask, "final_execution_state"] = merged.loc[mask, "adaptive_adjusted_execution_action"]
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
    policy_dist = rows["adaptive_policy_v2"].value_counts().to_dict()
    permission_dist = rows["adaptive_execution_permission"].value_counts().to_dict()
    denied = int((rows["adaptive_execution_permission"] == "DENY").sum())
    reduced = int((rows["adaptive_execution_permission"] == "REDUCE").sum())
    allowed = int((rows["adaptive_execution_permission"] == "ALLOW").sum())
    avg_model = rows["adaptive_model_trust"].mean()
    avg_market = rows["adaptive_market_trust"].mean()
    avg_risk = rows["adaptive_risk_score"].mean()
    avg_aggression = rows["adaptive_aggression_score"].mean()
    common_reason = rows["adaptive_policy_reason"].astype(str).str.split("|").str[0].str.strip().value_counts()
    return pd.DataFrame([
        {"diagnostic_type": "OVERALL", "rows": len(rows), "value": len(rows), "reason": "Self-adaptive policy rows processed"},
        {"diagnostic_type": "POLICY_DISTRIBUTION", "rows": len(rows), "value": ";".join(f"{k}:{v}" for k, v in policy_dist.items()), "reason": "Live adaptive policy distribution"},
        {"diagnostic_type": "PERMISSION_DISTRIBUTION", "rows": len(rows), "value": ";".join(f"{k}:{v}" for k, v in permission_dist.items()), "reason": "Denied/reduced/allowed count"},
        {"diagnostic_type": "DENIED_REDUCED_ALLOWED", "rows": len(rows), "value": f"DENY={denied};REDUCE={reduced};ALLOW={allowed}", "reason": "Execution permission summary"},
        {"diagnostic_type": "AVERAGE_TRUST", "rows": len(rows), "value": f"model={avg_model:.4f};market={avg_market:.4f}", "reason": "Average adaptive trust weights"},
        {"diagnostic_type": "AVERAGE_RISK_AGGRESSION", "rows": len(rows), "value": f"risk={avg_risk:.2f};aggression={avg_aggression:.2f}", "reason": "Average live risk/aggression"},
        {"diagnostic_type": "MOST_COMMON_REASON", "rows": int(common_reason.iloc[0]) if len(common_reason) else 0, "value": common_reason.index[0] if len(common_reason) else "", "reason": "Most common adaptive policy reason"},
    ])


def main():
    print("=" * 100)
    print("EDGEIQ SELF-ADAPTIVE POLICY ENGINE V2")
    print("=" * 100)
    live = read_csv(LIVE)
    if live.empty:
        pd.DataFrame(columns=OUTPUT_COLUMNS).to_csv(OUT, index=False)
        diagnostics(pd.DataFrame(columns=OUTPUT_COLUMNS)).to_csv(DIAGNOSTICS, index=False)
        print("[adaptive_v2] rows processed: 0")
        return

    base = add_keys(live)
    base = merge_by_runner(base, read_csv(UNCERTAINTY), ["uncertainty_band", "uncertainty_score"], "uncertainty")
    base = merge_by_runner(base, read_csv(FIRST_STARTER), ["debut_risk_grade", "first_starter_engine_flag", "no_official_form_engine_flag", "lightly_raced_engine_flag"], "first")
    base = merge_by_runner(base, read_csv(ENVIRONMENT), ["environment_type", "matched_interaction_recommendation"], "env")
    base = merge_by_runner(base, read_csv(MICROSTRUCTURE), ["microstructure_type", "microstructure_risk_grade"], "micro")
    base = merge_by_timing_window(base, read_csv(TIMING))
    base = merge_by_runner(base, read_csv(TRANSITIONS), ["transition_type", "execution_window_status"], "transition")

    policy_preference, policy_reason = preferred_policy(read_csv(POLICY_RANKINGS))
    results_penalty, results_reason = summary_bias(read_csv(RESULTS_SUMMARY))

    rows = compute_rows(base, policy_preference, policy_reason, results_penalty, results_reason)
    rows.to_csv(OUT, index=False)
    diagnostics(rows).to_csv(DIAGNOSTICS, index=False)

    live_rows = patch_board(LIVE, rows)
    terminal_rows = patch_board(TERMINAL, rows)

    policy_distribution = rows["adaptive_policy_v2"].value_counts().to_dict()
    permission_distribution = rows["adaptive_execution_permission"].value_counts().to_dict()
    print(f"[adaptive_v2] rows processed: {len(rows)}")
    print(f"[adaptive_v2] live board rows patched: {live_rows}")
    print(f"[adaptive_v2] terminal rows patched: {terminal_rows}")
    print(f"[adaptive_v2] policy distribution: {policy_distribution}")
    print(f"[adaptive_v2] permission distribution: {permission_distribution}")
    print(f"[adaptive_v2] average model trust: {rows['adaptive_model_trust'].mean():.4f}")
    print(f"[adaptive_v2] average market trust: {rows['adaptive_market_trust'].mean():.4f}")
    print(f"[adaptive_v2] wrote {OUT}")
    print(f"[adaptive_v2] wrote {DIAGNOSTICS}")
    print("=" * 100)


if __name__ == "__main__":
    main()
