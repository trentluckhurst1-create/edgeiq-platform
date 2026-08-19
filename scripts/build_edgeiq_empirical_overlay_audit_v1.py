from __future__ import annotations

from pathlib import Path
import math
import re
import unicodedata

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "public" / "data"

FAIR_PATH = DATA_DIR / "edgeiq_fair_price_empirical_v1.csv"
RACECARDS_PATH = DATA_DIR / "edgeiq_tab_vic_racecards_v1.csv"
RUNNER_V6_PATH = DATA_DIR / "edgeiq_runner_score_v6.csv"

AUDIT_PATH = DATA_DIR / "edgeiq_empirical_overlay_audit_v1.csv"
SUMMARY_PATH = DATA_DIR / "edgeiq_empirical_overlay_audit_v1_summary.csv"
BY_EDGE_BAND_PATH = DATA_DIR / "edgeiq_empirical_overlay_audit_v1_by_edge_band.csv"
BY_RANK_PATH = DATA_DIR / "edgeiq_empirical_overlay_audit_v1_by_rank.csv"
CANDIDATES_PATH = DATA_DIR / "edgeiq_empirical_overlay_audit_v1_candidates.csv"

EDGE_BAND_ORDER = [
    "SCRATCHED",
    "NO_MARKET",
    "UNDERLAY",
    "0-4.99",
    "5-9.99",
    "10-14.99",
    "15-19.99",
    "20-29.99",
    "30-49.99",
    "50+",
]

RANK_BUCKET_ORDER = [
    "RANK_1",
    "RANK_2",
    "RANK_3",
    "RANK_4_5",
    "RANK_6_10",
    "RANK_11_PLUS",
    "UNKNOWN",
]


def normalize_text(value: object) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    text = str(value).strip().upper()
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.replace("&", " AND ")
    text = text.replace("@", " AT ")
    text = re.sub(r"[\'`]+", "", text)
    text = re.sub(r"[^A-Z0-9]+", "", text)
    return text


def to_float(value: object) -> float:
    if value is None:
        return float("nan")
    if isinstance(value, (int, float)):
        try:
            value = float(value)
        except Exception:
            return float("nan")
        return value if math.isfinite(value) else float("nan")
    text = str(value).strip().replace(",", "")
    if text == "":
        return float("nan")
    try:
        number = float(text)
    except Exception:
        return float("nan")
    return number if math.isfinite(number) else float("nan")


def to_int(value: object) -> float:
    number = to_float(value)
    if math.isnan(number):
        return float("nan")
    return int(number)


def choose_column(columns: list[str], preferred_names: list[str], keyword_groups: list[tuple[str, ...]] | None = None) -> str | None:
    lowered = {column.lower(): column for column in columns}
    for name in preferred_names:
        match = lowered.get(name.lower())
        if match:
            return match
    if keyword_groups:
        for keywords in keyword_groups:
            for column in columns:
                column_lower = column.lower()
                if all(keyword in column_lower for keyword in keywords):
                    return column
    return None


def build_rank_bucket(rank_value: object) -> str:
    rank_number = to_int(rank_value)
    if math.isnan(rank_number):
        return "UNKNOWN"
    if rank_number == 1:
        return "RANK_1"
    if rank_number == 2:
        return "RANK_2"
    if rank_number == 3:
        return "RANK_3"
    if 4 <= rank_number <= 5:
        return "RANK_4_5"
    if 6 <= rank_number <= 10:
        return "RANK_6_10"
    return "RANK_11_PLUS"


def build_edge_band(scratched: bool, market_price: float, fair_price: float, edge_pct: float) -> str:
    if scratched:
        return "SCRATCHED"
    if math.isnan(market_price) or market_price <= 1 or math.isnan(fair_price) or fair_price <= 1:
        return "NO_MARKET"
    if edge_pct < 0:
        return "UNDERLAY"
    if edge_pct < 5:
        return "0-4.99"
    if edge_pct < 10:
        return "5-9.99"
    if edge_pct < 15:
        return "10-14.99"
    if edge_pct < 20:
        return "15-19.99"
    if edge_pct < 30:
        return "20-29.99"
    if edge_pct < 50:
        return "30-49.99"
    return "50+"


