from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RESULTS = DATA / "edgeiq_results_master.csv"
SUPPRESSION = DATA / "edgeiq_suppression_intelligence.csv"
CONFIDENCE = DATA / "edgeiq_confidence_calibration_v1.csv"
LIVE_BOARD = DATA / "edgeiq_execution_board_live.csv"
TERMINAL_BOARD = DATA / "edgeiq_execution_board_terminal.csv"
ADJUSTMENTS = DATA / "edgeiq_price_truth_adjustments.csv"

ADJUSTMENT_COLUMNS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "market_price",
    "rated_price",
    "overlay_pct",
    "price_truth_adjustment_pct",
    "adjusted_rated_price",
    "adjusted_overlay_pct",
    "overlay_realism_grade",
    "original_execution_action",
    "price_truth_execution_action",
    "suppression_risk_grade",
    "calibrated_confidence_label",
    "price_truth_reason",
    "matched_truth_segments",
]

RISK_WEIGHT = {
    "KILL": 35.0,
    "SUPPRESS": 25.0,
    "REDUCE": 12.0,
    "MONITOR": 4.0,
    "ALLOW": 0.0,
}

TRUST_WEIGHT = {
    "DISTRUST": 20.0,
    "WEAK": 12.0,
    "CAUTION": 7.0,
    "PROVISIONAL": 4.0,
    "TRUST": 0.0,
    "ALLOW": 0.0,
}


def log(message: str) -> None:
    print(f"[edgeiq_price_truth_v2] {message}")


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        log(f"missing: {path.relative_to(ROOT)}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", on_bad_lines="skip").fillna("")
        log(f"read {path.relative_to(ROOT)}: {len(df)} rows")
        return df
    except Exception as exc:
        log(f"warning: failed to read {path.name}: {exc}")
        return pd.DataFrame()


def to_num(value) -> float | None:
    try:
        text = str(value or "").replace("$", "").replace("%", "").strip()
        if not text:
            return None
        parsed = float(text)
        if pd.isna(parsed):
            return None
        return parsed
    except Exception:
        return None


def clean(value) -> str:
    return str(value or "").strip().upper()


def first(row: pd.Series, names: list[str]) -> str:
    for name in names:
        if name in row.index:
            value = str(row.get(name, "")).strip()
            if value and value.lower() not in {"nan", "none", "null"}:
                return value
    return ""


def odds_bucket(value) -> str:
    price = to_num(value)
    if price is None or price <= 0:
        return ""
    if price < 3:
        return "UNDER_3"
    if price < 6:
        return "3_TO_6"
    if price < 12:
        return "6_TO_12"
    if price < 26:
        return "12_TO_26"
    return "26_PLUS"


def overlay_bucket(value) -> str:
    overlay = to_num(value)
    if overlay is None:
        return ""
    if overlay < 0:
        return "NEGATIVE_OVERLAY"
    if overlay < 10:
        return "0_TO_10"
    if overlay < 25:
        return "10_TO_25"
    if overlay < 50:
        return "25_TO_50"
    if overlay < 100:
        return "50_TO_100"
    return "100_PLUS"


def read_segment_lookup(path: Path, grade_column: str) -> dict[tuple[str, str], dict[str, str]]:
    df = read_csv(path)
    lookup: dict[tuple[str, str], dict[str, str]] = {}
    if df.empty:
        return lookup
    for _, row in df.iterrows():
        segment_type = clean(row.get("segment_type"))
        segment_value = clean(row.get("segment_value"))
        if not segment_type or not segment_value:
            continue
        lookup[(segment_type, segment_value)] = {
            "grade": clean(row.get(grade_column)),
            "roi_pct": str(row.get("roi_pct", "")).strip(),
            "average_clv_pct": str(row.get("average_clv_pct", "")).strip(),
            "beat_close_pct": str(row.get("beat_close_pct", "")).strip(),
            "strike_rate": str(row.get("strike_rate", "")).strip(),
            "reason": str(row.get("reason", "")).strip(),
        }
    return lookup


