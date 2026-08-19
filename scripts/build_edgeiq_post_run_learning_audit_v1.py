from pathlib import Path
import re
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RESULTS = DATA / "edgeiq_results_master.csv"
LIVE = DATA / "edgeiq_execution_board_live.csv"
UNCERTAINTY = DATA / "edgeiq_uncertainty_engine_v1.csv"
FIRST_STARTER = DATA / "edgeiq_first_starter_engine_v1.csv"
MARKET_CONFIRMATION = DATA / "edgeiq_market_confirmation_v2.csv"
ADAPTIVE_POLICY = DATA / "edgeiq_self_adaptive_policy_v2.csv"
FORM_DEPTH = DATA / "edgeiq_form_depth_ability_v2.csv"
TRAINER_JOCKEY = DATA / "edgeiq_trainer_jockey_intelligence_v1.csv"

AUDIT_OUT = DATA / "edgeiq_post_run_learning_audit_v1.csv"
ENGINE_OUT = DATA / "edgeiq_post_run_learning_by_engine_v1.csv"
ACTION_OUT = DATA / "edgeiq_post_run_learning_actions_v1.csv"

AUDIT_COLUMNS = [
    "horse",
    "race_key",
    "result",
    "profit_loss",
    "final_execution_state",
    "uncertainty_band",
    "debut_risk_grade",
    "market_confirmation_grade",
    "adaptive_policy_v2",
    "adaptive_execution_permission",
    "form_depth_grade",
    "trainer_jockey_signal_grade",
    "was_suppressed",
    "was_reduced",
    "was_allowed",
    "suppressed_winner_flag",
    "suppressed_loser_flag",
    "saved_loss_estimate",
    "missed_profit_estimate",
    "protection_verdict",
]

ENGINE_COLUMNS = [
    "engine",
    "settled_rows",
    "good_decisions",
    "bad_decisions",
    "unknowns",
    "saved_loss",
    "missed_profit",
    "net_effect",
    "recommended_action",
]

ACTION_COLUMNS = [
    "action_scope",
    "settled_rows",
    "awaiting_sample_count",
    "good_suppressions",
    "bad_suppressions",
    "good_reductions",
    "bad_reductions",
    "good_allows",
    "bad_allows",
    "saved_loss",
    "missed_profit",
    "net_effect",
    "recommended_action",
    "reason",
]

ENGINE_SPECS = [
    ("uncertainty", "uncertainty_band", {"HIGH", "EXTREME"}),
    ("first_starter", "debut_risk_grade", {"HIGH", "EXTREME"}),
    ("market_confirmation", "market_confirmation_grade", {"REJECTED", "NOISY"}),
    ("self_adaptive_policy", "adaptive_execution_permission", {"DENY", "REDUCE"}),
    ("form_depth_ability", "form_depth_grade", {"NO_OFFICIAL_FORM", "LOW", "WEAK", "UNKNOWN"}),
    ("trainer_jockey", "trainer_jockey_signal_grade", {"NEGATIVE", "WEAK", "UNKNOWN"}),
]


def log(message: str) -> None:
    print(f"[edgeiq_post_run_learning_audit_v1] {message}")


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


def upper(value) -> str:
    return str(value or "").strip().upper()


def normalise_text(value) -> str:
    text = str(value or "").strip().upper()
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"[^A-Z0-9]+", "", text)
    return text


def first_existing(row: pd.Series, names: list[str]) -> str:
    for name in names:
        if name in row.index and str(row.get(name, "")).strip():
            return str(row.get(name, "")).strip()
    return ""


def safe_number(value, default=0.0) -> float:
    try:
        text = str(value or "").replace("$", "").replace("%", "").strip()
        if text == "":
            return default
        return float(text)
    except Exception:
        return default


def fmt(value) -> str:
    try:
        return f"{float(value):.4f}"
    except Exception:
        return ""


