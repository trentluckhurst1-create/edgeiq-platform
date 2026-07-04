import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_PATH = DATA / "edgeiq_live_runner_board_v1.csv"

OUT_PATH = DATA / "edgeiq_campaign_intelligence_engine_v1_1.csv"
SUMMARY_PATH = DATA / "edgeiq_campaign_intelligence_engine_v1_1_summary.csv"
AUDIT_PATH = DATA / "edgeiq_campaign_intelligence_engine_v1_1_audit.csv"

SPELL_DAYS = 56
NOW_UTC = datetime.now(timezone.utc).isoformat()

STAGE_LABELS = {
    1: "FIRST_UP",
    2: "SECOND_UP",
    3: "THIRD_UP",
    4: "FOURTH_UP",
    5: "FIFTH_UP",
    6: "SIXTH_UP_PLUS",
}

SOURCE_PRIORITY = [
    ("edgeiq_historical_run_ratings_master_v1.csv", 1),
    ("edgeiq_historical_performance_rating_v6_1_research.csv", 2),
    ("edgeiq_historical_performance_rating_v6_research.csv", 3),
    ("historical_form_table.csv", 4),
    ("edgeiq_racingcom_results_warehouse_full_v1.csv", 5),
]


def normalize_strict(value):
    if pd.isna(value):
        return ""
    text = str(value).upper().strip()
    text = re.sub(r"[^A-Z0-9]+", "", text)
    return text


def normalize_loose(value):
    if pd.isna(value):
        return ""
    text = str(value).upper().strip()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^A-Z0-9]+", "", text)
    return text


def normalize_track(value):
    if pd.isna(value):
        return ""
    text = str(value).upper().strip()
    text = re.sub(r"[^A-Z0-9]+", "", text)
    return text


def parse_date_series(series):
    return pd.to_datetime(series, errors="coerce").dt.normalize()


def to_text(series):
    return series.fillna("").astype(str).str.strip()


def to_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def first_existing(columns, candidates):
    column_map = {str(column).strip().lower(): str(column) for column in columns}
    for candidate in candidates:
        if candidate.lower() in column_map:
            return column_map[candidate.lower()]
    return None


def existing_columns(columns, candidates):
    column_map = {str(column).strip().lower(): str(column) for column in columns}
    return [column_map[candidate.lower()] for candidate in candidates if candidate.lower() in column_map]


def parse_finish_pos(value):
    if pd.isna(value):
        return math.nan
    if isinstance(value, (int, float)) and not pd.isna(value):
        return float(value)
    match = re.search(r"(\d+)", str(value))
    if not match:
        return math.nan
    return float(match.group(1))


def stage_num_to_label(stage_num):
    if stage_num is None or pd.isna(stage_num):
        return "UNKNOWN"
    return STAGE_LABELS.get(int(stage_num), "UNKNOWN")


def stage_num_from_run_no(run_no):
    if pd.isna(run_no):
        return math.nan
    run_no = int(run_no)
    if run_no <= 0:
        return math.nan
    return min(run_no, 6)


def stage_num_to_window_text(start_stage, end_stage):
    if start_stage is None or end_stage is None:
        return "unknown stage"
    if start_stage == end_stage:
        return stage_num_to_label(start_stage).replace("_", "-").lower()
    return f"{stage_num_to_label(start_stage).replace('_', '-').lower()} to {stage_num_to_label(end_stage).replace('_', '-').lower()}"


def band_from_evidence_status(status):
    if status == "STRONG_PROFILE":
        return "STRONG"
    if status == "DEVELOPING_PROFILE":
        return "DEVELOPING"
    if status in {"LIMITED_HISTORY", "UNRATED_HISTORY"}:
        return "LIMITED"
    return "UNPROVEN"


def risk_band_from_score(score):
    if score is None or pd.isna(score):
        return "UNKNOWN"
    if score <= 33:
        return "LOW"
    if score <= 66:
        return "MODERATE"
    return "HIGH"


def safe_count(counter, key):
    return int(counter.get(key, 0))


def pick_rating_value(frame):
    preferred = [
        "performance_rating_v6_1_research",
        "performance_rating_v6_research",
        "performance_rating",
        "run_rating_final",
        "run_rating",
        "race_rating",
        "rating",
        "projected_rating",
        "latest_rating",
        "peak_rating",
        "last_start_rating",
    ]
    available = existing_columns(frame.columns, preferred)
    if not available:
        return pd.Series([math.nan] * len(frame), index=frame.index)
    numeric_frame = frame[available].apply(to_numeric)
    return numeric_frame.bfill(axis=1).iloc[:, 0]


def choose_first_non_empty(rows, column):
    for value in rows[column]:
        if pd.notna(value):
            if isinstance(value, str):
                if value.strip() != "":
                    return value.strip()
            else:
                return value
    return ""


