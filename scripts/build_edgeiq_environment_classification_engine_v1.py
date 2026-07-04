from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "public" / "data"

LIVE = DATA / "edgeiq_execution_board_live.csv"
TERMINAL = DATA / "edgeiq_execution_board_terminal.csv"
INTERACTIONS = DATA / "edgeiq_feature_interactions_v1.csv"
INTERACTION_RANKINGS = DATA / "edgeiq_feature_interaction_rankings_v1.csv"
POLICY_RANKINGS = DATA / "edgeiq_policy_rankings_v1.csv"
REGIME = DATA / "edgeiq_market_regime_v2.csv"
CALIBRATION = DATA / "edgeiq_probability_calibration_v1.csv"
BAYESIAN = DATA / "edgeiq_bayesian_blending_v1.csv"

OUT_ENV = DATA / "edgeiq_environment_classification_v1.csv"
OUT_RANKINGS = DATA / "edgeiq_environment_rankings_v1.csv"

ENV_COLUMNS = [
    "track",
    "race_no",
    "horse",
    "environment_type",
    "environment_confidence",
    "environment_risk_grade",
    "environment_reason",
    "recommended_policy",
    "recommended_model_weight",
    "recommended_market_weight",
    "recommended_execution_aggression",
    "recommended_stake_multiplier",
    "environment_adjusted_execution_action",
    "environment_original_execution_action",
    "environment_applied",
    "matched_interaction_key",
    "matched_interaction_grade",
    "matched_interaction_recommendation",
]

RANKING_COLUMNS = [
    "ranking_type",
    "environment_type",
    "rows",
    "avg_confidence",
    "avg_model_weight",
    "avg_market_weight",
    "suppression_rate",
    "executable_rate",
    "fake_overlay_rate",
    "avg_stake_multiplier",
    "risk_grade",
    "recommended_policy",
    "reason",
]


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"[environment] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"[environment] read {path.name}: {len(df)} rows")
        return df
    except pd.errors.EmptyDataError:
        print(f"[environment] empty {path.name}")
        return pd.DataFrame()
    except Exception as exc:
        print(f"[environment] warning: could not read {path.name}: {exc}")
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


def runner_key(df: pd.DataFrame) -> pd.Series:
    parts = []
    for col in ["track", "race_no", "horse"]:
        if col in df.columns:
            parts.append(df[col].map(upper))
        else:
            parts.append(pd.Series([""] * len(df), index=df.index))
    return parts[0] + "|" + parts[1] + "|" + parts[2]


def merge_runner(live: pd.DataFrame, extra: pd.DataFrame, cols: list[str], suffix: str) -> pd.DataFrame:
    if live.empty or extra.empty:
        return live
    if not {"track", "race_no", "horse"}.issubset(live.columns) or not {"track", "race_no", "horse"}.issubset(extra.columns):
        return live
    available = [col for col in cols if col in extra.columns]
    if not available:
        return live

    left = live.copy()
    right = extra.copy()
    left["_env_key"] = runner_key(left)
    right["_env_key"] = runner_key(right)
    right = right[["_env_key"] + available].drop_duplicates("_env_key", keep="last")
    merged = left.merge(right, on="_env_key", how="left", suffixes=("", suffix))

    for col in available:
        extra_col = f"{col}{suffix}"
        if extra_col in merged.columns:
            if col in merged.columns:
                current = merged[col].map(text)
                merged[col] = merged[col].where(current != "", merged[extra_col])
                merged[col] = merged[col].fillna(merged[extra_col])
            else:
                merged[col] = merged[extra_col]
            merged = merged.drop(columns=[extra_col])

    return merged.drop(columns=["_env_key"], errors="ignore")


def probability_bucket(value) -> str:
    parsed = num(value)
    if parsed is None:
        return ""
    if parsed < 0.05:
        return "0_5"
    if parsed < 0.10:
        return "5_10"
    if parsed < 0.15:
        return "10_15"
    if parsed < 0.20:
        return "15_20"
    if parsed < 0.30:
        return "20_30"
    return "30_PLUS"