def add_keys(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    horse_col = next((c for c in ["horse", "runner_name", "runner", "selection"] if c in out.columns), "")
    track_col = next((c for c in ["track", "meeting", "venue"] if c in out.columns), "")
    race_col = next((c for c in ["race_no", "race_number", "race"] if c in out.columns), "")
    date_col = next((c for c in ["race_date", "date"] if c in out.columns), "")
    race_id_col = next((c for c in ["race_id", "race_key"] if c in out.columns), "")

    out["_horse_key"] = out[horse_col].map(normalise_text) if horse_col else ""
    out["_track_key"] = out[track_col].map(normalise_text) if track_col else ""
    out["_race_no_key"] = out[race_col].astype(str).str.extract(r"(\d+)", expand=False).fillna("") if race_col else ""
    out["_date_key"] = out[date_col].astype(str).str.slice(0, 10) if date_col else ""
    if race_id_col:
        out["_race_id_key"] = out[race_id_col].astype(str).str.strip()
    else:
        out["_race_id_key"] = ""
    out["_match_key"] = (
        out["_race_id_key"].where(out["_race_id_key"].ne(""), out["_date_key"] + "|" + out["_track_key"] + "|R" + out["_race_no_key"])
    )
    return out


def compact_engine(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["_match_key", "_horse_key", *cols])
    keyed = add_keys(df)
    keep = ["_match_key", "_horse_key", *[c for c in cols if c in keyed.columns]]
    return keyed[keep].drop_duplicates(subset=["_match_key", "_horse_key"], keep="last")


def build_context() -> pd.DataFrame:
    live = add_keys(read_csv(LIVE))
    if live.empty:
        return pd.DataFrame()

    context = live.copy()
    merge_specs = [
        (UNCERTAINTY, ["uncertainty_band"]),
        (FIRST_STARTER, ["debut_risk_grade", "first_starter_engine_flag", "no_official_form_engine_flag"]),
        (MARKET_CONFIRMATION, ["market_confirmation_grade"]),
        (ADAPTIVE_POLICY, ["adaptive_policy_v2", "adaptive_execution_permission"]),
        (FORM_DEPTH, ["form_depth_grade"]),
        (TRAINER_JOCKEY, ["trainer_jockey_signal_grade"]),
    ]

    for path, cols in merge_specs:
        engine = compact_engine(read_csv(path), cols)
        if engine.empty:
            continue
        context = context.merge(engine, on=["_match_key", "_horse_key"], how="left", suffixes=("", "_engine"))
        for col in cols:
            engine_col = f"{col}_engine"
            if engine_col in context.columns:
                if col in context.columns:
                    context[col] = context[col].where(context[col].astype(str).str.strip().ne(""), context[engine_col])
                else:
                    context[col] = context[engine_col]
                context = context.drop(columns=[engine_col])

    return context.fillna("")


def final_state(row: pd.Series) -> str:
    return first_existing(row, ["final_execution_state", "execution_state", "execution_action", "adaptive_action_impact"])


def stake_value(row: pd.Series) -> float:
    return safe_number(first_existing(row, ["stake", "original_stake", "stake_units", "recommended_stake", "kelly_stake"]), 0.0)


def runner_price(row: pd.Series) -> float:
    return safe_number(first_existing(row, ["market_price", "price", "best_price", "closing_price"]), 0.0)


def classify_action(row: pd.Series) -> tuple[bool, bool, bool]:
    state = upper(final_state(row))
    permission = upper(first_existing(row, ["adaptive_execution_permission", "execution_permission", "policy_decision"]))
    learned = upper(first_existing(row, ["learned_suppression_applied"]))
    was_suppressed = (
        state in {"SUPPRESS", "SUPPRESSED", "PASS", "NO_BET", "DO_NOT_BET"}
        or permission in {"DENY", "SUPPRESS"}
        or learned == "TRUE"
    )
    was_reduced = "REDUCE" in state or permission == "REDUCE"
    was_allowed = (
        any(token in state for token in ["EXECUTE", "BET", "ALLOW"])
        or permission == "ALLOW"
    ) and not was_suppressed
    return was_suppressed, was_reduced, was_allowed


def estimate_missed_profit(row: pd.Series) -> float:
    profit = safe_number(row.get("profit_loss", ""), 0.0)
    if profit > 0:
        return profit
    stake = stake_value(row)
    price = runner_price(row)
    if stake > 0 and price > 1:
        return stake * (price - 1)
    return 0.0


def estimate_saved_loss(row: pd.Series) -> float:
    profit = safe_number(row.get("profit_loss", ""), 0.0)
    if profit < 0:
        return abs(profit)
    stake = stake_value(row)
    return stake if stake > 0 else 0.0


def verdict_for(row: pd.Series, was_suppressed: bool, was_reduced: bool, was_allowed: bool) -> str:
    result = upper(row.get("result", ""))
    if result not in {"WON", "LOST", "VOID"}:
        return "AWAITING_SAMPLE"
    if result == "VOID":
        return "UNKNOWN"
    if was_suppressed and result == "LOST":
        return "GOOD_SUPPRESSION"
    if was_suppressed and result == "WON":
        return "BAD_SUPPRESSION"
    if was_reduced and result == "LOST":
        return "GOOD_REDUCTION"
    if was_reduced and result == "WON":
        return "BAD_REDUCTION"
    if was_allowed and result == "WON":
        return "GOOD_ALLOW"
    if was_allowed and result == "LOST":
        return "BAD_ALLOW"
    return "UNKNOWN"


def build_audit(results: pd.DataFrame, context: pd.DataFrame) -> pd.DataFrame:
    results = add_keys(results)
    if context.empty:
        return pd.DataFrame(columns=AUDIT_COLUMNS)

    settled = results[results.get("result", pd.Series("", index=results.index)).map(upper).isin({"WON", "LOST", "VOID"})].copy() if not results.empty else pd.DataFrame()
    merged = context.merge(
        settled,
        on=["_match_key", "_horse_key"],
        how="left",
        suffixes=("", "_result"),
    ).fillna("")

    rows = []
    for _, row in merged.iterrows():
        result = first_existing(row, ["result", "result_result"])
        profit = first_existing(row, ["profit_loss", "profit_loss_result"])
        was_suppressed, was_reduced, was_allowed = classify_action(row)
        verdict = verdict_for(row, was_suppressed, was_reduced, was_allowed)
        is_winner = upper(result) == "WON"
        is_loser = upper(result) == "LOST"
        rows.append({
            "horse": first_existing(row, ["horse", "runner_name", "runner", "selection", "horse_result"]),
            "race_key": first_existing(row, ["race_id", "race_key", "race_id_result"]) or row.get("_match_key", ""),
            "result": result if result else "PENDING",
            "profit_loss": profit,
            "final_execution_state": final_state(row),
            "uncertainty_band": first_existing(row, ["uncertainty_band"]),
            "debut_risk_grade": first_existing(row, ["debut_risk_grade"]),
            "market_confirmation_grade": first_existing(row, ["market_confirmation_grade"]),
            "adaptive_policy_v2": first_existing(row, ["adaptive_policy_v2"]),
            "adaptive_execution_permission": first_existing(row, ["adaptive_execution_permission"]),
            "form_depth_grade": first_existing(row, ["form_depth_grade"]),
            "trainer_jockey_signal_grade": first_existing(row, ["trainer_jockey_signal_grade"]),
            "was_suppressed": str(was_suppressed).upper(),
            "was_reduced": str(was_reduced).upper(),
            "was_allowed": str(was_allowed).upper(),
            "suppressed_winner_flag": str(was_suppressed and is_winner).upper(),
            "suppressed_loser_flag": str(was_suppressed and is_loser).upper(),
            "saved_loss_estimate": fmt(estimate_saved_loss(row) if was_suppressed and is_loser else 0),
            "missed_profit_estimate": fmt(estimate_missed_profit(row) if was_suppressed and is_winner else 0),
            "protection_verdict": verdict,
        })

    return pd.DataFrame(rows, columns=AUDIT_COLUMNS)


def engine_verdict(engine: str, row: pd.Series, column: str, protective_values: set[str]) -> str:
    result = upper(row.get("result", ""))
    if result not in {"WON", "LOST"}:
        return "UNKNOWN"
    value = upper(row.get(column, ""))
    if not value:
        return "UNKNOWN"
    protective = value in protective_values or any(value.startswith(item) for item in protective_values)
    if protective and result == "LOST":
        return "GOOD"
    if protective and result == "WON":
        return "BAD"
    if not protective and result == "WON":
        return "GOOD"
    if not protective and result == "LOST":
        return "BAD"
    return "UNKNOWN"


def recommended_action(settled_rows: int, good: int, bad: int, saved: float, missed: float) -> str:
    if settled_rows < 20:
        return "NEED_MORE_SAMPLE"
    if bad > good and missed > saved:
        return "LOOSEN_RULE"
    if bad > good:
        return "TIGHTEN_RULE"
    if good >= bad and saved >= missed:
        return "KEEP_RULE"
    return "REVIEW_MATCHING"


def build_engine_summary(audit: pd.DataFrame) -> pd.DataFrame:
    rows = []
    settled_mask = audit["result"].map(upper).isin({"WON", "LOST", "VOID"}) if not audit.empty else pd.Series(dtype=bool)
    for engine, column, protective_values in ENGINE_SPECS:
        if audit.empty or column not in audit.columns:
            rows.append({
                "engine": engine,
                "settled_rows": "0",
                "good_decisions": "0",
                "bad_decisions": "0",
                "unknowns": "0",
                "saved_loss": "0.0000",
                "missed_profit": "0.0000",
                "net_effect": "0.0000",
                "recommended_action": "NEED_MORE_SAMPLE",
            })
            continue

        settled = audit[settled_mask].copy()
        verdicts = settled.apply(lambda row: engine_verdict(engine, row, column, protective_values), axis=1) if not settled.empty else pd.Series(dtype=str)
        good = int((verdicts == "GOOD").sum())
        bad = int((verdicts == "BAD").sum())
        unknown = int((verdicts == "UNKNOWN").sum()) + int((~settled_mask).sum())
        saved = pd.to_numeric(settled.get("saved_loss_estimate", pd.Series(dtype=str)), errors="coerce").fillna(0).sum()
        missed = pd.to_numeric(settled.get("missed_profit_estimate", pd.Series(dtype=str)), errors="coerce").fillna(0).sum()
        rows.append({
            "engine": engine,
            "settled_rows": str(len(settled)),
            "good_decisions": str(good),
            "bad_decisions": str(bad),
            "unknowns": str(unknown),
            "saved_loss": fmt(saved),
            "missed_profit": fmt(missed),
            "net_effect": fmt(saved - missed),
            "recommended_action": recommended_action(len(settled), good, bad, saved, missed),
        })
    return pd.DataFrame(rows, columns=ENGINE_COLUMNS)


def build_actions(audit: pd.DataFrame, engine_summary: pd.DataFrame) -> pd.DataFrame:
    if audit.empty:
        return pd.DataFrame([{
            "action_scope": "OVERALL",
            "settled_rows": "0",
            "awaiting_sample_count": "0",
            "good_suppressions": "0",
            "bad_suppressions": "0",
            "good_reductions": "0",
            "bad_reductions": "0",
            "good_allows": "0",
            "bad_allows": "0",
            "saved_loss": "0.0000",
            "missed_profit": "0.0000",
            "net_effect": "0.0000",
            "recommended_action": "NEED_MORE_SAMPLE",
            "reason": "No live post-learning context available.",
        }], columns=ACTION_COLUMNS)

    verdict = audit["protection_verdict"].map(upper)
    settled = audit["result"].map(upper).isin({"WON", "LOST", "VOID"})
    saved = pd.to_numeric(audit["saved_loss_estimate"], errors="coerce").fillna(0).sum()
    missed = pd.to_numeric(audit["missed_profit_estimate"], errors="coerce").fillna(0).sum()
    good = int(verdict.isin(["GOOD_SUPPRESSION", "GOOD_REDUCTION", "GOOD_ALLOW"]).sum())
    bad = int(verdict.isin(["BAD_SUPPRESSION", "BAD_REDUCTION", "BAD_ALLOW"]).sum())
    settled_rows = int(settled.sum())
    awaiting = int((verdict == "AWAITING_SAMPLE").sum())
    recommendation = recommended_action(settled_rows, good, bad, saved, missed)
    if settled_rows == 0:
        reason = "Awaiting settled post-learning sample."
    elif saved >= missed:
        reason = "Protection effects are currently non-negative on matched settled sample."
    else:
        reason = "Missed profit exceeds saved loss on matched settled sample."

    rows = [{
        "action_scope": "OVERALL",
        "settled_rows": str(settled_rows),
        "awaiting_sample_count": str(awaiting),
        "good_suppressions": str(int((verdict == "GOOD_SUPPRESSION").sum())),
        "bad_suppressions": str(int((verdict == "BAD_SUPPRESSION").sum())),
        "good_reductions": str(int((verdict == "GOOD_REDUCTION").sum())),
        "bad_reductions": str(int((verdict == "BAD_REDUCTION").sum())),
        "good_allows": str(int((verdict == "GOOD_ALLOW").sum())),
        "bad_allows": str(int((verdict == "BAD_ALLOW").sum())),
        "saved_loss": fmt(saved),
        "missed_profit": fmt(missed),
        "net_effect": fmt(saved - missed),
        "recommended_action": recommendation,
        "reason": reason,
    }]

    for _, row in engine_summary.iterrows():
        rows.append({
            "action_scope": f"ENGINE:{row.get('engine', '')}",
            "settled_rows": row.get("settled_rows", "0"),
            "awaiting_sample_count": "",
            "good_suppressions": row.get("good_decisions", "0"),
            "bad_suppressions": row.get("bad_decisions", "0"),
            "good_reductions": "",
            "bad_reductions": "",
            "good_allows": "",
            "bad_allows": "",
            "saved_loss": row.get("saved_loss", "0.0000"),
            "missed_profit": row.get("missed_profit", "0.0000"),
            "net_effect": row.get("net_effect", "0.0000"),
            "recommended_action": row.get("recommended_action", "NEED_MORE_SAMPLE"),
            "reason": "Engine-level post-run protection summary.",
        })

    return pd.DataFrame(rows, columns=ACTION_COLUMNS)


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    results = read_csv(RESULTS)
    context = build_context()

    audit = build_audit(results, context)
    engine_summary = build_engine_summary(audit)
    actions = build_actions(audit, engine_summary)

    audit.to_csv(AUDIT_OUT, index=False)
    engine_summary.to_csv(ENGINE_OUT, index=False)
    actions.to_csv(ACTION_OUT, index=False)

    matched_settled = int(audit["result"].map(upper).isin({"WON", "LOST", "VOID"}).sum()) if not audit.empty else 0
    awaiting = int((audit["protection_verdict"].map(upper) == "AWAITING_SAMPLE").sum()) if not audit.empty else 0
    good_supp = int((audit["protection_verdict"].map(upper) == "GOOD_SUPPRESSION").sum()) if not audit.empty else 0
    bad_supp = int((audit["protection_verdict"].map(upper) == "BAD_SUPPRESSION").sum()) if not audit.empty else 0
    saved = pd.to_numeric(audit.get("saved_loss_estimate", pd.Series(dtype=str)), errors="coerce").fillna(0).sum()
    missed = pd.to_numeric(audit.get("missed_profit_estimate", pd.Series(dtype=str)), errors="coerce").fillna(0).sum()

    log(f"matched settled rows: {matched_settled}")
    log(f"awaiting sample count: {awaiting}")
    log(f"good suppressions: {good_supp}")
    log(f"bad suppressions: {bad_supp}")
    log(f"saved loss: {saved:.4f}")
    log(f"missed profit: {missed:.4f}")
    log(f"wrote {AUDIT_OUT.relative_to(ROOT)}")
    log(f"wrote {ENGINE_OUT.relative_to(ROOT)}")
    log(f"wrote {ACTION_OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
