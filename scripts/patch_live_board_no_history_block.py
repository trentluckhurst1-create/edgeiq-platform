from pathlib import Path

path = Path(r".\scripts\build_edgeiq_live_runner_board_v1.py")
text = path.read_text(encoding="utf-8")

needle = 'out.to_csv(OUT, index=False)'

insert = r'''
# EDGEIQ SAFETY FIX:
# BASELINE_NO_HISTORY runners are unrated/unraced in the fair-price review.
# They must never create overlay/watch/execute decisions.
fair_review_path = Path(__file__).resolve().parents[1] / "public" / "data" / "edgeiq_current_fair_prices_review_v5_2.csv"

if fair_review_path.exists():
    fair_review = pd.read_csv(fair_review_path, dtype=str, keep_default_na=False, low_memory=False)
    if {"race_date", "track", "race_no", "horse", "rated_price_status_v5_2_review"}.issubset(fair_review.columns):
        fair_review["horse_canon"] = fair_review["horse"].apply(canon)
        status_keep = fair_review[
            ["race_date", "track", "race_no", "horse_canon", "rated_price_status_v5_2_review"]
        ].drop_duplicates(["race_date", "track", "race_no", "horse_canon"], keep="first")

        out = out.merge(
            status_keep,
            on=["race_date", "track", "race_no", "horse_canon"],
            how="left",
        )

        no_hist_mask = out["rated_price_status_v5_2_review"].astype(str).eq("BASELINE_NO_HISTORY")

        out.loc[no_hist_mask, "fair_price"] = ""
        out.loc[no_hist_mask, "edge_pct"] = ""
        out.loc[no_hist_mask, "execution_action"] = "NO_HISTORY"
        out.loc[no_hist_mask, "market_state"] = "NO_HISTORY"
        out.loc[no_hist_mask, "confidence_score"] = 0
'''

if insert.strip() not in text:
    if needle not in text:
        raise SystemExit("Could not find out.to_csv(OUT, index=False)")
    text = text.replace(needle, insert + "\n" + needle)

path.write_text(text, encoding="utf-8")
print("Inserted BASELINE_NO_HISTORY block before live board write")
