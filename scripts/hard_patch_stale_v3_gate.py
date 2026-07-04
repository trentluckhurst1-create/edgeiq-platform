from pathlib import Path

path = Path(r".\scripts\build_edgeiq_live_runner_board_v1.py")
text = path.read_text(encoding="utf-8")
lines = text.splitlines()

start = None
end = None

for i, line in enumerate(lines):
    if line.strip() == "if pd.isna(live_price):" and line.startswith("    "):
        start = i
        break

if start is None:
    raise SystemExit("Could not find execution start")

for i in range(start + 1, len(lines)):
    if lines[i].strip().startswith("if v3_action and v3_action not in"):
        end = i
        break

if end is None:
    raise SystemExit("Could not find v3_action override block")

new_block = [
'    # Hard safety gate: V3 prices marked NO_LIVE cannot create live actions.',
'    stale_v3 = realism == "NO_LIVE_MARKET" or safe(r.get("v3_pricing_action")) == "NO_LIVE_PRICE" or v3_action == "NO_LIVE_PRICE"',
'',
'    if pd.isna(live_price):',
'        execution = "NO LIVE"',
'',
'    elif stale_v3:',
'        fair_price = np.nan',
'        edge_pct = np.nan',
'        execution = "SUPPRESS_STALE_V3"',
'',
'    elif realism in ["EXTREME_FAKE_OVERLAY", "LOW_CONFIDENCE_FAKE_OVERLAY"]:',
'        execution = "SUPPRESS"',
'',
'    elif edge_pct >= 18 and confidence >= 70:',
'        execution = "EXECUTE"',
'',
'    elif edge_pct >= 10 and confidence >= 55:',
'        execution = "STRONG_WATCH"',
'',
'    elif edge_pct >= 6:',
'        execution = "WATCH"',
'',
'    elif edge_pct <= -18:',
'        execution = "UNDERLAY"',
'',
'    else:',
'        execution = "PASS"',
'',
]

lines = lines[:start] + new_block + lines[end:]
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("Patched stale V3 gate")
