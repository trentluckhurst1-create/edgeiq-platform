from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "public" / "data"

MARKET_TAPE = DATA / "edgeiq_market_tape.csv"
LIVE = DATA / "edgeiq_execution_board_live.csv"
TERMINAL = DATA / "edgeiq_execution_board_terminal.csv"
RESULTS = DATA / "edgeiq_results_master.csv"
ENVIRONMENT = DATA / "edgeiq_environment_classification_v1.csv"
POLICY = DATA / "edgeiq_policy_rankings_v1.csv"

OUT_TEMPORAL = DATA / "edgeiq_temporal_execution_intelligence_v1.csv"
OUT_RANKINGS = DATA / "edgeiq_timing_window_rankings_v1.csv"

TEMPORAL_COLUMNS = [
    "timing_window",
    "timing_environment",
    "rows",
    "settled_rows",
    "execution_rate",
    "suppression_rate",
    "average_overlay_pct",
    "fake_overlay_rate",
    "volatility_rate",
    "average_clv_pct",
    "beat_close_pct",
    "roi_pct",
    "environment_distribution",
    "calibration_quality",
    "stability_score",
    "timing_risk_grade",
    "recommended_wait_or_execute",
    "timing_reason",
]

RANKING_COLUMNS = [
    "ranking_type",
    "timing_window",
    "timing_environment",
    "metric_value",
    "timing_risk_grade",
    "recommended_wait_or_execute",
    "reason",
]


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"[temporal] missing {path.name}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"[temporal] read {path.name}: {len(df)} rows")
        return df
    except pd.errors.EmptyDataError:
        print(f"[temporal] empty {path.name}")
        return pd.DataFrame()
    except Exception as exc:
        print(f"[temporal] warning: could not read {path.name}: {exc}")
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


def parse_dt(value):
    raw = text(value)
    if not raw:
        return None
    parsed = pd.to_datetime(raw, errors="coerce")
    if pd.isna(parsed):
        return None
    try:
        return parsed.to_pydatetime().replace(tzinfo=None)
    except Exception:
        return None


def parse_race_datetime(row: pd.Series):
    date_raw = text(row.get("race_date") or row.get("date"))
    time_raw = text(row.get("race_time"))
    if not date_raw or not time_raw:
        return None
    date_parsed = pd.to_datetime(date_raw, errors="coerce")
    if pd.isna(date_parsed):
        return None

    cleaned = time_raw.upper().replace(".", "").strip()
    formats = ["%I:%M%p", "%I:%M %p", "%H:%M", "%H:%M:%S"]
    parsed_time = None
    for fmt in formats:
        try:
            parsed_time = datetime.strptime(cleaned, fmt).time()
            break
        except ValueError:
            continue
    if parsed_time is None:
        return None
    return datetime.combine(date_parsed.to_pydatetime().date(), parsed_time)


def runner_key(df: pd.DataFrame) -> pd.Series:
    parts = []
    for col in ["event_id", "horse"]:
        if col in df.columns:
            parts.append(df[col].map(upper))
        else:
            parts.append(pd.Series([""] * len(df), index=df.index))
    return parts[0] + "|" + parts[1]


def full_runner_key(df: pd.DataFrame) -> pd.Series:
    parts = []
    for col in ["track", "race_no", "horse"]:
        if col in df.columns:
            parts.append(df[col].map(upper))
        else:
            parts.append(pd.Series([""] * len(df), index=df.index))
    return parts[0] + "|" + parts[1] + "|" + parts[2]


def timing_window(minutes_to_jump) -> str:
    if minutes_to_jump is None:
        return "UNKNOWN_TIMING"
    if minutes_to_jump >= 120:
        return "120_PLUS_MINS"
    if minutes_to_jump >= 60:
        return "60_TO_120_MINS"
    if minutes_to_jump >= 30:
        return "30_TO_60_MINS"
    if minutes_to_jump >= 15:
        return "15_TO_30_MINS"
    if minutes_to_jump >= 5:
        return "5_TO_15_MINS"
    if minutes_to_jump >= 0:
        return "FINAL_5_MINS"
    return "POST_JUMP_OR_STALE"


