from pathlib import Path

path = Path(r".\scripts\build_edgeiq_probability_engine_v3.py")
text = path.read_text(encoding="utf-8")

if 'SPORTSBET = DATA / "sportsbet_live_market_v1.csv"' not in text:
    text = text.replace(
        'LIVE_RUNNER = DATA / "edgeiq_live_runner_board_v1.csv"',
        'LIVE_RUNNER = DATA / "edgeiq_live_runner_board_v1.csv"\nSPORTSBET = DATA / "sportsbet_live_market_v1.csv"'
    )

helper = r'''
def merge_sportsbet_prices_direct(live):
    sports = read_csv(SPORTSBET)
    if live.empty or sports.empty:
        return live

    left = live.copy()
    right = sports.copy()

    left["_key"] = key(left)
    right["_key"] = key(right)

    right["sportsbet_price_direct"] = right.get("sportsbet_price", "").astype(str).str.strip()
    right = (
        right[["_key", "sportsbet_price_direct"]]
        .drop_duplicates("_key", keep="last")
    )

    merged = left.merge(right, on="_key", how="left")

    price = merged["sportsbet_price_direct"].astype(str).str.strip()
    has_price = price.ne("") & price.ne("nan") & price.ne("0") & price.ne("0.0")

    for col in ["sportsbet_price", "market_price", "live_price", "current_price"]:
        if col not in merged.columns:
            merged[col] = ""
        merged.loc[has_price, col] = price[has_price]

    return merged.drop(columns=["_key", "sportsbet_price_direct"], errors="ignore")

'''

if "def merge_sportsbet_prices_direct(live):" not in text:
    text = text.replace("def diagnostics(audit):", helper + "\ndef diagnostics(audit):")

old = '''    live = read_csv(LIVE)
    live = merge_live_runner_prices(live)
    terminal = read_csv(TERMINAL)
'''

new = '''    live = read_csv(LIVE)
    live = merge_live_runner_prices(live)
    live = merge_sportsbet_prices_direct(live)
    terminal = read_csv(TERMINAL)
'''

if old not in text:
    raise SystemExit("main live merge block not found")

text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
print("patched direct Sportsbet price merge into V3")
