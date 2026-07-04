import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_PATH = DATA / "edgeiq_live_runner_board_v1.csv"
HISTORY_DETAIL_PATH = DATA / "edgeiq_runner_history_detail_v1.csv"
RUNNER_FORM_HISTORY_PATH = DATA / "runner_form_history.csv"
RUNNER_FORM_ENGINE_PATH = DATA / "edgeiq_runner_form_engine_current.csv"

OUT_PATH = DATA / "edgeiq_campaign_intelligence_engine_v1.csv"
SUMMARY_PATH = DATA / "edgeiq_campaign_intelligence_engine_v1_summary.csv"
AUDIT_PATH = DATA / "edgeiq_campaign_intelligence_engine_v1_audit.csv"

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


def clean_key(value):
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


def first_existing(df, candidates):
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


def to_text(series):
    return series.fillna("").astype(str).str.strip()


def to_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def parse_date_series(series):
    return pd.to_datetime(series, errors="coerce").dt.normalize()


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
    stage_num = int(stage_num)
    return STAGE_LABELS.get(stage_num, "UNKNOWN")


def stage_num_to_window_text(start_stage, end_stage):
    if start_stage is None or end_stage is None:
        return "unknown stage"
    if start_stage == end_stage:
        return stage_num_to_label(start_stage).replace("_", "-").lower()
    return f"{stage_num_to_label(start_stage).replace('_', '-').lower()} to {stage_num_to_label(end_stage).replace('_', '-').lower()}"


def stage_num_from_run_no(run_no):
    if pd.isna(run_no):
        return math.nan
    run_no = int(run_no)
    if run_no <= 0:
        return math.nan
    return min(run_no, 6)


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


def pick_rating_value(df):
    preferred = [
        "performance_rating_v6_1_research",
        "performance_rating",
        "run_rating_final",
        "rating",
        "projected_rating",
        "run_rating",
    ]
    available = [column for column in preferred if column in df.columns]
    if not available:
        return pd.Series([math.nan] * len(df), index=df.index)
    numeric_frame = df[available].apply(to_numeric)
    return numeric_frame.bfill(axis=1).iloc[:, 0]


def prepare_history_source(path, source_name, source_rank):
    if not path.exists():
        return pd.DataFrame(
            columns=[
                "horse",
                "horse_key_norm",
                "horse_name_norm",
                "runner_identity",
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
                "source_file",
                "source_confidence",
                "source_rank",
                "row_richness",
                "dedup_key",
            ]
        )

    print(f"[CAMPAIGN_INTELLIGENCE_V1] loading {path.name} ...")
    df = pd.read_csv(path, low_memory=False)

    horse_col = first_existing(df, ["horse", "horse_name", "runner", "runner_name"])
    horse_key_col = first_existing(df, ["horse_key", "runner_key"])
    date_col = first_existing(df, ["run_date_iso", "race_date", "meeting_date", "run_date", "date"])
    track_col = first_existing(df, ["track", "meeting_name", "venue"])
    race_no_col = first_existing(df, ["race_no", "race_number"])
    distance_col = first_existing(df, ["distance", "race_distance"])
    class_col = first_existing(df, ["class_name", "race_class", "class"])
    condition_col = first_existing(df, ["condition", "track_condition", "going"])
    finish_col = first_existing(df, ["finish_pos", "finish_position", "finish_num", "position"])
    sp_col = first_existing(df, ["sp", "sp_settled", "sp_num_settled", "stab"])
    confidence_col = first_existing(df, ["source_confidence", "history_status"])

    out = pd.DataFrame(index=df.index)
    out["horse"] = to_text(df[horse_col]) if horse_col else ""
    if horse_key_col:
        out["horse_key_norm"] = to_text(df[horse_key_col]).map(clean_key)
    else:
        out["horse_key_norm"] = ""
    out["horse_name_norm"] = out["horse"].map(clean_key)
    out["runner_identity"] = out["horse_key_norm"]
    out.loc[out["runner_identity"] == "", "runner_identity"] = out["horse_name_norm"]
    out["run_date_dt"] = parse_date_series(df[date_col]) if date_col else pd.NaT
    out["run_date_iso"] = out["run_date_dt"].dt.strftime("%Y-%m-%d").fillna("")
    out["track"] = to_text(df[track_col]) if track_col else ""
    out["track_norm"] = out["track"].map(normalize_track)
    out["race_no"] = to_numeric(df[race_no_col]) if race_no_col else math.nan
    out["distance"] = to_numeric(df[distance_col]) if distance_col else math.nan
    out["class_name"] = to_text(df[class_col]) if class_col else ""
    out["condition"] = to_text(df[condition_col]) if condition_col else ""
    out["finish_pos"] = df[finish_col].map(parse_finish_pos) if finish_col else math.nan
    out["rating_value"] = pick_rating_value(df)
    out["sp"] = to_numeric(df[sp_col]) if sp_col else math.nan
    out["source_file"] = path.name
    out["source_confidence"] = to_text(df[confidence_col]) if confidence_col else source_name
    out["source_rank"] = source_rank

    out = out[
        (out["runner_identity"] != "") &
        out["run_date_dt"].notna()
    ].copy()

    distance_norm = out["distance"].round(0).fillna(-1).astype(int).astype(str).replace("-1", "")
    race_no_norm = out["race_no"].round(0).fillna(-1).astype(int).astype(str).replace("-1", "")
    out["dedup_key"] = (
        out["runner_identity"]
        + "|"
        + out["run_date_iso"]
        + "|"
        + out["track_norm"]
        + "|"
        + distance_norm
        + "|"
        + race_no_norm
    )

    richness_columns = ["track", "distance", "class_name", "condition", "finish_pos", "rating_value", "sp"]
    richness_score = 0
    for column in richness_columns:
        if column in {"finish_pos", "distance", "rating_value", "sp"}:
            richness_score += out[column].notna().astype(int)
        else:
            richness_score += out[column].astype(str).str.strip().ne("").astype(int)
    out["row_richness"] = richness_score + out["source_rank"] * 10 + out["rating_value"].notna().astype(int) * 4
    return out