def odds_bucket(value) -> str:
    parsed = num(value)
    if parsed is None:
        return ""
    if parsed <= 2:
        return "ODDS_<=2"
    if parsed <= 4:
        return "ODDS_2_TO_4"
    if parsed <= 8:
        return "ODDS_4_TO_8"
    if parsed <= 15:
        return "ODDS_8_TO_15"
    if parsed <= 26:
        return "ODDS_15_TO_26"
    return "ODDS_26_PLUS"


def overlay_bucket(value) -> str:
    parsed = num(value)
    if parsed is None:
        return ""
    if parsed < 0:
        return "NEGATIVE"
    if parsed < 10:
        return "0_TO_10"
    if parsed < 25:
        return "10_TO_25"
    if parsed < 50:
        return "25_TO_50"
    if parsed < 100:
        return "50_TO_100"
    return "100_PLUS"


def coalesce(row: pd.Series, cols: list[str]) -> str:
    for col in cols:
        if col in row.index and text(row.get(col)):
            return text(row.get(col))
    return ""


def recommended_policy(policy: pd.DataFrame) -> str:
    if policy.empty:
        return "DEFAULT"
    if {"ranking_type", "recommended_active_policy"}.issubset(policy.columns):
        rec = policy[policy["ranking_type"].map(upper) == "RECOMMENDED_ACTIVE_POLICY"]
        if len(rec):
            value = text(rec.iloc[0].get("recommended_active_policy"))
            if value:
                return value
    if "policy_name" in policy.columns and len(policy):
        return text(policy.iloc[0].get("policy_name")) or "DEFAULT"
    return "DEFAULT"


def calibration_summary(calibration: pd.DataFrame) -> tuple[str, float]:
    if calibration.empty:
        return "UNKNOWN", 0.0
    overall = calibration[calibration.get("bucket_type", pd.Series(dtype=str)).map(upper) == "OVERALL"]
    row = overall.iloc[0] if len(overall) else calibration.iloc[0]
    grade = upper(row.get("reliability_grade")) or "UNKNOWN"
    error = abs(num(row.get("calibration_error"), 0.0) or 0.0)
    return grade, error


def interaction_lookup(interactions: pd.DataFrame) -> dict[tuple[str, str, str, str], dict]:
    lookup: dict[tuple[str, str, str, str], dict] = {}
    if interactions.empty:
        return lookup
    required = {"feature_a", "value_a", "feature_b", "value_b"}
    if not required.issubset(interactions.columns):
        return lookup
    for _, row in interactions.iterrows():
        key = (upper(row.get("feature_a")), upper(row.get("value_a")), upper(row.get("feature_b")), upper(row.get("value_b")))
        rev = (key[2], key[3], key[0], key[1])
        value = row.to_dict()
        lookup[key] = value
        lookup[rev] = value
    return lookup


def live_features(row: pd.Series) -> dict[str, str]:
    market_regime = coalesce(row, ["market_regime_v2", "market_regime", "regime"])
    confidence = coalesce(row, ["calibrated_confidence_label", "confidence_band_v1", "confidence"])
    market_price = coalesce(row, ["sportsbet_price", "market_price", "current_price"])
    overlay = coalesce(row, ["blended_overlay_pct", "shrunk_overlay_pct", "adjusted_overlay_pct", "overlay_pct"])
    return {
        "market_regime": upper(market_regime),
        "confidence": upper(confidence),
        "suppression_risk_grade": upper(coalesce(row, ["suppression_risk_grade"])),
        "final_execution_state": upper(coalesce(row, ["final_execution_state", "execution_action"])),
        "track": upper(coalesce(row, ["track"])),
        "race_class": upper(coalesce(row, ["race_class"])),
        "speed_map_bucket": upper(coalesce(row, ["speed_map_bucket"])),
        "track_condition": upper(coalesce(row, ["track_condition"])),
        "odds_bucket": odds_bucket(market_price),
        "overlay_bucket": overlay_bucket(overlay),
    }