def build_overlay_reason(status: str, market_price: float, fair_price: float, edge_pct: float) -> str:
    if status == "SCRATCHED":
        return "runner marked scratched in TAB market"
    if status == "NO_MARKET":
        return "no valid TAB fixed win market price found"
    if math.isnan(edge_pct):
        return "unable to compare market and empirical fair price"
    if edge_pct < 0:
        return f"market {market_price:.2f} is shorter than fair {fair_price:.2f} ({edge_pct:.2f}% underlay)"
    return f"market {market_price:.2f} vs fair {fair_price:.2f} ({edge_pct:.2f}% overlay)"


def confidence_safe_mean(series: pd.Series) -> float:
    return float(series.mean()) if len(series) else float("nan")


def main() -> None:
    fair_df = pd.read_csv(FAIR_PATH)
    racecards_df = pd.read_csv(RACECARDS_PATH)
    runner_v6_df = pd.read_csv(RUNNER_V6_PATH)

    fair_price_col = choose_column(
        list(fair_df.columns),
        [
            "active_fair_price_empirical_v1",
            "fair_price_empirical_v1",
            "fair_price_v6_empirical_v1",
            "fair_price_v5_empirical_v1",
            "active_fair_odds_empirical_v1",
            "fair_odds_empirical_v1",
            "fair_odds_v6_empirical_v1",
            "fair_odds_v5_empirical_v1",
            "active_fair_odds_v1",
        ],
        [("active", "fair", "empirical"), ("fair", "price", "empirical"), ("fair", "odds", "empirical")],
    )
    fair_prob_col = choose_column(
        list(fair_df.columns),
        [
            "active_fair_prob_empirical_v1",
            "fair_prob_empirical_v1",
            "fair_prob_v6_empirical_v1",
            "fair_prob_v5_empirical_v1",
            "active_blended_prob_empirical_v1",
            "blended_prob_norm_v6_empirical_v1",
            "blended_prob_norm_v5_empirical_v1",
        ],
        [("active", "prob", "empirical"), ("fair", "prob", "empirical"), ("blended", "prob", "empirical")],
    )
    market_price_col = choose_column(
        list(racecards_df.columns),
        ["tab_fixed_win", "fixed_win", "market_price", "live_price", "price"],
    )

    if fair_price_col is None:
        raise ValueError("Could not find an empirical fair-price column in edgeiq_fair_price_empirical_v1.csv")
    if market_price_col is None:
        raise ValueError("Could not find a market price column in edgeiq_tab_vic_racecards_v1.csv")

    fair_df = fair_df.copy()
    fair_df["meeting_date"] = fair_df["meeting_date"].astype(str).str[:10]
    fair_df["race_no"] = fair_df["race_no"].apply(to_int)
    fair_df["join_track"] = fair_df["track"].apply(normalize_text)
    fair_df["join_horse"] = fair_df["horse"].apply(normalize_text)
    fair_df["join_key"] = (
        fair_df["meeting_date"].astype(str)
        + "|"
        + fair_df["join_track"]
        + "|"
        + fair_df["race_no"].fillna(-1).astype(int).astype(str)
        + "|"
        + fair_df["join_horse"]
    )
    fair_df["empirical_fair_price_v1"] = fair_df[fair_price_col].apply(to_float)
    if fair_prob_col:
        fair_df["empirical_fair_prob_v1"] = fair_df[fair_prob_col].apply(to_float)
    else:
        fair_df["empirical_fair_prob_v1"] = np.nan
    fair_df["empirical_fair_prob_v1"] = np.where(
        fair_df["empirical_fair_prob_v1"].notna(),
        fair_df["empirical_fair_prob_v1"],
        np.where(
            fair_df["empirical_fair_price_v1"] > 0,
            1.0 / fair_df["empirical_fair_price_v1"],
            np.nan,
        ),
    )

    racecards_df = racecards_df.copy()
    racecards_df["meeting_date"] = racecards_df["meeting_date"].astype(str).str[:10]
    racecards_df["race_no"] = racecards_df["race_no"].apply(to_int)
    racecards_df["join_track"] = racecards_df["meeting_name"].apply(normalize_text)
    racecards_df["join_horse"] = racecards_df["horse"].apply(normalize_text)
    racecards_df["join_key"] = (
        racecards_df["meeting_date"].astype(str)
        + "|"
        + racecards_df["join_track"]
        + "|"
        + racecards_df["race_no"].fillna(-1).astype(int).astype(str)
        + "|"
        + racecards_df["join_horse"]
    )
    racecards_df["market_price_v1"] = racecards_df[market_price_col].apply(to_float)
    fixed_status = racecards_df.get("tab_fixed_betting_status", pd.Series("", index=racecards_df.index)).astype(str).str.upper()
    tote_status = racecards_df.get("tab_tote_betting_status", pd.Series("", index=racecards_df.index)).astype(str).str.upper()
    scratched_time = racecards_df.get("scratched_time", pd.Series("", index=racecards_df.index)).fillna("").astype(str).str.strip()
    racecards_df["is_scratched_v1"] = (
        scratched_time.ne("")
        | fixed_status.str.contains("SCRATCH", na=False)
        | tote_status.str.contains("SCRATCH", na=False)
    )
    if "scraped_at" in racecards_df.columns:
        racecards_df["scraped_at_sort"] = pd.to_datetime(racecards_df["scraped_at"], errors="coerce")
        racecards_df = racecards_df.sort_values(["join_key", "scraped_at_sort", "market_price_v1"], ascending=[True, True, True])
    racecards_df = racecards_df.drop_duplicates(subset=["join_key"], keep="last")
    market_lookup = racecards_df[["join_key", "market_price_v1", "is_scratched_v1"]].copy()

    runner_v6_df = runner_v6_df.copy()
    meeting_date_col = "meeting_date" if "meeting_date" in runner_v6_df.columns else "race_date"
    runner_v6_df[meeting_date_col] = runner_v6_df[meeting_date_col].astype(str).str[:10]
    runner_v6_df["race_no"] = runner_v6_df["race_no"].apply(to_int)
    runner_v6_df["join_track"] = runner_v6_df["track"].apply(normalize_text)
    runner_v6_df["join_horse"] = runner_v6_df["horse"].apply(normalize_text)
    runner_v6_df["join_key"] = (
        runner_v6_df[meeting_date_col].astype(str)
        + "|"
        + runner_v6_df["join_track"]
        + "|"
        + runner_v6_df["race_no"].fillna(-1).astype(int).astype(str)
        + "|"
        + runner_v6_df["join_horse"]
    )

    v6_score_col = choose_column(list(runner_v6_df.columns), ["runner_score_v6", "runner_score"])
    v6_rank_col = choose_column(list(runner_v6_df.columns), ["runner_rank_v6", "runner_rank"])
    governance_col = choose_column(list(runner_v6_df.columns), ["governance_band_v7_2", "governance_band_v7", "governance_band_v6", "governance_band"])

    runner_lookup = runner_v6_df[["join_key"]].copy()
    runner_lookup["runner_score_v6"] = runner_v6_df[v6_score_col].apply(to_float) if v6_score_col else np.nan
    runner_lookup["runner_rank_v6"] = runner_v6_df[v6_rank_col].apply(to_int) if v6_rank_col else np.nan
    runner_lookup["governance_band_v7_2"] = runner_v6_df[governance_col].fillna("") if governance_col else ""
    runner_lookup = runner_lookup.drop_duplicates(subset=["join_key"], keep="last")

    audit_df = fair_df[["meeting_date", "track", "race_no", "horse", "join_key", "empirical_fair_price_v1", "empirical_fair_prob_v1"]].copy()
    audit_df = audit_df.merge(runner_lookup, on="join_key", how="left")
    audit_df = audit_df.merge(market_lookup, on="join_key", how="left")

    audit_df["market_price_v1"] = audit_df["market_price_v1"].apply(to_float)
    audit_df["runner_score_v6"] = audit_df["runner_score_v6"].apply(to_float)
    audit_df["runner_rank_v6"] = audit_df["runner_rank_v6"].apply(to_int)
    audit_df["governance_band_v7_2"] = audit_df["governance_band_v7_2"].fillna("")
    audit_df["is_scratched_v1"] = audit_df["is_scratched_v1"].fillna(False).astype(bool)

    audit_df["market_prob_v1"] = np.where(
        audit_df["market_price_v1"] > 1,
        1.0 / audit_df["market_price_v1"],
        np.nan,
    )
    audit_df["edge_pct_v1"] = np.where(
        (~audit_df["is_scratched_v1"]) & (audit_df["market_price_v1"] > 1) & (audit_df["empirical_fair_price_v1"] > 1),
        ((audit_df["market_price_v1"] / audit_df["empirical_fair_price_v1"]) - 1.0) * 100.0,
        np.nan,
    )
    audit_df["market_match_status_v1"] = np.select(
        [
            audit_df["is_scratched_v1"],
            (~audit_df["is_scratched_v1"]) & (audit_df["market_price_v1"] > 1) & (audit_df["empirical_fair_price_v1"] > 1),
        ],
        ["SCRATCHED", "MATCHED"],
        default="NO_MARKET",
    )
    audit_df["edge_band_v1"] = [
        build_edge_band(scratched, market_price, fair_price, edge_pct)
        for scratched, market_price, fair_price, edge_pct in zip(
            audit_df["is_scratched_v1"],
            audit_df["market_price_v1"],
            audit_df["empirical_fair_price_v1"],
            audit_df["edge_pct_v1"],
        )
    ]
    audit_df["overlay_5_v1"] = ((audit_df["market_match_status_v1"] == "MATCHED") & (audit_df["edge_pct_v1"] >= 5)).astype(int)
    audit_df["overlay_10_v1"] = ((audit_df["market_match_status_v1"] == "MATCHED") & (audit_df["edge_pct_v1"] >= 10)).astype(int)
    audit_df["overlay_15_v1"] = ((audit_df["market_match_status_v1"] == "MATCHED") & (audit_df["edge_pct_v1"] >= 15)).astype(int)
    audit_df["overlay_20_v1"] = ((audit_df["market_match_status_v1"] == "MATCHED") & (audit_df["edge_pct_v1"] >= 20)).astype(int)
    audit_df["overlay_30_v1"] = ((audit_df["market_match_status_v1"] == "MATCHED") & (audit_df["edge_pct_v1"] >= 30)).astype(int)
    audit_df["overlay_reason_v1"] = [
        build_overlay_reason(status, market_price, fair_price, edge_pct)
        for status, market_price, fair_price, edge_pct in zip(
            audit_df["market_match_status_v1"],
            audit_df["market_price_v1"],
            audit_df["empirical_fair_price_v1"],
            audit_df["edge_pct_v1"],
        )
    ]
    audit_df["runner_rank_bucket_v1"] = audit_df["runner_rank_v6"].apply(build_rank_bucket)
    audit_df["race_key_v1"] = audit_df["meeting_date"].astype(str) + "|" + audit_df["track"].astype(str) + "|R" + audit_df["race_no"].fillna(-1).astype(int).astype(str)

    audit_df = audit_df[
        [
            "meeting_date",
            "track",
            "race_no",
            "horse",
            "runner_score_v6",
            "runner_rank_v6",
            "governance_band_v7_2",
            "empirical_fair_price_v1",
            "empirical_fair_prob_v1",
            "market_price_v1",
            "market_prob_v1",
            "edge_pct_v1",
            "edge_band_v1",
            "overlay_5_v1",
            "overlay_10_v1",
            "overlay_15_v1",
            "overlay_20_v1",
            "overlay_30_v1",
            "market_match_status_v1",
            "overlay_reason_v1",
            "runner_rank_bucket_v1",
            "race_key_v1",
        ]
    ].copy()

    valid_edge_df = audit_df[audit_df["market_match_status_v1"] == "MATCHED"].copy()
    candidates_df = audit_df[(audit_df["market_match_status_v1"] == "MATCHED") & (audit_df["edge_pct_v1"] >= 5)].copy()
    candidates_df = candidates_df.sort_values(["edge_pct_v1", "runner_rank_v6", "runner_score_v6"], ascending=[False, True, False])

    edge_band_df = (
        audit_df.groupby("edge_band_v1", dropna=False)
        .agg(
            runners=("horse", "size"),
            avg_edge=("edge_pct_v1", "mean"),
            avg_market_price=("market_price_v1", "mean"),
            avg_fair_price=("empirical_fair_price_v1", "mean"),
            avg_score=("runner_score_v6", "mean"),
            avg_rank=("runner_rank_v6", "mean"),
        )
        .reset_index()
    )
    edge_band_df["sort_order"] = edge_band_df["edge_band_v1"].map({value: index for index, value in enumerate(EDGE_BAND_ORDER, start=1)}).fillna(999)
    edge_band_df = edge_band_df.sort_values(["sort_order", "edge_band_v1"]).drop(columns=["sort_order"])

    rank_df = (
        audit_df.groupby("runner_rank_bucket_v1", dropna=False)
        .agg(
            runners=("horse", "size"),
            overlay_5_count=("overlay_5_v1", "sum"),
            overlay_10_count=("overlay_10_v1", "sum"),
            overlay_15_count=("overlay_15_v1", "sum"),
            overlay_20_count=("overlay_20_v1", "sum"),
            overlay_30_count=("overlay_30_v1", "sum"),
            avg_edge=("edge_pct_v1", "mean"),
            avg_market_price=("market_price_v1", "mean"),
            avg_fair_price=("empirical_fair_price_v1", "mean"),
            avg_score=("runner_score_v6", "mean"),
        )
        .reset_index()
        .rename(columns={"runner_rank_bucket_v1": "rank_bucket_v1"})
    )
    rank_df["sort_order"] = rank_df["rank_bucket_v1"].map({value: index for index, value in enumerate(RANK_BUCKET_ORDER, start=1)}).fillna(999)
    rank_df = rank_df.sort_values(["sort_order", "rank_bucket_v1"]).drop(columns=["sort_order"])

    if len(valid_edge_df):
        highest_overlay_row = valid_edge_df.sort_values(["edge_pct_v1", "runner_rank_v6"], ascending=[False, True]).iloc[0]
        avg_edge_value = float(valid_edge_df["edge_pct_v1"].mean())
        median_edge_value = float(valid_edge_df["edge_pct_v1"].median())
        highest_overlay_horse = str(highest_overlay_row["horse"])
        highest_edge_pct = float(highest_overlay_row["edge_pct_v1"])
    else:
        avg_edge_value = float("nan")
        median_edge_value = float("nan")
        highest_overlay_horse = ""
        highest_edge_pct = float("nan")

    summary_df = pd.DataFrame(
        {
            "metric": [
                "rows",
                "races",
                "matched_market_rows",
                "no_market_rows",
                "scratched_rows",
                "overlay_5_count",
                "overlay_10_count",
                "overlay_15_count",
                "overlay_20_count",
                "overlay_30_count",
                "avg_edge",
                "median_edge",
                "highest_overlay_horse",
                "highest_edge_pct",
            ],
            "value": [
                int(len(audit_df)),
                int(audit_df["race_key_v1"].nunique()),
                int((audit_df["market_match_status_v1"] == "MATCHED").sum()),
                int((audit_df["market_match_status_v1"] == "NO_MARKET").sum()),
                int((audit_df["market_match_status_v1"] == "SCRATCHED").sum()),
                int(audit_df["overlay_5_v1"].sum()),
                int(audit_df["overlay_10_v1"].sum()),
                int(audit_df["overlay_15_v1"].sum()),
                int(audit_df["overlay_20_v1"].sum()),
                int(audit_df["overlay_30_v1"].sum()),
                avg_edge_value,
                median_edge_value,
                highest_overlay_horse,
                highest_edge_pct,
            ],
        }
    )

    audit_df.to_csv(AUDIT_PATH, index=False)
    summary_df.to_csv(SUMMARY_PATH, index=False)
    edge_band_df.to_csv(BY_EDGE_BAND_PATH, index=False)
    rank_df.to_csv(BY_RANK_PATH, index=False)
    candidates_df.to_csv(CANDIDATES_PATH, index=False)

    print("[EDGEIQ_EMPIRICAL_OVERLAY_AUDIT_V1] COMPLETE")
    print(f"rows={len(audit_df)}")
    print(f"races={audit_df['race_key_v1'].nunique()}")
    print(f"matched_market_rows={(audit_df['market_match_status_v1'] == 'MATCHED').sum()}")
    print(f"overlay_5_count={int(audit_df['overlay_5_v1'].sum())}")
    print(f"overlay_10_count={int(audit_df['overlay_10_v1'].sum())}")
    print(f"overlay_15_count={int(audit_df['overlay_15_v1'].sum())}")
    print(f"overlay_20_count={int(audit_df['overlay_20_v1'].sum())}")
    print(f"overlay_30_count={int(audit_df['overlay_30_v1'].sum())}")
    print(f"fair_price_column={fair_price_col}")
    print(f"fair_prob_column={fair_prob_col or 'derived_from_price'}")
    print(f"market_price_column={market_price_col}")
    print(f"audit_out={AUDIT_PATH}")
    print(f"summary_out={SUMMARY_PATH}")
    print(f"by_edge_band_out={BY_EDGE_BAND_PATH}")
    print(f"by_rank_out={BY_RANK_PATH}")
    print(f"candidates_out={CANDIDATES_PATH}")


if __name__ == "__main__":
    main()
