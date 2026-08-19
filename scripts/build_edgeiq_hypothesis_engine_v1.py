from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "public" / "data"

BY_FACTOR = DATA / "edgeiq_model_diagnostic_by_factor.csv"
RECOMMENDATIONS = DATA / "edgeiq_model_diagnostic_recommendations.csv"
LAB = DATA / "edgeiq_model_diagnostic_lab_v1.csv"
RESULTS = DATA / "edgeiq_results_master.csv"
OUT = DATA / "edgeiq_hypothesis_engine_v1.csv"

OUT_COLUMNS = [
    "hypothesis_id",
    "hypothesis_type",
    "trigger_factor",
    "trigger_value",
    "proposed_rule",
    "historical_rows",
    "settled_rows",
    "historical_roi_pct",
    "historical_clv_pct",
    "beat_close_pct",
    "expected_effect",
    "risk",
    "priority",
    "status",
]


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"[hypothesis_engine] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"[hypothesis_engine] read {path.name}: {len(df)} rows")
        return df
    except Exception as exc:
        print(f"[hypothesis_engine] warning: could not read {path.name}: {exc}")
        return pd.DataFrame()


def text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def num(value, default=0.0) -> float:
    try:
        parsed = float(value)
    except Exception:
        return default
    return parsed if pd.notna(parsed) else default


