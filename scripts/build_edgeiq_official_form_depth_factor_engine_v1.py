from pathlib import Path
from datetime import datetime
import re
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RACE_FIELDS = DATA / "race_fields.csv"
FORM_SUMMARY = DATA / "form_card_summary.csv"
FORM_RUNS = DATA / "form_card_runs.csv"
OFFICIAL_RUNS_MASTER = DATA / "edgeiq_official_runs_master_v1.csv"
SECTIONAL_MASTER = DATA / "edgeiq_sectional_master_v1.csv"
LIVE_BOARD = DATA / "edgeiq_execution_board_live.csv"
TERMINAL_BOARD = DATA / "edgeiq_execution_board_terminal.csv"
DATA_QUALITY = DATA / "edgeiq_data_quality_by_runner_v1.csv"

DEPTH_OUT = DATA / "edgeiq_official_form_depth_factor_v1.csv"
GAPS_OUT = DATA / "edgeiq_official_form_factor_gaps_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_official_form_factor_summary_v1.csv"

DEPTH_COLUMNS = [
    "race_id",
    "race_date",
    "track",
    "race_no",
    "horse",
    "matched_to_form_card_summary",
    "matched_to_form_card_runs",
    "official_race_run_count",
    "trial_run_count",
    "jumpout_run_count",
    "last_official_run_date",
    "days_since_last_official_run",
    "has_last3_rating",
    "has_last5_rating",
    "has_peak_rating",
    "has_distance_history",
    "has_track_condition_history",
    "has_class_history",
    "has_margin_history",
    "has_sp_history",
    "has_jockey_history",
    "has_trainer_history",
    "has_barrier_history",
    "has_in_run_position_history",
    "has_sectional_data",
    "has_last600",
    "has_last400",
    "has_last200",
    "has_speed_figure",
    "has_run_context_flags",
    "official_form_depth_score",
    "official_form_depth_grade",
    "missing_form_factors",
    "pricing_impact",
    "recommended_data_fix",
]

SUMMARY_COLUMNS = [
    "total_runners",
    "official_form_coverage_pct",
    "average_official_run_count",
    "no_official_form_count",
    "thin_official_form_count",
    "elite_form_depth_count",
    "sectional_data_coverage_pct",
    "class_history_coverage_pct",
    "distance_history_coverage_pct",
    "condition_history_coverage_pct",
    "biggest_missing_factor",
    "top_recommended_data_fix",
]

GAP_COLUMNS = [
    "factor",
    "missing_count",
    "missing_pct",
    "pricing_impact",
    "recommended_data_fix",
]


def log(message: str) -> None:
    print(f"[official_form_depth_v1] {message}")


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


def clean(value) -> str:
    return str(value or "").strip()


def upper(value) -> str:
    return clean(value).upper()


def norm(value) -> str:
    text = re.sub(r"\([^)]*\)", "", upper(value))
    return re.sub(r"[^A-Z0-9]+", "", text)


def has_value(value) -> bool:
    text = clean(value)
    if not text:
        return False
    return text.upper() not in {"NAN", "NONE", "NULL", "UNKNOWN", "N/A", "-"}


