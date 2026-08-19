from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "public" / "data"

LIVE = DATA / "edgeiq_live_terminal_feed_v1.csv"
LIVE_RUNNER = DATA / "edgeiq_live_runner_board_v1.csv"
SPORTSBET = DATA / "sportsbet_live_market_v1.csv"
TERMINAL = DATA / "edgeiq_live_terminal_feed_v1.csv"
CALIBRATION = DATA / "edgeiq_probability_calibration_v1.csv"
FAIR_REVIEW = DATA / "edgeiq_current_fair_prices_review_v5_2.csv"

OUT = DATA / "edgeiq_probability_engine_v3.csv"
OUT_DIAG = DATA / "edgeiq_probability_engine_v3_diagnostics.csv"

OUTPUT_COLUMNS = [
    "track","race_no","horse",
    "market_price","market_probability",
    "raw_model_probability","model_probability_source",
    "alpha_signal","alpha_cap","alpha_applied",
    "v3_probability","v3_fair_price","v3_overlay_pct",
    "v3_realism_grade","v3_pricing_action","v3_reason",
    "pre_v3_execution_action","post_v3_execution_action","v3_applied"
]

def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"[probability_v3] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"[probability_v3] read {path.name}: {len(df)} rows")
        return df
    except Exception as exc:
        print(f"[probability_v3] failed {path.name}: {exc}")
        return pd.DataFrame()

def text(v):
    if pd.isna(v):
        return ""
    return str(v).strip()

def upper(v):
    return text(v).upper()

def num(v, default=None):
    try:
        x = float(v)
        return x if pd.notna(x) else default
    except Exception:
        return default

def key(df):
    return (
        df.get("track", "").astype(str).str.upper().str.strip()
        + "|" + df.get("race_no", "").astype(str).str.upper().str.strip()
        + "|" + df.get("horse", "").astype(str).str.upper().str.strip()
    )

def coalesce(row, cols):
    for c in cols:
        if c in row.index and text(row.get(c)):
            return text(row.get(c))
    return ""

def raw_model_probability(row):
    v = num(row.get("rated_probability_v5_2_review"), None)
    if v is not None and 0 < v <= 1:
        return v, "rated_probability_v5_2_review"

    p = num(row.get("rated_price_v5_2_review"), None)
    if p is not None and p > 1:
        return max(0.001, min(0.95, 1.0 / p)), "1/rated_price_v5_2_review"
    for c in [
        "blended_probability",
        "shrunk_probability",
        "final_probability_v5_1",
        "contextual_probability_v5_1",
        "rated_probability",
        "confidence_adjusted_probability_v1",
    ]:
        v = num(row.get(c), None)
        if v is not None and 0 < v <= 1:
            return v, c

    for c in [
        "blended_fair_price",
        "shrunk_fair_price",
        "adjusted_rated_price",
        "rated_price",
        "final_price_v5_1",
        "fair_price",
    ]:
        p = num(row.get(c), None)
        if p is not None and p > 1:
            return max(0.001, min(0.95, 1.0 / p)), f"1/{c}"

    return 0.001, "fallback_floor"

def market_probability(row):
    for c in ["sportsbet_price", "market_price", "current_price", "fixed_odds", "win_odds", "live_price"]:
        p = num(row.get(c), None)
        if p is not None and p > 1:
            return max(0.001, min(0.95, 1.0 / p)), p
    return 0.001, 0.0

def action_from(row):
    return upper(coalesce(row, ["final_execution_state", "execution_action", "post_v2_execution_action"])) or "PASS"