def segments_for(row: pd.Series) -> list[tuple[str, str]]:
    market_price = first(row, ["sportsbet_price", "market_price", "current_price", "fixed_win"])
    overlay = first(row, ["adjusted_overlay_pct", "overlay_pct", "edge_pct", "final_edge_v5_1"])
    confidence = first(row, ["calibrated_confidence_label", "confidence_band_v1", "confidence_band", "confidence"])
    regime = first(row, ["movement_signal", "market_regime", "market_signal", "regime"])
    execution = first(row, ["original_execution_state", "execution_action_before_confidence_throttle", "price_truth_original_execution_action", "execution_action", "final_execution_state"])
    volatility = first(row, ["volatility", "volatility_state", "market_volatility"])

    segments: list[tuple[str, str]] = []
    ob = odds_bucket(market_price)
    if ob:
        segments.append(("ODDS_BUCKET", ob))
    ovb = overlay_bucket(overlay)
    if ovb:
        segments.append(("OVERLAY_BUCKET", ovb))
    if confidence:
        segments.append(("CONFIDENCE_BUCKET", clean(confidence)))
    if regime:
        segments.append(("REGIME", clean(regime)))
    if execution:
        segments.append(("EXECUTION_STATE", clean(execution)))
    if volatility:
        segments.append(("VOLATILITY", clean(volatility)))
    return segments


def historical_metric_adjustment(item: dict[str, str]) -> tuple[float, list[str]]:
    adjustment = 0.0
    reasons: list[str] = []
    roi = to_num(item.get("roi_pct"))
    clv = to_num(item.get("average_clv_pct"))
    beat = to_num(item.get("beat_close_pct"))
    strike = to_num(item.get("strike_rate"))

    if roi is not None and roi < -15:
        adjustment += 10
        reasons.append(f"ROI {roi:.1f}%")
    elif roi is not None and roi < -5:
        adjustment += 5
        reasons.append(f"ROI {roi:.1f}%")

    if clv is not None and clv < -5:
        adjustment += 10
        reasons.append(f"CLV {clv:.1f}%")

    if beat is not None and beat < 35:
        adjustment += 10
        reasons.append(f"beat-close {beat:.1f}%")
    elif beat is not None and beat < 45:
        adjustment += 5
        reasons.append(f"beat-close {beat:.1f}%")

    if strike is not None and strike < 8:
        adjustment += 5
        reasons.append(f"strike {strike:.1f}%")

    return adjustment, reasons


def calculate_adjustment(
    row: pd.Series,
    suppression_lookup: dict[tuple[str, str], dict[str, str]],
    confidence_lookup: dict[tuple[str, str], dict[str, str]],
) -> tuple[float, str, str, str]:
    total = 0.0
    reasons: list[str] = []
    matched: list[str] = []
    strongest_risk = clean(row.get("suppression_risk_grade"))

    for segment in segments_for(row):
        sup = suppression_lookup.get(segment)
        conf = confidence_lookup.get(segment)
        segment_label = f"{segment[0]}={segment[1]}"

        if sup:
            grade = clean(sup.get("grade"))
            strongest_risk = strongest_risk or grade
            weight = RISK_WEIGHT.get(grade, 0)
            total += weight
            metric_adj, metric_reasons = historical_metric_adjustment(sup)
            total += metric_adj
            if grade and weight:
                reasons.append(f"{segment_label} {grade}")
            reasons.extend(f"{segment_label} {reason}" for reason in metric_reasons[:2])
            matched.append(segment_label)

        if conf:
            trust = clean(conf.get("grade"))
            weight = TRUST_WEIGHT.get(trust, 0)
            total += weight
            metric_adj, metric_reasons = historical_metric_adjustment(conf)
            total += metric_adj * 0.5
            if trust and weight:
                reasons.append(f"{segment_label} confidence {trust}")
            reasons.extend(f"{segment_label} {reason}" for reason in metric_reasons[:1])
            matched.append(segment_label)

    direct_risk = clean(row.get("suppression_risk_grade"))
    if direct_risk in RISK_WEIGHT:
        total += RISK_WEIGHT[direct_risk] * 0.5
        strongest_risk = direct_risk
        reasons.append(f"live suppression {direct_risk}")

    total = max(0.0, min(total, 75.0))
    return total, strongest_risk, " | ".join(reasons[:8]), ",".join(dict.fromkeys(matched))


