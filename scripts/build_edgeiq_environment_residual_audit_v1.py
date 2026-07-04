from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

TF_PATH = DATA / "edgeiq_trust_field_engine_v1.csv"
ENV_PATH = DATA / "edgeiq_environment_score_replay_v1.csv"

OUT_MAIN = DATA / "edgeiq_environment_residual_audit_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_environment_residual_audit_v1_summary.csv"
OUT_VERDICT = DATA / "edgeiq_environment_residual_audit_v1_verdict.csv"

BAND_ORDER = ["POOR", "NEGATIVE", "NEUTRAL", "POSITIVE", "ELITE"]


def clean_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def parse_float(value: object) -> float | None:
    text = clean_text(value)
    if not text:
        return None
    text = text.replace(",", "").replace("$", "")
    if text.upper() in {"NA", "N/A", "NULL", "NONE", "-", "--"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def normalise_date(value: object) -> str:
    text = clean_text(value)
    if not text:
        return ""
    try:
        return pd.to_datetime(text).strftime("%Y-%m-%d")
    except Exception:
        match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        return match.group(1) if match else text


def normalise_track(value: object) -> str:
    text = clean_text(value).upper()
    if not text:
        return ""
    text = re.sub(r"[^A-Z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalise_race_no(value: object) -> str:
    text = clean_text(value)
    match = re.search(r"(\d+)", text)
    return str(int(match.group(1))) if match else ""


def normalise_horse_key(value: object) -> str:
    text = clean_text(value).upper()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def make_join_key(meeting_date: object, track: object, race_no: object, horse_key: object, horse_name: object) -> str:
    date_part = normalise_date(meeting_date)
    track_part = normalise_track(track)
    race_part = normalise_race_no(race_no)
    horse_part = normalise_horse_key(horse_key if clean_text(horse_key) else horse_name)
    return f"{date_part}|{track_part}|R{race_part}|{horse_part}"


def tf_band(score: float) -> str:
    if score <= -15:
        return "POOR"
    if score <= 4:
        return "NEGATIVE"
    if score <= 24:
        return "NEUTRAL"
    if score <= 44:
        return "POSITIVE"
    return "ELITE"


def truthy(value: object) -> bool:
    return clean_text(value).upper() in {"TRUE", "1", "YES", "Y"}


def pace_points(value: object) -> int:
    band = clean_text(value).upper()
    if band == "ELITE":
        return 20
    if band == "POSITIVE":
        return 10
    if band == "POOR":
        return -10
    return 0


def race_strength_points(value: object) -> int:
    band = clean_text(value).upper()
    if band in {"ELITE", "VERY_STRONG", "VSTRONG"}:
        return 15
    if band == "STRONG":
        return 10
    if band == "WEAK":
        return -5
    return 0


def lone_leader_points(value: object) -> int:
    return 20 if truthy(value) else 0


def summarise_band_test(test_name: str, band_series: pd.Series, win_series: pd.Series) -> dict[str, object]:
    temp = pd.DataFrame({
        "band": band_series,
        "won": win_series.astype(int),
    })

    weak = temp[temp["band"].isin(["POOR", "NEGATIVE"])]
    neutral = temp[temp["band"] == "NEUTRAL"]
    strong = temp[temp["band"].isin(["POSITIVE", "ELITE"])]

    weak_runners = int(len(weak))
    neutral_runners = int(len(neutral))
    strong_runners = int(len(strong))

    weak_win_pct = round(weak["won"].mean() * 100, 2) if weak_runners else 0.0
    neutral_win_pct = round(neutral["won"].mean() * 100, 2) if neutral_runners else 0.0
    strong_win_pct = round(strong["won"].mean() * 100, 2) if strong_runners else 0.0
    lift_pts = round(strong_win_pct - weak_win_pct, 2) if weak_runners and strong_runners else 0.0

    output = {
        "test_id_v1": test_name,
        "runners": int(len(temp)),
        "wins": int(temp["won"].sum()),
        "overall_win_pct": round(temp["won"].mean() * 100, 2) if len(temp) else 0.0,
        "weak_runners": weak_runners,
        "weak_win_pct": weak_win_pct,
        "neutral_runners": neutral_runners,
        "neutral_win_pct": neutral_win_pct,
        "strong_runners": strong_runners,
        "strong_win_pct": strong_win_pct,
        "strong_vs_weak_lift_pts": lift_pts,
    }

    for band in BAND_ORDER:
        output[f"{band.lower()}_count_v1"] = int((temp["band"] == band).sum())

    return output


def summarise_score_test(test_name: str, score_series: pd.Series, win_series: pd.Series) -> dict[str, object]:
    bands = score_series.map(tf_band)
    return summarise_band_test(test_name, bands, win_series)


def main() -> None:
    if not TF_PATH.exists():
        raise SystemExit(f"Missing Trust+Field file: {TF_PATH}")
    if not ENV_PATH.exists():
        raise SystemExit(f"Missing Environment replay file: {ENV_PATH}")

    tf_df = pd.read_csv(TF_PATH, low_memory=False)
    env_df = pd.read_csv(ENV_PATH, low_memory=False)

    tf_df["join_key_v1"] = [
        make_join_key(meeting_date, track, race_no, horse_key, horse_name)
        for meeting_date, track, race_no, horse_key, horse_name in zip(
            tf_df.get("meeting_date", ""),
            tf_df.get("track", ""),
            tf_df.get("race_no", ""),
            tf_df.get("rank1_horse_key", ""),
            tf_df.get("rank1_horse", ""),
        )
    ]
    env_df["join_key_v1"] = [
        make_join_key(meeting_date, track, race_no, horse_key, horse_name)
        for meeting_date, track, race_no, horse_key, horse_name in zip(
            env_df.get("meeting_date", ""),
            env_df.get("track", ""),
            env_df.get("race_no", ""),
            env_df.get("rank1_horse_key", ""),
            env_df.get("rank1_horse", ""),
        )
    ]

    tf_df["trust_field_score_v1"] = pd.to_numeric(tf_df["trust_field_score_v1"], errors="coerce").fillna(0.0)
    tf_df["trust_field_win_v1"] = pd.to_numeric(tf_df["trust_field_win_v1"], errors="coerce").fillna(0).astype(int)
    env_df["environment_score_v1"] = pd.to_numeric(env_df["environment_score_v1"], errors="coerce").fillna(0.0)
    env_df["environment_win_v1"] = pd.to_numeric(env_df["environment_win_v1"], errors="coerce").fillna(0).astype(int)

    env_keep = [
        "join_key_v1",
        "pace_advantage_band_v1",
        "pace_advantage_score_v1",
        "race_strength_band",
        "field_strength_score",
        "field_strength_percentile",
        "lone_leader_bool",
        "lone_leader_crawl_v1",
    ]
    env_keep = [column for column in env_keep if column in env_df.columns]
    env_slice = env_df[env_keep].drop_duplicates("join_key_v1")

    merged = tf_df.merge(env_slice, on="join_key_v1", how="left", validate="one_to_one")

    merged["pace_modifier_points_v1"] = merged.get("pace_advantage_band_v1", pd.Series("", index=merged.index)).map(pace_points)
    merged["race_strength_modifier_points_v1"] = merged.get("race_strength_band", pd.Series("", index=merged.index)).map(race_strength_points)
    merged["lone_leader_modifier_points_v1"] = merged.get("lone_leader_bool", pd.Series("", index=merged.index)).map(lone_leader_points)
    merged["residual_modifier_score_v1"] = (
        merged["pace_modifier_points_v1"]
        + merged["race_strength_modifier_points_v1"]
        + merged["lone_leader_modifier_points_v1"]
    )

    merged["tf_plus_pace_score_v1"] = merged["trust_field_score_v1"] + merged["pace_modifier_points_v1"]
    merged["tf_plus_race_strength_score_v1"] = merged["trust_field_score_v1"] + merged["race_strength_modifier_points_v1"]
    merged["tf_plus_lone_leader_score_v1"] = merged["trust_field_score_v1"] + merged["lone_leader_modifier_points_v1"]
    merged["tf_plus_pace_race_strength_score_v1"] = (
        merged["trust_field_score_v1"] + merged["pace_modifier_points_v1"] + merged["race_strength_modifier_points_v1"]
    )
    merged["tf_plus_pace_lone_leader_score_v1"] = (
        merged["trust_field_score_v1"] + merged["pace_modifier_points_v1"] + merged["lone_leader_modifier_points_v1"]
    )
    merged["tf_plus_race_strength_lone_leader_score_v1"] = (
        merged["trust_field_score_v1"] + merged["race_strength_modifier_points_v1"] + merged["lone_leader_modifier_points_v1"]
    )
    merged["tf_plus_all_modifiers_score_v1"] = merged["trust_field_score_v1"] + merged["residual_modifier_score_v1"]

    merged["tf_plus_pace_band_v1"] = merged["tf_plus_pace_score_v1"].map(tf_band)
    merged["tf_plus_race_strength_band_v1"] = merged["tf_plus_race_strength_score_v1"].map(tf_band)
    merged["tf_plus_lone_leader_band_v1"] = merged["tf_plus_lone_leader_score_v1"].map(tf_band)
    merged["tf_plus_pace_race_strength_band_v1"] = merged["tf_plus_pace_race_strength_score_v1"].map(tf_band)
    merged["tf_plus_pace_lone_leader_band_v1"] = merged["tf_plus_pace_lone_leader_score_v1"].map(tf_band)
    merged["tf_plus_race_strength_lone_leader_band_v1"] = merged["tf_plus_race_strength_lone_leader_score_v1"].map(tf_band)
    merged["tf_plus_all_modifiers_band_v1"] = merged["tf_plus_all_modifiers_score_v1"].map(tf_band)

    residual_reasons: list[str] = []
    for pace_pts, strength_pts, lone_pts in zip(
        merged["pace_modifier_points_v1"],
        merged["race_strength_modifier_points_v1"],
        merged["lone_leader_modifier_points_v1"],
    ):
        reasons: list[str] = []
        if pace_pts == 20:
            reasons.append("PACE_ELITE:+20")
        elif pace_pts == 10:
            reasons.append("PACE_POSITIVE:+10")
        elif pace_pts == -10:
            reasons.append("PACE_POOR:-10")

        if strength_pts == 15:
            reasons.append("RACE_STRENGTH_ELITE_OR_VERY_STRONG:+15")
        elif strength_pts == 10:
            reasons.append("RACE_STRENGTH_STRONG:+10")
        elif strength_pts == -5:
            reasons.append("RACE_STRENGTH_WEAK:-5")

        if lone_pts == 20:
            reasons.append("LONE_LEADER:+20")

        residual_reasons.append("; ".join(reasons) if reasons else "NO_RESIDUAL_MODIFIER")

    merged["residual_reason_v1"] = residual_reasons

    output_columns = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "rank1_horse",
        "rank1_horse_key",
        "rank1_won",
        "trust_profile_v1",
        "field_size",
        "field_size_bucket_tf_v1",
        "trust_field_score_v1",
        "trust_field_band_v1",
        "pace_advantage_band_v1",
        "race_strength_band",
        "lone_leader_bool",
        "pace_modifier_points_v1",
        "race_strength_modifier_points_v1",
        "lone_leader_modifier_points_v1",
        "residual_modifier_score_v1",
        "residual_reason_v1",
        "tf_plus_pace_score_v1",
        "tf_plus_pace_band_v1",
        "tf_plus_race_strength_score_v1",
        "tf_plus_race_strength_band_v1",
        "tf_plus_lone_leader_score_v1",
        "tf_plus_lone_leader_band_v1",
        "tf_plus_pace_race_strength_score_v1",
        "tf_plus_pace_race_strength_band_v1",
        "tf_plus_pace_lone_leader_score_v1",
        "tf_plus_pace_lone_leader_band_v1",
        "tf_plus_race_strength_lone_leader_score_v1",
        "tf_plus_race_strength_lone_leader_band_v1",
        "tf_plus_all_modifiers_score_v1",
        "tf_plus_all_modifiers_band_v1",
        "environment_score_v1",
        "environment_band_v1",
        "environment_reason_v1",
        "trust_field_win_v1",
        "environment_win_v1",
    ]
    existing_output_columns = [column for column in output_columns if column in merged.columns]
    merged[existing_output_columns].to_csv(OUT_MAIN, index=False)

    win_series = merged["trust_field_win_v1"]

    tests = [
        summarise_score_test("TRUST_FIELD_CORE", merged["trust_field_score_v1"], win_series),
        summarise_score_test("CORE_PLUS_PACE", merged["tf_plus_pace_score_v1"], win_series),
        summarise_score_test("CORE_PLUS_RACE_STRENGTH", merged["tf_plus_race_strength_score_v1"], win_series),
        summarise_score_test("CORE_PLUS_LONE_LEADER", merged["tf_plus_lone_leader_score_v1"], win_series),
        summarise_score_test("CORE_PLUS_PACE_RACE_STRENGTH", merged["tf_plus_pace_race_strength_score_v1"], win_series),
        summarise_score_test("CORE_PLUS_PACE_LONE_LEADER", merged["tf_plus_pace_lone_leader_score_v1"], win_series),
        summarise_score_test("CORE_PLUS_RACE_STRENGTH_LONE_LEADER", merged["tf_plus_race_strength_lone_leader_score_v1"], win_series),
        summarise_score_test("CORE_PLUS_ALL_MODIFIERS", merged["tf_plus_all_modifiers_score_v1"], win_series),
        summarise_band_test("ENVIRONMENT_V1_REFERENCE", merged["environment_band_v1"], merged["environment_win_v1"]),
    ]

    summary_df = pd.DataFrame(tests)
    core_lift = float(summary_df.loc[summary_df["test_id_v1"] == "TRUST_FIELD_CORE", "strong_vs_weak_lift_pts"].iloc[0])
    env_ref_lift = float(summary_df.loc[summary_df["test_id_v1"] == "ENVIRONMENT_V1_REFERENCE", "strong_vs_weak_lift_pts"].iloc[0])

    summary_df["increment_vs_trust_field_core_pts"] = summary_df["strong_vs_weak_lift_pts"].map(lambda value: round(float(value) - core_lift, 2))
    summary_df["increment_vs_environment_v1_reference_pts"] = summary_df["strong_vs_weak_lift_pts"].map(
        lambda value: round(float(value) - env_ref_lift, 2)
    )

    test_order = {
        "TRUST_FIELD_CORE": 0,
        "CORE_PLUS_PACE": 1,
        "CORE_PLUS_RACE_STRENGTH": 2,
        "CORE_PLUS_LONE_LEADER": 3,
        "CORE_PLUS_PACE_RACE_STRENGTH": 4,
        "CORE_PLUS_PACE_LONE_LEADER": 5,
        "CORE_PLUS_RACE_STRENGTH_LONE_LEADER": 6,
        "CORE_PLUS_ALL_MODIFIERS": 7,
        "ENVIRONMENT_V1_REFERENCE": 8,
    }
    summary_df["sort_order_v1"] = summary_df["test_id_v1"].map(test_order)
    summary_df = summary_df.sort_values("sort_order_v1").drop(columns=["sort_order_v1"])
    summary_df.to_csv(OUT_SUMMARY, index=False)

    individual_tests = summary_df[summary_df["test_id_v1"].isin(["CORE_PLUS_PACE", "CORE_PLUS_RACE_STRENGTH", "CORE_PLUS_LONE_LEADER"])].copy()
    best_individual = individual_tests.sort_values(
        ["increment_vs_trust_field_core_pts", "strong_vs_weak_lift_pts"],
        ascending=[False, False],
    ).iloc[0]

    combo_tests = summary_df[
        summary_df["test_id_v1"].isin(
            [
                "CORE_PLUS_PACE_RACE_STRENGTH",
                "CORE_PLUS_PACE_LONE_LEADER",
                "CORE_PLUS_RACE_STRENGTH_LONE_LEADER",
                "CORE_PLUS_ALL_MODIFIERS",
            ]
        )
    ].copy()
    best_combo = combo_tests.sort_values(
        ["increment_vs_trust_field_core_pts", "strong_vs_weak_lift_pts"],
        ascending=[False, False],
    ).iloc[0]

    best_individual_increment = float(best_individual["increment_vs_trust_field_core_pts"])
    best_combo_increment = float(best_combo["increment_vs_trust_field_core_pts"])
    environment_reference_gap = round(env_ref_lift - core_lift, 2)

    if abs(environment_reference_gap) < 1.0 and best_combo_increment < 1.0:
        verdict = "TRUST_FIELD_CORE_CAPTURES_ENVIRONMENT_V1"
        recommendation = "ENVIRONMENT_V2_EQUALS_TRUST_FIELD_CORE"
    elif best_combo_increment >= 1.0 or best_individual_increment >= 1.0:
        verdict = "SELECTED_MODIFIERS_ADD_MEANINGFUL_RESIDUAL_LIFT"
        recommendation = "ENVIRONMENT_V2_EQUALS_TRUST_FIELD_PLUS_SELECTED_MODIFIERS"
    else:
        verdict = "RESIDUAL_LIFT_MINOR"
        recommendation = "ENVIRONMENT_V2_EQUALS_TRUST_FIELD_CORE_WITH_OPTIONAL_MINOR_MODIFIERS"

    verdict_rows = [
        {"metric": "rows", "value": int(len(merged))},
        {"metric": "trust_field_core_lift_pts", "value": round(core_lift, 2)},
        {"metric": "environment_v1_reference_lift_pts", "value": round(env_ref_lift, 2)},
        {"metric": "environment_reference_gap_vs_core_pts", "value": environment_reference_gap},
        {"metric": "pace_increment_vs_core_pts", "value": float(summary_df.loc[summary_df["test_id_v1"] == "CORE_PLUS_PACE", "increment_vs_trust_field_core_pts"].iloc[0])},
        {"metric": "race_strength_increment_vs_core_pts", "value": float(summary_df.loc[summary_df["test_id_v1"] == "CORE_PLUS_RACE_STRENGTH", "increment_vs_trust_field_core_pts"].iloc[0])},
        {"metric": "lone_leader_increment_vs_core_pts", "value": float(summary_df.loc[summary_df["test_id_v1"] == "CORE_PLUS_LONE_LEADER", "increment_vs_trust_field_core_pts"].iloc[0])},
        {"metric": "all_modifiers_increment_vs_core_pts", "value": float(summary_df.loc[summary_df["test_id_v1"] == "CORE_PLUS_ALL_MODIFIERS", "increment_vs_trust_field_core_pts"].iloc[0])},
        {"metric": "best_individual_modifier_test", "value": best_individual["test_id_v1"]},
        {"metric": "best_individual_modifier_increment_pts", "value": best_individual_increment},
        {"metric": "best_modifier_combo_test", "value": best_combo["test_id_v1"]},
        {"metric": "best_modifier_combo_increment_pts", "value": best_combo_increment},
        {"metric": "verdict", "value": verdict},
        {"metric": "recommendation", "value": recommendation},
    ]
    pd.DataFrame(verdict_rows).to_csv(OUT_VERDICT, index=False)

    print("[ENVIRONMENT_RESIDUAL_AUDIT_V1] COMPLETE")
    print(f"rows={len(merged)}")
    print(f"trust_field_core_lift_pts={round(core_lift, 2)}")
    print(f"environment_v1_reference_lift_pts={round(env_ref_lift, 2)}")
    print(f"environment_reference_gap_vs_core_pts={environment_reference_gap}")
    print(f"best_individual_modifier={best_individual['test_id_v1']}")
    print(f"best_individual_increment_pts={best_individual_increment}")
    print(f"best_modifier_combo={best_combo['test_id_v1']}")
    print(f"best_modifier_combo_increment_pts={best_combo_increment}")
    print(f"verdict={verdict}")
    print(f"recommendation={recommendation}")
    print(f"wrote={OUT_MAIN}")
    print(f"wrote={OUT_SUMMARY}")
    print(f"wrote={OUT_VERDICT}")


if __name__ == "__main__":
    main()