def calculate(row):
    market_prob, market_price = market_probability(row)
    model_prob, model_source = raw_model_probability(row)

    confidence = upper(coalesce(row, ["calibrated_confidence_label", "confidence_band_v1", "confidence"]))
    environment = upper(coalesce(row, ["environment_type", "market_environment"]))
    micro = upper(coalesce(row, ["microstructure_type"]))
    risk = upper(coalesce(row, ["transition_risk_grade", "microstructure_risk_grade", "environment_risk_grade"]))
    flags = upper(coalesce(row, ["risk_flags", "rating_notes", "intelligence_note"]))

    official_runs = num(coalesce(row, ["official_run_count", "official_run_count_v5", "summary_official_run_count"]), None)
    first_starter = "FIRST" in flags or "NO_OFFICIAL_FORM" in flags or official_runs == 0
    no_market = market_price <= 0

    # Core V3 philosophy:
    # Market is the prior. EDGEIQ can only move probability by a bounded alpha.
    raw_alpha = model_prob - market_prob

    # =============================================================================
    # HARD UNCERTAINTY COLLAPSE
    # =============================================================================

    collapse_factor = 1.0

    uncertainty_flags = 0

    if confidence in {"VERY_LOW", "LOW", ""}:
        uncertainty_flags += 1

    if first_starter:
        uncertainty_flags += 1

    if environment in {"CHAOTIC", "PUBLIC_TRAP", "ILLIQUID", "VOLATILE"}:
        uncertainty_flags += 1

    if micro in {"VOLATILITY_CLUSTER", "FALSE_STEAM", "PANIC_DRIFT", "PUBLIC_STEAM"}:
        uncertainty_flags += 1

    if risk == "RED":
        uncertainty_flags += 1

    if market_price >= 26:
        uncertainty_flags += 1

    # progressively collapse model belief toward market
    if uncertainty_flags >= 5:
        collapse_factor = 0.08
    elif uncertainty_flags == 4:
        collapse_factor = 0.15
    elif uncertainty_flags == 3:
        collapse_factor = 0.28
    elif uncertainty_flags == 2:
        collapse_factor = 0.45
    elif uncertainty_flags == 1:
        collapse_factor = 0.70

    collapsed_model_prob = (
        market_prob
        + ((model_prob - market_prob) * collapse_factor)
    )

    raw_alpha = collapsed_model_prob - market_prob

    cap = 0.018

    if market_price >= 26:
        cap = 0.006
    elif market_price >= 12:
        cap = 0.010
    elif market_price >= 6:
        cap = 0.015
    elif market_price >= 3:
        cap = 0.025
    elif market_price > 1:
        cap = 0.040

    if confidence in {"VERY_LOW", "LOW", ""}:
        cap *= 0.45
    elif confidence == "MEDIUM":
        cap *= 0.70
    elif confidence in {"HIGH", "VERY_HIGH"}:
        cap *= 1.15

    if first_starter:
        cap *= 0.35

    if environment in {"CHAOTIC", "PUBLIC_TRAP", "ILLIQUID", "VOLATILE"}:
        cap *= 0.55

    if micro in {"VOLATILITY_CLUSTER", "FALSE_STEAM", "PANIC_DRIFT", "PUBLIC_STEAM"}:
        cap *= 0.70

    if risk == "RED":
        cap *= 0.55

    cap = max(0.0015, min(0.045, cap))

    alpha = max(-cap, min(cap, raw_alpha))

    # FAIR PRICE REVIEW IS NOW CANONICAL.
    # If V5.2 review probabilities are available, do not market-anchor them.
    if model_source in {"rated_probability_v5_2_review", "1/rated_price_v5_2_review"}:
        v3_prob = model_prob
        alpha = 0.0
        raw_alpha = 0.0
        collapsed_model_prob = model_prob
        reason_prefix = "CANONICAL_FAIR_PRICE_MODEL"
    elif no_market:
        v3_prob = model_prob
        reason_prefix = "NO LIVE MARKET: model fallback"
    else:
        v3_prob = market_prob + alpha
        reason_prefix = "MARKET_ANCHORED"

    v3_prob = max(0.001, min(0.65, v3_prob))
    fair_price = min(400.0, max(1.01, 1.0 / v3_prob))
    overlay = ((market_price / fair_price) - 1.0) * 100.0 if market_price > 0 else 0.0

    if no_market:
        grade = "NO_LIVE_MARKET"
        pricing_action = "NO_LIVE_PRICE"
    elif market_price >= 26 and overlay > 60:
        grade = "ROUGHIE_CAP_BREACH"
        pricing_action = "SUPPRESS_FAKE_OVERLAY"
    elif overlay > 80:
        grade = "EXTREME_FAKE_OVERLAY"
        pricing_action = "SUPPRESS_FAKE_OVERLAY"
    elif overlay > 35 and confidence in {"VERY_LOW", "LOW", ""}:
        grade = "LOW_CONFIDENCE_FAKE_OVERLAY"
        pricing_action = "SUPPRESS_FAKE_OVERLAY"
    elif overlay > 20:
        grade = "QUESTIONABLE_EDGE"
        pricing_action = "WATCH"
    elif overlay > 6:
        grade = "REALISTIC_EDGE"
        pricing_action = "ALLOW_REALISTIC"
    else:
        grade = "NO_EDGE"
        pricing_action = "PASS"

    pre_action = action_from(row)
    post_action = pre_action

    executable = {"MAX_BET", "PRIORITY_EXECUTE", "EXECUTE", "REDUCED_EXECUTE", "BET"}

    if pricing_action in {"SUPPRESS_FAKE_OVERLAY", "NO_LIVE_PRICE"}:
        post_action = "SUPPRESS" if pre_action in executable else pre_action
    elif pricing_action == "WATCH" and pre_action in executable:
        post_action = "WATCH"
    elif pricing_action == "PASS":
        post_action = "PASS" if pre_action in executable or pre_action == "WATCH" else pre_action

    reasons = [
        reason_prefix,
        f"market_prob={market_prob:.4f}",
        f"model_prob={model_prob:.4f}",
        f"collapsed_model_prob={collapsed_model_prob:.4f}",
        f"collapse_factor={collapse_factor:.2f}",
        f"uncertainty_flags={uncertainty_flags}",
        f"raw_alpha={raw_alpha:.4f}",
        f"cap={cap:.4f}",
        f"alpha={alpha:.4f}",
        f"confidence={confidence or 'UNKNOWN'}",
        f"environment={environment or 'UNKNOWN'}",
    ]

    if first_starter:
        reasons.append("first starter/no-form alpha restriction")
    if risk:
        reasons.append(f"risk={risk}")

    return {
        "market_price": round(market_price, 4),
        "market_probability": round(market_prob, 6),
        "raw_model_probability": round(model_prob, 6),
        "model_probability_source": model_source,
        "alpha_signal": round(raw_alpha, 6),
        "alpha_cap": round(cap, 6),
        "alpha_applied": round(alpha, 6),
        "v3_probability": round(v3_prob, 6),
        "v3_fair_price": round(fair_price, 4),
        "v3_overlay_pct": round(overlay, 2),
        "v3_realism_grade": grade,
        "v3_pricing_action": pricing_action,
        "v3_reason": " | ".join(reasons),
        "pre_v3_execution_action": pre_action,
        "post_v3_execution_action": post_action,
        "v3_applied": abs(v3_prob - model_prob) > 0.0001,
    }