def deduplicate_history(history):
    if history.empty:
        return history.copy()
    history = history.sort_values(
        ["dedup_key", "row_richness", "source_rank", "rating_value", "finish_pos"],
        ascending=[True, False, False, False, True],
        na_position="last",
    )
    history = history.drop_duplicates("dedup_key", keep="first").copy()
    history = history.sort_values(["runner_identity", "run_date_dt", "track", "race_no"], na_position="last").copy()
    return history


def assign_historical_prep_stages(history):
    if history.empty:
        return history.copy()
    history = history.sort_values(["runner_identity", "run_date_dt", "track", "race_no"], na_position="last").copy()
    history["prev_run_date"] = history.groupby("runner_identity")["run_date_dt"].shift(1)
    history["days_since_prev"] = (history["run_date_dt"] - history["prev_run_date"]).dt.days
    history["new_prep"] = history["days_since_prev"].isna() | (history["days_since_prev"] >= SPELL_DAYS)
    history["prep_id"] = history.groupby("runner_identity")["new_prep"].cumsum()
    history["prep_run_no"] = history.groupby(["runner_identity", "prep_id"]).cumcount() + 1
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


def weighted_segment_average(rated_rows, stages):
    sample = rated_rows[rated_rows["prep_stage_num"].isin(stages)]
    if sample.empty:
        return None
    return float(sample["rating_value"].mean())


def build_peak_window(stage_stats, best_stage, best_avg):
    if stage_stats.empty or best_stage is None or best_avg is None:
        return (None, None)

    threshold = 2.0 if int(stage_stats["sample_count"].sum()) >= 6 else 3.0
    start_stage = best_stage
    end_stage = best_stage

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
        mid_or_late_lower = True
        if build_avg is not None and early_avg < build_avg + 2:
            mid_or_late_lower = False
        if late_avg is not None and early_avg < late_avg + 3:
            mid_or_late_lower = False
        if mid_or_late_lower:
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


def build_campaign_narrative(
    evidence_status,
    campaign_profile,
    current_stage,
    risk_band,
    window_start,
    window_end,
):
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


