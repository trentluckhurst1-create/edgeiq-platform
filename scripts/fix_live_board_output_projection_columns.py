from pathlib import Path

path = Path(r".\scripts\build_edgeiq_live_runner_board_v1.py")
text = path.read_text(encoding="utf-8")

needle = '''        "rated_price_status_v5_2_review": safe(r.get("rated_price_status_v5_2_review")),
'''

insert = '''        "projected_rating_v5_2": r.get("projected_rating_v5_2"),
        "race_target_rating_v5_2": r.get("race_target_rating_v5_2"),
        "projection_gap_v5_2": r.get("projection_gap_v5_2"),
        "projection_band_v5_2": safe(r.get("projection_band_v5_2")),
        "projection_confidence_v5_2": safe(r.get("projection_confidence_v5_2")),
        "rated_price_status_v5_2_review": safe(r.get("rated_price_status_v5_2_review")),
'''

if needle not in text:
    raise SystemExit("rated_price_status output line not found")

text = text.replace(needle, insert)

path.write_text(text, encoding="utf-8")
print("patched live board output projection columns")