def append_to_terminal(terminal, audit):
    if terminal.empty or audit.empty:
        return terminal

    left = terminal.copy()
    right = audit.copy()

    left["_key"] = key(left)
    right["_key"] = key(right)

    cols = [c for c in OUTPUT_COLUMNS if c not in {"track", "race_no", "horse"}]
    right = right[["_key"] + cols].drop_duplicates("_key", keep="last")

    merged = left.merge(right, on="_key", how="left", suffixes=("", "_v3"))

    for c in cols:
        extra = f"{c}_v3"
        if extra in merged.columns:
            merged[c] = merged[extra]
            merged = merged.drop(columns=[extra])

    return merged.drop(columns=["_key"], errors="ignore")



def merge_fair_review(live):
    fair = read_csv(FAIR_REVIEW)
    if live.empty or fair.empty:
        return live

    left = live.copy()
    right = fair.copy()

    left["_key"] = key(left)
    right["_key"] = key(right)

    keep_cols = [
        "_key",
        "rated_probability_v5_2_review",
        "rated_price_v5_2_review",
        "rated_price_status_v5_2_review",
        "projection_gap_v5_2",
        "projection_band_v5_2",
        "price_rank_in_race_v5_2"
    ]
    keep_cols = [c for c in keep_cols if c in right.columns]

    right = right[keep_cols].drop_duplicates("_key", keep="last")
    return left.merge(right, on="_key", how="left", suffixes=("", "_fair_review"))
def merge_live_runner_prices(live):
    board = read_csv(LIVE_RUNNER)
    if live.empty or board.empty:
        return live

    left = live.copy()
    right = board.copy()

    left["_key"] = key(left)
    right["_key"] = key(right)

    keep_cols = [
        "_key",
        "live_price",
        "sportsbet_event_id",
        "sportsbet_market_id",
        "sportsbet_timestamp",
        "bookmaker",
    ]
    keep_cols = [c for c in keep_cols if c in right.columns]

    right = right[keep_cols].drop_duplicates("_key", keep="last")
    merged = left.merge(right, on="_key", how="left", suffixes=("", "_runner"))

    if "live_price_runner" in merged.columns:
        runner_price = merged["live_price_runner"].astype(str).str.strip()
        has_runner_price = runner_price.ne("") & runner_price.ne("nan")

        for col in ["sportsbet_price", "market_price", "live_price", "current_price"]:
            if col not in merged.columns:
                merged[col] = ""
            existing = merged[col].astype(str).str.strip()
            merged.loc[has_runner_price & existing.eq(""), col] = runner_price[has_runner_price]

    for src in ["sportsbet_event_id", "sportsbet_market_id", "sportsbet_timestamp", "bookmaker"]:
        runner_col = f"{src}_runner"
        if runner_col in merged.columns:
            if src not in merged.columns:
                merged[src] = ""
            existing = merged[src].astype(str).str.strip()
            runner_value = merged[runner_col].astype(str).str.strip()
            merged.loc[existing.eq("") & runner_value.ne("") & runner_value.ne("nan"), src] = runner_value

    return merged.drop(columns=[c for c in merged.columns if c.endswith("_runner") or c == "_key"], errors="ignore")