def matched_interactions(features: dict[str, str], lookup: dict[tuple[str, str, str, str], dict]) -> list[dict]:
    pairs = [
        ("market_regime", "confidence"),
        ("market_regime", "odds_bucket"),
        ("market_regime", "overlay_bucket"),
        ("confidence", "odds_bucket"),
        ("confidence", "overlay_bucket"),
        ("suppression_risk_grade", "market_regime"),
        ("final_execution_state", "market_regime"),
        ("track", "market_regime"),
        ("race_class", "market_regime"),
        ("speed_map_bucket", "market_regime"),
        ("track_condition", "market_regime"),
    ]
    matches = []
    for a, b in pairs:
        va = features.get(a, "")
        vb = features.get(b, "")
        if not va or not vb:
            continue
        found = lookup.get((upper(a), upper(va), upper(b), upper(vb)))
        if found:
            matches.append(found)
    return matches


def classify(row: pd.Series, interactions: list[dict], policy_rec: str, calibration_grade: str) -> dict:
    regime = upper(coalesce(row, ["market_regime_v2", "market_regime"]))
    confidence = upper(coalesce(row, ["calibrated_confidence_label", "confidence_band_v1", "confidence"]))
    risk = upper(coalesce(row, ["suppression_risk_grade", "policy_risk_grade"]))
    realism = upper(coalesce(row, ["overlay_realism_grade"]))
    action = upper(coalesce(row, ["final_execution_state", "execution_action"]))
    model_weight = num(row.get("model_weight"), num(row.get("model_weight_v5_1"), 0.5)) or 0.5
    market_weight = num(row.get("market_weight"), num(row.get("market_weight_v5_1"), 0.5)) or 0.5
    blended_overlay = num(coalesce(row, ["blended_overlay_pct", "shrunk_overlay_pct", "adjusted_overlay_pct", "overlay_pct"]), 0.0) or 0.0
    market_price = num(coalesce(row, ["sportsbet_price", "market_price", "current_price"]), 0.0) or 0.0

    toxic_matches = [m for m in interactions if upper(m.get("interaction_grade")) in {"TOXIC", "WEAK"}]
    edge_matches = [m for m in interactions if upper(m.get("interaction_grade")) in {"STRONG_EDGE", "POSSIBLE_EDGE"}]
    suppress_matches = [m for m in interactions if upper(m.get("recommendation")) == "SUPPRESS"]
    protect_matches = [m for m in interactions if upper(m.get("recommendation")) == "PROTECT"]

    fake_overlay = "FAKE" in realism or blended_overlay >= 100
    volatile = any(token in regime for token in ["VOLATILE", "TOXIC", "STEAM", "SHOCK", "EXTREME"])
    illiquid = market_price >= 26 or "ROUGHIE" in regime
    suppressed = action in {"SUPPRESS", "PASS", "NO BET"} or risk in {"KILL", "SUPPRESS"}
    executable = action in {"MAX_BET", "PRIORITY_EXECUTE", "EXECUTE", "REDUCED_EXECUTE", "BET"}
    stable = "STABLE" in regime

    risk_points = 0
    reasons = []
    if volatile:
        risk_points += 25
        reasons.append("volatile/toxic regime")
    if fake_overlay:
        risk_points += 25
        reasons.append("fake overlay exposure")
    if suppressed:
        risk_points += 20
        reasons.append("suppression pressure")
    if toxic_matches:
        risk_points += min(30, 10 * len(toxic_matches))
        reasons.append(f"{len(toxic_matches)} toxic/weak interactions")
    if confidence in {"VERY_LOW", "LOW"}:
        risk_points += 15
        reasons.append(f"{confidence} confidence")
    if market_weight >= 0.65:
        risk_points += 10
        reasons.append("market-weighted blend")
    if edge_matches:
        risk_points -= min(20, 8 * len(edge_matches))
        reasons.append(f"{len(edge_matches)} positive interactions")
    if protect_matches:
        risk_points -= 15
        reasons.append("protected interaction")
    if calibration_grade in {"SHARP", "ACCEPTABLE"}:
        risk_points -= 5
        reasons.append(f"{calibration_grade} calibration")

    confidence_score = max(20, min(95, 50 + abs(risk_points) + (10 if interactions else 0)))

    if protect_matches and stable and confidence in {"HIGH", "VERY_HIGH"}:
        env = "PROTECTED_EDGE"
    elif suppress_matches or (risk_points >= 60 and fake_overlay):
        env = "CHAOTIC"
    elif volatile and market_weight >= 0.65:
        env = "VOLATILE"
    elif illiquid and (fake_overlay or risk in {"KILL", "SUPPRESS"}):
        env = "ILLIQUID"
    elif fake_overlay and confidence in {"VERY_LOW", "LOW"}:
        env = "PUBLIC_TRAP"
    elif edge_matches and blended_overlay > 0:
        env = "OVERREACTION"
    elif market_weight >= 0.65 and calibration_grade in {"SHARP", "ACCEPTABLE"} and not volatile:
        env = "SHARP"
    elif stable and risk_points <= 10:
        env = "CLEAN"
    else:
        env = "NEUTRAL"

    if env in {"CHAOTIC", "PUBLIC_TRAP", "ILLIQUID"}:
        risk_grade = "RED"
        aggression = "DEFENSIVE"
        stake_mult = 0.25
        rec_model = min(model_weight, 0.35)
        rec_market = 1.0 - rec_model
    elif env == "VOLATILE":
        risk_grade = "AMBER"
        aggression = "REDUCED"
        stake_mult = 0.5
        rec_model = min(model_weight, 0.45)
        rec_market = 1.0 - rec_model
    elif env == "PROTECTED_EDGE":
        risk_grade = "GREEN"
        aggression = "SELECTIVE_ATTACK"
        stake_mult = 1.0
        rec_model = max(model_weight, 0.6)
        rec_market = 1.0 - rec_model
    elif env in {"CLEAN", "SHARP", "OVERREACTION"}:
        risk_grade = "GREEN" if env == "CLEAN" else "AMBER"
        aggression = "NORMAL"
        stake_mult = 0.75 if env != "CLEAN" else 1.0
        rec_model = model_weight
        rec_market = market_weight
    else:
        risk_grade = "AMBER"
        aggression = "BALANCED"
        stake_mult = 0.5
        rec_model = model_weight
        rec_market = market_weight

    adjusted_action = action
    if env in {"CHAOTIC", "PUBLIC_TRAP", "ILLIQUID"} and executable:
        adjusted_action = "WATCH"
    if env == "CHAOTIC" and action in {"MAX_BET", "PRIORITY_EXECUTE", "EXECUTE", "REDUCED_EXECUTE"}:
        adjusted_action = "SUPPRESS"
    if env == "VOLATILE" and action in {"MAX_BET", "PRIORITY_EXECUTE"}:
        adjusted_action = "EXECUTE"

    best_match = interactions[0] if interactions else {}
    return {
        "environment_type": env,
        "environment_confidence": round(confidence_score, 2),
        "environment_risk_grade": risk_grade,
        "environment_reason": " | ".join(reasons) if reasons else "balanced environment",
        "recommended_policy": "SAFE_MODE" if env in {"CHAOTIC", "PUBLIC_TRAP", "ILLIQUID", "VOLATILE"} else policy_rec,
        "recommended_model_weight": round(rec_model, 4),
        "recommended_market_weight": round(rec_market, 4),
        "recommended_execution_aggression": aggression,
        "recommended_stake_multiplier": round(stake_mult, 2),
        "environment_adjusted_execution_action": adjusted_action,
        "environment_original_execution_action": action,
        "environment_applied": adjusted_action != action,
        "matched_interaction_key": text(best_match.get("interaction_key")),
        "matched_interaction_grade": text(best_match.get("interaction_grade")),
        "matched_interaction_recommendation": text(best_match.get("recommendation")),
    }