def safe_int(value, default=0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def clean_factor_name(value: str) -> str:
    return text(value).replace("_", " ")


def priority_for(grade: str, settled_rows: int) -> str:
    grade = text(grade).upper()
    if grade == "PROMISING":
        return "PROTECT"
    if settled_rows < 20:
        return "LOW"
    if grade == "TOXIC" and settled_rows >= 50:
        return "HIGH"
    if grade == "TOXIC":
        return "MEDIUM"
    if grade == "WEAK" and settled_rows >= 50:
        return "MEDIUM"
    if grade == "WEAK":
        return "LOW"
    return "LOW"


def status_for(grade: str, settled_rows: int) -> str:
    grade = text(grade).upper()
    if grade == "PROMISING":
        return "PROTECT_EDGE"
    if settled_rows < 20:
        return "NEEDS_MORE_SAMPLE"
    return "READY_TO_TEST"


def hypothesis_type_for(grade: str, recommendation: str) -> str:
    grade = text(grade).upper()
    recommendation = text(recommendation).upper()
    if grade == "PROMISING":
        return "PROTECT_EDGE"
    if recommendation in {"KILL", "SUPPRESS"} or grade == "TOXIC":
        return "SUPPRESSION_TEST"
    if recommendation == "REQUIRE_HIGHER_CONFIDENCE":
        return "CONFIDENCE_GATE_TEST"
    if recommendation == "REDUCE_STAKE" or grade == "WEAK":
        return "STAKE_REDUCTION_TEST"
    return "MONITORING_TEST"


def proposed_rule(row: pd.Series) -> str:
    factor = text(row.get("factor"))
    value = text(row.get("factor_value"))
    grade = text(row.get("reliability_grade")).upper()
    recommendation = text(row.get("recommendation")).upper()
    beat_close = num(row.get("beat_close_pct"))
    roi = num(row.get("roi_pct"))

    if grade == "PROMISING":
        return f"Protect {factor}={value}; allow normal execution while ROI remains positive and beat-close stays >= 45%."
    if recommendation == "KILL" or grade == "TOXIC":
        return f"Suppress {factor}={value} unless calibrated confidence is HIGH+ and live beat-close evidence improves above 45%."
    if recommendation == "SUPPRESS":
        return f"Suppress {factor}={value}; retest only after ROI improves above -8% and CLV is no longer negative."
    if recommendation == "REQUIRE_HIGHER_CONFIDENCE":
        return f"Allow {factor}={value} only when calibrated confidence is HIGH+; current beat-close is {beat_close:.1f}%."
    if recommendation == "REDUCE_STAKE" or grade == "WEAK":
        return f"Reduce stake on {factor}={value}; restore normal staking only if ROI improves above 0%."
    if roi < 0:
        return f"Monitor {factor}={value}; do not increase exposure until ROI is non-negative."
    return f"Monitor {factor}={value}; no forced action until more evidence arrives."


def expected_effect(row: pd.Series) -> str:
    grade = text(row.get("reliability_grade")).upper()
    profit_loss = num(row.get("profit_loss"))
    roi = num(row.get("roi_pct"))
    beat_close = num(row.get("beat_close_pct"))

    if grade == "PROMISING":
        return f"Preserve profitable sample: ROI {roi:.1f}%, beat-close {beat_close:.1f}%."
    if profit_loss < 0:
        return f"Reduce exposure to historical loss contribution of {profit_loss:.2f} units."
    return f"Contain risk while sample validates; ROI {roi:.1f}%, beat-close {beat_close:.1f}%."


def risk_text(row: pd.Series) -> str:
    settled = safe_int(row.get("settled_rows"))
    grade = text(row.get("reliability_grade")).upper()
    roi = num(row.get("roi_pct"))
    beat = num(row.get("beat_close_pct"))

    if settled < 20:
        return f"Small sample risk: {settled} settled rows."
    if grade == "PROMISING":
        return "Opportunity cost if protected edge is over-filtered."
    if grade == "TOXIC":
        return f"Continuation risk: ROI {roi:.1f}% and beat-close {beat:.1f}%."
    return f"Model uncertainty: ROI {roi:.1f}%, beat-close {beat:.1f}%."


def build_hypothesis(row: pd.Series, idx: int) -> dict:
    grade = text(row.get("reliability_grade")).upper()
    recommendation = text(row.get("recommendation")).upper()
    settled_rows = safe_int(row.get("settled_rows"))

    return {
        "hypothesis_id": f"HYP-{idx:04d}",
        "hypothesis_type": hypothesis_type_for(grade, recommendation),
        "trigger_factor": text(row.get("factor")),
        "trigger_value": text(row.get("factor_value")),
        "proposed_rule": proposed_rule(row),
        "historical_rows": safe_int(row.get("rows")),
        "settled_rows": settled_rows,
        "historical_roi_pct": round(num(row.get("roi_pct")), 2),
        "historical_clv_pct": round(num(row.get("average_clv_pct")), 2),
        "beat_close_pct": round(num(row.get("beat_close_pct")), 2),
        "expected_effect": expected_effect(row),
        "risk": risk_text(row),
        "priority": priority_for(grade, settled_rows),
        "status": status_for(grade, settled_rows),
    }


def load_factor_source(by_factor: pd.DataFrame, lab: pd.DataFrame) -> pd.DataFrame:
    if not by_factor.empty:
        return by_factor.copy()
    return lab.copy()


def main():
    DATA.mkdir(parents=True, exist_ok=True)

    by_factor = read_csv(BY_FACTOR)
    recommendations = read_csv(RECOMMENDATIONS)
    lab = read_csv(LAB)
    results = read_csv(RESULTS)

    source = load_factor_source(by_factor, lab)
    if source.empty:
        pd.DataFrame(columns=OUT_COLUMNS).to_csv(OUT, index=False)
        print("[hypothesis_engine] no diagnostic factor rows; wrote empty hypothesis file")
        return

    required_cols = {"factor", "factor_value", "reliability_grade"}
    missing = required_cols - set(source.columns)
    if missing:
        pd.DataFrame(columns=OUT_COLUMNS).to_csv(OUT, index=False)
        print(f"[hypothesis_engine] missing required columns {sorted(missing)}; wrote empty hypothesis file")
        return

    candidates = source[
        source["reliability_grade"].astype(str).str.upper().isin(["TOXIC", "WEAK", "PROMISING", "UNKNOWN"])
    ].copy()

    if "settled_rows" in candidates.columns:
        candidates["_settled_sort"] = pd.to_numeric(candidates["settled_rows"], errors="coerce").fillna(0)
    else:
        candidates["_settled_sort"] = 0

    if "profit_loss" in candidates.columns:
        candidates["_loss_sort"] = pd.to_numeric(candidates["profit_loss"], errors="coerce").fillna(0)
    else:
        candidates["_loss_sort"] = 0

    grade_order = {"TOXIC": 0, "WEAK": 1, "PROMISING": 2, "UNKNOWN": 3}
    candidates["_grade_sort"] = candidates["reliability_grade"].astype(str).str.upper().map(grade_order).fillna(9)
    candidates = candidates.sort_values(["_grade_sort", "_loss_sort", "_settled_sort"], ascending=[True, True, False])

    rows = []
    for idx, (_, row) in enumerate(candidates.iterrows(), start=1):
        rows.append(build_hypothesis(row, idx))

    out = pd.DataFrame(rows, columns=OUT_COLUMNS)
    out.to_csv(OUT, index=False)

    high_priority = int((out["priority"] == "HIGH").sum()) if not out.empty else 0
    protected = int((out["status"] == "PROTECT_EDGE").sum()) if not out.empty else 0
    ready = int((out["status"] == "READY_TO_TEST").sum()) if not out.empty else 0

    print("[hypothesis_engine] results rows available:", len(results))
    print("[hypothesis_engine] diagnostic recommendation rows available:", len(recommendations))
    print("[hypothesis_engine] hypotheses created:", len(out))
    print("[hypothesis_engine] high-priority tests:", high_priority)
    print("[hypothesis_engine] protected edges:", protected)
    print("[hypothesis_engine] ready to test:", ready)
    if len(out):
        print("[hypothesis_engine] top hypotheses:")
        print(out.head(8)[["hypothesis_id", "hypothesis_type", "trigger_factor", "trigger_value", "priority", "status"]].to_string(index=False))


if __name__ == "__main__":
    main()
