from pathlib import Path
import re
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RACE_FIELDS = DATA / "race_fields.csv"
FORM_SUMMARY = DATA / "form_card_summary.csv"
FORM_RUNS = DATA / "form_card_runs.csv"
OFFICIAL_RUNS_MASTER = DATA / "edgeiq_official_runs_master_v1.csv"
LIVE_BOARD = DATA / "edgeiq_execution_board_live.csv"
TERMINAL_BOARD = DATA / "edgeiq_execution_board_terminal.csv"
RESULTS_MASTER = DATA / "edgeiq_results_master.csv"
RACE_RESULTS = DATA / "race_results.csv"
SPORTSBET_LIVE = DATA / "sportsbet_live_market_v1.csv"
TRAINER_JOCKEY = DATA / "edgeiq_trainer_jockey_intelligence_v1.csv"
FORM_DEPTH = DATA / "edgeiq_form_depth_ability_v2.csv"
MARKET_CONFIRMATION = DATA / "edgeiq_market_confirmation_v2.csv"

SUMMARY_OUT = DATA / "edgeiq_data_feature_quality_v1.csv"
RUNNER_OUT = DATA / "edgeiq_data_quality_by_runner_v1.csv"
ACTIONS_OUT = DATA / "edgeiq_data_quality_actions_v1.csv"

RUNNER_COLUMNS = [
    "race_id",
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key_present",
    "matched_to_race_fields",
    "matched_to_form_summary",
    "matched_to_form_runs",
    "official_run_count",
    "trainer_present",
    "jockey_present",
    "barrier_present",
    "weight_present",
    "race_class_present",
    "distance_present",
    "track_condition_present",
    "market_price_present",
    "live_price_present",
    "result_linkage_available",
    "trainer_jockey_coverage",
    "form_depth_coverage",
    "market_confirmation_coverage",
    "data_quality_score",
    "data_quality_grade",
    "missing_critical_fields",
    "missing_feature_fields",
    "recommended_fix",
]

SUMMARY_COLUMNS = [
    "total_runners",
    "elite_count",
    "good_count",
    "thin_count",
    "poor_count",
    "broken_count",
    "overall_grade",
    "average_data_quality_score",
    "official_form_coverage_pct",
    "trainer_coverage_pct",
    "jockey_coverage_pct",
    "market_price_coverage_pct",
    "result_linkage_coverage_pct",
    "biggest_missing_field",
    "biggest_pricing_blocker",
    "highest_priority_fix",
]

ACTION_COLUMNS = [
    "action_scope",
    "metric",
    "value",
    "severity",
    "recommended_fix",
    "reason",
]


def log(message: str) -> None:
    print(f"[data_feature_quality_v1] {message}")


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
    text = upper(value)
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"[^A-Z0-9]+", "", text)
    return text


def truth(value) -> bool:
    return upper(value) in {"TRUE", "YES", "1", "Y"}


def has_value(value) -> bool:
    text = clean(value)
    if not text:
        return False
    return text.upper() not in {"NAN", "NONE", "NULL", "UNKNOWN", "N/A", "-"}


def number(value):
    try:
        text = clean(value).replace("$", "").replace("%", "")
        if not text:
            return None
        parsed = float(text)
        return parsed if pd.notna(parsed) else None
    except Exception:
        return None


