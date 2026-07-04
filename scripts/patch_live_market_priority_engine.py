from pathlib import Path

path = Path(r".\scripts\build_edgeiq_execution_explainability_v1.py")
text = path.read_text(encoding="utf-8")

old = '''    if action == "EXECUTE":
        tier = "PRIORITY EXECUTE"
        risk = "CONTROLLED"
        score += 20
    elif action == "WATCH":
        tier = "WATCHLIST"
        risk = "SPECULATIVE"
    elif action == "PASS":
        tier = "PASSIVE"
        risk = "LOW"
        score -= 10
    else:
        tier = "SUPPRESSED"
        risk = "HIGH"'''

new = '''    live_price = row.get("live_price")

    has_live = pd.notna(live_price)

    if has_live:
        reasons.append("Active live market")
        score += 40
    else:
        reasons.append("No live market")
        score -= 55

    if action == "EXECUTE":

        if has_live:
            tier = "PRIORITY EXECUTE"
            risk = "CONTROLLED"
            score += 25
        else:
            tier = "SUPPRESSED"
            risk = "HIGH"
            score -= 50

    elif action == "WATCH":

        if has_live:
            tier = "WATCHLIST"
            risk = "SPECULATIVE"
            score += 10
        else:
            tier = "SUPPRESSED"
            risk = "HIGH"
            score -= 40

    elif action == "PASS":
        tier = "PASSIVE"
        risk = "LOW"
        score -= 15

    else:
        tier = "SUPPRESSED"
        risk = "HIGH"
        score -= 25'''

if old not in text:
    raise SystemExit("TARGET BLOCK NOT FOUND")

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")

print("LIVE MARKET PRIORITY ENGINE PATCHED")
