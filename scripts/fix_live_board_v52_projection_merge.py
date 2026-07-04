from pathlib import Path

path = Path(r".\scripts\build_edgeiq_live_runner_board_v1.py")
text = path.read_text(encoding="utf-8")

insert = r'''
# Merge V5.2 projection/fair-price context directly into the live board before execution logic.
# This prevents V3 market-anchored prices from creating WATCH rows without model support.
fair_review_path = DATA / "edgeiq_current_fair_prices_review_v5_2.csv"
if fair_review_path.exists():
    fair_ctx = pd.read_csv(fair_review_path, dtype=str, keep_default_na=False, low_memory=False)
    if "horse" in fair_ctx.columns:
        fair_ctx["horse_canon"] = fair_ctx["horse"].apply(canon)

        fair_cols = [
            "race_date",
            "track",
            "race_no",
            "horse_canon",
            "projected_rating_v5_2",
            "race_target_rating_v5_2",
            "projection_gap_v5_2",
            "projection_band_v5_2",
            "projection_confidence_v5_2",
            "rated_price_status_v5_2_review",
        ]

        for col in fair_cols:
            if col not in fair_ctx.columns:
                fair_ctx[col] = ""

        fair_small = (
            fair_ctx[fair_cols]
            .drop_duplicates(["race_date", "track", "race_no", "horse_canon"], keep="first")
        )

        for col in [
            "projected_rating_v5_2",
            "race_target_rating_v5_2",
            "projection_gap_v5_2",
            "projection_band_v5_2",
            "projection_confidence_v5_2",
            "rated_price_status_v5_2_review",
        ]:
            if col in merged.columns:
                merged = merged.drop(columns=[col])

        merged = merged.merge(
            fair_small,
            on=["race_date", "track", "race_no", "horse_canon"],
            how="left",
        )
'''

marker = 'rows = []'

if insert.strip() not in text:
    if marker not in text:
        raise SystemExit("rows marker not found")
    text = text.replace(marker, insert + "\n" + marker)

path.write_text(text, encoding="utf-8")
print("patched V5.2 projection field merge")
