import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "public" / "data"

TERMINAL_CANDIDATES = [
    DATA / "edgeiq_live_terminal_feed_v1.csv",
    DATA / "edgeiq_vic_live_terminal_feed_v1.csv",
]
V71_PATH = DATA / "edgeiq_fair_price_engine_v7_1_candidate.csv"
V7_PATH = DATA / "edgeiq_probability_engine_v7.csv"

OUT_CANDIDATE = DATA / "edgeiq_live_terminal_feed_v7_1_candidate.csv"
OUT_AUDIT = DATA / "edgeiq_live_terminal_feed_v7_1_candidate_join_audit_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_live_terminal_feed_v7_1_candidate_join_summary_v1.csv"
OUT_REPORT = DATA / "edgeiq_live_terminal_feed_v7_1_candidate_join_report_v1.txt"

REQUIRED_JOIN_FIELDS = ["track", "race_no", "horse"]
APPEND_COLUMNS = [
    "edgeiq_probability_v7_candidate",
    "edgeiq_fair_price_v7_calibrated_candidate",
    "edgeiq_display_fair_price_v7_1_candidate",
    "edgeiq_price_engine_version_candidate",
    "edgeiq_display_price_engine_version_candidate",
    "edgeiq_v7_1_join_status",
    "edgeiq_v7_1_live_wired_flag",
    "edgeiq_v7_1_feature_flag",
    "edgeiq_v7_1_production_changed",
    "edgeiq_v7_1_source_file",
    "edgeiq_v7_1_join_key",
]


def read_csv_safe(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)


def pick_terminal_source() -> Path | None:
    for path in TERMINAL_CANDIDATES:
        if path.exists():
            return path
    return None