def classify_timing(row: pd.Series) -> tuple[str, str, str, str]:
    window = text(row.get("timing_window"))
    fake = num(row.get("fake_overlay_rate"), 0.0) or 0.0
    volatility = num(row.get("volatility_rate"), 0.0) or 0.0
    suppression = num(row.get("suppression_rate"), 0.0) or 0.0
    beat_close = num(row.get("beat_close_pct"), None)
    roi = num(row.get("roi_pct"), None)
    clv = num(row.get("average_clv_pct"), None)

    if window == "UNKNOWN_TIMING":
        return "NEUTRAL", "AMBER", "WAIT_FOR_MARKET", "timing unavailable"
    if window == "POST_JUMP_OR_STALE":
        return "TRAP_WINDOW", "RED", "WAIT_FOR_MARKET", "post-jump or stale timing"
    if window == "FINAL_5_MINS" and (volatility >= 35 or fake >= 35):
        return "CHAOTIC_LATE", "RED", "AVOID_LATE_CHAOS", "late volatility/fake-overlay pressure"
    if fake >= 40:
        return "PUBLIC_OVERREACTION", "RED", "MONITOR_STEAM", "fake overlay timing pressure"
    if suppression >= 60:
        return "TRAP_WINDOW", "RED", "WAIT_FOR_MARKET", "high suppression timing window"
    if clv is not None and clv > 0 and (beat_close or 0) >= 45:
        return "SHARP_INFORMATION", "GREEN", "EXECUTE_NOW", "positive CLV timing"
    if roi is not None and roi > 0 and fake < 25:
        return "PROTECTED_EDGE_WINDOW", "GREEN", "PROTECTED_EDGE_WINDOW", "positive ROI timing"
    if window in {"30_TO_60_MINS", "15_TO_30_MINS"} and volatility < 30:
        return "LIQUIDITY_STABLE", "GREEN", "EXECUTE_NOW", "stable mid-window timing"
    if window in {"120_PLUS_MINS", "60_TO_120_MINS"}:
        return "EARLY_DISCOVERY", "AMBER", "WAIT_FOR_MARKET", "early market still forming"
    return "LIQUIDITY_STABLE", "AMBER", "MONITOR_STEAM", "balanced timing window"


def add_live_metadata_to_tape(tape: pd.DataFrame, live: pd.DataFrame) -> pd.DataFrame:
    if tape.empty:
        return tape
    if live.empty:
        tape = tape.copy()
        tape["timing_window"] = "UNKNOWN_TIMING"
        tape["minutes_to_jump"] = pd.NA
        return tape

    live_cols = [
        "event_id",
        "horse",
        "track",
        "race_no",
        "race_date",
        "date",
        "race_time",
        "overlay_pct",
        "adjusted_overlay_pct",
        "shrunk_overlay_pct",
        "blended_overlay_pct",
        "overlay_realism_grade",
        "execution_action",
        "final_execution_state",
        "environment_type",
        "market_regime_v2",
        "market_regime",
        "suppression_risk_grade",
    ]
    available = [col for col in live_cols if col in live.columns]
    left = tape.copy()
    right = live[available].copy()
    left["_join_key"] = runner_key(left)
    right["_join_key"] = runner_key(right)
    right = right.drop_duplicates("_join_key", keep="last")
    merged = left.merge(right, on="_join_key", how="left", suffixes=("", "_live"))
    merged = merged.drop(columns=["_join_key"], errors="ignore")

    windows = []
    minutes = []
    for _, row in merged.iterrows():
        stamp = parse_dt(row.get("timestamp"))
        race_dt = parse_race_datetime(row)
        if stamp is None or race_dt is None:
            minutes_to_jump = None
        else:
            minutes_to_jump = (race_dt - stamp).total_seconds() / 60.0
        minutes.append(round(minutes_to_jump, 2) if minutes_to_jump is not None else pd.NA)
        windows.append(timing_window(minutes_to_jump))
    merged["minutes_to_jump"] = minutes
    merged["timing_window"] = windows
    return merged


