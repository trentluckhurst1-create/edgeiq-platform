from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
DNA = DATA / "edgeiq_live_runner_dna_v6_2.csv"
DRAWER = DATA / "edgeiq_runner_dna_drawer_feed_v2.csv"
SCORECARD = DATA / "edgeiq_live_runner_factor_scorecard_v2.csv"

AUDIT_OUT = DATA / "edgeiq_live_dna_quality_audit_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_live_dna_quality_summary_v1.csv"

TRUTHY = {"1", "TRUE", "YES", "Y"}
EXPECTED_FACTORS = {"FORM", "RATING", "PACE", "DISTANCE", "CONDITION", "CLASS", "SECTIONALS", "PROFILE", "TRAINER", "JOCKEY", "COMBO"}


def safe_text(value: object) -> str:
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return str(value).strip()


def clean_track(value: object) -> str:
    text = safe_text(value).upper()
    text = text.replace("SPORTSBET-", "SPORTSBET ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_horse(value: object) -> str:
    text = safe_text(value).upper()
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"[^A-Z0-9]+", "", text)
    return text


def build_key(frame: pd.DataFrame) -> pd.Series:
    horse_key = frame.get("horse_key", pd.Series("", index=frame.index)).map(clean_horse)
    horse = frame.get("horse", pd.Series("", index=frame.index)).map(clean_horse)
    final_horse = horse_key.where(horse_key != "", horse)
    return (
        frame.get("race_date", pd.Series("", index=frame.index)).map(safe_text).str[:10]
        + "|"
        + frame.get("track", pd.Series("", index=frame.index)).map(clean_track)
        + "|"
        + frame.get("race_no", pd.Series("", index=frame.index)).map(safe_text)
        + "|"
        + final_horse
    )


def truthy(value: object) -> bool:
    return safe_text(value).upper() in TRUTHY


def load_active_universe() -> pd.DataFrame:
    frame = pd.read_csv(LIVE_BOARD, dtype=str, keep_default_na=False, low_memory=False)
    if "runner_status" in frame.columns:
        frame = frame[frame["runner_status"].astype(str).str.upper().ne("SCRATCHED")].copy()
    if "is_scratched" in frame.columns:
        frame = frame[~frame["is_scratched"].map(truthy)].copy()
    frame["refresh_key"] = build_key(frame)
    return frame


def load_unique(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)
    frame["refresh_key"] = build_key(frame)
    return frame


