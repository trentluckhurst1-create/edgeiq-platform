from pathlib import Path
import re
import sys

import pandas as pd


APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA = APP_ROOT / "public" / "data"

SOURCES = [
    (PROJECT_ROOT / "outputs" / "ra_careers" / "ra_horse_runs.csv", "ra_horse_runs.csv", 1),
    (PROJECT_ROOT / "outputs" / "enrichment" / "run_context_FIXED.csv", "run_context_FIXED.csv", 2),
    (PROJECT_ROOT / "outputs" / "enrichment" / "run_context.csv", "run_context.csv", 3),
    (DATA / "form_card_runs.csv", "form_card_runs.csv", 4),
    (DATA / "race_results.csv", "race_results.csv", 5),
]

OPTIONAL_CONTEXT = [
    PROJECT_ROOT / "stewards_history_flags.csv",
    PROJECT_ROOT / "stewards_all_states.csv",
    PROJECT_ROOT / "gear_changes.csv",
]

FORM_SUMMARY = DATA / "form_card_summary.csv"
RACE_FIELDS = DATA / "race_fields.csv"
LIVE_BOARD = DATA / "edgeiq_execution_board_live.csv"

MASTER_OUT = DATA / "edgeiq_official_runs_master_v1.csv"
DIAG_OUT = DATA / "edgeiq_official_runs_master_diagnostics_v1.csv"

MASTER_COLUMNS = [
    "horse_key",
    "horse",
    "race_date",
    "track",
    "state",
    "race_no",
    "distance",
    "race_class",
    "track_condition",
    "barrier",
    "weight",
    "jockey",
    "trainer",
    "settle_position",
    "in_run_positions",
    "finish_pos",
    "margin",
    "sp",
    "official_run_flag",
    "trial_flag",
    "jumpout_flag",
    "stewards_flags",
    "gear_changes",
    "source_file",
    "data_quality_grade",
    "missing_fields",
]

DIAG_COLUMNS = [
    "total_rows",
    "official_rows",
    "trial_rows",
    "jumpout_rows",
    "unique_horses",
    "date_range",
    "rows_with_jockey",
    "rows_with_trainer",
    "rows_with_class",
    "rows_with_condition",
    "rows_with_sp",
    "rows_with_margin",
    "biggest_missing_field",
    "official_form_coverage_against_current_live_runners",
]


def log(message: str) -> None:
    print(f"[official_runs_master_v1] {message}")


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        log(f"missing: {path}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", on_bad_lines="skip").fillna("")
        log(f"read {path}: {len(df)} rows")
        return df
    except Exception as exc:
        log(f"warning: failed to read {path}: {exc}")
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


def first(row: pd.Series, names: list[str]) -> str:
    for name in names:
        if name in row.index and has_value(row.get(name, "")):
            return clean(row.get(name, ""))
    return ""


def true_flag(value) -> bool:
    return upper(value) in {"TRUE", "YES", "1", "Y"}


def is_trial(row: pd.Series) -> bool:
    text = " ".join(upper(row.get(c, "")) for c in ["run_type", "race_class", "class_name", "race_name", "raw_text"])
    return "TRIAL" in text


def is_jumpout(row: pd.Series) -> bool:
    text = " ".join(upper(row.get(c, "")) for c in ["run_type", "race_class", "class_name", "race_name", "raw_text"])
    return "JUMPOUT" in text or "JUMP OUT" in text


def is_official(row: pd.Series) -> bool:
    if true_flag(row.get("is_official_race", "")):
        return True
    run_type = upper(row.get("run_type", ""))
    if run_type in {"RACE", "OFFICIAL_RACE"}:
        return True
    if is_trial(row) or is_jumpout(row):
        return False
    return has_value(first(row, ["finish_pos", "margin", "sp"])) and has_value(first(row, ["run_date", "race_date", "date"]))


def parse_date(value: str) -> str:
    parsed = pd.to_datetime(clean(value), errors="coerce", dayfirst=False)
    if pd.isna(parsed):
        return ""
    return parsed.date().isoformat()