def add_result_flags(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    result = out.get("result", pd.Series([""] * len(out))).map(upper)
    out["_is_win"] = result.isin(["WON", "WIN", "1", "TRUE"])
    out["_is_loss"] = result.isin(["LOST", "LOSS", "LOSE", "0", "FALSE"])
    out["_is_settled"] = out["_is_win"] | out["_is_loss"] | result.isin(["VOID"])
    out["_stake"] = pd.to_numeric(out.get("stake", 0), errors="coerce").fillna(0)
    out["_profit_loss"] = pd.to_numeric(out.get("profit_loss", 0), errors="coerce")
    out["_clv_pct"] = pd.to_numeric(out.get("clv_pct", pd.NA), errors="coerce")
    return out


def environment_distribution(group: pd.DataFrame) -> str:
    if "environment_type" not in group.columns:
        return ""
    counts = group["environment_type"].map(text)
    counts = counts[counts != ""].value_counts()
    if counts.empty:
        return ""
    return ";".join([f"{idx}:{int(value)}" for idx, value in counts.items()])


def summarise_windows(tape: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame:
    if tape.empty:
        return pd.DataFrame(columns=TEMPORAL_COLUMNS)

    rows = []
    for window, group in tape.groupby("timing_window", dropna=False):
        action = group.get("final_execution_state", group.get("execution_action", pd.Series([""] * len(group)))).map(upper)
        execution_rate = action.isin(["MAX_BET", "PRIORITY_EXECUTE", "EXECUTE", "REDUCED_EXECUTE", "BET"]).mean() * 100.0 if len(group) else 0.0
        suppression_rate = action.isin(["SUPPRESS", "PASS", "NO BET"]).mean() * 100.0 if len(group) else 0.0
        overlay_source = None
        for col in ["blended_overlay_pct", "shrunk_overlay_pct", "adjusted_overlay_pct", "overlay_pct"]:
            if col in group.columns:
                overlay_source = pd.to_numeric(group[col], errors="coerce")
                if overlay_source.notna().any():
                    break
        avg_overlay = float(overlay_source.dropna().mean()) if overlay_source is not None and overlay_source.notna().any() else None
        realism = group.get("overlay_realism_grade", pd.Series([""] * len(group))).map(upper)
        fake_rate = realism.str.contains("FAKE", na=False).mean() * 100.0 if len(group) else 0.0
        regime = group.get("market_regime_v2", group.get("market_regime", pd.Series([""] * len(group)))).map(upper)
        volatility_rate = regime.str.contains("VOLATILE|TOXIC|STEAM|SHOCK|EXTREME", regex=True, na=False).mean() * 100.0 if len(group) else 0.0

        settled_rows = 0
        roi = None
        avg_clv = None
        beat_close = None
        if not results.empty and "timing_window" in results.columns:
            result_group = results[results["timing_window"] == window]
            settled = result_group[result_group["_is_settled"]]
            settled_rows = len(settled)
            turnover = float(settled["_stake"].sum()) if settled_rows else 0.0
            profit = float(settled["_profit_loss"].dropna().sum()) if settled_rows else 0.0
            roi = (profit / turnover * 100.0) if turnover > 0 else None
            clv = settled["_clv_pct"].dropna()
            avg_clv = float(clv.mean()) if len(clv) else None
            beat_close = (float((clv > 0).sum()) / len(clv) * 100.0) if len(clv) else None

        stability = max(0.0, 100.0 - fake_rate - volatility_rate - (suppression_rate * 0.25))
        row = {
            "timing_window": text(window) or "UNKNOWN_TIMING",
            "rows": len(group),
            "settled_rows": settled_rows,
            "execution_rate": round(execution_rate, 2),
            "suppression_rate": round(suppression_rate, 2),
            "average_overlay_pct": round(avg_overlay, 2) if avg_overlay is not None else "",
            "fake_overlay_rate": round(fake_rate, 2),
            "volatility_rate": round(volatility_rate, 2),
            "average_clv_pct": round(avg_clv, 2) if avg_clv is not None else "",
            "beat_close_pct": round(beat_close, 2) if beat_close is not None else "",
            "roi_pct": round(roi, 2) if roi is not None else "",
            "environment_distribution": environment_distribution(group),
            "calibration_quality": "UNMEASURED" if settled_rows < 20 else "MEASURED",
            "stability_score": round(stability, 2),
        }
        timing_env, risk, recommendation, reason = classify_timing(pd.Series(row))
        row["timing_environment"] = timing_env
        row["timing_risk_grade"] = risk
        row["recommended_wait_or_execute"] = recommendation
        row["timing_reason"] = reason
        rows.append(row)

    return pd.DataFrame(rows, columns=TEMPORAL_COLUMNS)


def make_rankings(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame(columns=RANKING_COLUMNS)
    rows = []

    def add(ranking_type: str, row: pd.Series, metric: str, reason: str):
        rows.append({
            "ranking_type": ranking_type,
            "timing_window": row.get("timing_window", ""),
            "timing_environment": row.get("timing_environment", ""),
            "metric_value": row.get(metric, ""),
            "timing_risk_grade": row.get("timing_risk_grade", ""),
            "recommended_wait_or_execute": row.get("recommended_wait_or_execute", ""),
            "reason": reason,
        })

    measured = summary.copy()
    measured["_stability"] = pd.to_numeric(measured["stability_score"], errors="coerce")
    measured["_fake"] = pd.to_numeric(measured["fake_overlay_rate"], errors="coerce")
    measured["_volatility"] = pd.to_numeric(measured["volatility_rate"], errors="coerce")
    measured["_clv"] = pd.to_numeric(measured["average_clv_pct"], errors="coerce")
    measured["_risk_sort"] = measured["timing_risk_grade"].map(lambda v: {"GREEN": 0, "AMBER": 1, "RED": 2}.get(upper(v), 1))

    if len(measured):
        add("SAFEST_EXECUTION_WINDOW", measured.sort_values(["_risk_sort", "_stability"], ascending=[True, False]).iloc[0], "stability_score", "Highest stability with lowest live risk")
        add("MOST_DANGEROUS_EXECUTION_WINDOW", measured.sort_values(["_risk_sort", "_fake", "_volatility"], ascending=[False, False, False]).iloc[0], "fake_overlay_rate", "Highest live timing danger")
        add("HIGHEST_FAKE_OVERLAY_TIMING", measured.sort_values("_fake", ascending=False).iloc[0], "fake_overlay_rate", "Highest fake-overlay timing pressure")
        add("HIGHEST_VOLATILITY_TIMING", measured.sort_values("_volatility", ascending=False).iloc[0], "volatility_rate", "Highest volatility timing pressure")

    clv_measured = measured.dropna(subset=["_clv"])
    if len(clv_measured):
        add("STRONGEST_CLV_TIMING", clv_measured.sort_values("_clv", ascending=False).iloc[0], "average_clv_pct", "Highest average CLV timing")

    protected = measured[measured["timing_environment"] == "PROTECTED_EDGE_WINDOW"]
    if len(protected):
        add("STRONGEST_PROTECTED_EDGE_TIMING", protected.sort_values("_stability", ascending=False).iloc[0], "stability_score", "Protected-edge timing currently present")

    return pd.DataFrame(rows, columns=RANKING_COLUMNS)


def attach_timing_to_live(live: pd.DataFrame, tape: pd.DataFrame, summary: pd.DataFrame) -> pd.DataFrame:
    if live.empty:
        return live
    out = live.copy()
    if tape.empty:
        out["timing_window"] = "UNKNOWN_TIMING"
    else:
        tape_latest = tape.copy()
        tape_latest["_key"] = runner_key(tape_latest)
        tape_latest["_stamp"] = pd.to_datetime(tape_latest.get("timestamp"), errors="coerce")
        tape_latest = tape_latest.sort_values("_stamp").drop_duplicates("_key", keep="last")
        out["_key"] = runner_key(out)
        cols = ["_key", "timing_window", "minutes_to_jump"]
        tape_latest = tape_latest[[col for col in cols if col in tape_latest.columns]]
        out = out.merge(tape_latest, on="_key", how="left", suffixes=("", "_timing"))
        out = out.drop(columns=["_key"], errors="ignore")
        out["timing_window"] = out["timing_window"].fillna("UNKNOWN_TIMING")

    summary_lookup = summary.set_index("timing_window").to_dict("index") if not summary.empty and "timing_window" in summary.columns else {}
    for idx, row in out.iterrows():
        window = text(row.get("timing_window")) or "UNKNOWN_TIMING"
        info = summary_lookup.get(window, {})
        out.at[idx, "timing_environment"] = info.get("timing_environment", "NEUTRAL")
        out.at[idx, "timing_risk_grade"] = info.get("timing_risk_grade", "AMBER")
        out.at[idx, "timing_execution_quality"] = info.get("stability_score", "")
        out.at[idx, "recommended_wait_or_execute"] = info.get("recommended_wait_or_execute", "WAIT_FOR_MARKET")
        out.at[idx, "timing_reason"] = info.get("timing_reason", "timing unavailable")
    return out


def append_timing_to_terminal(terminal: pd.DataFrame, live: pd.DataFrame) -> pd.DataFrame:
    if terminal.empty or live.empty:
        return terminal
    left = terminal.copy()
    right = live.copy()
    left["_key"] = full_runner_key(left)
    right["_key"] = full_runner_key(right)
    cols = [
        "timing_window",
        "timing_environment",
        "timing_risk_grade",
        "timing_execution_quality",
        "recommended_wait_or_execute",
        "timing_reason",
    ]
    right = right[["_key"] + [col for col in cols if col in right.columns]].drop_duplicates("_key", keep="last")
    merged = left.merge(right, on="_key", how="left", suffixes=("", "_timing"))
    for col in cols:
        extra = f"{col}_timing"
        if extra in merged.columns:
            current = merged[col].map(text) if col in merged.columns else pd.Series([""] * len(merged), index=merged.index)
            merged[col] = merged[col].where(current != "", merged[extra]) if col in merged.columns else merged[extra]
            merged = merged.drop(columns=[extra])
    return merged.drop(columns=["_key"], errors="ignore")


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    tape = read_csv(MARKET_TAPE)
    live = read_csv(LIVE)
    results = read_csv(RESULTS)
    environment = read_csv(ENVIRONMENT)
    policy = read_csv(POLICY)

    if live.empty and tape.empty:
        pd.DataFrame(columns=TEMPORAL_COLUMNS).to_csv(OUT_TEMPORAL, index=False)
        pd.DataFrame(columns=RANKING_COLUMNS).to_csv(OUT_RANKINGS, index=False)
        print("[temporal] no live/tape rows; wrote empty outputs")
        return

    if not environment.empty:
        live = live.merge(
            environment[["track", "race_no", "horse", "environment_type"]].drop_duplicates(["track", "race_no", "horse"], keep="last"),
            on=["track", "race_no", "horse"],
            how="left",
            suffixes=("", "_env"),
        )
        if "environment_type_env" in live.columns:
            current = live["environment_type"].map(text) if "environment_type" in live.columns else pd.Series([""] * len(live), index=live.index)
            live["environment_type"] = live["environment_type"].where(current != "", live["environment_type_env"]) if "environment_type" in live.columns else live["environment_type_env"]
            live = live.drop(columns=["environment_type_env"])

    tape = add_live_metadata_to_tape(tape, live)
    results = add_result_flags(results) if not results.empty else results
    summary = summarise_windows(tape, results)
    rankings = make_rankings(summary)
    live_with_timing = attach_timing_to_live(live, tape, summary)

    live_with_timing.to_csv(LIVE, index=False)
    if TERMINAL.exists():
        terminal = read_csv(TERMINAL)
        append_timing_to_terminal(terminal, live_with_timing).to_csv(TERMINAL, index=False)
    else:
        live_with_timing.to_csv(TERMINAL, index=False)
    summary.to_csv(OUT_TEMPORAL, index=False)
    rankings.to_csv(OUT_RANKINGS, index=False)

    dominant = summary.sort_values("rows", ascending=False).iloc[0]["timing_environment"] if not summary.empty else "NONE"
    safest = rankings[rankings["ranking_type"] == "SAFEST_EXECUTION_WINDOW"].head(1)
    dangerous = rankings[rankings["ranking_type"] == "MOST_DANGEROUS_EXECUTION_WINDOW"].head(1)
    clv = rankings[rankings["ranking_type"] == "STRONGEST_CLV_TIMING"].head(1)

    print("[temporal] timing windows analysed:", len(summary))
    print("[temporal] safest timing window:", safest.iloc[0].to_dict() if len(safest) else "none")
    print("[temporal] most dangerous timing window:", dangerous.iloc[0].to_dict() if len(dangerous) else "none")
    print("[temporal] strongest CLV timing:", clv.iloc[0].to_dict() if len(clv) else "none")
    print("[temporal] dominant timing environment:", dominant)
    print("[temporal] policy rows read:", len(policy))


if __name__ == "__main__":
    main()
