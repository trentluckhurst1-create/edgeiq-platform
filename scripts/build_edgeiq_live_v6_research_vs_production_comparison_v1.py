from pathlib import Path
import pandas as pd
import math

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_live_runner_board_v1.csv"
V6 = DATA / "edgeiq_current_fair_prices_v6_research_replay.csv"

OUT = DATA / "edgeiq_live_v6_research_vs_production_comparison_v1.csv"
SUMMARY = DATA / "edgeiq_live_v6_research_action_summary_v1.csv"

def num(x, default=math.nan):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return default
        return float(str(x).strip())
    except Exception:
        return default

def clean(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def action(edge, band, gap):
    if edge is None or math.isnan(edge):
        return "NO_EDGE"

    band = clean(band).upper()
    gap_num = num(gap)

    bad = {"POOR","NEGATIVE"}
    watch = {"ELITE","STRONG","POSITIVE"}
    lean = {"ELITE","STRONG","POSITIVE"}

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

    keys = ["track","race_no","horse"]

    keep = [
        "track","race_no","horse",
        "v6_research_fair_price",
        "v6_research_probability",
        "projection_gap_v6_research",
        "projection_band_v6_research",
        "v6_research_price_status",
        "v6_research_pricing_guardrail",
        "v6_research_pricing_power_used",
    ]

    v6s = v6[[c for c in keep if c in v6.columns]].drop_duplicates(keys, keep="first")

    df = live.merge(v6s, on=keys, how="left")

    rows = []
    for _, r in df.iterrows():
        live_price = num(r.get("live_price",""))
        fair = num(r.get("v6_research_fair_price",""))

        edge = math.nan
        act = "NO_MODEL"

        if not math.isnan(live_price) and not math.isnan(fair) and fair > 0:
            edge = round(((live_price / fair) - 1.0) * 100.0, 1)
            act = action(edge, r.get("projection_band_v6_research",""), r.get("projection_gap_v6_research",""))
        elif clean(r.get("v6_research_price_status","")) == "":
            act = "NO_MODEL"

        rows.append({
            "race_date": r.get("race_date",""),
            "track": r.get("track",""),
            "race_no": r.get("race_no",""),
            "horse": r.get("horse",""),
            "live_price": r.get("live_price",""),

            "production_fair_price": r.get("fair_price",""),
            "production_edge_pct": r.get("edge_pct",""),
            "production_action": r.get("execution_action",""),
            "production_band": r.get("projection_band_v5_2",""),

            "v6_research_fair_price": r.get("v6_research_fair_price",""),
            "v6_research_probability": r.get("v6_research_probability",""),
            "v6_research_edge_pct": "" if math.isnan(edge) else edge,
            "v6_research_action": act,
            "v6_research_gap": r.get("projection_gap_v6_research",""),
            "v6_research_band": r.get("projection_band_v6_research",""),
            "v6_research_status": r.get("v6_research_price_status",""),
            "v6_research_guardrail": r.get("v6_research_pricing_guardrail",""),
            "v6_research_power": r.get("v6_research_pricing_power_used",""),
        })

    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)

    summary = (
        out.groupby("v6_research_action", dropna=False)
        .size()
        .reset_index(name="Count")
        .rename(columns={"v6_research_action":"Name"})
        .sort_values("Name")
    )
    summary.to_csv(SUMMARY, index=False)

    print("[LIVE_V6_RESEARCH_VS_PRODUCTION_COMPARISON_V1] COMPLETE")
    print(summary.to_string(index=False))
    print(f"out={OUT}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()

