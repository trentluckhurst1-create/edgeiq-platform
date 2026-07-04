from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_live_terminal_feed_v1_TAB_ONLY_TODAY.csv"
V6 = DATA / "edgeiq_current_fair_prices_V6_1_RESEARCH_replay.csv"

OUT = DATA / "edgeiq_live_v6_1_research_vs_production_comparison_v1_TAB_ONLY_TODAY.csv"
SUMMARY = DATA / "edgeiq_live_v6_1_research_action_summary_v1_TAB_ONLY_TODAY.csv"


def num(value, default=math.nan):
    try:
        if pd.isna(value) or str(value).strip() == "":
            return default
        return float(str(value).strip())
    except Exception:
        return default


def clean(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def norm_track(value: object) -> str:
    text = clean(value).upper()
    if "PAKENHAM" in text and "SYN" in text:
        return "PAKENHAM SYNTHETIC"
    if text == "PAKENHAM":
        return "PAKENHAM SYNTHETIC"
    return re.sub(r"\s+", " ", text)


def horse_key(value: object) -> str:
    text = clean(value).upper()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"\b(NZ|GB|IRE|USA|FR|JPN|SAF|GER|CAN)\b", " ", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def action(edge, band, gap):
    if edge is None or math.isnan(edge):
        return "NO_EDGE"

    band = clean(band).upper()
    gap_num = num(gap)
    bad = {"POOR", "NEGATIVE"}
    watch = {"ELITE", "STRONG", "POSITIVE"}
    lean = {"ELITE", "STRONG", "POSITIVE"}

    if band in bad:
        return "PASS"
    if edge >= 18 and band in watch and not math.isnan(gap_num) and gap_num >= 2:
        return "WATCH"
    if edge >= 25 and band == "NEUTRAL":
        return "LEAN"
    if edge >= 10 and band in lean and not math.isnan(gap_num) and gap_num >= 2:
        return "LEAN"
    if edge <= -18:
        return "UNDERLAY"
    return "PASS"


def main():
    live = pd.read_csv(LIVE, dtype=str, keep_default_na=False, low_memory=False)
    v6 = pd.read_csv(V6, dtype=str, keep_default_na=False, low_memory=False)

    live["race_date_key"] = live["race_date"].map(clean).str[:10]
    live["track_key"] = live["track"].map(norm_track)
    live["race_no_key"] = live["race_no"].map(clean)
    live["horse_key_join"] = live["horse_key"].map(clean)
    live.loc[live["horse_key_join"] == "", "horse_key_join"] = live.loc[live["horse_key_join"] == "", "horse"].map(horse_key)

    v6["race_date_key"] = v6["race_date"].map(clean).str[:10]
    v6["track_key"] = v6["track"].map(norm_track)
    v6["race_no_key"] = v6["race_no"].map(clean)
    v6["horse_key_join"] = v6["horse_key"].map(clean)
    v6.loc[v6["horse_key_join"] == "", "horse_key_join"] = v6.loc[v6["horse_key_join"] == "", "horse"].map(horse_key)

    keep = [
        "race_date_key",
        "track_key",
        "race_no_key",
        "horse_key_join",
        "V6_1_RESEARCH_fair_price",
        "V6_1_RESEARCH_probability",
        "projection_gap_V6_1_RESEARCH",
        "projection_band_V6_1_RESEARCH",
        "V6_1_RESEARCH_price_status",
        "V6_1_RESEARCH_pricing_guardrail",
        "V6_1_RESEARCH_pricing_power_used",
    ]
    v6s = v6[[c for c in keep if c in v6.columns]].drop_duplicates(
        ["race_date_key", "track_key", "race_no_key", "horse_key_join"],
        keep="first",
    )

    df = live.merge(
        v6s,
        on=["race_date_key", "track_key", "race_no_key", "horse_key_join"],
        how="left",
    )

    rows = []
    for _, r in df.iterrows():
        live_price = num(r.get("live_price", ""))
        fair = num(r.get("V6_1_RESEARCH_fair_price", ""))

        edge = math.nan
        act = "NO_RESEARCH_PRICE"

        if not math.isnan(live_price) and not math.isnan(fair) and fair > 0:
            edge = round(((live_price / fair) - 1.0) * 100.0, 1)
            act = action(edge, r.get("projection_band_V6_1_RESEARCH", ""), r.get("projection_gap_V6_1_RESEARCH", ""))
        elif clean(r.get("V6_1_RESEARCH_price_status", "")) == "":
            act = "NO_RESEARCH_PRICE"

        rows.append(
            {
                "race_date": r.get("race_date", ""),
                "track": r.get("track", ""),
                "race_no": r.get("race_no", ""),
                "horse": r.get("horse", ""),
                "live_price": r.get("live_price", ""),
                "production_fair_price": r.get("fair_price", "") or r.get("ui_fair_price", "") or r.get("rated_price", ""),
                "production_edge_pct": r.get("edge_pct", ""),
                "production_action": r.get("execution_action", ""),
                "production_band": r.get("projection_band_v5_2", ""),
                "V6_1_RESEARCH_fair_price": r.get("V6_1_RESEARCH_fair_price", ""),
                "V6_1_RESEARCH_probability": r.get("V6_1_RESEARCH_probability", ""),
                "v6_1_research_edge_pct": "" if math.isnan(edge) else edge,
                "v6_1_research_action": act,
                "v6_1_research_gap": r.get("projection_gap_V6_1_RESEARCH", ""),
                "v6_1_research_band": r.get("projection_band_V6_1_RESEARCH", ""),
                "v6_1_research_status": r.get("V6_1_RESEARCH_price_status", ""),
                "v6_1_research_guardrail": r.get("V6_1_RESEARCH_pricing_guardrail", ""),
                "v6_1_research_power": r.get("V6_1_RESEARCH_pricing_power_used", ""),
            }
        )

    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)

    summary = (
        out.groupby("v6_1_research_action", dropna=False)
        .size()
        .reset_index(name="Count")
        .rename(columns={"v6_1_research_action": "Name"})
        .sort_values("Name")
    )
    summary.to_csv(SUMMARY, index=False)

    print("[LIVE_V6_1_RESEARCH_VS_PRODUCTION_COMPARISON_V1] COMPLETE")
    print(summary.to_string(index=False))
    print(f"out={OUT}")
    print(f"summary={SUMMARY}")


if __name__ == "__main__":
    main()