def main():
    if not LIVE_PATH.exists():
        raise FileNotFoundError(f"Required live runner board is missing: {LIVE_PATH}")

    print("[CAMPAIGN_INTELLIGENCE_V1] loading live runner board ...")
    live = pd.read_csv(LIVE_PATH, low_memory=False)
    live["current_race_date_dt"] = parse_date_series(live[first_existing(live, ["race_date", "meeting_date", "_date"])])
    live["current_race_date"] = live["current_race_date_dt"].dt.strftime("%Y-%m-%d").fillna("")
    live["horse_key_norm"] = to_text(live[first_existing(live, ["horse_key", "runner_key"])]).map(clean_key) if first_existing(live, ["horse_key", "runner_key"]) else ""
    live["horse_name_norm"] = to_text(live[first_existing(live, ["horse"])]).map(clean_key) if first_existing(live, ["horse"]) else ""
    live["runner_identity_pref"] = live["horse_key_norm"]
    live.loc[live["runner_identity_pref"] == "", "runner_identity_pref"] = live["horse_name_norm"]

    scratched_mask = pd.Series([False] * len(live), index=live.index)
    if "runner_status" in live.columns:
        scratched_mask = scratched_mask | to_text(live["runner_status"]).str.upper().eq("SCRATCHED")
    if "is_scratched" in live.columns:
        scratched_mask = scratched_mask | to_text(live["is_scratched"]).str.upper().isin({"TRUE", "1", "YES"})

    active_live = live[~scratched_mask].copy()

    history_detail = prepare_history_source(HISTORY_DETAIL_PATH, "HISTORY_DETAIL", source_rank=2)
    runner_form_history = prepare_history_source(RUNNER_FORM_HISTORY_PATH, "RUNNER_FORM_HISTORY", source_rank=1)

    current_key_set = {value for value in active_live["horse_key_norm"] if value}
    current_name_set = {value for value in active_live["horse_name_norm"] if value}

    def filter_to_current(history_source):
        if history_source.empty:
            return history_source
        return history_source[
            history_source["horse_key_norm"].isin(current_key_set) |
            history_source["horse_name_norm"].isin(current_name_set)
        ].copy()

    history_detail = filter_to_current(history_detail)
    runner_form_history = filter_to_current(runner_form_history)

    history = pd.concat([history_detail, runner_form_history], ignore_index=True)
    history = deduplicate_history(history)
    history = assign_historical_prep_stages(history)

    print("[CAMPAIGN_INTELLIGENCE_V1] loading runner form engine audit surface ...")
    form_engine = pd.read_csv(RUNNER_FORM_ENGINE_PATH, low_memory=False) if RUNNER_FORM_ENGINE_PATH.exists() else pd.DataFrame()
    if not form_engine.empty:
        horse_col = first_existing(form_engine, ["horse", "runner", "runner_name"])
        form_engine["horse_name_norm"] = to_text(form_engine[horse_col]).map(clean_key) if horse_col else ""
        form_engine_recent_col = first_existing(form_engine, ["recent_runs_found"])
        form_engine_hist_source_col = first_existing(form_engine, ["historical_source_used"])
    else:
        form_engine_recent_col = None
        form_engine_hist_source_col = None

    print("[CAMPAIGN_INTELLIGENCE_V1] building campaign intelligence rows ...")
    output_rows = []
    audit_rows = []

    history_detail_keys = history_detail["dedup_key"].tolist() if not history_detail.empty else []
    runner_form_history_keys = runner_form_history["dedup_key"].tolist() if not runner_form_history.empty else []
    history_detail_key_set = set(history_detail_keys)
    runner_form_history_key_set = set(runner_form_history_keys)

    for _, live_row in active_live.sort_values(["current_race_date", "track", "race_no", "saddlecloth", "horse"], na_position="last").iterrows():
        horse_name = str(live_row.get("horse", "")).strip()
        horse_key_norm = live_row.get("horse_key_norm", "")
        horse_name_norm = live_row.get("horse_name_norm", "")
        current_date = live_row.get("current_race_date_dt", pd.NaT)

        if horse_key_norm:
            matched_history = history[history["horse_key_norm"] == horse_key_norm].copy()
            match_method = "HORSE_KEY" if not matched_history.empty else "HORSE_NAME_FALLBACK"
        else:
            matched_history = pd.DataFrame(columns=history.columns)
            match_method = "HORSE_NAME_FALLBACK"

        if matched_history.empty and horse_name_norm:
            matched_history = history[history["horse_name_norm"] == horse_name_norm].copy()

        matched_history = matched_history.sort_values(["run_date_dt", "track", "race_no"], na_position="last").copy()
        prior_history = matched_history[matched_history["run_date_dt"] < current_date].copy() if pd.notna(current_date) else matched_history.iloc[0:0].copy()
        rated_history = prior_history[prior_history["rating_value"].notna()].copy()

        current_stage = infer_current_prep_stage(prior_history["run_date_dt"].tolist(), current_date) if pd.notna(current_date) else None
        current_stage_label = stage_num_to_label(current_stage)

        stage_counts_all = prior_history.groupby("prep_stage_num").size().to_dict() if not prior_history.empty else {}
        stage_counts_rated = rated_history.groupby("prep_stage_num").size().to_dict() if not rated_history.empty else {}
        stage_avg = rated_history.groupby("prep_stage_num")["rating_value"].mean().to_dict() if not rated_history.empty else {}

        total_history_runs = int(len(prior_history))
        rated_runs = int(len(rated_history))
        unique_stages = int(len(stage_avg))

        if pd.isna(current_date):
            evidence_status = "MISSING_CURRENT_DATE"
        elif total_history_runs == 0:
            evidence_status = "NO_HISTORY"
        elif rated_runs == 0:
            evidence_status = "UNRATED_HISTORY"
        elif rated_runs >= 8 and unique_stages >= 3:
            evidence_status = "STRONG_PROFILE"
        elif rated_runs >= 4 and unique_stages >= 2:
            evidence_status = "DEVELOPING_PROFILE"
        else:
            evidence_status = "LIMITED_HISTORY"

        stage_stats = (
            rated_history.groupby("prep_stage_num")["rating_value"]
            .agg(sample_count="count", avg_rating="mean")
            .sort_index()
        ) if not rated_history.empty else pd.DataFrame(columns=["sample_count", "avg_rating"])

        if not stage_stats.empty:
            strong_stage_stats = stage_stats[stage_stats["sample_count"] >= 2]
            peak_source = strong_stage_stats if not strong_stage_stats.empty else stage_stats
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

        prior_keys = set(prior_history["dedup_key"]) if not prior_history.empty else set()
        history_detail_rows = len(prior_keys & history_detail_key_set)
        runner_form_history_rows = len(prior_keys & runner_form_history_key_set)

        form_engine_row = pd.DataFrame()
        if not form_engine.empty and horse_name_norm:
            form_engine_row = form_engine[form_engine["horse_name_norm"] == horse_name_norm].head(1)

        form_engine_recent_runs_found = ""
        form_engine_history_source = ""
        if not form_engine_row.empty:
            if form_engine_recent_col:
                form_engine_recent_runs_found = str(form_engine_row.iloc[0][form_engine_recent_col])
            if form_engine_hist_source_col:
                form_engine_history_source = str(form_engine_row.iloc[0][form_engine_hist_source_col])

        output_rows.append(
            {
                "track": str(live_row.get("track", "")).strip(),
                "race_no": str(live_row.get("race_no", "")).strip(),
                "horse": horse_name,
                "horse_key": str(live_row.get("horse_key", "")).strip(),
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
                "built_at": NOW_UTC,
            }
        )

        audit_rows.append(
            {
                "track": str(live_row.get("track", "")).strip(),
                "race_no": str(live_row.get("race_no", "")).strip(),
                "horse": horse_name,
                "horse_key": str(live_row.get("horse_key", "")).strip(),
                "current_race_date": live_row.get("current_race_date", ""),
                "match_method": match_method,
                "history_detail_rows_used": history_detail_rows,
                "runner_form_history_rows_used": runner_form_history_rows,
                "matched_history_rows": total_history_runs,
                "rated_history_rows": rated_runs,
                "unique_rated_prep_stages": unique_stages,
                "current_prep_stage": "" if current_stage is None else int(current_stage),
                "prep_stage_label": current_stage_label,
                "historical_peak_prep_stage": "" if historical_peak_stage is None else int(historical_peak_stage),
                "peak_window_start": "" if peak_window_start is None else int(peak_window_start),
                "peak_window_end": "" if peak_window_end is None else int(peak_window_end),
                "stage_count_map": serialise_stage_counts(stage_counts_all),
                "stage_rated_count_map": serialise_stage_counts(stage_counts_rated),
                "stage_avg_rating_map": serialise_stage_map(stage_avg),
                "current_stage_history_sample": prep_stage_sample_count,
                "current_stage_avg_rating": "" if current_stage is None or current_stage not in stage_avg else round(float(stage_avg[current_stage]), 2),
                "peak_stage_avg_rating": "" if best_avg is None else round(float(best_avg), 2),
                "campaign_profile": campaign_profile,
                "campaign_profile_band": campaign_profile_band,
                "campaign_risk_score": "" if campaign_risk_score is None else int(campaign_risk_score),
                "campaign_risk_band": campaign_risk_band,
                "campaign_positive_flag": campaign_positive_flag,
                "campaign_risk_flag": campaign_risk_flag,
                "evidence_status": evidence_status,
                "form_engine_recent_runs_found": form_engine_recent_runs_found,
                "form_engine_history_source": form_engine_history_source,
                "campaign_narrative": campaign_narrative,
            }
        )

    output_df = pd.DataFrame(output_rows)
    audit_df = pd.DataFrame(audit_rows)

    output_df = output_df.sort_values(["current_race_date", "track", "race_no", "horse"], na_position="last")
    audit_df = audit_df.sort_values(["current_race_date", "track", "race_no", "matched_history_rows", "horse"], ascending=[True, True, True, False, True], na_position="last")

    output_df.to_csv(OUT_PATH, index=False)
    audit_df.to_csv(AUDIT_PATH, index=False)

    profile_counts = Counter(output_df["campaign_profile"].astype(str))
    profile_band_counts = Counter(output_df["campaign_profile_band"].astype(str))
    risk_band_counts = Counter(output_df["campaign_risk_band"].astype(str))
    evidence_status_counts = Counter(output_df["evidence_status"].astype(str))

    null_current_stage_count = int(output_df["current_prep_stage"].replace("", pd.NA).isna().sum())
    null_peak_stage_count = int(output_df["historical_peak_prep_stage"].replace("", pd.NA).isna().sum())
    null_risk_score_count = int(output_df["campaign_risk_score"].replace("", pd.NA).isna().sum())

    sample_rows = audit_df.sort_values(
        ["matched_history_rows", "rated_history_rows", "unique_rated_prep_stages", "horse"],
        ascending=[False, False, False, True],
        na_position="last",
    ).head(10)
    top_samples = (
        "; ".join(
            f"{row['horse']} ({row['matched_history_rows']} runs, {row['evidence_status']})"
            for _, row in sample_rows.iterrows()
        )
        if not sample_rows.empty
        else ""
    )

    summary_df = pd.DataFrame(
        [
            {
                "status": "EDGEIQ_CAMPAIGN_INTELLIGENCE_ENGINE_V1_BUILT",
                "spell_days": SPELL_DAYS,
                "input_live_rows": int(len(live)),
                "active_runner_rows": int(len(active_live)),
                "history_detail_source_rows": int(len(history_detail)),
                "runner_form_history_source_rows": int(len(runner_form_history)),
                "deduped_history_rows": int(len(history)),
                "output_rows": int(len(output_df)),
                "horses_processed": int(output_df["horse"].nunique()),
                "current_runners_matched": int((output_df["history_runs_used"] > 0).sum()),
                "unmatched_current_runners": int((output_df["history_runs_used"] <= 0).sum()),
                "strong_profile_rows": safe_count(evidence_status_counts, "STRONG_PROFILE"),
                "developing_profile_rows": safe_count(evidence_status_counts, "DEVELOPING_PROFILE"),
                "limited_history_rows": safe_count(evidence_status_counts, "LIMITED_HISTORY"),
                "unrated_history_rows": safe_count(evidence_status_counts, "UNRATED_HISTORY"),
                "no_history_rows": safe_count(evidence_status_counts, "NO_HISTORY"),
                "missing_current_date_rows": safe_count(evidence_status_counts, "MISSING_CURRENT_DATE"),
                "campaign_profile_counts": serialise_counts(profile_counts),
                "campaign_profile_band_counts": serialise_counts(profile_band_counts),
                "campaign_risk_band_counts": serialise_counts(risk_band_counts),
                "evidence_status_counts": serialise_counts(evidence_status_counts),
                "null_current_prep_stage_count": null_current_stage_count,
                "null_historical_peak_stage_count": null_peak_stage_count,
                "null_campaign_risk_score_count": null_risk_score_count,
                "top_sample_rows_for_sanity": top_samples,
                "built_at": NOW_UTC,
            }
        ]
    )
    summary_df.to_csv(SUMMARY_PATH, index=False)

    print("[CAMPAIGN_INTELLIGENCE_V1] COMPLETE")
    print(f"out={OUT_PATH}")
    print(f"summary={SUMMARY_PATH}")
    print(f"audit={AUDIT_PATH}")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
