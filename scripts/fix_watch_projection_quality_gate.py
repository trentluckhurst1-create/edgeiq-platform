from pathlib import Path

path = Path(r".\scripts\build_edgeiq_live_runner_board_v1.py")
text = path.read_text(encoding="utf-8")

old = '''    if pd.isna(live_price):
        execution = "NO LIVE"
    elif pricing_action in ["PASS", "NO_EDGE"]:
        execution = "PASS"
    elif pricing_action in ["SUPPRESS", "SUPPRESS_FAKE_OVERLAY"]:
        execution = "SUPPRESS"
    elif pricing_action in ["WATCH", "ALLOW_REALISTIC"]:
        execution = "WATCH"
    elif pricing_action == "UNDERLAY":
        execution = "UNDERLAY"
    elif v3_action and v3_action not in ["NO LIVE", "NO_LIVE", "NO_LIVE_PRICE"]:
        execution = v3_action
'''

new = '''    projection_band = safe(r.get("projection_band_v5_2"))
    projection_confidence = safe(r.get("projection_confidence_v5_2"))
    weak_projection = projection_band in ["POOR", "NO_PROJECTION", ""] or projection_confidence in ["LOW", "VERY_LOW", ""]

    if pd.isna(live_price):
        execution = "NO LIVE"
    elif pricing_action in ["PASS", "NO_EDGE"]:
        execution = "PASS"
    elif pricing_action in ["SUPPRESS", "SUPPRESS_FAKE_OVERLAY"]:
        execution = "SUPPRESS"
    elif pricing_action in ["WATCH", "ALLOW_REALISTIC"] and weak_projection:
        execution = "PASS"
    elif pricing_action in ["WATCH", "ALLOW_REALISTIC"]:
        execution = "WATCH"
    elif pricing_action == "UNDERLAY":
        execution = "UNDERLAY"
    elif v3_action and v3_action not in ["NO LIVE", "NO_LIVE", "NO_LIVE_PRICE"]:
        execution = v3_action
'''

if old not in text:
    raise SystemExit("action mapping block not found")

text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
print("patched projection quality gate")