def normalize_date(value: object) -> str:
    raw = "" if pd.isna(value) else str(value).strip()
    if not raw:
        return ""
    parsed = pd.to_datetime(raw, errors="coerce", dayfirst=False)
    if pd.isna(parsed):
        parsed = pd.to_datetime(raw, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        match = re.search(r"(20\d{2})[-_/]?(\d{2})[-_/]?(\d{2})", raw)
        if match:
            return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        return raw.upper().strip()
    return parsed.strftime("%Y-%m-%d")


def normalize_track(value: object) -> str:
    raw = "" if pd.isna(value) else str(value).upper().strip()
    return re.sub(r"\s+", " ", raw)


def normalize_race_no(value: object) -> str:
    raw = "" if pd.isna(value) else str(value).strip().upper()
    if not raw:
        return ""
    match = re.search(r"\d+", raw)
    if not match:
        return raw
    return str(int(match.group(0)))


def normalize_horse(value: object) -> str:
    raw = "" if pd.isna(value) else str(value).upper().strip()
    raw = re.sub(r"[^A-Z0-9\s]", "", raw)
    return re.sub(r"\s+", " ", raw).strip()


def date_column(df: pd.DataFrame) -> str | None:
    for col in ["race_date", "meeting_date", "date"]:
        if col in df.columns:
            return col
    return None


def build_join_key(df: pd.DataFrame, prefix: str) -> tuple[pd.Series, list[str]]:
    missing = []
    date_col = date_column(df)
    if date_col is None:
        missing.append("race_date/meeting_date")
        date_values = pd.Series([""] * len(df), index=df.index)
    else:
        date_values = df[date_col].map(normalize_date)

    for col in REQUIRED_JOIN_FIELDS:
        if col not in df.columns:
            missing.append(col)

    track_values = df["track"].map(normalize_track) if "track" in df.columns else pd.Series([""] * len(df), index=df.index)
    race_values = df["race_no"].map(normalize_race_no) if "race_no" in df.columns else pd.Series([""] * len(df), index=df.index)
    horse_values = df["horse"].map(normalize_horse) if "horse" in df.columns else pd.Series([""] * len(df), index=df.index)
    return (date_values + "|" + track_values + "|" + race_values + "|" + horse_values).rename(f"{prefix}_join_key"), missing


def numeric_present_count(df: pd.DataFrame, col: str) -> int:
    if col not in df.columns:
        return 0
    return int((df[col].astype(str).str.strip() != "").sum())


def metric_rows(metrics: dict[str, object]) -> pd.DataFrame:
    return pd.DataFrame([{"metric": key, "value": value} for key, value in metrics.items()])


def build_report(metrics: dict[str, object], warnings: list[str]) -> str:
    warning_text = "\n".join([f"- {w}" for w in warnings]) if warnings else "- None."
    return f"""EDGEiQ LIVE TERMINAL FEED V7.1 CANDIDATE JOIN V1

1. Status
- Candidate only.
- No live wiring.
- No production change.
- Feature flag OFF.
- Existing terminal columns preserved.
- Candidate columns appended only.
- Status: {metrics.get('status')}.

2. Join result
- Terminal source file used: {metrics.get('terminal_source_file_used')}.
- Terminal rows: {metrics.get('terminal_rows')}.
- Candidate rows: {metrics.get('candidate_rows')}.
- Output rows: {metrics.get('output_rows')}.
- Matched rows: {metrics.get('matched_rows')}.
- Unmatched rows: {metrics.get('unmatched_rows')}.
- Match rate pct: {metrics.get('match_rate_pct')}.
- Probability joined rows: {metrics.get('probability_joined_rows')}.
- Display fair joined rows: {metrics.get('display_fair_joined_rows')}.

3. Production safety
- edgeiq_v7_1_live_wired_flag values: {metrics.get('live_wired_values')}.
- edgeiq_v7_1_feature_flag values: {metrics.get('feature_flag_values')}.
- edgeiq_v7_1_production_changed values: {metrics.get('production_changed_values')}.
- Existing fair_price column found: {metrics.get('old_fair_price_column_found')}.
- Existing live_price column found: {metrics.get('old_live_price_column_found')}.
- Existing ui_price column found: {metrics.get('old_ui_price_column_found')}.
- Existing ui_fair_price column found: {metrics.get('old_ui_fair_price_column_found')}.
- Original terminal feed files were not overwritten by this script.
- Live runner board files were not modified by this script.
- UI files were not modified by this script.

4. Data quality notes
- Duplicate terminal keys: {metrics.get('duplicate_terminal_keys')}.
- Duplicate candidate keys: {metrics.get('duplicate_candidate_keys')}.
- Warnings:
{warning_text}

5. Review requirement
- Review required before any wiring.
- Candidate may have low or zero match rate because the terminal feed is current-day while V7/V7.1 artifacts are TAB-quality replay-history artifacts.
"""


def write_blocked_outputs(status: str, terminal_path: Path | None, terminal_df: pd.DataFrame, missing_reasons: list[str]) -> pd.DataFrame:
    output_df = terminal_df.copy()
    for col in APPEND_COLUMNS:
        if col not in output_df.columns:
            output_df[col] = ""
    output_df["edgeiq_v7_1_join_status"] = status
    output_df["edgeiq_v7_1_live_wired_flag"] = "NO"
    output_df["edgeiq_v7_1_feature_flag"] = "OFF"
    output_df["edgeiq_v7_1_production_changed"] = "NO"
    output_df.to_csv(OUT_CANDIDATE, index=False)

    audit = pd.DataFrame([{
        "terminal_source_file_used": str(terminal_path.relative_to(BASE)) if terminal_path else "MISSING",
        "join_key": "",
        "track": "",
        "race_no": "",
        "horse": "",
        "join_status": status,
        "candidate_probability_found": "NO",
        "candidate_display_fair_found": "NO",
        "reason": "; ".join(missing_reasons),
    }])
    audit.to_csv(OUT_AUDIT, index=False)

    summary_metrics = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "terminal_source_file_used": str(terminal_path.relative_to(BASE)) if terminal_path else "MISSING",
        "terminal_rows": len(terminal_df),
        "candidate_rows": 0,
        "output_rows": len(output_df),
        "matched_rows": 0,
        "unmatched_rows": len(output_df),
        "match_rate_pct": 0.0,
        "probability_joined_rows": 0,
        "display_fair_joined_rows": 0,
        "old_fair_price_column_found": "YES" if "fair_price" in terminal_df.columns else "NO",
        "old_live_price_column_found": "YES" if "live_price" in terminal_df.columns else "NO",
        "old_ui_price_column_found": "YES" if "ui_price" in terminal_df.columns else "NO",
        "old_ui_fair_price_column_found": "YES" if "ui_fair_price" in terminal_df.columns else "NO",
        "feature_flag_values": "OFF",
        "live_wired_values": "NO",
        "production_changed_values": "NO",
        "duplicate_terminal_keys": 0,
        "duplicate_candidate_keys": 0,
        "status": status,
    }
    summary = metric_rows(summary_metrics)
    summary.to_csv(OUT_SUMMARY, index=False)
    OUT_REPORT.write_text(build_report(summary_metrics, missing_reasons), encoding="utf-8")
    return summary