def bool_text(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def number(value):
    try:
        text = clean(value).replace("$", "").replace("%", "").replace("M", "")
        if not text:
            return None
        parsed = float(text)
        return parsed if pd.notna(parsed) else None
    except Exception:
        return None


def first_existing(row: pd.Series, names: list[str]) -> str:
    for name in names:
        if name in row.index and has_value(row.get(name, "")):
            return clean(row.get(name, ""))
    return ""


def parse_date(value):
    text = clean(value)
    if not text:
        return None
    parsed = pd.to_datetime(text, errors="coerce", dayfirst=False)
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def key_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    horse_key_col = next((c for c in ["horse_key", "_horse_key"] if c in out.columns), "")
    horse_col = next((c for c in ["horse", "runner", "runner_name", "selection"] if c in out.columns), "")
    track_col = next((c for c in ["track", "meeting", "venue"] if c in out.columns), "")
    race_col = next((c for c in ["race_no", "race_number", "race"] if c in out.columns), "")
    date_col = next((c for c in ["race_date", "date"] if c in out.columns), "")
    race_id_col = next((c for c in ["race_id", "race_key"] if c in out.columns), "")

    out["_horse_key"] = out[horse_key_col].map(norm) if horse_key_col else (out[horse_col].map(norm) if horse_col else "")
    out["_track_key"] = out[track_col].map(norm) if track_col else ""
    out["_race_no_key"] = out[race_col].astype(str).str.extract(r"(\d+)", expand=False).fillna("") if race_col else ""
    out["_date_key"] = out[date_col].astype(str).str.slice(0, 10) if date_col else ""
    out["_race_id_key"] = out[race_id_col].astype(str).str.strip() if race_id_col else ""
    out["_race_match_key"] = out["_race_id_key"].where(
        out["_race_id_key"].ne(""),
        out["_date_key"] + "|" + out["_track_key"] + "|R" + out["_race_no_key"],
    )
    return out


def is_official_run(row: pd.Series) -> bool:
    if "official_run_flag" in row.index:
        return upper(row.get("official_run_flag", "")) == "TRUE"
    official = upper(row.get("is_official_race", ""))
    run_type = upper(row.get("run_type", ""))
    if official in {"TRUE", "YES", "1"}:
        return True
    if run_type in {"RACE", "OFFICIAL_RACE"}:
        return True
    return False


def is_trial_run(row: pd.Series) -> bool:
    if "trial_flag" in row.index:
        return upper(row.get("trial_flag", "")) == "TRUE"
    text = " ".join(upper(row.get(c, "")) for c in ["run_type", "race_class", "class_name", "race_name", "raw_text"])
    return "TRIAL" in text


def is_jumpout_run(row: pd.Series) -> bool:
    if "jumpout_flag" in row.index:
        return upper(row.get("jumpout_flag", "")) == "TRUE"
    text = " ".join(upper(row.get(c, "")) for c in ["run_type", "race_class", "class_name", "race_name", "raw_text"])
    return "JUMPOUT" in text or "JUMP OUT" in text


def pct(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0.00"
    return f"{(numerator / denominator) * 100:.2f}"


def summary_rows(df: pd.DataFrame, horse_key: str, race_match_key: str) -> pd.DataFrame:
    if df.empty:
        return df
    keyed = key_frame(df)
    direct = keyed[(keyed["_horse_key"] == horse_key) & (keyed["_race_match_key"] == race_match_key)]
    if not direct.empty:
        return direct
    return keyed[keyed["_horse_key"] == horse_key]


def run_rows(df: pd.DataFrame, horse_key: str) -> pd.DataFrame:
    if df.empty:
        return df
    keyed = key_frame(df)
    return keyed[keyed["_horse_key"] == horse_key]


def sectional_rows(df: pd.DataFrame, horse_key: str, race_match_key: str) -> pd.DataFrame:
    if df.empty:
        return df
    keyed = key_frame(df)
    direct = keyed[(keyed["_horse_key"] == horse_key) & (keyed["_race_match_key"] == race_match_key)]
    if not direct.empty:
        return direct
    return keyed[keyed["_horse_key"] == horse_key]


def row_has_any(rows: pd.DataFrame, columns: list[str]) -> bool:
    for column in columns:
        if column in rows.columns and rows[column].map(has_value).any():
            return True
    return False


def build_runner_audit(live: pd.DataFrame, form_summary: pd.DataFrame, form_runs: pd.DataFrame, sectionals: pd.DataFrame) -> pd.DataFrame:
    records = []
    for _, row in live.iterrows():
        horse_key = row.get("_horse_key", "")
        race_match_key = row.get("_race_match_key", "")
        summaries = summary_rows(form_summary, horse_key, race_match_key)
        runs = run_rows(form_runs, horse_key)
        sectional_history = sectional_rows(sectionals, horse_key, race_match_key)
        official_runs = runs[runs.apply(is_official_run, axis=1)] if not runs.empty else pd.DataFrame()
        trials = runs[runs.apply(is_trial_run, axis=1)] if not runs.empty else pd.DataFrame()
        jumpouts = runs[runs.apply(is_jumpout_run, axis=1)] if not runs.empty else pd.DataFrame()

        official_count = len(official_runs)
        trial_count = len(trials)
        jumpout_count = len(jumpouts)
        race_date = parse_date(first_existing(row, ["race_date", "date"]))
        run_dates = []
        if not official_runs.empty:
            for _, run in official_runs.iterrows():
                parsed = parse_date(first_existing(run, ["run_date", "date"]))
                if parsed:
                    run_dates.append(parsed)
        last_run = max(run_dates) if run_dates else None
        days_since = (race_date - last_run).days if race_date and last_run else ""

        summary = summaries.iloc[-1] if not summaries.empty else pd.Series(dtype=str)
        has_last3 = has_value(first_existing(summary, ["3LSA", "last3_rating_avg", "last3_flat_avg", "summary_3lsa"]))
        has_last5 = has_value(first_existing(summary, ["5LSA", "last5_rating_avg", "last5_flat_avg", "summary_5lsa"]))
        has_peak = has_value(first_existing(summary, ["PEAK", "peak_rating", "peak", "summary_peak"]))
        has_distance = row_has_any(official_runs, ["distance"])
        has_condition = row_has_any(official_runs, ["track_condition", "condition"])
        has_class = row_has_any(official_runs, ["race_class", "class_name"])
        has_margin = row_has_any(official_runs, ["margin"])
        has_sp = row_has_any(official_runs, ["starting_price", "sp", "sp_text"])
        has_jockey = row_has_any(official_runs, ["jockey"])
        has_trainer = row_has_any(official_runs, ["trainer"])
        has_barrier = row_has_any(official_runs, ["barrier"])
        has_in_run = row_has_any(official_runs, ["pos_800", "pos_400", "in_run_positions"])
        has_last600 = row_has_any(official_runs, ["last600", "last_600", "sectional_600", "final_600"]) or row_has_any(sectional_history, ["last_600", "last600"])
        has_last400 = row_has_any(official_runs, ["last400", "last_400", "sectional_400", "final_400"]) or row_has_any(sectional_history, ["last_400", "last400"])
        has_last200 = row_has_any(official_runs, ["last200", "last_200", "sectional_200", "final_200"]) or row_has_any(sectional_history, ["last_200", "last200"])
        has_sectional = has_last600 or has_last400 or has_last200 or row_has_any(official_runs, ["sectionals", "sectional_data"]) or row_has_any(sectional_history, ["peak_speed", "top_speed", "early_speed", "mid_speed", "late_speed"])
        has_speed = row_has_any(official_runs, ["run_rating", "rating", "speed_figure", "latest_flat_rating"])
        has_context = row_has_any(official_runs, ["raw_text", "rating_band", "in_run_positions", "finish_pos"])

        factors = {
            "last3_rating": has_last3,
            "last5_rating": has_last5,
            "peak_rating": has_peak,
            "distance_history": has_distance,
            "track_condition_history": has_condition,
            "class_history": has_class,
            "margin_history": has_margin,
            "sp_history": has_sp,
            "jockey_history": has_jockey,
            "trainer_history": has_trainer,
            "barrier_history": has_barrier,
            "in_run_position_history": has_in_run,
            "sectional_data": has_sectional,
            "last600": has_last600,
            "last400": has_last400,
            "last200": has_last200,
            "speed_figure": has_speed,
            "run_context_flags": has_context,
        }
        missing = [name for name, ok in factors.items() if not ok]
        coverage = sum(1 for ok in factors.values() if ok)
        score = 0
        score += min(official_count, 5) * 8
        score += 8 if has_last3 else 0
        score += 8 if has_last5 else 0
        score += 8 if has_peak else 0
        score += 6 if has_distance else 0
        score += 6 if has_class else 0
        score += 5 if has_condition else 0
        score += 5 if has_margin else 0
        score += 5 if has_sp else 0
        score += 4 if has_jockey else 0
        score += 4 if has_trainer else 0
        score += 4 if has_barrier else 0
        score += 5 if has_in_run else 0
        score += 5 if has_speed else 0
        score += 5 if has_context else 0
        score += 4 if has_sectional else 0
        score = min(score, 100)

        if official_count == 0:
            grade = "NONE"
            impact = "NO_OFFICIAL_FORM_BLOCKS_MODEL_PRICING"
            fix = "CAP MODEL CONFIDENCE; IMPROVE OFFICIAL FORM MATCHING OR TREAT AS FIRST STARTER"
        elif official_count <= 2:
            grade = "THIN"
            impact = "LIMITED_SAMPLE_REQUIRES_UNCERTAINTY_PENALTY"
            fix = "USE MARKET CONFIRMATION AND CAP STAKE UNTIL MORE OFFICIAL RUNS"
        elif score >= 88 and not {"sectional_data", "distance_history", "class_history", "track_condition_history"}.intersection(set(missing)):
            grade = "ELITE"
            impact = "OFFICIAL_FORM_DEPTH_SUPPORTS_SHARPER_PRICING"
            fix = "DATA COVERAGE ACCEPTABLE"
        elif score >= 62:
            grade = "GOOD"
            impact = "USABLE_FORM_DEPTH_WITH_FACTOR_GAPS"
            fix = "BACKFILL MISSING FORM FACTORS: " + ", ".join(missing[:4])
        else:
            grade = "THIN"
            impact = "FORM_FACTOR_GAPS_LIMIT_PRICE_CONFIDENCE"
            fix = "REPAIR FORM RUN FACTOR COVERAGE: " + ", ".join(missing[:4])

        records.append({
            "race_id": first_existing(row, ["race_id", "race_key"]) or race_match_key,
            "race_date": first_existing(row, ["race_date", "date"]),
            "track": first_existing(row, ["track"]),
            "race_no": first_existing(row, ["race_no", "race_number"]),
            "horse": first_existing(row, ["horse", "runner", "runner_name"]),
            "matched_to_form_card_summary": bool_text(not summaries.empty),
            "matched_to_form_card_runs": bool_text(not runs.empty),
            "official_race_run_count": str(official_count),
            "trial_run_count": str(trial_count),
            "jumpout_run_count": str(jumpout_count),
            "last_official_run_date": last_run.date().isoformat() if last_run else "",
            "days_since_last_official_run": str(days_since),
            "has_last3_rating": bool_text(has_last3),
            "has_last5_rating": bool_text(has_last5),
            "has_peak_rating": bool_text(has_peak),
            "has_distance_history": bool_text(has_distance),
            "has_track_condition_history": bool_text(has_condition),
            "has_class_history": bool_text(has_class),
            "has_margin_history": bool_text(has_margin),
            "has_sp_history": bool_text(has_sp),
            "has_jockey_history": bool_text(has_jockey),
            "has_trainer_history": bool_text(has_trainer),
            "has_barrier_history": bool_text(has_barrier),
            "has_in_run_position_history": bool_text(has_in_run),
            "has_sectional_data": bool_text(has_sectional),
            "has_last600": bool_text(has_last600),
            "has_last400": bool_text(has_last400),
            "has_last200": bool_text(has_last200),
            "has_speed_figure": bool_text(has_speed),
            "has_run_context_flags": bool_text(has_context),
            "official_form_depth_score": str(score),
            "official_form_depth_grade": grade,
            "missing_form_factors": ", ".join(missing),
            "pricing_impact": impact,
            "recommended_data_fix": fix,
        })
    return pd.DataFrame(records, columns=DEPTH_COLUMNS)


def build_gaps(depth: pd.DataFrame) -> pd.DataFrame:
    total = len(depth)
    official_counts = pd.to_numeric(depth.get("official_race_run_count", pd.Series(dtype=str)), errors="coerce").fillna(0)
    official_missing = int((official_counts <= 0).sum())
    rows = [{
        "factor": "official_race_runs",
        "missing_count": str(official_missing),
        "missing_pct": pct(official_missing, total),
        "pricing_impact": "NO_OFFICIAL_FORM_BLOCKS_SHARP_PRICING",
        "recommended_data_fix": "BUILD OFFICIAL FORM DEPTH",
    }]
    factor_names = [
        ("last3_rating", "has_last3_rating"),
        ("last5_rating", "has_last5_rating"),
        ("peak_rating", "has_peak_rating"),
        ("distance_history", "has_distance_history"),
        ("track_condition_history", "has_track_condition_history"),
        ("class_history", "has_class_history"),
        ("margin_history", "has_margin_history"),
        ("sp_history", "has_sp_history"),
        ("jockey_history", "has_jockey_history"),
        ("trainer_history", "has_trainer_history"),
        ("barrier_history", "has_barrier_history"),
        ("in_run_position_history", "has_in_run_position_history"),
        ("sectional_data", "has_sectional_data"),
        ("last600", "has_last600"),
        ("last400", "has_last400"),
        ("last200", "has_last200"),
        ("speed_figure", "has_speed_figure"),
        ("run_context_flags", "has_run_context_flags"),
    ]
    for factor, column in factor_names:
        missing_count = int((depth[column] != "TRUE").sum()) if total else 0
        if factor == "sectional_data":
            impact = "SECTIONALS_NOT_AVAILABLE; DO_NOT_INVENT"
            fix = "SOURCE OFFICIAL SECTIONALS ONLY IF AVAILABLE"
        elif factor in {"last3_rating", "last5_rating", "peak_rating", "speed_figure"}:
            impact = "RATING_DEPTH_LIMITS_FAIR_PRICE_REALISM"
            fix = "REPAIR FORM RATINGS FROM OFFICIAL RUN HISTORY"
        elif factor in {"distance_history", "class_history", "track_condition_history"}:
            impact = "CONTEXT_SUITABILITY_LIMITS_PRICING"
            fix = "BACKFILL RUN CONTEXT FACTORS"
        else:
            impact = "FEATURE_GAP_LIMITS_CONFIDENCE"
            fix = "BACKFILL FORM RUN FACTOR"
        rows.append({
            "factor": factor,
            "missing_count": str(missing_count),
            "missing_pct": pct(missing_count, total),
            "pricing_impact": impact,
            "recommended_data_fix": fix,
        })
    out = pd.DataFrame(rows, columns=GAP_COLUMNS)
    out["_missing_n"] = pd.to_numeric(out["missing_count"], errors="coerce").fillna(0)
    out["_priority"] = out["factor"].map(lambda value: 0 if value == "official_race_runs" else 1)
    out = out.sort_values(["_missing_n", "_priority", "factor"], ascending=[False, True, True])
    return out.drop(columns=["_missing_n", "_priority"])


def build_summary(depth: pd.DataFrame, gaps: pd.DataFrame) -> pd.DataFrame:
    total = len(depth)
    official_counts = pd.to_numeric(depth.get("official_race_run_count", pd.Series(dtype=str)), errors="coerce").fillna(0)
    grade_counts = depth.get("official_form_depth_grade", pd.Series(dtype=str)).value_counts().to_dict()
    biggest = gaps.iloc[0]["factor"] if not gaps.empty else "NONE"
    top_fix = "BUILD OFFICIAL FORM DEPTH" if int((official_counts <= 0).sum()) else (gaps.iloc[0]["recommended_data_fix"] if not gaps.empty else "DATA COVERAGE ACCEPTABLE")
    row = {
        "total_runners": str(total),
        "official_form_coverage_pct": pct(int((official_counts > 0).sum()), total),
        "average_official_run_count": f"{official_counts.mean():.2f}" if total else "0.00",
        "no_official_form_count": str(int((official_counts <= 0).sum())),
        "thin_official_form_count": str(grade_counts.get("THIN", 0)),
        "elite_form_depth_count": str(grade_counts.get("ELITE", 0)),
        "sectional_data_coverage_pct": pct(int((depth.get("has_sectional_data", pd.Series(dtype=str)) == "TRUE").sum()), total),
        "class_history_coverage_pct": pct(int((depth.get("has_class_history", pd.Series(dtype=str)) == "TRUE").sum()), total),
        "distance_history_coverage_pct": pct(int((depth.get("has_distance_history", pd.Series(dtype=str)) == "TRUE").sum()), total),
        "condition_history_coverage_pct": pct(int((depth.get("has_track_condition_history", pd.Series(dtype=str)) == "TRUE").sum()), total),
        "biggest_missing_factor": biggest,
        "top_recommended_data_fix": top_fix,
    }
    return pd.DataFrame([row], columns=SUMMARY_COLUMNS)


def patch_board(path: Path, depth: pd.DataFrame) -> None:
    board = read_csv(path)
    if board.empty or depth.empty:
        return
    keyed = key_frame(board)
    patch = key_frame(depth)
    cols = [
        "_race_match_key",
        "_horse_key",
        "official_race_run_count",
        "official_form_depth_score",
        "official_form_depth_grade",
        "missing_form_factors",
        "pricing_impact",
        "recommended_data_fix",
    ]
    merged = keyed.merge(patch[cols], on=["_race_match_key", "_horse_key"], how="left", suffixes=("", "_official_form"))
    for col in cols[2:]:
        patch_col = f"{col}_official_form"
        if patch_col in merged.columns:
            merged[col] = merged[patch_col].where(merged[patch_col].astype(str).str.strip().ne(""), merged.get(col, ""))
            merged = merged.drop(columns=[patch_col])
    merged = merged.drop(columns=[c for c in ["_horse_key", "_track_key", "_race_no_key", "_date_key", "_race_id_key", "_race_match_key"] if c in merged.columns])
    merged.to_csv(path, index=False)
    log(f"patched {path.name}: {len(merged)} rows")


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    read_csv(RACE_FIELDS)
    live = key_frame(read_csv(LIVE_BOARD))
    form_summary = key_frame(read_csv(FORM_SUMMARY))
    official_master = read_csv(OFFICIAL_RUNS_MASTER)
    if not official_master.empty:
        form_runs = key_frame(official_master)
        log("using edgeiq_official_runs_master_v1.csv for official form depth")
    else:
        form_runs = key_frame(read_csv(FORM_RUNS))
    sectionals = key_frame(read_csv(SECTIONAL_MASTER))
    read_csv(DATA_QUALITY)

    depth = build_runner_audit(live, form_summary, form_runs, sectionals) if not live.empty else pd.DataFrame(columns=DEPTH_COLUMNS)
    gaps = build_gaps(depth) if not depth.empty else pd.DataFrame(columns=GAP_COLUMNS)
    summary = build_summary(depth, gaps)

    depth.to_csv(DEPTH_OUT, index=False)
    gaps.to_csv(GAPS_OUT, index=False)
    summary.to_csv(SUMMARY_OUT, index=False)
    patch_board(LIVE_BOARD, depth)
    patch_board(TERMINAL_BOARD, depth)

    s = summary.iloc[0]
    log(f"rows processed: {len(depth)}")
    log(f"official form coverage: {s['official_form_coverage_pct']}%")
    log(f"average official run count: {s['average_official_run_count']}")
    log(f"biggest missing factor: {s['biggest_missing_factor']}")
    log(f"top recommended data fix: {s['top_recommended_data_fix']}")
    log(f"wrote {DEPTH_OUT.relative_to(ROOT)}")
    log(f"wrote {GAPS_OUT.relative_to(ROOT)}")
    log(f"wrote {SUMMARY_OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
