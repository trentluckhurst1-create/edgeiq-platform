from pathlib import Path
import ast
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_execution_board_live.csv"
TERMINAL = DATA / "edgeiq_execution_board_terminal.csv"
FIRST_STARTER = DATA / "edgeiq_first_starter_engine_v1.csv"
UNCERTAINTY = DATA / "edgeiq_uncertainty_engine_v1.csv"
MICROSTRUCTURE = DATA / "edgeiq_market_microstructure_v1.csv"
TIMING = DATA / "edgeiq_temporal_execution_intelligence_v1.csv"
ENVIRONMENT = DATA / "edgeiq_environment_classification_v1.csv"
TRANSITIONS = DATA / "edgeiq_market_state_transitions_v1.csv"
BAYESIAN = DATA / "edgeiq_bayesian_blending_v1.csv"
SPORTSBET = DATA / "sportsbet_live_market_v1.csv"
REGIME_BOARD = DATA / "market_regime_board.csv"
MOVEMENT_BOARD = DATA / "market_movement_board.csv"

OUT = DATA / "edgeiq_market_confirmation_v2.csv"
DIAGNOSTICS = DATA / "edgeiq_market_confirmation_diagnostics_v2.csv"

OUTPUT_COLUMNS = [
    "track",
    "race_no",
    "horse",
    "market_confirmation_grade",
    "market_confirmation_score",
    "market_confirmation_reason",
    "confirmed_price_support",
    "drift_rejection_flag",
    "chaotic_noise_flag",
    "volatility_discount",
    "first_starter_market_support",
    "market_confirmation_probability_adjustment",
    "market_confirmation_stake_multiplier",
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
        print(f"[market_confirmation_v2] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"[market_confirmation_v2] read {path.name}: {len(df)} rows")
        return df
    except Exception as exc:
        print(f"[market_confirmation_v2] failed {path.name}: {exc}")
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


def parse_flucs(value):
    if isinstance(value, list):
        raw = value
    else:
        text = str(value or "").strip()
        if not text or text.lower() == "nan":
            return []
        try:
            raw = ast.literal_eval(text)
        except Exception:
            raw = re.findall(r"\d+(?:\.\d+)?", text)
    prices = []
    for item in raw:
        price = as_num(item, 0)
        if price > 1:
            prices.append(price)
    return prices


def sportsbet_features(row):
    current = as_num(row.get("sportsbet_price") or row.get("market_price") or row.get("current_price"), 0)
    flucs = parse_flucs(row.get("recent_odds_fluctuations"))
    if not flucs:
        open_price = as_num(row.get("open_price"), 0) or current
        return current, open_price, 0.0, False, False
    open_price = flucs[0]
    latest = current or flucs[-1]
    if open_price <= 0 or latest <= 0:
        return latest, open_price, 0.0, False, False
    move_pct = ((open_price - latest) / open_price) * 100.0
    firming = move_pct >= 5
    drifting = move_pct <= -12
    return latest, open_price, move_pct, firming, drifting


def protected_edge(row):
    return (
        clean(row.get("environment_type") or row.get("env_environment_type")) == "PROTECTED_EDGE"
        or clean(row.get("overlay_realism_grade")) == "REALISTIC"
        or "PROTECT" in clean(row.get("matched_interaction_recommendation") or row.get("env_matched_interaction_recommendation"))
    )


def confirmation_for_row(row):
    current, open_price, move_pct, firming, drifting = sportsbet_features(row)
    micro = clean(row.get("microstructure_type") or row.get("micro_microstructure_type"))
    environment = clean(row.get("environment_type") or row.get("env_environment_type"))
    timing = clean(row.get("timing_environment"))
    transition = clean(row.get("transition_type") or row.get("transition_transition_type"))
    movement_signal = clean(row.get("movement_signal") or row.get("move_movement_signal") or row.get("regime_movement_signal"))
    first_flag = clean(row.get("first_starter_engine_flag") or row.get("first_first_starter_engine_flag")) == "TRUE"
    no_form = clean(row.get("no_official_form_engine_flag") or row.get("first_no_official_form_engine_flag")) == "TRUE"
    uncertainty = clean(row.get("uncertainty_band") or row.get("uncertainty_uncertainty_band"))
    is_protected = protected_edge(row)

    reasons = []
    score = 50.0
    confirmed_price_support = False
    drift_rejection = False
    chaotic_noise = False
    volatility_discount = 0.0

    if current <= 0:
        return {
            "grade": "UNKNOWN",
            "score": 0.0,
            "reason": "no usable live market price",
            "confirmed": False,
            "drift": False,
            "noise": False,
            "discount": 0.0,
            "first_support": False,
            "adjustment": 0.0,
            "stake": 1.0,
        }

    if firming:
        score += min(25.0, move_pct * 0.8)
        confirmed_price_support = True
        reasons.append(f"price firming {move_pct:.1f}%")
    elif drifting:
        score -= min(35.0, abs(move_pct) * 0.9)
        drift_rejection = True
        reasons.append(f"price drifting {abs(move_pct):.1f}%")
    else:
        reasons.append("no decisive price confirmation")

    if movement_signal in {"STEAM", "MAJOR STEAM", "FIRMING", "CONTROLLED_FIRMING"}:
        score += 10
        confirmed_price_support = True
        reasons.append(f"movement signal {movement_signal}")
    elif movement_signal in {"DRIFTER", "MAJOR DRIFT", "DRIFT"}:
        score -= 12
        drift_rejection = True
        reasons.append(f"movement signal {movement_signal}")

    if micro in {"VOLATILITY_CLUSTER", "FALSE_STEAM", "PUBLIC_STEAM"}:
        score -= 18
        chaotic_noise = True
        volatility_discount += 0.35
        reasons.append(f"{micro} noise")
    elif micro in {"CONTROLLED_FIRMING", "SHARP_STEAM"}:
        score += 10
        reasons.append(f"{micro} support")

    if environment in {"CHAOTIC", "PUBLIC_TRAP", "VOLATILE"}:
        score -= 18
        chaotic_noise = True
        volatility_discount += 0.30
        reasons.append(f"{environment} environment")
    elif environment in {"CLEAN", "PROTECTED_EDGE", "SHARP"}:
        score += 8

    if timing == "TRAP_WINDOW" or transition == "EXECUTE_WINDOW_TO_AVOID":
        score -= 12
        chaotic_noise = True
        volatility_discount += 0.20
        reasons.append("execution window caution")

    first_support = bool((first_flag or no_form) and confirmed_price_support and not chaotic_noise and score >= 62)
    if first_flag or no_form:
        reasons.append("first/no-form profile requires market confirmation")
        if not first_support:
            score -= 8

    if drift_rejection and not is_protected:
        grade = "REJECTED"
    elif chaotic_noise:
        grade = "NOISY"
    elif score >= 72 and confirmed_price_support:
        grade = "CONFIRMED"
    elif score >= 58 and confirmed_price_support:
        grade = "WEAK_CONFIRMATION"
    elif score <= 38:
        grade = "REJECTED"
    else:
        grade = "UNKNOWN"

    adjustment = 0.0
    if grade == "CONFIRMED":
        adjustment = 0.05
    elif grade == "WEAK_CONFIRMATION":
        adjustment = 0.025
    elif grade == "REJECTED":
        adjustment = -0.05
    elif grade == "NOISY":
        adjustment = -0.02

    if uncertainty == "EXTREME" and adjustment > 0.015:
        adjustment = 0.015
        reasons.append("EXTREME uncertainty positive cap")
    if (first_flag or no_form) and not first_support and adjustment > 0:
        adjustment = 0.0
        reasons.append("no first/no-form confirmation lift")
    if clean(row.get("adaptive_policy_v2")) == "SAFE_MODE" and grade != "CONFIRMED":
        adjustment = min(adjustment, 0.0)

    stake = 1.0
    if grade == "CONFIRMED" and not chaotic_noise:
        stake = 1.03
    elif grade == "WEAK_CONFIRMATION":
        stake = 1.0
    elif grade == "NOISY":
        stake = 0.85
    elif grade == "REJECTED":
        stake = 0.75
    if uncertainty == "EXTREME":
        stake = min(stake, 1.0)

    return {
        "grade": grade,
        "score": max(0.0, min(100.0, round(score, 2))),
        "reason": " | ".join(reasons[:7]) or "neutral market evidence",
        "confirmed": confirmed_price_support,
        "drift": drift_rejection,
        "noise": chaotic_noise,
        "discount": round(min(1.0, volatility_discount), 2),
        "first_support": first_support,
        "adjustment": round(max(-0.075, min(0.05, adjustment)), 4),
        "stake": round(stake, 4),
    }


def build_rows(live):
    rows = []
    for _, row in live.iterrows():
        decision = confirmation_for_row(row)
        rows.append({
            "track": row.get("track", ""),
            "race_no": row.get("race_no", ""),
            "horse": row.get("horse", ""),
            "market_confirmation_grade": decision["grade"],
            "market_confirmation_score": decision["score"],
            "market_confirmation_reason": decision["reason"],
            "confirmed_price_support": str(decision["confirmed"]).upper(),
            "drift_rejection_flag": str(decision["drift"]).upper(),
            "chaotic_noise_flag": str(decision["noise"]).upper(),
            "volatility_discount": decision["discount"],
            "first_starter_market_support": str(decision["first_support"]).upper(),
            "market_confirmation_probability_adjustment": decision["adjustment"],
            "market_confirmation_stake_multiplier": decision["stake"],
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
    merged = board.merge(patch, on=["_horse_key", "_track_key", "_race_key"], how="left", suffixes=("", "_market_confirmation_new"))
    for col in patch_cols:
        extra = f"{col}_market_confirmation_new"
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
    dist = rows["market_confirmation_grade"].value_counts().to_dict()
    confirmed = int(rows["market_confirmation_grade"].isin(["CONFIRMED", "WEAK_CONFIRMATION"]).sum())
    rejected = int(rows["market_confirmation_grade"].eq("REJECTED").sum())
    noisy = int(rows["market_confirmation_grade"].eq("NOISY").sum())
    avg_adj = rows["market_confirmation_probability_adjustment"].map(lambda v: as_num(v, 0)).mean()
    no_form_confirm = int(rows["first_starter_market_support"].astype(str).str.upper().eq("TRUE").sum())
    strongest = rows.sort_values("market_confirmation_score", ascending=False).head(1)

    def row_value(df, cols):
        if df.empty:
            return ""
        row = df.iloc[0]
        return " | ".join(str(row.get(col, "")) for col in cols)

    return pd.DataFrame([
        {"diagnostic_type": "OVERALL", "rows": len(rows), "value": len(rows), "reason": "Market confirmation rows processed"},
        {"diagnostic_type": "CONFIRMATION_DISTRIBUTION", "rows": len(rows), "value": ";".join(f"{k}:{v}" for k, v in dist.items()), "reason": "Live confirmation grade distribution"},
        {"diagnostic_type": "CONFIRMED_REJECTED_NOISY", "rows": len(rows), "value": f"CONFIRMED={confirmed};REJECTED={rejected};NOISY={noisy}", "reason": "Confirmation action counts"},
        {"diagnostic_type": "AVERAGE_ADJUSTMENT", "rows": len(rows), "value": f"{avg_adj:.4f}", "reason": "Average capped probability adjustment"},
        {"diagnostic_type": "NO_FORM_CONFIRMATION_COUNT", "rows": no_form_confirm, "value": no_form_confirm, "reason": "First/no-form runners with usable market confirmation"},
        {"diagnostic_type": "STRONGEST_CONFIRMATION", "rows": 1 if len(strongest) else 0, "value": row_value(strongest, ["horse", "market_confirmation_grade", "market_confirmation_score"]), "reason": row_value(strongest, ["market_confirmation_reason"])},
    ])


def main():
    print("=" * 100)
    print("EDGEIQ MARKET CONFIRMATION ENGINE V2")
    print("=" * 100)
    live = read_csv(LIVE)
    if live.empty:
        pd.DataFrame(columns=OUTPUT_COLUMNS).to_csv(OUT, index=False)
        diagnostics(pd.DataFrame(columns=OUTPUT_COLUMNS)).to_csv(DIAGNOSTICS, index=False)
        print("[market_confirmation_v2] rows processed: 0")
        return

    base = add_runner_keys(live)
    base = merge_by_runner(base, read_csv(FIRST_STARTER), ["first_starter_engine_flag", "no_official_form_engine_flag"], "first")
    base = merge_by_runner(base, read_csv(UNCERTAINTY), ["uncertainty_band"], "uncertainty")
    base = merge_by_runner(base, read_csv(MICROSTRUCTURE), ["microstructure_type", "microstructure_risk_grade"], "micro")
    base = merge_by_runner(base, read_csv(ENVIRONMENT), ["environment_type", "matched_interaction_recommendation"], "env")
    base = merge_by_runner(base, read_csv(TRANSITIONS), ["transition_type", "execution_window_status"], "transition")
    base = merge_by_runner(base, read_csv(BAYESIAN), ["model_weight", "market_weight", "blended_overlay_pct"], "bayes")
    base = merge_by_runner(base, read_csv(SPORTSBET), ["sportsbet_price", "recent_odds_fluctuations", "market_mover"], "sportsbet")
    base = merge_by_runner(base, read_csv(REGIME_BOARD), ["market_regime", "movement_signal", "move_pct"], "regime")
    base = merge_by_runner(base, read_csv(MOVEMENT_BOARD), ["movement_signal", "open_price", "current_price", "move_pct"], "move")
    timing = read_csv(TIMING)
    if not timing.empty:
        print(f"[market_confirmation_v2] timing windows available: {len(timing)}")

    rows = build_rows(base)
    rows.to_csv(OUT, index=False)
    diagnostics(rows).to_csv(DIAGNOSTICS, index=False)

    live_rows = patch_board(LIVE, rows)
    terminal_rows = patch_board(TERMINAL, rows)
    dist = rows["market_confirmation_grade"].value_counts().to_dict()
    confirmed = int(rows["market_confirmation_grade"].isin(["CONFIRMED", "WEAK_CONFIRMATION"]).sum())
    rejected = int(rows["market_confirmation_grade"].eq("REJECTED").sum())
    noisy = int(rows["market_confirmation_grade"].eq("NOISY").sum())
    avg_adj = rows["market_confirmation_probability_adjustment"].mean()

    print(f"[market_confirmation_v2] rows processed: {len(rows)}")
    print(f"[market_confirmation_v2] live board rows patched: {live_rows}")
    print(f"[market_confirmation_v2] terminal rows patched: {terminal_rows}")
    print(f"[market_confirmation_v2] confirmation distribution: {dist}")
    print(f"[market_confirmation_v2] confirmed/rejected/noisy: {confirmed}/{rejected}/{noisy}")
    print(f"[market_confirmation_v2] average adjustment: {avg_adj:.4f}")
    print(f"[market_confirmation_v2] wrote {OUT}")
    print(f"[market_confirmation_v2] wrote {DIAGNOSTICS}")
    print("=" * 100)


if __name__ == "__main__":
    main()
