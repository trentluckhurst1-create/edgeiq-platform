from pathlib import Path
import os

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "public" / "data"

COUNTERFACTUAL = DATA / "edgeiq_counterfactual_engine_v1.csv"
HYPOTHESES = DATA / "edgeiq_hypothesis_engine_v1.csv"
LIVE = DATA / "edgeiq_execution_board_live.csv"
CONFIDENCE = DATA / "edgeiq_confidence_calibration_v1.csv"
SUPPRESSION = DATA / "edgeiq_suppression_intelligence.csv"
POLICY_OUT = DATA / "edgeiq_policy_engine_v1.csv"
LIVE_OUT = DATA / "edgeiq_execution_board_live.csv"
TERMINAL_OUT = DATA / "edgeiq_execution_board_terminal.csv"

POLICY_COLUMNS = [
    "policy_name",
    "active_policy",
    "min_confidence",
    "allowed_regimes",
    "allowed_realism_grades",
    "max_odds_bucket",
    "suppression_aggressiveness",
    "stake_multiplier",
    "overlay_tolerance",
    "drawdown_protection",
    "historical_policy_source",
    "rows_processed",
    "allowed_live_executions",
    "suppressed_by_policy",
    "reduced_by_policy",
    "watched_by_policy",
    "policy_risk_state",
]

TERMINAL_COLUMNS = [
    "timestamp",
    "track",
    "race_no",
    "race_time",
    "horse",
    "runner_number",
    "sportsbet_price",
    "rated_price",
    "adjusted_rated_price",
    "overlay_pct",
    "adjusted_overlay_pct",
    "overlay_realism_grade",
    "price_truth_adjustment_pct",
    "execution_action",
    "final_execution_state",
    "original_execution_state",
    "policy_original_execution_action",
    "price_truth_original_execution_action",
    "active_policy",
    "policy_decision",
    "policy_reason",
    "policy_stake_multiplier",
    "policy_risk_grade",
    "suppression_risk_grade",
    "suppression_recommendation",
    "suppression_intelligence_reason",
    "price_truth_reason",
    "overlay_tier",
    "final_action_v5_1",
    "cap_note_v5_1",
    "confidence_band_v1",
    "calibrated_confidence_label",
    "risk_flags",
    "market_mover",
    "recent_odds_fluctuations",
    "jockey",
    "trainer",
    "mobile_silk_image",
]

ODDS_ORDER = {
    "UNDER_3": 1,
    "3_TO_6": 2,
    "6_TO_12": 3,
    "12_TO_26": 4,
    "26_PLUS": 5,
    "UNKNOWN": 9,
}

CONFIDENCE_ORDER = {
    "VERY_LOW": 1,
    "LOW": 2,
    "MEDIUM": 3,
    "HIGH": 4,
    "VERY_HIGH": 5,
    "UNKNOWN": 0,
    "": 0,
}