def extract_settle(row: pd.Series) -> str:
    return first(row, ["settle_position", "pos_800", "position_800", "settle_pos"])


def context_flags(row: pd.Series) -> str:
    flags = []
    for col in ["held_up", "checked", "wide", "slow", "lame", "vet"]:
        if col in row.index and true_flag(row.get(col, "")):
            flags.append(col.upper())
    text = first(row, ["stewards_short", "comment"])
    if text:
        flags.append(text)
    return " | ".join(flags)


def gear_text(row: pd.Series) -> str:
    raw = first(row, ["gear_changes", "gear_raw"])
    pieces = [raw] if raw else []
    for col in ["gear_on", "gear_off", "blinkers_on", "blinkers_off", "visor_on", "visor_off", "tongue_tie_on", "tongue_tie_off", "winkers_on", "winkers_off"]:
        if col in row.index and has_value(row.get(col, "")) and clean(row.get(col, "")) not in {"0", "False", "FALSE"}:
            pieces.append(f"{col}={clean(row.get(col, ''))}")
    return " | ".join(pieces)


def standardise(df: pd.DataFrame, source_file: str, priority: int) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        horse = first(row, ["horse", "runner", "selection"])
        horse_key = first(row, ["horse_key"])
        if not horse_key:
            horse_key = norm(horse)
        race_date = parse_date(first(row, ["run_date", "race_date", "date"]))
        track = first(row, ["track", "venue", "meeting"])
        race_no = first(row, ["race_no", "source_race_no", "race_number"])
        official = is_official(row)
        trial = is_trial(row)
        jumpout = is_jumpout(row)

        output = {
            "horse_key": horse_key,
            "horse": horse,
            "race_date": race_date,
            "track": track,
            "state": first(row, ["state"]),
            "race_no": race_no,
            "distance": first(row, ["distance"]),
            "race_class": first(row, ["race_class_clean", "race_class", "class_name"]),
            "track_condition": first(row, ["track_condition", "condition"]),
            "barrier": first(row, ["barrier"]),
            "weight": first(row, ["weight", "weight_carried"]),
            "jockey": first(row, ["jockey"]),
            "trainer": first(row, ["trainer"]),
            "settle_position": extract_settle(row),
            "in_run_positions": first(row, ["in_run_positions"]),
            "finish_pos": first(row, ["finish_pos", "finish_position"]),
            "margin": first(row, ["margin", "margin_num"]),
            "sp": first(row, ["sp", "starting_price", "sp_text"]),
            "official_run_flag": str(official).upper(),
            "trial_flag": str(trial).upper(),
            "jumpout_flag": str(jumpout).upper(),
            "stewards_flags": context_flags(row),
            "gear_changes": gear_text(row),
            "source_file": source_file,
            "_source_priority": priority,
        }
        missing = [col for col in MASTER_COLUMNS if col not in {"stewards_flags", "gear_changes", "missing_fields"} and not has_value(output.get(col, ""))]
        present_count = len([col for col in MASTER_COLUMNS if col not in {"missing_fields"} and has_value(output.get(col, ""))])
        if not output["horse_key"] or not output["race_date"] or not output["track"]:
            grade = "BROKEN"
        elif present_count >= 20:
            grade = "GOOD"
        elif present_count >= 14:
            grade = "THIN"
        else:
            grade = "POOR"
        output["data_quality_grade"] = grade
        output["missing_fields"] = ", ".join(missing)
        rows.append(output)
    return pd.DataFrame(rows)


def combine_sources() -> pd.DataFrame:
    frames = []
    for path, source_file, priority in SOURCES:
        df = read_csv(path)
        if not df.empty:
            frames.append(standardise(df, source_file, priority))
    if not frames:
        return pd.DataFrame(columns=MASTER_COLUMNS)
    combined = pd.concat(frames, ignore_index=True).fillna("")
    combined["_horse_norm"] = combined["horse_key"].map(norm)
    combined["_track_norm"] = combined["track"].map(norm)
    combined["_race_norm"] = combined["race_no"].astype(str).str.extract(r"(\d+)", expand=False).fillna("")
    combined["_dedupe_key"] = combined["_horse_norm"] + "|" + combined["race_date"] + "|" + combined["_track_norm"] + "|R" + combined["_race_norm"]
    combined = combined.sort_values(["_source_priority", "data_quality_grade"])
    combined = combined.drop_duplicates(subset=["_dedupe_key"], keep="first")
    return combined[MASTER_COLUMNS].sort_values(["horse_key", "race_date", "track"]).reset_index(drop=True)