def realism_grade(raw_overlay: float | None, adjusted_overlay: float | None, adjustment: float, risk: str) -> str:
    risk = clean(risk)
    if risk == "KILL" or adjustment >= 55 or (raw_overlay is not None and raw_overlay >= 100 and adjustment >= 30):
        return "EXTREME_FAKE_OVERLAY"
    if risk == "SUPPRESS" or adjustment >= 35 or (adjusted_overlay is not None and adjusted_overlay >= 50 and adjustment >= 20):
        return "FAKE_OVERLAY"
    if risk == "REDUCE" or adjustment >= 15:
        return "QUESTIONABLE"
    return "REALISTIC"


def action_after_truth(original: str, adjusted_overlay: float | None, realism: str, risk: str) -> str:
    original = clean(original)
    risk = clean(risk)
    if realism == "EXTREME_FAKE_OVERLAY" or risk == "KILL":
        return "SUPPRESS"
    if realism == "FAKE_OVERLAY" or risk == "SUPPRESS":
        if original in {"MAX_BET", "EXECUTE", "REDUCED_EXECUTE", "BET", "PRIORITY_EXECUTE"}:
            return "SUPPRESS"
        return "PASS" if original in {"WATCH", "MONITOR"} else original
    if adjusted_overlay is None:
        return original
    if adjusted_overlay < 0:
        return "PASS"
    if adjusted_overlay < 6 and original in {"MAX_BET", "EXECUTE", "REDUCED_EXECUTE", "BET", "WATCH"}:
        return "PASS"
    if adjusted_overlay < 12 and original in {"MAX_BET", "EXECUTE", "REDUCED_EXECUTE", "BET"}:
        return "WATCH"
    if realism == "QUESTIONABLE" and original == "MAX_BET":
        return "EXECUTE"
    if realism == "QUESTIONABLE" and original == "EXECUTE":
        return "REDUCED_EXECUTE"
    return original