def policies() -> dict[str, dict]:
    return {
        "DEFAULT": {
            "min_confidence": "VERY_LOW",
            "allowed_regimes": "ANY",
            "allowed_realism_grades": "REALISTIC,QUESTIONABLE,FAKE_OVERLAY,EXTREME_FAKE_OVERLAY,UNKNOWN",
            "max_odds_bucket": "26_PLUS",
            "suppression_aggressiveness": "NORMAL",
            "stake_multiplier": 1.0,
            "overlay_tolerance": -100.0,
            "drawdown_protection": "STANDARD",
        },
        "SAFE_MODE": {
            "min_confidence": "HIGH",
            "allowed_regimes": "STABLE,POSITIVE_CLV,UNKNOWN",
            "allowed_realism_grades": "REALISTIC,QUESTIONABLE,UNKNOWN",
            "max_odds_bucket": "12_TO_26",
            "suppression_aggressiveness": "HIGH",
            "stake_multiplier": 0.5,
            "overlay_tolerance": 0.0,
            "drawdown_protection": "HIGH",
        },
        "HIGH_CONFIDENCE_ONLY": {
            "min_confidence": "HIGH",
            "allowed_regimes": "ANY",
            "allowed_realism_grades": "REALISTIC,QUESTIONABLE,UNKNOWN",
            "max_odds_bucket": "26_PLUS",
            "suppression_aggressiveness": "MEDIUM",
            "stake_multiplier": 0.75,
            "overlay_tolerance": 0.0,
            "drawdown_protection": "MEDIUM",
        },
        "PROTECTED_EDGES_ONLY": {
            "min_confidence": "VERY_LOW",
            "allowed_regimes": "PROTECTED_ONLY",
            "allowed_realism_grades": "REALISTIC,QUESTIONABLE,UNKNOWN",
            "max_odds_bucket": "26_PLUS",
            "suppression_aggressiveness": "HIGH",
            "stake_multiplier": 0.75,
            "overlay_tolerance": -100.0,
            "drawdown_protection": "HIGH",
        },
        "LOW_DRAWDOWN_MODE": {
            "min_confidence": "MEDIUM",
            "allowed_regimes": "STABLE,DRIFTER,BIG DRIFTER,UNKNOWN",
            "allowed_realism_grades": "REALISTIC,QUESTIONABLE,UNKNOWN",
            "max_odds_bucket": "12_TO_26",
            "suppression_aggressiveness": "HIGH",
            "stake_multiplier": 0.5,
            "overlay_tolerance": 0.0,
            "drawdown_protection": "MAX",
        },
        "EXPERIMENTAL_MODE": {
            "min_confidence": "LOW",
            "allowed_regimes": "ANY",
            "allowed_realism_grades": "REALISTIC,QUESTIONABLE,FAKE_OVERLAY,UNKNOWN",
            "max_odds_bucket": "26_PLUS",
            "suppression_aggressiveness": "LOW",
            "stake_multiplier": 0.25,
            "overlay_tolerance": -10.0,
            "drawdown_protection": "LOW",
        },
    }


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"[policy_engine] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"[policy_engine] read {path.name}: {len(df)} rows")
        return df
    except Exception as exc:
        print(f"[policy_engine] warning: could not read {path.name}: {exc}")
        return pd.DataFrame()


def text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def upper(value) -> str:
    return text(value).upper()


def num(value, default=None):
    try:
        parsed = float(value)
    except Exception:
        return default
    return parsed if pd.notna(parsed) else default


def first_existing(df: pd.DataFrame, names: list[str]) -> str | None:
    for name in names:
        if name in df.columns:
            return name
    return None


def odds_bucket(price) -> str:
    value = num(price)
    if value is None or value <= 0:
        return "UNKNOWN"
    if value < 3:
        return "UNDER_3"
    if value < 6:
        return "3_TO_6"
    if value < 12:
        return "6_TO_12"
    if value < 26:
        return "12_TO_26"
    return "26_PLUS"


def confidence_bucket(confidence) -> str:
    label = upper(confidence)
    if label in CONFIDENCE_ORDER:
        return label
    value = num(confidence)
    if value is None:
        return "UNKNOWN"
    if value <= 20:
        return "VERY_LOW"
    if value <= 40:
        return "LOW"
    if value <= 60:
        return "MEDIUM"
    if value <= 80:
        return "HIGH"
    return "VERY_HIGH"


def overlay_bucket(overlay) -> str:
    value = num(overlay)
    if value is None:
        return "UNKNOWN"
    if value < 0:
        return "NEGATIVE_OVERLAY"
    if value < 10:
        return "0_TO_10"
    if value < 25:
        return "10_TO_25"
    if value < 50:
        return "25_TO_50"
    if value < 100:
        return "50_TO_100"
    return "100_PLUS"