def choose_first_numeric(rows, column):
    series = rows[column]
    notna = series[series.notna()]
    if notna.empty:
        return math.nan
    return notna.iloc[0]


def serialise_counts(counter):
    if not counter:
        return ""
    return "; ".join(f"{key}={counter[key]}" for key in sorted(counter))


def serialise_stage_map(mapping):
    ordered = []
    for stage in range(1, 7):
        value = mapping.get(stage)
        if value is None or pd.isna(value):
            ordered.append(f"{stage}=--")
        else:
            ordered.append(f"{stage}={float(value):.2f}")
    return "; ".join(ordered)


def serialise_stage_counts(mapping):
    return "; ".join(f"{stage}={int(mapping.get(stage, 0))}" for stage in range(1, 7))


def weighted_segment_average(rated_rows, stages):
    sample = rated_rows[rated_rows["prep_stage_num"].isin(stages)]
    if sample.empty:
        return None
    return float(sample["rating_value"].mean())


def build_peak_window(stage_stats, best_stage, best_avg):
    if stage_stats.empty or best_stage is None or best_avg is None:
        return (None, None)

    threshold = 2.0 if int(stage_stats["sample_count"].sum()) >= 6 else 3.0
    start_stage = int(best_stage)
    end_stage = int(best_stage)

    while start_stage - 1 in stage_stats.index and abs(best_avg - stage_stats.loc[start_stage - 1, "avg_rating"]) <= threshold:
        start_stage -= 1
    while end_stage + 1 in stage_stats.index and abs(best_avg - stage_stats.loc[end_stage + 1, "avg_rating"]) <= threshold:
        end_stage += 1

    return (int(start_stage), int(end_stage))


def classify_campaign_profile(evidence_status, rated_rows, stage_stats, best_stage, best_avg, peak_window_end):
    if evidence_status not in {"STRONG_PROFILE", "DEVELOPING_PROFILE"}:
        return "UNPROVEN_PROFILE"

    early_avg = weighted_segment_average(rated_rows, [1, 2])
    build_avg = weighted_segment_average(rated_rows, [3, 4])
    late_avg = weighted_segment_average(rated_rows, [5, 6])
    late_count = int(rated_rows[rated_rows["prep_stage_num"].isin([5, 6])].shape[0])
    after_peak = rated_rows[rated_rows["prep_stage_num"] > peak_window_end] if peak_window_end is not None else rated_rows.iloc[0:0]
    after_avg = float(after_peak["rating_value"].mean()) if not after_peak.empty else None

    if best_stage is None or best_avg is None:
        return "UNPROVEN_PROFILE"

    if best_stage >= 5 and late_avg is not None and (early_avg is None or late_avg >= early_avg + 2):
        return "DEEP_PREP_HORSE"

    if late_count >= 2 and late_avg is not None and best_avg - late_avg <= 1.5 and peak_window_end is not None and peak_window_end >= 4:
        return "TOUGH_CAMPAIGNER"

    if peak_window_end is not None and peak_window_end <= 2 and early_avg is not None:
        early_dominant = True
        if build_avg is not None and early_avg < build_avg + 2:
            early_dominant = False
        if late_avg is not None and early_avg < late_avg + 3:
            early_dominant = False
        if early_dominant:
            return "FRESH_SPECIALIST"

    if after_avg is not None and after_peak.shape[0] >= 2 and best_avg >= after_avg + 4:
        return "PEAK_AND_DROP"

    if best_stage in {3, 4} and build_avg is not None and (early_avg is None or build_avg >= early_avg + 2):
        return "FITNESS_BUILDER"

    return "MIXED_PROFILE"


def assess_campaign_risk(evidence_status, campaign_profile, current_stage, window_start, window_end):
    if evidence_status not in {"STRONG_PROFILE", "DEVELOPING_PROFILE"}:
        return (None, "UNKNOWN")
    if current_stage is None or window_start is None or window_end is None:
        return (None, "UNKNOWN")

    if window_start <= current_stage <= window_end:
        score = 18
    elif current_stage == window_start - 1 or current_stage == window_end + 1:
        score = 48
    else:
        score = 72

    if current_stage > window_end:
        if campaign_profile in {"FRESH_SPECIALIST", "PEAK_AND_DROP"}:
            score += 14
        elif campaign_profile == "FITNESS_BUILDER":
            score += 8
        elif campaign_profile == "TOUGH_CAMPAIGNER":
            score -= 10
        elif campaign_profile == "DEEP_PREP_HORSE":
            score -= 6
    elif current_stage < window_start:
        if campaign_profile in {"DEEP_PREP_HORSE", "FITNESS_BUILDER"}:
            score += 10
        elif campaign_profile == "FRESH_SPECIALIST":
            score -= 5

    score = max(0, min(100, int(round(score))))
    return (score, risk_band_from_score(score))