def append_environment_to_terminal(terminal: pd.DataFrame, env: pd.DataFrame) -> pd.DataFrame:
    if terminal.empty or env.empty:
        return terminal
    if not {"track", "race_no", "horse"}.issubset(terminal.columns):
        return terminal
    left = terminal.copy()
    right = env.copy()
    left["_env_key"] = runner_key(left)
    right["_env_key"] = runner_key(right)
    env_cols = [col for col in ENV_COLUMNS if col in right.columns and col not in {"track", "race_no", "horse"}]
    right = right[["_env_key"] + env_cols].drop_duplicates("_env_key", keep="last")
    merged = left.merge(right, on="_env_key", how="left", suffixes=("", "_env"))
    return merged.drop(columns=["_env_key"], errors="ignore")


def make_rankings(env: pd.DataFrame) -> pd.DataFrame:
    if env.empty:
        return pd.DataFrame(columns=RANKING_COLUMNS)

    rows = []
    for env_type, group in env.groupby("environment_type", dropna=True):
        risk = group["environment_risk_grade"].mode().iloc[0] if len(group["environment_risk_grade"].mode()) else ""
        policy = group["recommended_policy"].mode().iloc[0] if len(group["recommended_policy"].mode()) else ""
        suppressed = group["environment_adjusted_execution_action"].map(upper).isin(["SUPPRESS", "PASS", "NO BET"]).mean() * 100.0
        executable = group["environment_adjusted_execution_action"].map(upper).isin(["MAX_BET", "PRIORITY_EXECUTE", "EXECUTE", "REDUCED_EXECUTE", "BET"]).mean() * 100.0
        fake = group["environment_reason"].map(lambda v: "fake overlay" in text(v).lower()).mean() * 100.0
        rows.append({
            "ranking_type": "ENVIRONMENT_SUMMARY",
            "environment_type": env_type,
            "rows": len(group),
            "avg_confidence": round(pd.to_numeric(group["environment_confidence"], errors="coerce").mean(), 2),
            "avg_model_weight": round(pd.to_numeric(group["recommended_model_weight"], errors="coerce").mean(), 4),
            "avg_market_weight": round(pd.to_numeric(group["recommended_market_weight"], errors="coerce").mean(), 4),
            "suppression_rate": round(suppressed, 2),
            "executable_rate": round(executable, 2),
            "fake_overlay_rate": round(fake, 2),
            "avg_stake_multiplier": round(pd.to_numeric(group["recommended_stake_multiplier"], errors="coerce").mean(), 2),
            "risk_grade": risk,
            "recommended_policy": policy,
            "reason": "Live environment classification summary",
        })

    ranking = pd.DataFrame(rows, columns=RANKING_COLUMNS)
    if ranking.empty:
        return ranking

    risk_score = {"GREEN": 0, "AMBER": 1, "RED": 2}
    ranking["_risk_score"] = ranking["risk_grade"].map(lambda v: risk_score.get(upper(v), 1))
    ranking["_toxicity"] = ranking["_risk_score"] * 100 + ranking["suppression_rate"] + ranking["fake_overlay_rate"]
    ranking["_safety"] = (2 - ranking["_risk_score"]) * 100 + ranking["executable_rate"] - ranking["fake_overlay_rate"]

    extra = []
    safest = ranking.sort_values(["_safety", "rows"], ascending=[False, False]).head(1)
    toxic = ranking.sort_values(["_toxicity", "rows"], ascending=[False, False]).head(1)
    protected = ranking[ranking["environment_type"] == "PROTECTED_EDGE"].head(1)
    if len(safest):
        row = safest.iloc[0].copy()
        row["ranking_type"] = "SAFEST_ENVIRONMENT"
        row["reason"] = "Lowest live risk/fake-overlay pressure"
        extra.append(row)
    if len(toxic):
        row = toxic.iloc[0].copy()
        row["ranking_type"] = "MOST_TOXIC_ENVIRONMENT"
        row["reason"] = "Highest live risk/fake-overlay pressure"
        extra.append(row)
    if len(protected):
        row = protected.iloc[0].copy()
        row["ranking_type"] = "STRONGEST_PROTECTED_EDGE_ENVIRONMENT"
        row["reason"] = "Protected-edge environment currently present"
        extra.append(row)

    if extra:
        ranking = pd.concat([ranking, pd.DataFrame(extra)], ignore_index=True)
    return ranking.drop(columns=["_risk_score", "_toxicity", "_safety"], errors="ignore")


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    live = read_csv(LIVE)
    interactions = read_csv(INTERACTIONS)
    interaction_rankings = read_csv(INTERACTION_RANKINGS)
    policy_rankings = read_csv(POLICY_RANKINGS)
    regime = read_csv(REGIME)
    calibration = read_csv(CALIBRATION)
    bayesian = read_csv(BAYESIAN)

    if live.empty:
        pd.DataFrame(columns=ENV_COLUMNS).to_csv(OUT_ENV, index=False)
        pd.DataFrame(columns=RANKING_COLUMNS).to_csv(OUT_RANKINGS, index=False)
        print("[environment] no live rows; wrote empty outputs")
        return

    live = merge_runner(live, regime, [
        "market_regime_v2",
        "market_regime_v2_tags",
        "market_regime_v2_risk",
        "market_regime_v2_action",
    ], "_regime")
    live = merge_runner(live, bayesian, [
        "model_weight",
        "market_weight",
        "blended_overlay_pct",
        "blending_reason",
    ], "_bayes")

    lookup = interaction_lookup(interactions)
    policy_rec = recommended_policy(policy_rankings)
    calibration_grade, calibration_error = calibration_summary(calibration)

    env_rows = []
    output = live.copy()
    for idx, row in output.iterrows():
        features = live_features(row)
        matches = matched_interactions(features, lookup)
        classification = classify(row, matches, policy_rec, calibration_grade)
        for col, value in classification.items():
            output.at[idx, col] = value
        env_rows.append({
            "track": row.get("track", ""),
            "race_no": row.get("race_no", ""),
            "horse": row.get("horse", ""),
            **classification,
        })

    env = pd.DataFrame(env_rows, columns=ENV_COLUMNS)
    rankings = make_rankings(env)

    output.to_csv(LIVE, index=False)
    if TERMINAL.exists():
        terminal = read_csv(TERMINAL)
        if terminal.empty:
            output.to_csv(TERMINAL, index=False)
        else:
            append_environment_to_terminal(terminal, env).to_csv(TERMINAL, index=False)
    else:
        output.to_csv(TERMINAL, index=False)
    env.to_csv(OUT_ENV, index=False)
    rankings.to_csv(OUT_RANKINGS, index=False)

    counts = env["environment_type"].value_counts().to_dict() if not env.empty else {}
    dominant = env["environment_type"].mode().iloc[0] if not env.empty and len(env["environment_type"].mode()) else "NONE"
    safest = rankings[rankings["ranking_type"] == "SAFEST_ENVIRONMENT"].head(1)
    toxic = rankings[rankings["ranking_type"] == "MOST_TOXIC_ENVIRONMENT"].head(1)

    print("[environment] rows processed:", len(env))
    print("[environment] environment counts:", counts)
    print("[environment] dominant environment:", dominant)
    print("[environment] safest environment:", safest.iloc[0].to_dict() if len(safest) else "none")
    print("[environment] most toxic environment:", toxic.iloc[0].to_dict() if len(toxic) else "none")
    print("[environment] policy recommendation:", policy_rec)
    print("[environment] calibration grade:", calibration_grade, "error:", round(calibration_error, 2))
    print("[environment] interaction rankings read:", len(interaction_rankings))


if __name__ == "__main__":
    main()