def apply_price_truth(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    suppression_lookup = read_segment_lookup(SUPPRESSION, "risk_grade")
    confidence_lookup = read_segment_lookup(CONFIDENCE, "confidence_trust_grade")
    output = df.copy().astype(object)
    adjustment_rows: list[dict[str, str]] = []

    for idx, row in output.iterrows():
        market = to_num(first(row, ["sportsbet_price", "market_price", "current_price", "fixed_win"]))
        rated = to_num(first(row, ["rated_price", "contextual_price_v5_1", "final_price_v5_1"]))
        raw_overlay = to_num(first(row, ["overlay_pct", "edge_pct", "final_edge_v5_1"]))
        original_action = first(row, ["original_execution_state", "execution_action_before_confidence_throttle", "price_truth_original_execution_action", "execution_action", "final_execution_state"]) or "PASS"

        adjustment, risk, reason, matched = calculate_adjustment(row, suppression_lookup, confidence_lookup)
        if raw_overlay is not None and raw_overlay <= 0:
            adjustment = 0.0
            reason = "No positive overlay; price truth adjustment not applied."
        adjusted_rated = rated
        adjusted_overlay = raw_overlay

        if rated is not None and rated > 0:
            adjusted_rated = rated * (1 + adjustment / 100)
            if adjustment > 0 and market is not None and market > 0:
                adjusted_rated = min(adjusted_rated, market * 1.05)
                adjusted_overlay = ((market / adjusted_rated) - 1) * 100

        realism = realism_grade(raw_overlay, adjusted_overlay, adjustment, risk)
        truth_action = action_after_truth(original_action, adjusted_overlay, realism, risk)

        output.at[idx, "price_truth_original_execution_action"] = original_action
        output.at[idx, "price_truth_adjustment_pct"] = round(adjustment, 2)
        output.at[idx, "adjusted_rated_price"] = round(adjusted_rated, 4) if adjusted_rated is not None else ""
        output.at[idx, "adjusted_overlay_pct"] = round(adjusted_overlay, 2) if adjusted_overlay is not None else ""
        output.at[idx, "overlay_realism_grade"] = realism
        output.at[idx, "price_truth_reason"] = reason
        output.at[idx, "price_truth_matched_segments"] = matched
        output.at[idx, "execution_action"] = truth_action
        output.at[idx, "final_execution_state"] = truth_action

        adjustment_rows.append(
            {
                "race_date": first(row, ["race_date", "date"]),
                "track": first(row, ["track"]),
                "race_no": first(row, ["race_no", "race_number"]),
                "horse": first(row, ["horse"]),
                "market_price": "" if market is None else f"{market:.4f}",
                "rated_price": "" if rated is None else f"{rated:.4f}",
                "overlay_pct": "" if raw_overlay is None else f"{raw_overlay:.4f}",
                "price_truth_adjustment_pct": f"{adjustment:.4f}",
                "adjusted_rated_price": "" if adjusted_rated is None else f"{adjusted_rated:.4f}",
                "adjusted_overlay_pct": "" if adjusted_overlay is None else f"{adjusted_overlay:.4f}",
                "overlay_realism_grade": realism,
                "original_execution_action": original_action,
                "price_truth_execution_action": truth_action,
                "suppression_risk_grade": risk,
                "calibrated_confidence_label": first(row, ["calibrated_confidence_label", "confidence_band_v1"]),
                "price_truth_reason": reason,
                "matched_truth_segments": matched,
            }
        )

    return output, pd.DataFrame(adjustment_rows, columns=ADJUSTMENT_COLUMNS)


def write_terminal(live: pd.DataFrame) -> pd.DataFrame:
    preferred = [
        "timestamp",
        "track",
        "race_no",
        "race_time",
        "track_timezone",
        "race_time_local",
        "race_time_utc",
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
        "price_truth_original_execution_action",
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
        "direction",
        "move_pct",
        "steam_flag",
        "drift_flag",
        "prev_price",
    ]
    cols = [col for col in preferred if col in live.columns]
    terminal = live[cols].copy()
    order = {"MAX_BET": 1, "EXECUTE": 2, "REDUCED_EXECUTE": 3, "WATCH": 4, "PASS": 5, "SUPPRESS": 8}
    if "execution_action" in terminal.columns:
        terminal["_sort"] = terminal["execution_action"].map(order).fillna(9)
        overlay_col = "adjusted_overlay_pct" if "adjusted_overlay_pct" in terminal.columns else "overlay_pct"
        terminal[overlay_col] = pd.to_numeric(terminal[overlay_col], errors="coerce")
        terminal = terminal.sort_values(["_sort", overlay_col], ascending=[True, False]).drop(columns=["_sort"])
    terminal.to_csv(TERMINAL_BOARD, index=False, encoding="utf-8")
    return terminal


def main() -> int:
    read_csv(RESULTS)
    live = read_csv(LIVE_BOARD)
    if live.empty:
        log("no live board rows; writing empty adjustments")
        pd.DataFrame(columns=ADJUSTMENT_COLUMNS).to_csv(ADJUSTMENTS, index=False, encoding="utf-8")
        return 0

    adjusted_live, adjustments = apply_price_truth(live)
    adjusted_live.to_csv(LIVE_BOARD, index=False, encoding="utf-8")
    terminal = write_terminal(adjusted_live)
    adjustments.to_csv(ADJUSTMENTS, index=False, encoding="utf-8")

    reduced = (
        pd.to_numeric(adjustments["adjusted_overlay_pct"], errors="coerce")
        < pd.to_numeric(adjustments["overlay_pct"], errors="coerce")
    ).sum()
    fake = adjustments["overlay_realism_grade"].isin(["FAKE_OVERLAY", "EXTREME_FAKE_OVERLAY"]).sum()
    avg_adjustment = pd.to_numeric(adjustments["price_truth_adjustment_pct"], errors="coerce").mean()
    dangerous = adjustments["matched_truth_segments"].value_counts().head(5)

    log(f"rows processed: {len(adjusted_live)}")
    log(f"terminal rows written: {len(terminal)}")
    log(f"overlays reduced: {int(reduced)}")
    log(f"fake overlays detected: {int(fake)}")
    log(f"average adjustment pct: {avg_adjustment:.4f}")
    log("top dangerous overlay structures:")
    log(dangerous.to_string() if len(dangerous) else "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