def build_campaign_narrative(evidence_status, campaign_profile, current_stage, risk_band, window_start, window_end):
    if evidence_status == "NO_HISTORY":
        return "Limited campaign history available."
    if evidence_status == "UNRATED_HISTORY":
        return "Historical runs exist, but there is not enough rated evidence to profile the preparation pattern."
    if evidence_status == "MISSING_CURRENT_DATE":
        return "Current race date is unavailable, so the horse's preparation stage cannot be assessed."
    if evidence_status == "LIMITED_HISTORY":
        return "Limited campaign history available; the preferred preparation window is not yet reliable."
    if current_stage is None:
        return "Preparation stage could not be resolved from the available dated history."

    window_text = stage_num_to_window_text(window_start, window_end)

    if risk_band == "LOW":
        if campaign_profile == "FRESH_SPECIALIST":
            return "Historically performs best early in preparation; today's stage is inside the preferred window."
        if campaign_profile == "FITNESS_BUILDER":
            return "Historically improves with racing and today's stage aligns with the horse's preferred build phase."
        if campaign_profile == "TOUGH_CAMPAIGNER":
            return "Historically holds ratings deep into a campaign, and today's stage sits inside that durable window."
        if campaign_profile == "DEEP_PREP_HORSE":
            return "Historically performs best deeper into a preparation, and today's stage is inside that preferred range."
        if campaign_profile == "PEAK_AND_DROP":
            return "Historically peaks in a defined preparation window and today's stage is still inside that range."
        return f"Today's stage sits inside the horse's historical peak window ({window_text})."

    if risk_band == "MODERATE":
        if current_stage < (window_start or current_stage):
            return f"Today's stage sits just ahead of the horse's preferred preparation window ({window_text})."
        return f"Today's stage sits just outside the horse's preferred preparation window ({window_text})."

    if risk_band == "HIGH":
        if current_stage > (window_end or current_stage):
            if campaign_profile == "FRESH_SPECIALIST":
                return "Historically performs best early in preparation; today looks beyond the preferred range."
            if campaign_profile == "PEAK_AND_DROP":
                return "Historically peaks and then drops away later in a campaign; today may be beyond the preferred range."
            return f"Historically vulnerable beyond the preferred preparation window ({window_text}); today may be beyond range."
        return f"Today's stage sits well away from the horse's preferred preparation window ({window_text})."

    return "Campaign evidence is available, but the current stage does not yet map cleanly to a risk view."