def enrich_live(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        return out

    price_col = first_existing(out, ["sportsbet_price", "market_price", "current_price", "fixed_odds", "win_odds"])
    confidence_col = first_existing(out, ["calibrated_confidence_label", "confidence_band_v1", "confidence", "calibrated_confidence_score"])
    overlay_col = first_existing(out, ["adjusted_overlay_pct", "overlay_pct", "edge_pct"])

    out["_policy_odds_bucket"] = out[price_col].map(odds_bucket) if price_col else "UNKNOWN"
    out["_policy_confidence_bucket"] = out[confidence_col].map(confidence_bucket) if confidence_col else "UNKNOWN"
    out["_policy_overlay_value"] = pd.to_numeric(out[overlay_col], errors="coerce") if overlay_col else 0.0
    out["_policy_overlay_bucket"] = out[overlay_col].map(overlay_bucket) if overlay_col else "UNKNOWN"

    aliases = {
        "_policy_regime": ["market_regime_v2", "market_regime", "regime"],
        "_policy_realism": ["overlay_realism_grade"],
        "_policy_suppression": ["suppression_risk_grade"],
        "_policy_action": ["policy_original_execution_action", "final_execution_state", "execution_action"],
    }
    for target, names in aliases.items():
        source = first_existing(out, names)
        out[target] = out[source].map(lambda x: upper(x) or "UNKNOWN") if source else "UNKNOWN"
    return out


def protected_segments(hypotheses: pd.DataFrame) -> dict[str, set[str]]:
    if hypotheses.empty:
        return {}
    required = {"trigger_factor", "trigger_value", "status"}
    if not required.issubset(hypotheses.columns):
        return {}
    protected = hypotheses[hypotheses["status"].astype(str).str.upper() == "PROTECT_EDGE"]
    out: dict[str, set[str]] = {}
    for factor, group in protected.groupby("trigger_factor"):
        out[str(factor)] = {upper(v) for v in group["trigger_value"].dropna().tolist()}
    return out


def row_matches_protected(row: pd.Series, protected: dict[str, set[str]]) -> bool:
    for factor, values in protected.items():
        lookup = factor
        if factor == "odds_bucket":
            lookup = "_policy_odds_bucket"
        elif factor == "overlay_bucket":
            lookup = "_policy_overlay_bucket"
        elif factor == "adjusted_overlay_bucket":
            lookup = "_policy_overlay_bucket"
        elif factor == "confidence_bucket":
            lookup = "_policy_confidence_bucket"
        elif factor == "market_regime":
            lookup = "market_regime"
        elif factor == "market_regime_v2":
            lookup = "market_regime_v2"
        elif factor == "overlay_realism_grade":
            lookup = "_policy_realism"
        if lookup in row.index and upper(row.get(lookup)) in values:
            return True
    return False


def downgrade(action: str, target: str) -> str:
    action = upper(action) or "PASS"
    if target == "SUPPRESS":
        return "SUPPRESS"
    if target == "WATCH":
        if action in {"MAX_BET", "PRIORITY_EXECUTE", "EXECUTE", "REDUCED_EXECUTE"}:
            return "WATCH"
        if action in {"WATCH", "MONITOR"}:
            return "WATCH"
        return action
    if target == "REDUCED_EXECUTE":
        if action in {"MAX_BET", "PRIORITY_EXECUTE", "EXECUTE"}:
            return "REDUCED_EXECUTE"
        return action
    return action


def evaluate_policy(row: pd.Series, policy_name: str, policy: dict, protected: dict[str, set[str]]) -> tuple[str, str, float, str]:
    action = upper(row.get("_policy_action")) or "PASS"
    reasons = []
    risk = "ALLOW"

    confidence = upper(row.get("_policy_confidence_bucket"))
    min_conf = upper(policy["min_confidence"])
    if CONFIDENCE_ORDER.get(confidence, 0) < CONFIDENCE_ORDER.get(min_conf, 0):
        reasons.append(f"confidence {confidence or 'UNKNOWN'} below {min_conf}")
        action = downgrade(action, "SUPPRESS" if policy["suppression_aggressiveness"] == "HIGH" else "WATCH")
        risk = "SUPPRESS" if policy["suppression_aggressiveness"] == "HIGH" else "WATCH"

    max_bucket = upper(policy["max_odds_bucket"])
    odds = upper(row.get("_policy_odds_bucket"))
    if ODDS_ORDER.get(odds, 9) > ODDS_ORDER.get(max_bucket, 9):
        reasons.append(f"odds bucket {odds} above {max_bucket}")
        action = downgrade(action, "SUPPRESS" if policy["suppression_aggressiveness"] in {"HIGH", "NORMAL"} else "WATCH")
        risk = "SUPPRESS"

    allowed_regimes = {x.strip().upper() for x in str(policy["allowed_regimes"]).split(",")}
    regime = upper(row.get("_policy_regime"))
    if "ANY" not in allowed_regimes and "PROTECTED_ONLY" not in allowed_regimes and regime not in allowed_regimes:
        reasons.append(f"regime {regime} not allowed")
        action = downgrade(action, "SUPPRESS" if policy["suppression_aggressiveness"] == "HIGH" else "WATCH")
        risk = "SUPPRESS"

    if "PROTECTED_ONLY" in allowed_regimes and not row_matches_protected(row, protected):
        reasons.append("not matched to protected historical edge")
        action = downgrade(action, "SUPPRESS")
        risk = "SUPPRESS"

    allowed_realism = {x.strip().upper() for x in str(policy["allowed_realism_grades"]).split(",")}
    realism = upper(row.get("_policy_realism")) or "UNKNOWN"
    if realism not in allowed_realism:
        reasons.append(f"realism {realism} not allowed")
        action = downgrade(action, "SUPPRESS" if "FAKE" in realism or policy["suppression_aggressiveness"] == "HIGH" else "WATCH")
        risk = "SUPPRESS" if "FAKE" in realism else "WATCH"

    overlay = num(row.get("_policy_overlay_value"), 0.0) or 0.0
    tolerance = float(policy["overlay_tolerance"])
    if overlay < tolerance:
        reasons.append(f"adjusted overlay {overlay:.1f}% below tolerance {tolerance:.1f}%")
        action = downgrade(action, "WATCH" if action in {"EXECUTE", "MAX_BET", "PRIORITY_EXECUTE"} else "SUPPRESS")
        risk = "WATCH" if risk == "ALLOW" else risk

    suppression = upper(row.get("_policy_suppression"))
    if suppression == "KILL":
        reasons.append("historical suppression grade KILL")
        action = downgrade(action, "SUPPRESS" if policy["suppression_aggressiveness"] != "LOW" else "WATCH")
        risk = "KILL"
    elif suppression == "SUPPRESS" and policy["suppression_aggressiveness"] in {"HIGH", "NORMAL"}:
        reasons.append("historical suppression grade SUPPRESS")
        action = downgrade(action, "SUPPRESS")
        risk = "SUPPRESS"
    elif suppression == "REDUCE" and policy["suppression_aggressiveness"] == "HIGH":
        reasons.append("historical suppression grade REDUCE")
        action = downgrade(action, "WATCH")
        risk = "REDUCE" if risk == "ALLOW" else risk

    multiplier = float(policy["stake_multiplier"])
    if action in {"SUPPRESS", "PASS"}:
        multiplier = 0.0
    elif action in {"WATCH", "MONITOR"}:
        multiplier = min(multiplier, 0.25)
    elif action == "REDUCED_EXECUTE":
        multiplier = min(multiplier, 0.5)

    if not reasons:
        reasons.append("policy allows existing execution state")

    return action, " | ".join(reasons), multiplier, risk


def historical_source(counterfactual: pd.DataFrame, policy_name: str) -> str:
    if counterfactual.empty or "policy_name" not in counterfactual.columns:
        return ""
    match = counterfactual[counterfactual["policy_name"].astype(str).str.upper() == policy_name]
    if match.empty:
        return ""
    row = match.iloc[0]
    return f"ROI_DELTA={text(row.get('delta_vs_original_roi'))}; DD_DELTA={text(row.get('delta_vs_original_drawdown'))}; STABILITY={text(row.get('edge_stability_score'))}"


def write_terminal(df: pd.DataFrame):
    terminal = pd.DataFrame()
    for col in TERMINAL_COLUMNS:
        terminal[col] = df[col] if col in df.columns else ""
    terminal.to_csv(TERMINAL_OUT, index=False)


def main():
    DATA.mkdir(parents=True, exist_ok=True)

    counterfactual = read_csv(COUNTERFACTUAL)
    hypotheses = read_csv(HYPOTHESES)
    live = enrich_live(read_csv(LIVE))
    confidence = read_csv(CONFIDENCE)
    suppression = read_csv(SUPPRESSION)

    policy_map = policies()
    active_policy = upper(os.environ.get("EDGEIQ_ACTIVE_POLICY", "DEFAULT"))
    if active_policy not in policy_map:
        print(f"[policy_engine] unknown EDGEIQ_ACTIVE_POLICY={active_policy}; using DEFAULT")
        active_policy = "DEFAULT"

    protected = protected_segments(hypotheses)
    active = policy_map[active_policy]

    if live.empty:
        pd.DataFrame(columns=POLICY_COLUMNS).to_csv(POLICY_OUT, index=False)
        print("[policy_engine] no live board rows; wrote empty policy file")
        return

    output = live.copy()
    if "original_execution_state" not in output.columns:
        output["original_execution_state"] = output.get("execution_action", "")
    if "original_stake" not in output.columns:
        output["original_stake"] = output.get("stake_units_v4_1", "")
    if "policy_original_execution_action" not in output.columns:
        output["policy_original_execution_action"] = output.get("execution_action", "")
    else:
        existing_original = output["policy_original_execution_action"].astype(str).str.strip()
        output.loc[existing_original == "", "policy_original_execution_action"] = output.get("execution_action", "")
    output["_policy_action"] = output["policy_original_execution_action"].map(lambda x: upper(x) or "PASS")

    decisions = []
    reasons = []
    multipliers = []
    risks = []
    modified = 0
    suppressed = 0
    reduced = 0
    watched = 0

    for idx, row in output.iterrows():
        before = upper(row.get("execution_action") or row.get("final_execution_state"))
        decision, reason, multiplier, risk = evaluate_policy(row, active_policy, active, protected)
        decisions.append(decision)
        reasons.append(reason)
        multipliers.append(multiplier)
        risks.append(risk)
        if decision != before:
            modified += 1
        if decision == "SUPPRESS":
            suppressed += 1
        if decision == "REDUCED_EXECUTE":
            reduced += 1
        if decision == "WATCH":
            watched += 1
        output.at[idx, "execution_action"] = decision
        output.at[idx, "final_execution_state"] = decision

    output["active_policy"] = active_policy
    output["policy_decision"] = decisions
    output["policy_reason"] = reasons
    output["policy_stake_multiplier"] = multipliers
    output["policy_risk_grade"] = risks

    output = output.drop(columns=[c for c in output.columns if c.startswith("_policy_")], errors="ignore")
    output.to_csv(LIVE_OUT, index=False)
    write_terminal(output)

    allowed = int(output["policy_decision"].isin(["EXECUTE", "MAX_BET", "PRIORITY_EXECUTE", "REDUCED_EXECUTE"]).sum())
    policy_rows = []
    for name, policy in policy_map.items():
        policy_rows.append({
            "policy_name": name,
            "active_policy": "TRUE" if name == active_policy else "FALSE",
            "min_confidence": policy["min_confidence"],
            "allowed_regimes": policy["allowed_regimes"],
            "allowed_realism_grades": policy["allowed_realism_grades"],
            "max_odds_bucket": policy["max_odds_bucket"],
            "suppression_aggressiveness": policy["suppression_aggressiveness"],
            "stake_multiplier": policy["stake_multiplier"],
            "overlay_tolerance": policy["overlay_tolerance"],
            "drawdown_protection": policy["drawdown_protection"],
            "historical_policy_source": historical_source(counterfactual, name),
            "rows_processed": len(output) if name == active_policy else "",
            "allowed_live_executions": allowed if name == active_policy else "",
            "suppressed_by_policy": suppressed if name == active_policy else "",
            "reduced_by_policy": reduced if name == active_policy else "",
            "watched_by_policy": watched if name == active_policy else "",
            "policy_risk_state": "DEFENSIVE" if suppressed else "OPEN",
        })
    pd.DataFrame(policy_rows, columns=POLICY_COLUMNS).to_csv(POLICY_OUT, index=False)

    print("[policy_engine] confidence rows available:", len(confidence))
    print("[policy_engine] suppression rows available:", len(suppression))
    print("[policy_engine] policies created:", len(policy_map))
    print("[policy_engine] active policy:", active_policy)
    print("[policy_engine] rows processed:", len(output))
    print("[policy_engine] rows modified by policy:", modified)
    print("[policy_engine] allowed live executions:", allowed)
    print("[policy_engine] suppressions by policy:", suppressed)
    print("[policy_engine] reduced by policy:", reduced)
    print("[policy_engine] watched by policy:", watched)


if __name__ == "__main__":
    main()
