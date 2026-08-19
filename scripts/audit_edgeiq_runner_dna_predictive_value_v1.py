from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PRIMARY = DATA / "edgeiq_runner_dna_v6_3_historical_replay_v1.csv"
SETTLED = DATA / "edgeiq_historical_replay_settled_v1.csv"
V61 = DATA / "edgeiq_v6_1_settled_gap_replay_v2_expanded.csv"

OUT = DATA / "edgeiq_runner_dna_predictive_value_v1.csv"
BY_BAND = DATA / "edgeiq_runner_dna_predictive_value_v1_by_band.csv"
SUMMARY = DATA / "edgeiq_runner_dna_predictive_value_v1_summary.csv"


V62_BAND_ORDER = {
    "ELITE": 1,
    "STRONG": 2,
    "POSITIVE": 3,
    "NEUTRAL": 4,
    "NEGATIVE": 5,
    "POOR": 6,
    "NO_PROFILE": 7,
}

POPULATION_ORDER = {
    "ALL_RUNNERS": 1,
    "DNA_RANK1": 2,
    "V6_1_PROJECTION_RANK1_MATCHED": 3,
}


def num(value) -> float:
    try:
        text = str(value).replace("$", "").replace("%", "").strip()
        if text == "" or text.lower() == "nan":
            return np.nan
        return float(text)
    except Exception:
        return np.nan


def canon_text(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).upper().strip()
    return "".join(ch for ch in text if ch.isalnum())


def band_v62(score: float) -> str:
    if pd.isna(score):
        return "NO_PROFILE"
    if score >= 85:
        return "ELITE"
    if score >= 72:
        return "STRONG"
    if score >= 58:
        return "POSITIVE"
    if score >= 45:
        return "NEUTRAL"
    if score >= 30:
        return "NEGATIVE"
    return "POOR"


def to_race_no(value) -> str:
    try:
        n = int(float(str(value).strip()))
        return str(n)
    except Exception:
        return str(value).strip()


def empirical_fair(win_rate_pct: float):
    if pd.isna(win_rate_pct) or win_rate_pct <= 0:
        return ""
    return round(100.0 / win_rate_pct, 2)


def bucket_rank(value: float) -> str:
    if pd.isna(value):
        return "UNKNOWN"
    value = float(value)
    if value == 1:
        return "RANK_1"
    if value == 2:
        return "RANK_2"
    if value == 3:
        return "RANK_3"
    if value <= 6:
        return "RANK_4_6"
    return "RANK_7_PLUS"