def prepare_source(path, source_name, source_priority, current_strict_keys, current_loose_keys):
    if not path.exists():
        return pd.DataFrame(
            columns=[
                "source_name",
                "source_priority",
                "horse",
                "horse_key_raw",
                "strict_key",
                "loose_key",
                "run_date_dt",
                "run_date_iso",
                "track",
                "track_norm",
                "race_no",
                "distance",
                "class_name",
                "condition",
                "finish_pos",
                "rating_value",
                "sp",
                "row_richness",
            ]
        )

    print(f"[CAMPAIGN_INTELLIGENCE_V1_1] loading {source_name} ...")
    header = pd.read_csv(path, nrows=0, low_memory=False)
    columns = header.columns

    horse_key_col = first_existing(columns, ["horse_key", "horsekey", "runner_key", "runnerkey", "horseKey"])
    horse_col = first_existing(columns, ["horse", "horse_name", "runner", "runner_name", "horseName"])
    date_col = first_existing(columns, ["run_date_iso", "race_date", "meeting_date", "run_date", "date"])
    track_col = first_existing(columns, ["track", "meeting_name", "venue"])
    race_no_col = first_existing(columns, ["race_no", "race_number"])
    distance_col = first_existing(columns, ["distance", "race_distance"])
    class_col = first_existing(columns, ["class_name", "race_class", "class", "raceClass", "race_class_clean"])
    condition_col = first_existing(columns, ["condition", "track_condition", "going", "trackCondition", "condition_recovered"])
    finish_col = first_existing(columns, ["finish_pos", "finish_position", "finish_num", "position", "finishPosition"])
    sp_col = first_existing(columns, ["sp", "sp_settled", "sp_num_settled", "stab"])

    rating_candidates = [
        "performance_rating_v6_1_research",
        "performance_rating_v6_research",
        "performance_rating",
        "run_rating_final",
        "run_rating",
        "race_rating",
        "rating",
        "projected_rating",
        "latest_rating",
        "peak_rating",
        "last_start_rating",
    ]
    rating_cols = existing_columns(columns, rating_candidates)

    usecols = [column for column in [horse_key_col, horse_col, date_col, track_col, race_no_col, distance_col, class_col, condition_col, finish_col, sp_col, *rating_cols] if column]
    if not usecols or not date_col or (not horse_key_col and not horse_col):
        return pd.DataFrame(
            columns=[
                "source_name",
                "source_priority",
                "horse",
                "horse_key_raw",
                "strict_key",
                "loose_key",
                "run_date_dt",
                "run_date_iso",
                "track",
                "track_norm",
                "race_no",
                "distance",
                "class_name",
                "condition",
                "finish_pos",
                "rating_value",
                "sp",
                "row_richness",
            ]
        )

    frame = pd.read_csv(path, usecols=usecols, low_memory=False)

    out = pd.DataFrame(index=frame.index)
    out["horse"] = to_text(frame[horse_col]) if horse_col else to_text(frame[horse_key_col])
    out["horse_key_raw"] = to_text(frame[horse_key_col]) if horse_key_col else ""
    strict_base = out["horse_key_raw"] if horse_key_col else out["horse"]
    out["strict_key"] = strict_base.map(normalize_strict)
    out.loc[out["strict_key"] == "", "strict_key"] = out["horse"].map(normalize_strict)
    out["loose_key"] = out["horse"].map(normalize_loose)
    out.loc[out["loose_key"] == "", "loose_key"] = strict_base.map(normalize_loose)
    out["run_date_dt"] = parse_date_series(frame[date_col])
    out["run_date_iso"] = out["run_date_dt"].dt.strftime("%Y-%m-%d").fillna("")
    out["track"] = to_text(frame[track_col]) if track_col else ""
    out["track_norm"] = out["track"].map(normalize_track)
    out["race_no"] = to_numeric(frame[race_no_col]) if race_no_col else math.nan
    out["distance"] = to_numeric(frame[distance_col]) if distance_col else math.nan
    out["class_name"] = to_text(frame[class_col]) if class_col else ""
    out["condition"] = to_text(frame[condition_col]) if condition_col else ""
    out["finish_pos"] = frame[finish_col].map(parse_finish_pos) if finish_col else math.nan
    out["rating_value"] = pick_rating_value(frame)
    out["sp"] = to_numeric(frame[sp_col]) if sp_col else math.nan
    out["source_name"] = source_name
    out["source_priority"] = source_priority

    out = out[
        out["run_date_dt"].notna()
        & (
            out["strict_key"].isin(current_strict_keys)
            | out["loose_key"].isin(current_loose_keys)
        )
    ].copy()

    if out.empty:
        return out

    richness = (
        out["track"].astype(str).str.strip().ne("").astype(int)
        + out["distance"].notna().astype(int)
        + out["class_name"].astype(str).str.strip().ne("").astype(int)
        + out["condition"].astype(str).str.strip().ne("").astype(int)
        + out["finish_pos"].notna().astype(int)
        + out["sp"].notna().astype(int)
        + out["rating_value"].notna().astype(int) * 4
    )
    out["row_richness"] = richness
    out = out.sort_values(["run_date_dt", "source_priority", "row_richness"], ascending=[True, True, False]).copy()
    return out


def assign_prep_stages(history):
    if history.empty:
        history = history.copy()
        history["prev_run_date"] = pd.NaT
        history["days_since_prev"] = math.nan
        history["new_prep"] = False
        history["prep_id"] = pd.Series(dtype="Int64")
        history["prep_run_no"] = pd.Series(dtype="Int64")
        history["prep_stage_num"] = pd.Series(dtype="Int64")
        history["prep_stage_label"] = pd.Series(dtype="object")
        return history
    sort_priority_col = "source_priority" if "source_priority" in history.columns else "source_priority_min"
    sort_columns = ["run_date_dt", sort_priority_col, "track", "race_no"]
    available_sort_columns = [column for column in sort_columns if column in history.columns]
    history = history.sort_values(available_sort_columns, na_position="last").copy()
    history["prev_run_date"] = history["run_date_dt"].shift(1)
    history["days_since_prev"] = (history["run_date_dt"] - history["prev_run_date"]).dt.days
    history["new_prep"] = history["days_since_prev"].isna() | (history["days_since_prev"] >= SPELL_DAYS)
    history["prep_id"] = history["new_prep"].cumsum()
    history["prep_run_no"] = history.groupby("prep_id").cumcount() + 1
    history["prep_stage_num"] = history["prep_run_no"].map(stage_num_from_run_no)
    history["prep_stage_label"] = history["prep_stage_num"].map(stage_num_to_label)
    return history


def infer_current_prep_stage(prior_dates, current_date):
    valid_dates = sorted({date for date in prior_dates if pd.notna(date) and date < current_date})
    if not valid_dates:
        return None

    last_date = valid_dates[-1]
    if (current_date - last_date).days >= SPELL_DAYS:
        return 1

    prior_count_in_prep = 1
    anchor = last_date
    for earlier_date in reversed(valid_dates[:-1]):
        if (anchor - earlier_date).days >= SPELL_DAYS:
            break
        prior_count_in_prep += 1
        anchor = earlier_date

    return min(prior_count_in_prep + 1, 6)


