from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

PRICE_TRUTH = DATA / "edgeiq_price_truth_v1.csv"
FAIR_REVIEW = DATA / "edgeiq_current_fair_prices_review_v5_2.csv"

OUT = DATA / "edgeiq_no_history_governance_v1.csv"
SUMMARY = DATA / "edgeiq_no_history_governance_v1_summary.csv"

def num(x):
    return pd.to_numeric(x, errors="coerce")

def classify(row):
    status = str(row.get("rated_price_status_v5_2_review", "")).strip()
    band = str(row.get("projection_band_v5_2", "")).strip()
    live = row.get("market_price_num", np.nan)
    fair = row.get("official_fair_price_num", np.nan)

    if status != "BASELINE_NO_HISTORY":
        return "HAS_HISTORY"

    if pd.isna(live) or live <= 0:
        return "NO_HISTORY_NO_LIVE"

    if band == "NO_PROJECTION" and pd.notna(fair) and fair >= 400:
        if live <= 10:
            return "NO_HISTORY_MARKET_CONFLICT_SHORT"
        if live <= 26:
            return "NO_HISTORY_MARKET_CONFLICT_MID"
        return "NO_HISTORY_LONGSHOT"

    return "NO_HISTORY_REVIEW"

def comment(row):
    g = row["no_history_governance_band"]
    live = row.get("market_price_num", np.nan)

    if g == "HAS_HISTORY":
        return "Runner has rated history; no no-history governance required."
    if g == "NO_HISTORY_NO_LIVE":
        return "No history profile and no reliable live market price. Treat as unknown rather than genuine 400 fair."
    if g == "NO_HISTORY_MARKET_CONFLICT_SHORT":
        return f"No history projection but market is short at {live:.2f}. Do not trust the 400 fair price as a true rating."
    if g == "NO_HISTORY_MARKET_CONFLICT_MID":
        return f"No history projection but market is active at {live:.2f}. Treat 400 fair as low-confidence placeholder."
    if g == "NO_HISTORY_LONGSHOT":
        return f"No history projection and market is long at {live:.2f}. 400 fair is plausible placeholder, not a calibrated price."
    return "No history runner requires manual/intelligence review."

def main():
    pt = pd.read_csv(PRICE_TRUTH, dtype=str, low_memory=False)
    fr = pd.read_csv(FAIR_REVIEW, dtype=str, low_memory=False)

    pt.columns = [c.strip() for c in pt.columns]
    fr.columns = [c.strip() for c in fr.columns]

    for df in [pt, fr]:
        df["_track"] = df["track"].astype(str).str.upper().str.replace(r"[^A-Z0-9]", "", regex=True)
        df["_race"] = df["race_no"].astype(str).str.replace(r"[^0-9]", "", regex=True)
        df["_horse"] = df["horse"].astype(str).str.upper().str.replace(r"\([^)]*\)", "", regex=True).str.replace(r"[^A-Z0-9]", "", regex=True)

    keep = [
        "_track","_race","_horse",
        "rated_price_status_v5_2_review",
        "projection_band_v5_2",
        "projection_gap_v5_2",
        "rated_probability_v5_2_review",
        "rated_price_v5_2_review",
        "price_rank_in_race_v5_2"
    ]
    keep = [c for c in keep if c in fr.columns]

    merged = pt.merge(
        fr[keep].drop_duplicates(["_track","_race","_horse"]),
        on=["_track","_race","_horse"],
        how="left"
    )

    merged["market_price_num"] = num(merged.get("market_price", np.nan))
    merged["official_fair_price_num"] = num(merged.get("official_fair_price", np.nan))
    merged["rated_probability_num"] = num(merged.get("rated_probability_v5_2_review", np.nan))
    merged["rated_price_num"] = num(merged.get("rated_price_v5_2_review", np.nan))

    merged["no_history_flag"] = merged["rated_price_status_v5_2_review"].eq("BASELINE_NO_HISTORY")
    merged["no_projection_flag"] = merged["projection_band_v5_2"].eq("NO_PROJECTION")
    merged["no_history_governance_band"] = merged.apply(classify, axis=1)
    merged["no_history_governance_comment"] = merged.apply(comment, axis=1)

    merged["display_fair_price_governed"] = np.where(
        merged["no_history_flag"],
        "UNKNOWN",
        merged["official_fair_price"].astype(str)
    )

    preferred = [
        "race_date","track","race_no","horse","market_price","official_fair_price",
        "display_fair_price_governed",
        "base_probability","base_fair_price","v8_candidate_price",
        "rated_price_status_v5_2_review","projection_band_v5_2","projection_gap_v5_2",
        "rated_probability_v5_2_review","rated_price_v5_2_review","price_rank_in_race_v5_2",
        "no_history_flag","no_projection_flag","no_history_governance_band","no_history_governance_comment",
        "price_governance_status"
    ]
    preferred = [c for c in preferred if c in merged.columns]

    out = merged[preferred].copy()
    out.to_csv(OUT, index=False)

    summary = [
        ("status", "COMPLETE"),
        ("rows", len(out)),
        ("no_history_rows", int(out["no_history_flag"].eq(True).sum())),
        ("no_projection_rows", int(out["no_projection_flag"].eq(True).sum())),
    ]

    for k, v in out["no_history_governance_band"].value_counts(dropna=False).to_dict().items():
        summary.append((f"band_{k}", v))

    pd.DataFrame(summary, columns=["metric","value"]).to_csv(SUMMARY, index=False)

    print("[NO_HISTORY_GOVERNANCE_V1] COMPLETE")
    print(f"rows={len(out)}")
    print(f"no_history_rows={int(out['no_history_flag'].eq(True).sum())}")
    print(f"wrote={OUT}")
    print(f"summary={SUMMARY}")

if __name__ == "__main__":
    main()
