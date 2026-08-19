from pathlib import Path

path = Path(r".\scripts\build_edgeiq_live_fair_price_v8_interaction_candidate_feed.py")
text = path.read_text(encoding="utf-8")

old = '''    out = live.merge(tj_keep, on="join_key_v8", how="left", validate="many_to_one")

    out["current_fair_price"] = num(out[fair_col])
'''

new = '''    out = live.merge(tj_keep, on="join_key_v8", how="left", validate="many_to_one")

    # HARD FIX: if live already contains an empty/stale tj_band_live_v8 column,
    # pandas suffixes the real merged TJ band as tj_band_live_v8_y.
    # Promote the populated merged column back to tj_band_live_v8.
    if "tj_band_live_v8_y" in out.columns:
        out["tj_band_live_v8"] = out["tj_band_live_v8_y"]
    elif "tj_band_live_v8_x" in out.columns:
        out["tj_band_live_v8"] = out["tj_band_live_v8_x"]

    if "tj_score_live_v8_y" in out.columns:
        out["tj_score_live_v8"] = out["tj_score_live_v8_y"]
    elif "tj_score_live_v8_x" in out.columns:
        out["tj_score_live_v8"] = out["tj_score_live_v8_x"]

    out["current_fair_price"] = num(out[fair_col])
'''

if old not in text:
    raise SystemExit("TARGET BLOCK NOT FOUND - script not changed")

path.write_text(text.replace(old, new), encoding="utf-8")
print("[PATCHED] promoted suffixed TJ merge columns")