def aggregate_candidate_runs(candidate_rows):
    if candidate_rows.empty:
        return pd.DataFrame(
            columns=[
                "run_date_iso",
                "run_date_dt",
                "track",
                "track_norm",
                "race_no",
                "distance",
                "class_name",
                "condition",
                "finish_pos",
                "rating_value",
                "sp",
                "history_source_used",
                "history_source_count_run",
                "strict_match_any",
                "loose_match_any",
                "source_priority_min",
            ]
        )

    rows = []
    for run_date_iso, group in candidate_rows.groupby("run_date_iso", sort=True):
        group = group.sort_values(
            ["source_priority", "rating_value", "row_richness"],
            ascending=[True, False, False],
            na_position="last",
        ).copy()
        sources = []
        for source_name in group["source_name"]:
            if source_name not in sources:
                sources.append(source_name)
        rows.append(
            {
                "run_date_iso": run_date_iso,
                "run_date_dt": group["run_date_dt"].iloc[0],
                "track": choose_first_non_empty(group, "track"),
                "track_norm": choose_first_non_empty(group, "track_norm"),
                "race_no": choose_first_numeric(group, "race_no"),
                "distance": choose_first_numeric(group, "distance"),
                "class_name": choose_first_non_empty(group, "class_name"),
                "condition": choose_first_non_empty(group, "condition"),
                "finish_pos": choose_first_numeric(group, "finish_pos"),
                "rating_value": choose_first_numeric(group[group["rating_value"].notna()] if group["rating_value"].notna().any() else group, "rating_value"),
                "sp": choose_first_numeric(group, "sp"),
                "history_source_used": ";".join(sources),
                "history_source_count_run": len(sources),
                "strict_match_any": bool(group["strict_hit"].any()),
                "loose_match_any": bool(group["loose_hit"].any()),
                "source_priority_min": int(group["source_priority"].min()),
            }
        )

    aggregated = pd.DataFrame(rows)
    aggregated = aggregated.sort_values(["run_date_dt", "source_priority_min", "track", "race_no"], na_position="last").copy()
    return aggregated