def merge_sportsbet_prices_direct(live):
    sports = read_csv(SPORTSBET)
    if live.empty or sports.empty:
        return live

    left = live.copy()
    right = sports.copy()

    left["_key"] = key(left)
    right["_key"] = key(right)

    right["sportsbet_price_direct"] = pd.to_numeric(right.get("sportsbet_price", ""), errors="coerce")
    right = (
        right[["_key", "sportsbet_price_direct"]]
        .dropna(subset=["sportsbet_price_direct"])
        .drop_duplicates("_key", keep="last")
    )

    merged = left.merge(right, on="_key", how="left")

    price = pd.to_numeric(merged["sportsbet_price_direct"], errors="coerce")
    has_price = price.notna() & (price > 1)

    for col in ["sportsbet_price", "market_price", "live_price", "current_price"]:
        if col not in merged.columns:
            merged[col] = pd.NA
        merged[col] = pd.to_numeric(merged[col], errors="coerce")
        merged.loc[has_price, col] = price.loc[has_price].astype(float)

    return merged.drop(columns=["_key", "sportsbet_price_direct"], errors="ignore")


def diagnostics(audit):
    if audit.empty:
        return pd.DataFrame()

    rows = []

    for name, frame in [
        ("OVERALL", audit),
        ("REALISTIC_EDGE", audit[audit["v3_realism_grade"].eq("REALISTIC_EDGE")]),
        ("QUESTIONABLE_EDGE", audit[audit["v3_realism_grade"].eq("QUESTIONABLE_EDGE")]),
        ("SUPPRESSED_FAKE", audit[audit["v3_pricing_action"].eq("SUPPRESS_FAKE_OVERLAY")]),
        ("NO_LIVE_MARKET", audit[audit["v3_realism_grade"].eq("NO_LIVE_MARKET")]),
    ]:
        rows.append({
            "diagnostic_type": name,
            "rows": len(frame),
            "avg_market_probability": round(pd.to_numeric(frame.get("market_probability"), errors="coerce").mean(), 6) if len(frame) else "",
            "avg_model_probability": round(pd.to_numeric(frame.get("raw_model_probability"), errors="coerce").mean(), 6) if len(frame) else "",
            "avg_v3_probability": round(pd.to_numeric(frame.get("v3_probability"), errors="coerce").mean(), 6) if len(frame) else "",
            "avg_alpha_applied": round(pd.to_numeric(frame.get("alpha_applied"), errors="coerce").mean(), 6) if len(frame) else "",
            "avg_overlay_pct": round(pd.to_numeric(frame.get("v3_overlay_pct"), errors="coerce").mean(), 2) if len(frame) else "",
        })

    return pd.DataFrame(rows)

def main():
    live = read_csv(LIVE)

    if live.empty:
        print("[probability_v3] primary live input empty; falling back to edgeiq_live_runner_board_v1.csv")
        live = read_csv(LIVE_RUNNER)

    live = merge_fair_review(live)
    live = merge_live_runner_prices(live)
    live = merge_sportsbet_prices_direct(live)
    terminal = read_csv(TERMINAL)

    if live.empty:
        pd.DataFrame(columns=OUTPUT_COLUMNS).to_csv(OUT, index=False)
        pd.DataFrame().to_csv(OUT_DIAG, index=False)
        print("[probability_v3] no live input")
        return

    audit_rows = []

    for _, row in live.iterrows():
        calc = calculate(row)
        audit_rows.append({
            "track": row.get("track", ""),
            "race_no": row.get("race_no", ""),
            "horse": row.get("horse", ""),
            **calc,
        })

    audit = pd.DataFrame(audit_rows, columns=OUTPUT_COLUMNS)
    audit.to_csv(OUT, index=False)

    diag = diagnostics(audit)
    diag.to_csv(OUT_DIAG, index=False)

    if not terminal.empty:
        terminal_v3 = append_to_terminal(terminal, audit)
        terminal_v3.to_csv(TERMINAL, index=False)

    print("=" * 100)
    print("EDGEIQ PROBABILITY ENGINE V3 — MARKET ANCHORED")
    print("=" * 100)
    print(f"ROWS: {len(audit)}")
    print(f"SAVED: {OUT}")
    print(f"SAVED: {OUT_DIAG}")
    if not diag.empty:
        print(diag.to_string(index=False))


if __name__ == "__main__":
    main()






