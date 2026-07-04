from pathlib import Path

path = Path(r".\scripts\build_edgeiq_probability_engine_v3.py")
text = path.read_text(encoding="utf-8")

old = '''def market_probability(row):
    for c in ["sportsbet_price", "market_price", "current_price", "fixed_odds", "win_odds", "live_price"]:
        price = num(row.get(c))
        if price > 0:
            return 1.0 / price, price
    return 0.001, 0.0
'''

new = '''def market_probability(row):
    for c in [
        "sportsbet_price",
        "price",
        "runner_price",
        "fixed_win_price",
        "market_price",
        "current_price",
        "fixed_odds",
        "win_odds",
        "live_price",
    ]:
        price = num(row.get(c))
        if price > 0:
            return 1.0 / price, price
    return 0.001, 0.0
'''

if old not in text:
    raise SystemExit("market_probability block not found")

text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
print("patched market_probability price column list")