def main():
    if not LIVE_PATH.exists():
        raise FileNotFoundError(f"Missing live runner board: {LIVE_PATH}")

    print("[CAMPAIGN_INTELLIGENCE_V1_1] loading live runner board ...")
    live = pd.read_csv(LIVE_PATH, low_memory=False)
    live["current_race_date_dt"] = parse_date_series(live[first_existing(live.columns, ["race_date", "meeting_date", "_date"])])
    live["current_race_date"] = live["current_race_date_dt"].dt.strftime("%Y-%m-%d").fillna("")

    live["horse_display"] = to_text(live[first_existing(live.columns, ["horse", "runner", "runner_name"])])
    if first_existing(live.columns, ["horse_key", "runner_key"]):
        horse_key_col = first_existing(live.columns, ["horse_key", "runner_key"])
        live["horse_key_raw"] = to_text(live[horse_key_col])
    else:
        live["horse_key_raw"] = ""

    live["strict_key"] = live["horse_key_raw"].map(normalize_strict)
    live.loc[live["strict_key"] == "", "strict_key"] = live["horse_display"].map(normalize_strict)
    live["loose_key"] = live["horse_display"].map(normalize_loose)

    scratched_mask = pd.Series([False] * len(live), index=live.index)
    if "runner_status" in live.columns:
        scratched_mask = scratched_mask | live["runner_status"].fillna("").astype(str).str.upper().eq("SCRATCHED")
    if "is_scratched" in live.columns:
        scratched_mask = scratched_mask | live["is_scratched"].fillna("").astype(str).str.upper().isin({"TRUE", "1", "YES"})
    active_live = live[~scratched_mask].copy()

    current_strict_keys = {value for value in active_live["strict_key"] if value}
    current_loose_keys = {value for value in active_live["loose_key"] if value}
    loose_key_counts = Counter(active_live["loose_key"])

    source_frames = []
    for source_name, source_priority in SOURCE_PRIORITY:
        source_path = DATA / source_name
        source_frames.append(
            prepare_source(
                source_path,
                source_name,
                source_priority,
                current_strict_keys,
                current_loose_keys,
            )
        )

    history_pool = pd.concat(source_frames, ignore_index=True) if source_frames else pd.DataFrame()

    strict_index = defaultdict(list)
    loose_index = defaultdict(list)
    if not history_pool.empty:
        for idx, row in history_pool.iterrows():
            if row["strict_key"]:
                strict_index[row["strict_key"]].append(idx)
            if row["loose_key"]:
                loose_index[row["loose_key"]].append(idx)

    print("[CAMPAIGN_INTELLIGENCE_V1_1] building runner campaign profiles ...")
    output_rows = []
    audit_rows = []

    for _, live_row in active_live.sort_values(["current_race_date", "track", "race_no", "saddlecloth", "horse_display"], na_position="last").iterrows():
        current_date = live_row.get("current_race_date_dt", pd.NaT)
        strict_key = live_row.get("strict_key", "")
        loose_key = live_row.get("loose_key", "")

        strict_indices = set(strict_index.get(strict_key, [])) if strict_key else set()
        use_loose = bool(loose_key and loose_key_counts.get(loose_key, 0) == 1)
        loose_indices = set(loose_index.get(loose_key, [])) if use_loose else set()
        all_indices = strict_indices | loose_indices

        if all_indices:
            candidate_rows = history_pool.loc[sorted(all_indices)].copy()
            candidate_rows["strict_hit"] = candidate_rows["strict_key"].eq(strict_key) if strict_key else False
            candidate_rows["loose_hit"] = candidate_rows["loose_key"].eq(loose_key) if use_loose else False
            candidate_rows = candidate_rows[candidate_rows["strict_hit"] | candidate_rows["loose_hit"]].copy()
        else:
            candidate_rows = pd.DataFrame(columns=list(history_pool.columns) + ["strict_hit", "loose_hit"])

        aggregated_runs = aggregate_candidate_runs(candidate_rows)
        prior_runs = aggregated_runs[aggregated_runs["run_date_dt"] < current_date].copy() if pd.notna(current_date) else aggregated_runs.iloc[0:0].copy()
        prior_runs = assign_prep_stages(prior_runs)
        rated_history = prior_runs[prior_runs["rating_value"].notna()].copy()

        total_history_runs = int(len(prior_runs))
        rated_runs = int(len(rated_history))
        unique_rated_stages = int(rated_history["prep_stage_num"].dropna().nunique())
        current_stage = infer_current_prep_stage(prior_runs["run_date_dt"].tolist(), current_date) if pd.notna(current_date) else None
        current_stage_label = stage_num_to_label(current_stage)

        stage_counts_all = prior_runs.groupby("prep_stage_num").size().to_dict() if not prior_runs.empty else {}
        stage_counts_rated = rated_history.groupby("prep_stage_num").size().to_dict() if not rated_history.empty else {}
        stage_avg = rated_history.groupby("prep_stage_num")["rating_value"].mean().to_dict() if not rated_history.empty else {}

        if pd.isna(current_date):
            evidence_status = "MISSING_CURRENT_DATE"
        elif total_history_runs == 0:
            evidence_status = "NO_HISTORY"
        elif rated_runs == 0:
            evidence_status = "UNRATED_HISTORY"
        elif rated_runs >= 8 and unique_rated_stages >= 3:
            evidence_status = "STRONG_PROFILE"
        elif rated_runs >= 4 and unique_rated_stages >= 2:
            evidence_status = "DEVELOPING_PROFILE"
        else:
            evidence_status = "LIMITED_HISTORY"

        stage_stats = (
            rated_history.groupby("prep_stage_num")["rating_value"]
            .agg(sample_count="count", avg_rating="mean")
            .sort_index()
        ) if not rated_history.empty else pd.DataFrame(columns=["sample_count", "avg_rating"])

        if not stage_stats.empty:
            peak_source = stage_stats[stage_stats["sample_count"] >= 2]
            if peak_source.empty:
                peak_source = stage_stats
            historical_peak_stage = int(peak_source["avg_rating"].idxmax())
            best_avg = float(peak_source.loc[historical_peak_stage, "avg_rating"])
            peak_window_start, peak_window_end = build_peak_window(peak_source, historical_peak_stage, best_avg)
        else:
            historical_peak_stage = None
            best_avg = None
            peak_window_start = None
            peak_window_end = None

        campaign_profile = classify_campaign_profile(
            evidence_status,
            rated_history,
            stage_stats,
            historical_peak_stage,
            best_avg,
            peak_window_end,
        )
        campaign_profile_band = band_from_evidence_status(evidence_status)
        campaign_risk_score, campaign_risk_band = assess_campaign_risk(
            evidence_status,
            campaign_profile,
            current_stage,
            peak_window_start,
            peak_window_end,
        )
        campaign_narrative = build_campaign_narrative(
            evidence_status,
            campaign_profile,
            current_stage,
            campaign_risk_band,
            peak_window_start,
            peak_window_end,
        )

        prep_stage_sample_count = int(stage_counts_rated.get(current_stage, 0)) if current_stage is not None else 0
        campaign_positive_flag = "YES" if campaign_risk_band == "LOW" else "NO"
        campaign_risk_flag = "YES" if campaign_risk_band == "HIGH" else "NO"

        history_sources = []
        for value in prior_runs["history_source_used"].tolist():
            for source_name in str(value).split(";"):
                source_name = source_name.strip()
                if source_name and source_name not in history_sources:
                    history_sources.append(source_name)

        history_source_used = ";".join(history_sources)
        history_source_count = len(history_sources)
        strict_match_flag = "YES" if bool(prior_runs["strict_match_any"].any()) else "NO"
        loose_match_flag = "YES" if bool(prior_runs["loose_match_any"].any() and not prior_runs["strict_match_any"].all()) or (bool(prior_runs["loose_match_any"].any()) and not bool(prior_runs["strict_match_any"].any())) else ("YES" if bool(prior_runs["loose_match_any"].any()) and bool(prior_runs["strict_match_any"].any()) else "NO")

        output_rows.append(
            {
                "track": str(live_row.get("track", "")).strip(),
                "race_no": str(live_row.get("race_no", "")).strip(),
                "horse": str(live_row.get("horse_display", "")).strip(),
                "horse_key": str(live_row.get("horse_key_raw", "")).strip(),
                "current_race_date": live_row.get("current_race_date", ""),
                "current_prep_stage": "" if current_stage is None else int(current_stage),
                "prep_stage_label": current_stage_label,
                "historical_peak_prep_stage": "" if historical_peak_stage is None else int(historical_peak_stage),
                "historical_peak_prep_stage_label": stage_num_to_label(historical_peak_stage),
                "peak_window_start": "" if peak_window_start is None else int(peak_window_start),
                "peak_window_end": "" if peak_window_end is None else int(peak_window_end),
                "campaign_profile": campaign_profile,
                "campaign_profile_band": campaign_profile_band,
                "campaign_risk_score": "" if campaign_risk_score is None else int(campaign_risk_score),
                "campaign_risk_band": campaign_risk_band,
                "campaign_positive_flag": campaign_positive_flag,
                "campaign_risk_flag": campaign_risk_flag,
                "campaign_narrative": campaign_narrative,
                "history_runs_used": total_history_runs,
                "prep_stage_sample_count": prep_stage_sample_count,
                "evidence_status": evidence_status,
                "history_source_used": history_source_used,
                "history_source_count": history_source_count,
                "strict_match_flag": strict_match_flag,
                "loose_match_flag": loose_match_flag,
                "built_at": NOW_UTC,
            }
        )

        audit_rows.append(
            {
                "track": str(live_row.get("track", "")).strip(),
                "race_no": str(live_row.get("race_no", "")).strip(),
                "horse": str(live_row.get("horse_display", "")).strip(),
                "horse_key": str(live_row.get("horse_key_raw", "")).strip(),
                "current_race_date": live_row.get("current_race_date", ""),
                "history_runs_used": total_history_runs,
                "rated_history_rows": rated_runs,
                "unique_rated_prep_stages": unique_rated_stages,
                "current_prep_stage": "" if current_stage is None else int(current_stage),
                "prep_stage_label": current_stage_label,
                "historical_peak_prep_stage": "" if historical_peak_stage is None else int(historical_peak_stage),
                "peak_window_start": "" if peak_window_start is None else int(peak_window_start),
                "peak_window_end": "" if peak_window_end is None else int(peak_window_end),
                "campaign_profile": campaign_profile,
                "campaign_profile_band": campaign_profile_band,
                "campaign_risk_score": "" if campaign_risk_score is None else int(campaign_risk_score),
                "campaign_risk_band": campaign_risk_band,
                "evidence_status": evidence_status,
                "history_source_used": history_source_used,
                "history_source_count": history_source_count,
                "strict_match_flag": strict_match_flag,
                "loose_match_flag": loose_match_flag,
                "stage_count_map": serialise_stage_counts(stage_counts_all),
                "stage_rated_count_map": serialise_stage_counts(stage_counts_rated),
                "stage_avg_rating_map": serialise_stage_map(stage_avg),
                "current_stage_history_sample": prep_stage_sample_count,
                "current_stage_avg_rating": "" if current_stage is None or current_stage not in stage_avg else round(float(stage_avg[current_stage]), 2),
                "peak_stage_avg_rating": "" if best_avg is None else round(float(best_avg), 2),
                "campaign_narrative": campaign_narrative,
            }
        )

    output_df = pd.DataFrame(output_rows)
    audit_df = pd.DataFrame(audit_rows)

    evidence_rank_map = {
        "STRONG_PROFILE": 4,
        "DEVELOPING_PROFILE": 3,
        "LIMITED_HISTORY": 2,
        "UNRATED_HISTORY": 1,
        "NO_HISTORY": 0,
        "MISSING_CURRENT_DATE": -1,
    }
    output_df["top_25_evidence_sort"] = output_df["evidence_status"].map(evidence_rank_map).fillna(-1)
    output_df["top_25_history_runs"] = pd.to_numeric(output_df["history_runs_used"], errors="coerce").fillna(0)
    output_df["top_25_stage_sample"] = pd.to_numeric(output_df["prep_stage_sample_count"], errors="coerce").fillna(0)
    output_df["top_25_source_count"] = pd.to_numeric(output_df["history_source_count"], errors="coerce").fillna(0)

    top_25 = (
        output_df[output_df["top_25_history_runs"] > 0]
        .sort_values(
            ["top_25_evidence_sort", "top_25_stage_sample", "top_25_history_runs", "top_25_source_count", "horse"],
            ascending=[False, False, False, False, True],
            na_position="last",
        )
        .head(25)
        .copy()
    )
    top_25["top_25_campaign_evidence_rank"] = range(1, len(top_25) + 1)

    output_df = output_df.merge(
        top_25[["track", "race_no", "horse", "top_25_campaign_evidence_rank"]],
        on=["track", "race_no", "horse"],
        how="left",
    )
    output_df["top_25_campaign_evidence_flag"] = output_df["top_25_campaign_evidence_rank"].notna().map(lambda value: "YES" if value else "NO")

    audit_df = audit_df.merge(
        output_df[["track", "race_no", "horse", "top_25_campaign_evidence_flag", "top_25_campaign_evidence_rank"]],
        on=["track", "race_no", "horse"],
        how="left",
    )

    output_df = output_df.drop(columns=["top_25_evidence_sort", "top_25_history_runs", "top_25_stage_sample", "top_25_source_count"])
    output_df = output_df.sort_values(["current_race_date", "track", "race_no", "horse"], na_position="last")
    audit_df = audit_df.sort_values(
        ["top_25_campaign_evidence_rank", "current_race_date", "track", "race_no", "history_runs_used", "horse"],
        ascending=[True, True, True, True, False, True],
        na_position="last",
    )

    output_df.to_csv(OUT_PATH, index=False)
    audit_df.to_csv(AUDIT_PATH, index=False)

    matched_current_runners = int((pd.to_numeric(output_df["history_runs_used"], errors="coerce").fillna(0) > 0).sum())
    no_history_runners = safe_count(Counter(output_df["evidence_status"].astype(str)), "NO_HISTORY")
    coverage_pct = round(matched_current_runners / len(output_df) * 100, 2) if len(output_df) else 0.0

    profile_counts = Counter(output_df["campaign_profile"].astype(str))
    risk_counts = Counter(output_df["campaign_risk_band"].astype(str))
    evidence_status_counts = Counter(output_df["evidence_status"].astype(str))

    source_usage = Counter()
    for value in output_df["history_source_used"].fillna("").astype(str):
        for source_name in [part.strip() for part in value.split(";") if part.strip()]:
            source_usage[source_name] += 1

    top_25_preview = "; ".join(
        f"{int(row['top_25_campaign_evidence_rank'])}. {row['horse']} ({row['evidence_status']}, {int(row['history_runs_used'])} runs)"
        for _, row in top_25.iterrows()
    )

    summary_df = pd.DataFrame(
        [
            {
                "status": "EDGEIQ_CAMPAIGN_INTELLIGENCE_ENGINE_V1_1_BUILT",
                "spell_days": SPELL_DAYS,
                "input_live_rows": int(len(live)),
                "active_runner_rows": int(len(active_live)),
                "output_rows": int(len(output_df)),
                "coverage_pct": coverage_pct,
                "matched_current_runners": matched_current_runners,
                "no_history_runners": no_history_runners,
                "strong_profile_rows": safe_count(evidence_status_counts, "STRONG_PROFILE"),
                "developing_profile_rows": safe_count(evidence_status_counts, "DEVELOPING_PROFILE"),
                "limited_history_rows": safe_count(evidence_status_counts, "LIMITED_HISTORY"),
                "unrated_history_rows": safe_count(evidence_status_counts, "UNRATED_HISTORY"),
                "profile_counts": serialise_counts(profile_counts),
                "risk_counts": serialise_counts(risk_counts),
                "source_usage_counts": serialise_counts(source_usage),
                "evidence_status_counts": serialise_counts(evidence_status_counts),
                "top_25_runners_with_strongest_campaign_evidence": top_25_preview,
                "built_at": NOW_UTC,
            }
        ]
    )
    summary_df.to_csv(SUMMARY_PATH, index=False)

    print("[CAMPAIGN_INTELLIGENCE_V1_1] COMPLETE")
    print(f"out={OUT_PATH}")
    print(f"summary={SUMMARY_PATH}")
    print(f"audit={AUDIT_PATH}")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