def bool_text(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def pct(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0.00"
    return f"{(numerator / denominator) * 100:.2f}"


def first_existing(row: pd.Series, names: list[str]) -> str:
    for name in names:
        if name in row.index and has_value(row.get(name, "")):
            return clean(row.get(name, ""))
    return ""


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

    if horse_key_col:
        out["_horse_key"] = out[horse_key_col].map(norm)
    elif horse_col:
        out["_horse_key"] = out[horse_col].map(norm)
    else:
        out["_horse_key"] = ""

    out["_track_key"] = out[track_col].map(norm) if track_col else ""
    out["_race_no_key"] = out[race_col].astype(str).str.extract(r"(\d+)", expand=False).fillna("") if race_col else ""
    out["_date_key"] = out[date_col].astype(str).str.slice(0, 10) if date_col else ""
    out["_race_id_key"] = out[race_id_col].astype(str).str.strip() if race_id_col else ""
    out["_race_match_key"] = out["_race_id_key"].where(
        out["_race_id_key"].ne(""),
        out["_date_key"] + "|" + out["_track_key"] + "|R" + out["_race_no_key"],
    )
    return out


def make_index(df: pd.DataFrame) -> set[tuple[str, str]]:
    if df.empty:
        return set()
    keyed = key_frame(df)
    return set(zip(keyed["_race_match_key"], keyed["_horse_key"]))


def make_horse_index(df: pd.DataFrame) -> set[str]:
    if df.empty:
        return set()
    keyed = key_frame(df)
    return set(keyed["_horse_key"])


def make_official_run_counts(df: pd.DataFrame) -> dict[str, int]:
    if df.empty:
        return {}
    keyed = key_frame(df)
    if "official_run_flag" in keyed.columns:
        official = keyed[keyed["official_run_flag"].map(truth)]
    elif "is_official_race" in keyed.columns:
        official = keyed[keyed["is_official_race"].map(truth)]
    else:
        text_cols = [c for c in ["run_type", "race_class", "class_name", "race_name"] if c in keyed.columns]
        if not text_cols:
            official = keyed
        else:
            joined = keyed[text_cols].astype(str).agg(" ".join, axis=1).str.upper()
            official = keyed[~joined.str.contains("TRIAL|JUMPOUT|JUMP OUT", regex=True)]
    if official.empty or "_horse_key" not in official.columns:
        return {}
    return official["_horse_key"].value_counts().astype(int).to_dict()


def count_missing_fields(rows: pd.DataFrame, field: str) -> int:
    if rows.empty or field not in rows.columns:
        return 0
    return int(rows[field].astype(str).str.contains(field, regex=False).sum())


def determine_grade(
    score: int,
    critical_missing: list[str],
    has_form_summary: bool,
    has_tj: bool,
    official_runs: int,
    has_market_confirmation: bool,
) -> str:
    if critical_missing:
        return "BROKEN"
    if not has_form_summary and not has_tj and official_runs <= 0 and not has_market_confirmation:
        return "POOR"
    if score >= 90 and official_runs >= 5:
        return "ELITE"
    if score >= 72:
        return "GOOD"
    if score >= 48:
        return "THIN"
    return "POOR"


def recommended_fix(critical: list[str], features: list[str], official_runs: int) -> str:
    if critical:
        return f"FIX CRITICAL LINKAGE: {', '.join(critical[:3])}"
    if official_runs <= 0:
        return "IMPROVE OFFICIAL FORM / FIRST-STARTER COVERAGE"
    if "form_summary" in features or "form_runs" in features:
        return "REPAIR FORM CARD MATCHING"
    if "trainer_jockey" in features:
        return "BACKFILL TRAINER/JOCKEY HISTORY"
    if "market_confirmation" in features:
        return "WAIT FOR MARKET CONFIRMATION"
    if features:
        return f"FILL FEATURE COVERAGE: {', '.join(features[:3])}"
    return "DATA COVERAGE ACCEPTABLE"


def score_runner(row: pd.Series, indexes: dict[str, set]) -> dict[str, str]:
    race_id = first_existing(row, ["race_id", "race_key"]) or row.get("_race_match_key", "")
    horse = first_existing(row, ["horse", "runner", "runner_name", "selection"])
    horse_key = first_existing(row, ["horse_key"]) or row.get("_horse_key", "")
    match_key = row.get("_race_match_key", "")
    horse_lookup = row.get("_horse_key", "")

    runner_pair = (match_key, horse_lookup)
    horse_key_present = has_value(horse_key) or has_value(horse_lookup)
    matched_to_race_fields = runner_pair in indexes["race_fields"] or horse_lookup in indexes["race_fields_horse"]
    matched_to_form_summary = runner_pair in indexes["form_summary"] or horse_lookup in indexes["form_summary_horse"]
    matched_to_form_runs = horse_lookup in indexes["form_runs_horse"]
    result_linkage_available = (
        runner_pair in indexes["results_master"]
        or runner_pair in indexes["race_results"]
        or horse_lookup in indexes["race_results_horse"]
    )
    trainer_jockey_coverage = runner_pair in indexes["trainer_jockey"] or horse_lookup in indexes["trainer_jockey_horse"]
    form_depth_coverage = runner_pair in indexes["form_depth"] or horse_lookup in indexes["form_depth_horse"]
    market_confirmation_coverage = runner_pair in indexes["market_confirmation"] or horse_lookup in indexes["market_confirmation_horse"]

    official_runs = number(first_existing(row, ["official_run_count", "official_run_count_v5", "summary_official_run_count", "total_form_runs"]))
    official_runs_int = int(official_runs) if official_runs is not None else 0
    if official_runs_int <= 0:
        official_runs_int = int(indexes.get("official_run_counts", {}).get(horse_lookup, 0))
    trainer_present = has_value(first_existing(row, ["trainer", "trainer_rated"]))
    jockey_present = has_value(first_existing(row, ["jockey", "jockey_rated"]))
    barrier_present = has_value(first_existing(row, ["barrier", "barrier_rated"]))
    weight_present = has_value(first_existing(row, ["weight", "weight_carried", "probable_weight"]))
    race_class_present = has_value(first_existing(row, ["race_class", "race_class_clean", "race_class_band"]))
    distance_present = has_value(first_existing(row, ["distance"]))
    track_condition_present = has_value(first_existing(row, ["track_condition"]))
    market_price_present = number(first_existing(row, ["market_price", "sportsbet_price", "fixed_win", "win_odds"])) is not None
    live_price_present = runner_pair in indexes["sportsbet_live"] or number(first_existing(row, ["sportsbet_price"])) is not None

    critical = []
    if not horse_key_present or not horse:
        critical.append("runner_identity")
    if not matched_to_race_fields and not race_id:
        critical.append("race_linkage")
    if not market_price_present:
        critical.append("market_price")

    features = []
    checks = {
        "form_summary": matched_to_form_summary,
        "form_runs": matched_to_form_runs,
        "official_form": official_runs_int > 0,
        "trainer": trainer_present,
        "jockey": jockey_present,
        "barrier": barrier_present,
        "weight": weight_present,
        "race_class": race_class_present,
        "distance": distance_present,
        "track_condition": track_condition_present,
        "result_linkage": result_linkage_available,
        "trainer_jockey": trainer_jockey_coverage,
        "form_depth": form_depth_coverage,
        "market_confirmation": market_confirmation_coverage,
    }
    for name, ok in checks.items():
        if not ok:
            features.append(name)

    score = 0
    score += 12 if horse_key_present else 0
    score += 12 if matched_to_race_fields else 0
    score += 12 if market_price_present else 0
    score += 8 if live_price_present else 0
    score += 8 if matched_to_form_summary else 0
    score += 8 if matched_to_form_runs else 0
    score += 6 if official_runs_int > 0 else 0
    score += 5 if trainer_present else 0
    score += 5 if jockey_present else 0
    score += 3 if barrier_present else 0
    score += 3 if weight_present else 0
    score += 3 if race_class_present else 0
    score += 3 if distance_present else 0
    score += 2 if track_condition_present else 0
    score += 5 if result_linkage_available else 0
    score += 3 if trainer_jockey_coverage else 0
    score += 2 if form_depth_coverage else 0

    grade = determine_grade(
        min(score, 100),
        critical,
        matched_to_form_summary,
        trainer_jockey_coverage,
        official_runs_int,
        market_confirmation_coverage,
    )

    return {
        "race_id": race_id,
        "race_date": first_existing(row, ["race_date", "date"]),
        "track": first_existing(row, ["track"]),
        "race_no": first_existing(row, ["race_no", "race_number"]),
        "horse": horse,
        "horse_key_present": bool_text(horse_key_present),
        "matched_to_race_fields": bool_text(matched_to_race_fields),
        "matched_to_form_summary": bool_text(matched_to_form_summary),
        "matched_to_form_runs": bool_text(matched_to_form_runs),
        "official_run_count": str(official_runs_int),
        "trainer_present": bool_text(trainer_present),
        "jockey_present": bool_text(jockey_present),
        "barrier_present": bool_text(barrier_present),
        "weight_present": bool_text(weight_present),
        "race_class_present": bool_text(race_class_present),
        "distance_present": bool_text(distance_present),
        "track_condition_present": bool_text(track_condition_present),
        "market_price_present": bool_text(market_price_present),
        "live_price_present": bool_text(live_price_present),
        "result_linkage_available": bool_text(result_linkage_available),
        "trainer_jockey_coverage": bool_text(trainer_jockey_coverage),
        "form_depth_coverage": bool_text(form_depth_coverage),
        "market_confirmation_coverage": bool_text(market_confirmation_coverage),
        "data_quality_score": str(min(score, 100)),
        "data_quality_grade": grade,
        "missing_critical_fields": ", ".join(critical),
        "missing_feature_fields": ", ".join(features),
        "recommended_fix": recommended_fix(critical, features, official_runs_int),
    }


def biggest_missing_field(runners: pd.DataFrame) -> str:
    fields = []
    for value in runners.get("missing_critical_fields", pd.Series(dtype=str)).tolist():
        fields.extend([item.strip() for item in str(value).split(",") if item.strip()])
    for value in runners.get("missing_feature_fields", pd.Series(dtype=str)).tolist():
        fields.extend([item.strip() for item in str(value).split(",") if item.strip()])
    if not fields:
        return "NONE"
    return pd.Series(fields).value_counts().idxmax()


def pricing_blocker(runners: pd.DataFrame) -> str:
    if runners.empty:
        return "NO LIVE RUNNERS"
    missing = biggest_missing_field(runners)
    grade_counts = runners["data_quality_grade"].value_counts().to_dict()
    if grade_counts.get("BROKEN", 0):
        return f"BROKEN RUNNER LINKAGE: {missing}"
    if int((runners["official_run_count"].astype(str).replace("", "0").astype(float) <= 0).sum()) > 0:
        return "NO OFFICIAL FORM / FIRST-STARTER COVERAGE"
    if missing != "NONE":
        return f"MISSING {missing.upper()}"
    return "NO MAJOR DATA BLOCKER"


def build_summary(runners: pd.DataFrame) -> pd.DataFrame:
    total = len(runners)
    counts = runners["data_quality_grade"].value_counts().to_dict() if total else {}
    avg = pd.to_numeric(runners.get("data_quality_score", pd.Series(dtype=str)), errors="coerce").fillna(0).mean() if total else 0
    biggest = biggest_missing_field(runners)
    blocker = pricing_blocker(runners)
    overall = "BROKEN" if counts.get("BROKEN", 0) else "POOR" if counts.get("POOR", 0) else "THIN" if counts.get("THIN", 0) else "GOOD"
    if counts.get("ELITE", 0) == total and total:
        overall = "ELITE"
    row = {
        "total_runners": str(total),
        "elite_count": str(counts.get("ELITE", 0)),
        "good_count": str(counts.get("GOOD", 0)),
        "thin_count": str(counts.get("THIN", 0)),
        "poor_count": str(counts.get("POOR", 0)),
        "broken_count": str(counts.get("BROKEN", 0)),
        "overall_grade": overall,
        "average_data_quality_score": f"{avg:.2f}",
        "official_form_coverage_pct": pct(int((pd.to_numeric(runners.get("official_run_count", pd.Series(dtype=str)), errors="coerce").fillna(0) > 0).sum()), total),
        "trainer_coverage_pct": pct(int((runners.get("trainer_present", pd.Series(dtype=str)) == "TRUE").sum()), total),
        "jockey_coverage_pct": pct(int((runners.get("jockey_present", pd.Series(dtype=str)) == "TRUE").sum()), total),
        "market_price_coverage_pct": pct(int((runners.get("market_price_present", pd.Series(dtype=str)) == "TRUE").sum()), total),
        "result_linkage_coverage_pct": pct(int((runners.get("result_linkage_available", pd.Series(dtype=str)) == "TRUE").sum()), total),
        "biggest_missing_field": biggest,
        "biggest_pricing_blocker": blocker,
        "highest_priority_fix": "REPAIR CRITICAL LINKAGE" if counts.get("BROKEN", 0) else ("BUILD OFFICIAL FORM DEPTH" if "OFFICIAL FORM" in blocker else "IMPROVE FEATURE COVERAGE"),
    }
    return pd.DataFrame([row], columns=SUMMARY_COLUMNS)


def build_actions(summary: pd.DataFrame, runners: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame(columns=ACTION_COLUMNS)
    s = summary.iloc[0]
    rows = [
        {
            "action_scope": "GLOBAL",
            "metric": "OVERALL_GRADE",
            "value": s["overall_grade"],
            "severity": "HIGH" if s["overall_grade"] in {"BROKEN", "POOR"} else "MEDIUM" if s["overall_grade"] == "THIN" else "LOW",
            "recommended_fix": s["highest_priority_fix"],
            "reason": s["biggest_pricing_blocker"],
        },
        {
            "action_scope": "GLOBAL",
            "metric": "BIGGEST_MISSING_FIELD",
            "value": s["biggest_missing_field"],
            "severity": "HIGH" if s["biggest_missing_field"] in {"runner_identity", "race_linkage", "market_price"} else "MEDIUM",
            "recommended_fix": s["highest_priority_fix"],
            "reason": "Most common missing data/feature field across current live runners.",
        },
        {
            "action_scope": "GLOBAL",
            "metric": "OFFICIAL_FORM_COVERAGE_PCT",
            "value": s["official_form_coverage_pct"],
            "severity": "HIGH" if float(s["official_form_coverage_pct"]) < 50 else "LOW",
            "recommended_fix": "BUILD OFFICIAL FORM DEPTH",
            "reason": "Official exposed-race sample is a core input for pricing realism.",
        },
    ]
    for _, row in runners.sort_values(["data_quality_grade", "data_quality_score"]).head(3).iterrows():
        rows.append({
            "action_scope": f"RUNNER:{row['horse']}",
            "metric": "RUNNER_QUALITY",
            "value": row["data_quality_grade"],
            "severity": "HIGH" if row["data_quality_grade"] in {"BROKEN", "POOR"} else "MEDIUM",
            "recommended_fix": row["recommended_fix"],
            "reason": row["missing_critical_fields"] or row["missing_feature_fields"] or "Runner data coverage acceptable.",
        })
    return pd.DataFrame(rows, columns=ACTION_COLUMNS)


def patch_board(path: Path, runners: pd.DataFrame) -> None:
    board = read_csv(path)
    if board.empty or runners.empty:
        return
    keyed = key_frame(board)
    patch = key_frame(runners)
    cols = ["_race_match_key", "_horse_key", "data_quality_score", "data_quality_grade", "missing_critical_fields", "missing_feature_fields", "recommended_fix"]
    merged = keyed.merge(patch[cols], on=["_race_match_key", "_horse_key"], how="left", suffixes=("", "_quality"))
    for col in ["data_quality_score", "data_quality_grade", "missing_critical_fields", "missing_feature_fields", "recommended_fix"]:
        qcol = f"{col}_quality"
        if qcol in merged.columns:
            merged[col] = merged[qcol].where(merged[qcol].astype(str).str.strip().ne(""), merged.get(col, ""))
            merged = merged.drop(columns=[qcol])
    merged = merged.drop(columns=[c for c in ["_horse_key", "_track_key", "_race_no_key", "_date_key", "_race_id_key", "_race_match_key"] if c in merged.columns])
    merged.to_csv(path, index=False)
    log(f"patched {path.name}: {len(merged)} rows")


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    live = key_frame(read_csv(LIVE_BOARD))
    form_runs = read_csv(OFFICIAL_RUNS_MASTER)
    if not form_runs.empty:
        log("using edgeiq_official_runs_master_v1.csv for form-run coverage")
    else:
        form_runs = read_csv(FORM_RUNS)
    sources = {
        "race_fields": make_index(read_csv(RACE_FIELDS)),
        "race_fields_horse": make_horse_index(read_csv(RACE_FIELDS)),
        "form_summary": make_index(read_csv(FORM_SUMMARY)),
        "form_summary_horse": make_horse_index(read_csv(FORM_SUMMARY)),
        "form_runs_horse": make_horse_index(form_runs),
        "official_run_counts": make_official_run_counts(form_runs),
        "results_master": make_index(read_csv(RESULTS_MASTER)),
        "race_results": make_index(read_csv(RACE_RESULTS)),
        "race_results_horse": make_horse_index(read_csv(RACE_RESULTS)),
        "sportsbet_live": make_index(read_csv(SPORTSBET_LIVE)),
        "trainer_jockey": make_index(read_csv(TRAINER_JOCKEY)),
        "trainer_jockey_horse": make_horse_index(read_csv(TRAINER_JOCKEY)),
        "form_depth": make_index(read_csv(FORM_DEPTH)),
        "form_depth_horse": make_horse_index(read_csv(FORM_DEPTH)),
        "market_confirmation": make_index(read_csv(MARKET_CONFIRMATION)),
        "market_confirmation_horse": make_horse_index(read_csv(MARKET_CONFIRMATION)),
    }

    rows = [score_runner(row, sources) for _, row in live.iterrows()] if not live.empty else []
    runners = pd.DataFrame(rows, columns=RUNNER_COLUMNS)
    summary = build_summary(runners)
    actions = build_actions(summary, runners)

    runners.to_csv(RUNNER_OUT, index=False)
    summary.to_csv(SUMMARY_OUT, index=False)
    actions.to_csv(ACTIONS_OUT, index=False)
    patch_board(LIVE_BOARD, runners)
    patch_board(TERMINAL_BOARD, runners)

    distribution = runners["data_quality_grade"].value_counts().to_dict() if not runners.empty else {}
    blocker = summary.iloc[0]["biggest_pricing_blocker"] if not summary.empty else "NO LIVE RUNNERS"
    fix = summary.iloc[0]["highest_priority_fix"] if not summary.empty else "NO ACTION"
    log(f"rows processed: {len(runners)}")
    log(f"quality distribution: {distribution}")
    log(f"biggest pricing blocker: {blocker}")
    log(f"highest priority fix: {fix}")
    log(f"wrote {SUMMARY_OUT.relative_to(ROOT)}")
    log(f"wrote {RUNNER_OUT.relative_to(ROOT)}")
    log(f"wrote {ACTIONS_OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
