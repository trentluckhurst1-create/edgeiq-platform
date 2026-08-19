from pathlib import Path

path = Path(r".\scripts\build_edgeiq_live_runner_board_v1.py")
text = path.read_text(encoding="utf-8")

old = '''        status_keep = fair_review[
            ["race_date", "track", "race_no", "horse_canon", "rated_price_status_v5_2_review"]
        ].drop_duplicates(["race_date", "track", "race_no", "horse_canon"], keep="first")

        out = out.merge(
            status_keep,
            on=["race_date", "track", "race_no", "horse_canon"],
            how="left",
        )
'''

new = '''        projection_keep_cols = [
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

        for col in projection_keep_cols:
            if col not in fair_review.columns:
                fair_review[col] = ""

        status_keep = fair_review[
            projection_keep_cols
        ].drop_duplicates(["race_date", "track", "race_no", "horse_canon"], keep="first")

        for col in [
            "projected_rating_v5_2",
            "race_target_rating_v5_2",
            "projection_gap_v5_2",
            "projection_band_v5_2",
            "projection_confidence_v5_2",
            "rated_price_status_v5_2_review",
        ]:
            if col in out.columns:
                out = out.drop(columns=[col])

        out = out.merge(
            status_keep,
            on=["race_date", "track", "race_no", "horse_canon"],
            how="left",
        )
'''

if old not in text:
    raise SystemExit("final fair review output merge block not found")

text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
print("patched final output V5.2 projection merge")