def main() -> None:
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    active = load_active_universe()
    active_keys = set(active["refresh_key"])

    if not DNA.exists() or not DRAWER.exists() or not SCORECARD.exists():
        missing = [path.name for path in [DNA, DRAWER, SCORECARD] if not path.exists()]
        raise FileNotFoundError(f"Missing DNA quality inputs: {missing}")

    dna = load_unique(DNA)
    drawer = load_unique(DRAWER)
    scorecard = pd.read_csv(SCORECARD, dtype=str, keep_default_na=False, low_memory=False)
    scorecard["refresh_key"] = build_key(scorecard)

    dna_unique = dna.drop_duplicates(subset=["refresh_key"], keep="first")
    drawer_unique = drawer.drop_duplicates(subset=["refresh_key"], keep="first")

    dna_matched = dna_unique[dna_unique["refresh_key"].isin(active_keys)].copy()
    drawer_matched = drawer_unique[drawer_unique["refresh_key"].isin(active_keys)].copy()
    scorecard_matched = scorecard[scorecard["refresh_key"].isin(active_keys)].copy()

    factor_coverage = (
        scorecard_matched.groupby("refresh_key")["factor"]
        .agg(lambda values: "|".join(sorted({safe_text(value).upper() for value in values if safe_text(value) != ""})))
        .reset_index(name="factor_set")
    )
    factor_coverage["factor_count"] = factor_coverage["factor_set"].map(lambda text: len([item for item in text.split("|") if item]))
    factor_coverage["all_expected_factors"] = factor_coverage["factor_set"].map(
        lambda text: "YES" if set([item for item in text.split("|") if item]) >= EXPECTED_FACTORS else "NO"
    )

    active_with_metrics = active[["refresh_key", "race_date", "track", "race_no", "horse", "horse_key"]].copy()
    active_with_metrics = active_with_metrics.merge(
        dna_matched[["refresh_key", "dna_v6_2_score", "dna_v6_2_band", "runner_dna_v6_2_narrative"]] if "runner_dna_v6_2_narrative" in dna_matched.columns else dna_matched[["refresh_key", "dna_v6_2_score", "dna_v6_2_band"]],
        on="refresh_key",
        how="left",
    )
    active_with_metrics = active_with_metrics.merge(
        drawer_matched[["refresh_key", "positive_1_factor", "negative_1_factor", "runner_dna_v6_2_narrative"]] if "runner_dna_v6_2_narrative" in drawer_matched.columns else drawer_matched[["refresh_key", "positive_1_factor", "negative_1_factor"]],
        on="refresh_key",
        how="left",
        suffixes=("", "_drawer"),
    )
    active_with_metrics = active_with_metrics.merge(
        factor_coverage[["refresh_key", "factor_set", "factor_count", "all_expected_factors"]],
        on="refresh_key",
        how="left",
    )
    active_with_metrics["dna_score_present"] = active_with_metrics.get("dna_v6_2_score", pd.Series("", index=active_with_metrics.index)).astype(str).str.strip().ne("")
    active_with_metrics["narrative_present"] = (
        active_with_metrics.get("runner_dna_v6_2_narrative", pd.Series("", index=active_with_metrics.index)).astype(str).str.strip().ne("")
        | active_with_metrics.get("runner_dna_v6_2_narrative_drawer", pd.Series("", index=active_with_metrics.index)).astype(str).str.strip().ne("")
    )
    active_with_metrics["factor_breakdown_present"] = active_with_metrics.get("factor_count", pd.Series(0, index=active_with_metrics.index)).fillna(0).astype(int) > 0

    bendigo_r6 = active_with_metrics[
        (active_with_metrics["race_date"].astype(str) == "2026-06-25")
        & (active_with_metrics["track"].astype(str).str.upper() == "BENDIGO")
        & (active_with_metrics["race_no"].astype(str) == "6")
    ].copy()

    detail_rows = [
        {
            "section": "DNA_FILE",
            "metric": "active_matches",
            "value": len(dna_matched),
            "extra": "",
            "built_at": built_at,
        },
        {
            "section": "DRAWER_FILE",
            "metric": "active_matches",
            "value": len(drawer_matched),
            "extra": "",
            "built_at": built_at,
        },
        {
            "section": "SCORECARD_FILE",
            "metric": "active_matches",
            "value": scorecard_matched["refresh_key"].nunique(),
            "extra": "",
            "built_at": built_at,
        },
    ]

    missing_detail = active_with_metrics[
        (~active_with_metrics["dna_score_present"])
        | (~active_with_metrics["factor_breakdown_present"])
        | (~active_with_metrics["narrative_present"])
    ].copy()
    for _, row in missing_detail.head(50).iterrows():
        detail_rows.append(
            {
                "section": "MISSING_RUNNER_DETAIL",
                "metric": f'{row["race_date"]} {row["track"]} R{row["race_no"]}',
                "value": row["horse"],
                "extra": f'dna_score_present={row["dna_score_present"]}; narrative_present={row["narrative_present"]}; factor_count={row.get("factor_count", "")}',
                "built_at": built_at,
            }
        )

    detail = pd.DataFrame(detail_rows)
    detail.to_csv(AUDIT_OUT, index=False)

    duplicates_dna = int(dna["refresh_key"].duplicated().sum())
    duplicates_drawer = int(drawer["refresh_key"].duplicated().sum())
    duplicates_scorecard = int(scorecard.duplicated(subset=["refresh_key", "factor"]).sum()) if "factor" in scorecard.columns else 0

    coverage_over_300 = len(dna_matched) > 300 and len(drawer_matched) > 300 and scorecard_matched["refresh_key"].nunique() > 300
    bendigo_ready = len(bendigo_r6) == 17 and bendigo_r6["dna_score_present"].sum() == 17
    no_duplicates = duplicates_dna == 0 and duplicates_drawer == 0 and duplicates_scorecard == 0
    ready = coverage_over_300 and bendigo_ready and no_duplicates

    summary_rows = [
        {"metric": "status", "value": "EDGEIQ_LIVE_DNA_QUALITY_AUDIT_V1_BUILT"},
        {"metric": "active_runner_rows", "value": len(active)},
        {"metric": "dna_active_matches", "value": len(dna_matched)},
        {"metric": "drawer_active_matches", "value": len(drawer_matched)},
        {"metric": "scorecard_active_matches", "value": scorecard_matched["refresh_key"].nunique()},
        {"metric": "dna_duplicates", "value": duplicates_dna},
        {"metric": "drawer_duplicates", "value": duplicates_drawer},
        {"metric": "scorecard_duplicates", "value": duplicates_scorecard},
        {"metric": "missing_dna_scores", "value": int((~active_with_metrics["dna_score_present"]).sum())},
        {"metric": "missing_narratives", "value": int((~active_with_metrics["narrative_present"]).sum())},
        {"metric": "missing_factor_breakdown", "value": int((~active_with_metrics["factor_breakdown_present"]).sum())},
        {"metric": "bendigo_r6_rows", "value": len(bendigo_r6)},
        {"metric": "bendigo_r6_dna_present", "value": int(bendigo_r6["dna_score_present"].sum())},
        {"metric": "bendigo_r6_narrative_present", "value": int(bendigo_r6["narrative_present"].sum())},
        {"metric": "bendigo_r6_factor_breakdown_present", "value": int(bendigo_r6["factor_breakdown_present"].sum())},
        {"metric": "verdict", "value": "READY_FOR_UI" if ready else "NOT_READY"},
        {"metric": "coverage_target_met", "value": "YES" if coverage_over_300 else "NO"},
        {"metric": "bendigo_r6_target_met", "value": "YES" if bendigo_ready else "NO"},
        {"metric": "built_at", "value": built_at},
    ]
    pd.DataFrame(summary_rows).to_csv(SUMMARY_OUT, index=False)

    print("[EDGEIQ_LIVE_DNA_QUALITY_AUDIT_V1] COMPLETE")
    print(active_with_metrics.head(25).to_string(index=False))
    print()
    print(pd.DataFrame(summary_rows).to_string(index=False))
    print(f"audit={AUDIT_OUT}")
    print(f"summary={SUMMARY_OUT}")


if __name__ == "__main__":
    main()
