from pathlib import Path

path = Path(r".\scripts\build_edgeiq_live_runner_board_v1.py")
text = path.read_text(encoding="utf-8")

old = '''    # Hard safety gate: V3 prices marked NO_LIVE cannot create live actions.
    stale_v3 = realism == "NO_LIVE_MARKET" or safe(r.get("v3_pricing_action")) == "NO_LIVE_PRICE" or v3_action == "NO_LIVE_PRICE"
'''

new = '''    # Hard safety gate: only suppress rows that V3 itself currently marks as no-live.
    # Do not use stale post_v3_execution_action here; it can carry old NO_LIVE values.
    pricing_action = safe(r.get("v3_pricing_action"))
    stale_v3 = realism == "NO_LIVE_MARKET" or pricing_action == "NO_LIVE_PRICE"
'''

if old not in text:
    raise SystemExit("stale_v3 block not found")

text = text.replace(old, new)

old2 = '''    pricing_action = safe(r.get("v3_pricing_action"))
    if pricing_action in ["PASS", "SUPPRESS", "UNDERLAY", "NO_EDGE"]:
        execution = pricing_action
    elif v3_action and v3_action not in ["NO LIVE", "NO_LIVE", "NO_LIVE_PRICE"]:
        execution = v3_action
'''

new2 = '''    if pricing_action in ["PASS", "NO_EDGE"]:
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

if old2 in text:
    text = text.replace(old2, new2)

path.write_text(text, encoding="utf-8")
print("patched stale gate and V3 action mapping")