def aggregate_by_band(frame: pd.DataFrame, population: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if frame.empty:
        return rows

    for dna_band, group in frame.groupby("dna_band_v62", dropna=False):
        win_pct = group["won"].mean() * 100
        place_pct = group["placed"].mean() * 100
        rows.append(
            {
                "population": population,
                "dna_band_v62": dna_band,
                "rows": len(group),
                "races": group["race_key"].nunique(),
                "wins": int(group["won"].sum()),
                "places": int(group["placed"].sum()),
                "win_pct": round(win_pct, 3),
                "place_pct": round(place_pct, 3),
                "empirical_fair_price": empirical_fair(win_pct),
                "avg_dna_score": round(group["dna_score_proxy"].mean(), 3),
                "avg_projection_gap_v61": round(group["projection_gap_V6_1_RESEARCH"].mean(), 3)
                if group["projection_gap_V6_1_RESEARCH"].notna().any()
                else "",
                "avg_projection_rank_v61": round(group["projection_rank_v61"].mean(), 3)
                if group["projection_rank_v61"].notna().any()
                else "",
                "projection_overlap_rows": int(group["projection_gap_V6_1_RESEARCH"].notna().sum()),
            }
        )
    return rows


def ensure_race_key(frame: pd.DataFrame) -> pd.Series:
    existing = frame.get("race_key", pd.Series("", index=frame.index)).astype(str).str.strip()
    derived = (
        frame["meeting_date"].astype(str).str.strip()
        + "|"
        + frame["track"].astype(str).str.strip()
        + "|R"
        + frame["race_no"].astype(str).str.strip()
    )
    return existing.where(existing != "", derived)


def main() -> None:
    if not PRIMARY.exists():
        raise SystemExit(f"Missing historical DNA replay source: {PRIMARY}")

    hist = pd.read_csv(PRIMARY, low_memory=False)
    settled = pd.read_csv(SETTLED, low_memory=False) if SETTLED.exists() else pd.DataFrame()
    v61 = pd.read_csv(V61, low_memory=False) if V61.exists() else pd.DataFrame()

    hist = hist.copy()
    hist["meeting_date"] = hist.get("meeting_date", hist.get("race_date", "")).astype(str).str.strip()
    hist["track"] = hist["track"].astype(str).str.strip()
    hist["race_no"] = hist["race_no"].astype(str).map(to_race_no)
    hist["horse_key"] = hist.get("horse_key", hist.get("horse", "")).map(canon_text)
    hist["race_key"] = ensure_race_key(hist)
    hist["dna_score_proxy"] = hist["current_score"].apply(num)
    hist["dna_band_v62"] = hist["dna_score_proxy"].apply(band_v62)
    hist["won"] = hist["won"].apply(num).fillna(0).astype(int)
    hist["placed"] = hist["placed"].apply(num).fillna(0).astype(int)
    hist["finish_position"] = hist["finish_position"].apply(num)
    hist["dna_rank"] = hist["current_rank"].apply(num)
    hist["v6_3_research_score"] = hist.get("v6_3_research_score", np.nan).apply(num) if "v6_3_research_score" in hist.columns else np.nan
    hist["v6_3_rank"] = hist.get("v6_3_rank", np.nan).apply(num) if "v6_3_rank" in hist.columns else np.nan
    hist["canon_track"] = hist["track"].map(canon_text)
    hist["join_key"] = hist["meeting_date"] + "|" + hist["canon_track"] + "|" + hist["race_no"] + "|" + hist["horse_key"]

    if not settled.empty:
        settled = settled.copy()
        settled["meeting_date"] = settled.get("meeting_date", settled.get("race_date", "")).astype(str).str.strip()
        settled["track"] = settled["track"].astype(str).str.strip()
        settled["race_no"] = settled["race_no"].astype(str).map(to_race_no)
        settled["horse_key"] = settled.get("horse_key", settled.get("horse", "")).map(canon_text)
        settled["canon_track"] = settled["track"].map(canon_text)
        settled["join_key"] = settled["meeting_date"] + "|" + settled["canon_track"] + "|" + settled["race_no"] + "|" + settled["horse_key"]
        keep = [
            col
            for col in ["join_key", "runner_score", "projected_rating_v5_2", "won", "finish_position"]
            if col in settled.columns
        ]
        settled = settled[keep].drop_duplicates(subset=["join_key"], keep="first")

    if not v61.empty:
        v61 = v61.copy()
        v61["meeting_date"] = v61.get("meeting_date", v61.get("race_date", "")).astype(str).str.strip()
        v61["track"] = v61["track"].astype(str).str.strip()
        v61["race_no"] = v61["race_no"].astype(str).map(to_race_no)
        v61["horse_key"] = v61.get("horse_key", v61.get("horse", "")).map(canon_text)
        v61["canon_track"] = v61["track"].map(canon_text)
        v61["join_key"] = v61["meeting_date"] + "|" + v61["canon_track"] + "|" + v61["race_no"] + "|" + v61["horse_key"]
        keep = [
            col
            for col in [
                "join_key",
                "projection_gap_V6_1_RESEARCH",
                "projected_rating_V6_1_RESEARCH",
                "projection_band_V6_1_RESEARCH",
                "V6_1_RESEARCH_probability",
                "V6_1_RESEARCH_fair_price",
                "V6_1_RESEARCH_price_rank",
                "source_match_status",
            ]
            if col in v61.columns
        ]
        v61 = v61[keep].drop_duplicates(subset=["join_key"], keep="first")
        for col in [
            "projection_gap_V6_1_RESEARCH",
            "projected_rating_V6_1_RESEARCH",
            "V6_1_RESEARCH_probability",
            "V6_1_RESEARCH_fair_price",
            "V6_1_RESEARCH_price_rank",
        ]:
            if col in v61.columns:
                v61[col] = v61[col].apply(num)

    detail = hist.copy()
    if not settled.empty:
        detail = detail.merge(
            settled.rename(
                columns={
                    "runner_score": "settled_runner_score",
                    "projected_rating_v5_2": "settled_projected_rating_v5_2",
                    "won": "settled_won",
                    "finish_position": "settled_finish_position",
                }
            ),
            on="join_key",
            how="left",
        )

    if not v61.empty:
        detail = detail.merge(v61, on="join_key", how="left")

    detail["race_key"] = ensure_race_key(detail)
    detail["projection_rank_v61"] = detail.get("V6_1_RESEARCH_price_rank", np.nan)
    detail["projection_rank_bucket_v61"] = detail["projection_rank_v61"].apply(bucket_rank)
    detail["projection_gap_overlap_flag"] = np.where(detail["projection_gap_V6_1_RESEARCH"].notna(), "YES", "NO")
    detail["source_variant"] = "CURRENT_SCORE_PROXY_REBANDED_TO_V6_2"
    detail["historical_source_note"] = (
        "Direct settled V6.2 DNA replay not found. Using current_score from edgeiq_runner_dna_v6_3_historical_replay_v1.csv as the closest historical DNA proxy, then remapping to V6.2 band thresholds."
    )
    detail["projection_overlap_flag"] = np.where(detail["projection_gap_V6_1_RESEARCH"].notna(), "MATCHED_V6_1", "NO_V6_1_MATCH")

    output_cols = [
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "horse",
        "horse_key",
        "won",
        "placed",
        "finish_position",
        "dna_score_proxy",
        "dna_band_v62",
        "dna_rank",
        "current_band",
        "v6_3_research_score",
        "v6_3_research_band",
        "projection_gap_V6_1_RESEARCH",
        "projected_rating_V6_1_RESEARCH",
        "projection_band_V6_1_RESEARCH",
        "V6_1_RESEARCH_probability",
        "V6_1_RESEARCH_fair_price",
        "projection_rank_v61",
        "projection_rank_bucket_v61",
        "projection_gap_overlap_flag",
        "projection_overlap_flag",
        "source_match_status",
        "source_variant",
        "historical_source_note",
    ]
    output_cols = [col for col in output_cols if col in detail.columns]
    detail[output_cols].to_csv(OUT, index=False)

    by_band_rows: list[dict[str, object]] = []
    by_band_rows.extend(aggregate_by_band(detail, "ALL_RUNNERS"))
    by_band_rows.extend(aggregate_by_band(detail[detail["dna_rank"] == 1], "DNA_RANK1"))
    if "projection_rank_v61" in detail.columns:
        by_band_rows.extend(
            aggregate_by_band(
                detail[(detail["projection_rank_v61"] == 1) & detail["projection_gap_V6_1_RESEARCH"].notna()],
                "V6_1_PROJECTION_RANK1_MATCHED",
            )
        )

    by_band_df = pd.DataFrame(by_band_rows)
    if not by_band_df.empty:
        by_band_df["_population_order"] = by_band_df["population"].map(POPULATION_ORDER).fillna(99)
        by_band_df["_band_order"] = by_band_df["dna_band_v62"].map(V62_BAND_ORDER).fillna(99)
        by_band_df = by_band_df.sort_values(["_population_order", "_band_order"]).drop(columns=["_population_order", "_band_order"])
    by_band_df.to_csv(BY_BAND, index=False)

    score_corr_win = detail["dna_score_proxy"].corr(detail["won"]) if detail["dna_score_proxy"].notna().sum() > 1 else np.nan
    score_corr_place = detail["dna_score_proxy"].corr(detail["placed"]) if detail["dna_score_proxy"].notna().sum() > 1 else np.nan

    matched = detail[detail["projection_gap_V6_1_RESEARCH"].notna()].copy()
    dna_gap_corr = matched["dna_score_proxy"].corr(matched["projection_gap_V6_1_RESEARCH"]) if len(matched) > 1 else np.nan

    proj_rank1 = matched[matched["projection_rank_v61"] == 1].copy()
    strong_mask = proj_rank1["dna_band_v62"].isin(["ELITE", "STRONG", "POSITIVE"])
    weak_mask = proj_rank1["dna_band_v62"].isin(["NEGATIVE", "POOR"])
    strong_rows = int(strong_mask.sum())
    weak_rows = int(weak_mask.sum())
    strong_win_pct = round(proj_rank1.loc[strong_mask, "won"].mean() * 100, 3) if strong_rows else np.nan
    weak_win_pct = round(proj_rank1.loc[weak_mask, "won"].mean() * 100, 3) if weak_rows else np.nan
    strong_vs_weak_lift = round(strong_win_pct - weak_win_pct, 3) if strong_rows and weak_rows else np.nan

    if strong_rows >= 25 and weak_rows >= 25:
        adds_signal = "YES" if strong_vs_weak_lift >= 2 else "NO"
    else:
        adds_signal = "INCONCLUSIVE"

    summary_rows = [
        {"metric": "status", "value": "EDGEIQ_RUNNER_DNA_PREDICTIVE_VALUE_AUDITED_V1"},
        {"metric": "historical_source_used", "value": PRIMARY.name},
        {"metric": "direct_v6_2_settled_source_found", "value": "NO"},
        {"metric": "dna_score_variant_used", "value": "current_score_rebanded_to_v6_2_thresholds"},
        {"metric": "rows", "value": len(detail)},
        {"metric": "races", "value": detail["race_key"].nunique()},
        {"metric": "missing_dna_rate_pct", "value": round(detail["dna_score_proxy"].isna().mean() * 100, 3)},
        {"metric": "win_correlation", "value": round(float(score_corr_win), 6) if pd.notna(score_corr_win) else ""},
        {"metric": "place_correlation", "value": round(float(score_corr_place), 6) if pd.notna(score_corr_place) else ""},
        {"metric": "projection_gap_overlap_rows", "value": len(matched)},
        {"metric": "projection_gap_overlap_pct", "value": round(len(matched) / len(detail) * 100, 3) if len(detail) else 0},
        {"metric": "dna_projection_gap_correlation", "value": round(float(dna_gap_corr), 6) if pd.notna(dna_gap_corr) else ""},
        {"metric": "dna_rank1_rows", "value": int((detail["dna_rank"] == 1).sum())},
        {"metric": "dna_rank1_win_pct", "value": round(detail.loc[detail["dna_rank"] == 1, "won"].mean() * 100, 3)},
        {"metric": "dna_rank1_place_pct", "value": round(detail.loc[detail["dna_rank"] == 1, "placed"].mean() * 100, 3)},
        {"metric": "projection_rank1_strong_rows", "value": strong_rows},
        {"metric": "projection_rank1_weak_rows", "value": weak_rows},
        {"metric": "projection_rank1_strong_win_pct", "value": strong_win_pct if pd.notna(strong_win_pct) else ""},
        {"metric": "projection_rank1_weak_win_pct", "value": weak_win_pct if pd.notna(weak_win_pct) else ""},
        {"metric": "projection_rank1_dna_lift_pts", "value": strong_vs_weak_lift if pd.notna(strong_vs_weak_lift) else ""},
        {"metric": "dna_adds_signal_beyond_projection_rank", "value": adds_signal},
        {"metric": "warning", "value": "Direct historical V6.2 settled DNA source was not found; results rely on a current_score proxy from edgeiq_runner_dna_v6_3_historical_replay_v1.csv."},
    ]

    pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)

    print("[RUNNER_DNA_PREDICTIVE_VALUE_V1] COMPLETE")
    print(pd.DataFrame(summary_rows).to_string(index=False))
    print(f"wrote={OUT}")
    print(f"wrote={BY_BAND}")
    print(f"wrote={SUMMARY}")


if __name__ == "__main__":
    main()