def main() -> None:
    warnings = []
    terminal_path = pick_terminal_source()
    if terminal_path is None:
        summary = write_blocked_outputs(
            "TERMINAL_CANDIDATE_JOIN_BLOCKED_SCHEMA_MISSING",
            None,
            pd.DataFrame(),
            ["No terminal feed source file found."],
        )
        print(summary.to_string(index=False))
        print(OUT_REPORT.read_text(encoding="utf-8"))
        return

    terminal_df = read_csv_safe(terminal_path)
    v71_df = read_csv_safe(V71_PATH)
    v7_df = read_csv_safe(V7_PATH)

    schema_missing = []
    if v71_df.empty:
        schema_missing.append(f"Missing or empty V7.1 candidate file: {V71_PATH.relative_to(BASE)}")
    if v7_df.empty:
        schema_missing.append(f"Missing or empty V7 probability file: {V7_PATH.relative_to(BASE)}")

    terminal_key, terminal_missing = build_join_key(terminal_df, "terminal")
    v71_key, v71_missing = build_join_key(v71_df, "v71") if not v71_df.empty else (pd.Series(dtype=str), ["V7.1 file empty"])
    v7_key, v7_missing = build_join_key(v7_df, "v7") if not v7_df.empty else (pd.Series(dtype=str), ["V7 file empty"])

    if terminal_missing:
        schema_missing.append("Terminal source missing join fields: " + ", ".join(terminal_missing))
    if v71_missing:
        schema_missing.append("V7.1 source missing join fields: " + ", ".join(v71_missing))
    if v7_missing:
        schema_missing.append("V7 source missing join fields: " + ", ".join(v7_missing))

    if schema_missing:
        summary = write_blocked_outputs("TERMINAL_CANDIDATE_JOIN_BLOCKED_SCHEMA_MISSING", terminal_path, terminal_df, schema_missing)
        print(summary.to_string(index=False))
        print(OUT_REPORT.read_text(encoding="utf-8"))
        return

    terminal_work = terminal_df.copy()
    terminal_work["__join_key"] = terminal_key
    v71_work = v71_df.copy()
    v71_work["__join_key"] = v71_key
    v7_work = v7_df.copy()
    v7_work["__join_key"] = v7_key

    duplicate_terminal_keys = int(terminal_work["__join_key"].duplicated(keep=False).sum())
    duplicate_v71_keys = int(v71_work["__join_key"].duplicated(keep=False).sum())
    duplicate_v7_keys = int(v7_work["__join_key"].duplicated(keep=False).sum())
    duplicate_candidate_keys = max(duplicate_v71_keys, duplicate_v7_keys)

    v71_cols = ["__join_key"] + [col for col in ["edgeiq_display_fair_price_v7_1", "display_price_engine", "artifact_status", "production_changed", "edgeiq_probability_v7", "edgeiq_fair_price_v7"] if col in v71_work.columns]
    v7_cols = ["__join_key"] + [col for col in ["edgeiq_probability_v7", "edgeiq_fair_price_v7", "probability_engine_version", "probability_engine_status"] if col in v7_work.columns]
    v71_map = v71_work[v71_cols].drop_duplicates("__join_key", keep="first")
    v7_map = v7_work[v7_cols].drop_duplicates("__join_key", keep="first")

    merged = terminal_work.merge(v71_map, on="__join_key", how="left", suffixes=("", "_v71src"))
    merged = merged.merge(v7_map, on="__join_key", how="left", suffixes=("", "_v7src"))

    output = terminal_df.copy()
    blank = pd.Series([""] * len(merged), index=merged.index)
    output["edgeiq_probability_v7_candidate"] = (merged["edgeiq_probability_v7_v7src"] if "edgeiq_probability_v7_v7src" in merged.columns else merged.get("edgeiq_probability_v7", blank)).fillna("").astype(str)
    output["edgeiq_fair_price_v7_calibrated_candidate"] = (merged["edgeiq_fair_price_v7_v7src"] if "edgeiq_fair_price_v7_v7src" in merged.columns else merged.get("edgeiq_fair_price_v7", blank)).fillna("").astype(str)
    output["edgeiq_display_fair_price_v7_1_candidate"] = merged.get("edgeiq_display_fair_price_v7_1", blank).fillna("").astype(str)
    output["edgeiq_price_engine_version_candidate"] = merged.get("probability_engine_version", pd.Series(["V7_TEMPERATURE6_TAB_QUALITY"] * len(merged), index=merged.index)).fillna("").astype(str)
    output["edgeiq_display_price_engine_version_candidate"] = merged.get("display_price_engine", pd.Series(["V7_1_DISPLAY_FAIR_PRICE_LAYER"] * len(merged), index=merged.index)).fillna("").astype(str)

    matched_mask = output["edgeiq_probability_v7_candidate"].str.strip().ne("") | output["edgeiq_display_fair_price_v7_1_candidate"].str.strip().ne("")
    output["edgeiq_v7_1_join_status"] = matched_mask.map(lambda x: "MATCHED" if x else "UNMATCHED")
    output["edgeiq_v7_1_live_wired_flag"] = "NO"
    output["edgeiq_v7_1_feature_flag"] = "OFF"
    output["edgeiq_v7_1_production_changed"] = "NO"
    output["edgeiq_v7_1_source_file"] = str(V71_PATH.relative_to(BASE))
    output["edgeiq_v7_1_join_key"] = terminal_work["__join_key"]

    matched_rows = int(matched_mask.sum())
    unmatched_rows = int(len(output) - matched_rows)
    match_rate_pct = round((matched_rows / len(output) * 100.0), 4) if len(output) else 0.0
    probability_joined_rows = numeric_present_count(output, "edgeiq_probability_v7_candidate")
    display_fair_joined_rows = numeric_present_count(output, "edgeiq_display_fair_price_v7_1_candidate")

    if len(output) != len(terminal_df):
        status = "TERMINAL_CANDIDATE_JOIN_BLOCKED_ROW_COUNT_CHANGED"
    elif matched_rows == 0:
        status = "TERMINAL_CANDIDATE_JOIN_BUILT_WITH_ZERO_MATCHES_REVIEW_REQUIRED"
    else:
        status = "TERMINAL_CANDIDATE_JOIN_BUILT_REVIEW_REQUIRED"

    output.to_csv(OUT_CANDIDATE, index=False)

    race_date_values = output["race_date"] if "race_date" in output.columns else output["meeting_date"] if "meeting_date" in output.columns else pd.Series([""] * len(output), index=output.index)
    audit = pd.DataFrame({
        "terminal_source_file_used": str(terminal_path.relative_to(BASE)),
        "join_key": output["edgeiq_v7_1_join_key"],
        "race_date": race_date_values,
        "track": output["track"] if "track" in output.columns else "",
        "race_no": output["race_no"] if "race_no" in output.columns else "",
        "horse": output["horse"] if "horse" in output.columns else "",
        "join_status": output["edgeiq_v7_1_join_status"],
        "candidate_probability_found": output["edgeiq_probability_v7_candidate"].astype(str).str.strip().ne("").map(lambda x: "YES" if x else "NO"),
        "candidate_display_fair_found": output["edgeiq_display_fair_price_v7_1_candidate"].astype(str).str.strip().ne("").map(lambda x: "YES" if x else "NO"),
        "reason": output["edgeiq_v7_1_join_status"].map(lambda x: "JOINED_ON_NORMALIZED_KEY" if x == "MATCHED" else "NO_MATCH_ON_NORMALIZED_DATE_TRACK_RACE_HORSE"),
    })
    audit.to_csv(OUT_AUDIT, index=False)

    feature_flag_values = ",".join(sorted(output["edgeiq_v7_1_feature_flag"].astype(str).unique()))
    live_wired_values = ",".join(sorted(output["edgeiq_v7_1_live_wired_flag"].astype(str).unique()))
    production_changed_values = ",".join(sorted(output["edgeiq_v7_1_production_changed"].astype(str).unique()))
    summary_metrics = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "terminal_source_file_used": str(terminal_path.relative_to(BASE)),
        "terminal_rows": len(terminal_df),
        "candidate_rows": len(v71_df),
        "v7_probability_rows": len(v7_df),
        "output_rows": len(output),
        "matched_rows": matched_rows,
        "unmatched_rows": unmatched_rows,
        "match_rate_pct": match_rate_pct,
        "probability_joined_rows": probability_joined_rows,
        "display_fair_joined_rows": display_fair_joined_rows,
        "old_fair_price_column_found": "YES" if "fair_price" in terminal_df.columns else "NO",
        "old_live_price_column_found": "YES" if "live_price" in terminal_df.columns else "NO",
        "old_ui_price_column_found": "YES" if "ui_price" in terminal_df.columns else "NO",
        "old_ui_fair_price_column_found": "YES" if "ui_fair_price" in terminal_df.columns else "NO",
        "old_market_price_column_found": "YES" if "market_price" in terminal_df.columns else "NO",
        "old_win_pct_column_found": "YES" if "win_pct" in terminal_df.columns else "NO",
        "feature_flag_values": feature_flag_values,
        "live_wired_values": live_wired_values,
        "production_changed_values": production_changed_values,
        "duplicate_terminal_keys": duplicate_terminal_keys,
        "duplicate_candidate_keys": duplicate_candidate_keys,
        "duplicate_v7_1_keys": duplicate_v71_keys,
        "duplicate_v7_probability_keys": duplicate_v7_keys,
        "status": status,
    }
    summary = metric_rows(summary_metrics)
    summary.to_csv(OUT_SUMMARY, index=False)

    if matched_rows == 0:
        warnings.append("Zero normalized-key matches. This can be expected when current-day terminal feed rows do not exist in replay-history V7/V7.1 artifacts.")
    if duplicate_terminal_keys:
        warnings.append("Duplicate normalized terminal keys found; audit rows should be reviewed before any future wiring.")
    if duplicate_candidate_keys:
        warnings.append("Duplicate normalized candidate keys found; first row per key was used for candidate join.")

    report = build_report(summary_metrics, warnings)
    OUT_REPORT.write_text(report, encoding="utf-8")

    print(summary.to_string(index=False))
    print(report)


if __name__ == "__main__":
    main()