def live_coverage(master: pd.DataFrame) -> str:
    live = read_csv(LIVE_BOARD)
    if live.empty or master.empty:
        return "0.00"
    live_keys = set()
    for _, row in live.iterrows():
        key = first(row, ["horse_key"]) or norm(first(row, ["horse", "runner"]))
        if key:
            live_keys.add(norm(key))
    official_keys = set(master.loc[master["official_run_flag"].map(upper) == "TRUE", "horse_key"].map(norm))
    matched = len(live_keys.intersection(official_keys))
    return f"{(matched / len(live_keys) * 100):.2f}" if live_keys else "0.00"


def biggest_missing(master: pd.DataFrame) -> str:
    fields = []
    for value in master.get("missing_fields", pd.Series(dtype=str)):
        fields.extend([item.strip() for item in str(value).split(",") if item.strip()])
    if not fields:
        return "NONE"
    return pd.Series(fields).value_counts().idxmax()


def diagnostics(master: pd.DataFrame) -> pd.DataFrame:
    if master.empty:
        row = {col: "0" for col in DIAG_COLUMNS}
        row["date_range"] = ""
        row["biggest_missing_field"] = "NO_OFFICIAL_RUNS_MASTER"
        return pd.DataFrame([row], columns=DIAG_COLUMNS)
    official = master["official_run_flag"].map(upper) == "TRUE"
    trial = master["trial_flag"].map(upper) == "TRUE"
    jumpout = master["jumpout_flag"].map(upper) == "TRUE"
    dates = pd.to_datetime(master["race_date"], errors="coerce")
    date_range = ""
    if dates.notna().any():
        date_range = f"{dates.min().date().isoformat()} to {dates.max().date().isoformat()}"
    row = {
        "total_rows": str(len(master)),
        "official_rows": str(int(official.sum())),
        "trial_rows": str(int(trial.sum())),
        "jumpout_rows": str(int(jumpout.sum())),
        "unique_horses": str(master["horse_key"].map(norm).nunique()),
        "date_range": date_range,
        "rows_with_jockey": str(int(master["jockey"].map(has_value).sum())),
        "rows_with_trainer": str(int(master["trainer"].map(has_value).sum())),
        "rows_with_class": str(int(master["race_class"].map(has_value).sum())),
        "rows_with_condition": str(int(master["track_condition"].map(has_value).sum())),
        "rows_with_sp": str(int(master["sp"].map(has_value).sum())),
        "rows_with_margin": str(int(master["margin"].map(has_value).sum())),
        "biggest_missing_field": biggest_missing(master),
        "official_form_coverage_against_current_live_runners": live_coverage(master),
    }
    return pd.DataFrame([row], columns=DIAG_COLUMNS)


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    read_csv(FORM_SUMMARY)
    read_csv(RACE_FIELDS)
    for path in OPTIONAL_CONTEXT:
        read_csv(path)
    master = combine_sources()
    diag = diagnostics(master)
    master.to_csv(MASTER_OUT, index=False)
    diag.to_csv(DIAG_OUT, index=False)

    row = diag.iloc[0]
    log(f"total rows: {row['total_rows']}")
    log(f"official rows: {row['official_rows']}")
    log(f"unique horses: {row['unique_horses']}")
    log(f"date range: {row['date_range']}")
    log(f"live runner official form coverage: {row['official_form_coverage_against_current_live_runners']}%")
    log(f"biggest missing field: {row['biggest_missing_field']}")
    log(f"wrote {MASTER_OUT.relative_to(APP_ROOT)}")
    log(f"wrote {DIAG_OUT.relative_to(APP_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
