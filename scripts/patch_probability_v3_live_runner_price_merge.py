from pathlib import Path

path = Path(r".\scripts\build_edgeiq_probability_engine_v3.py")
text = path.read_text(encoding="utf-8")

if 'LIVE_RUNNER = DATA / "edgeiq_live_runner_board_v1.csv"' not in text:
    text = text.replace(
        'LIVE = DATA / "edgeiq_execution_board_live.csv"',
        'LIVE = DATA / "edgeiq_execution_board_live.csv"\nLIVE_RUNNER = DATA / "edgeiq_live_runner_board_v1.csv"'
    )

helper = r'''
def merge_live_runner_prices(live):
    board = read_csv(LIVE_RUNNER)
    if live.empty or board.empty:
        return live

    left = live.copy()
    right = board.copy()

    left["_key"] = key(left)
    right["_key"] = key(right)

    keep_cols = [
        "_key",
        "live_price",
        "sportsbet_event_id",
        "sportsbet_market_id",
        "sportsbet_timestamp",
        "bookmaker",
    ]
    keep_cols = [c for c in keep_cols if c in right.columns]

    right = right[keep_cols].drop_duplicates("_key", keep="last")
    merged = left.merge(right, on="_key", how="left", suffixes=("", "_runner"))

    if "live_price_runner" in merged.columns:
        runner_price = merged["live_price_runner"].astype(str).str.strip()
        has_runner_price = runner_price.ne("") & runner_price.ne("nan")

        for col in ["sportsbet_price", "market_price", "live_price", "current_price"]:
            if col not in merged.columns:
                merged[col] = ""
            existing = merged[col].astype(str).str.strip()
            merged.loc[has_runner_price & existing.eq(""), col] = runner_price[has_runner_price]

    for src in ["sportsbet_event_id", "sportsbet_market_id", "sportsbet_timestamp", "bookmaker"]:
        runner_col = f"{src}_runner"
        if runner_col in merged.columns:
            if src not in merged.columns:
                merged[src] = ""
            existing = merged[src].astype(str).str.strip()
            runner_value = merged[runner_col].astype(str).str.strip()
            merged.loc[existing.eq("") & runner_value.ne("") & runner_value.ne("nan"), src] = runner_value

    return merged.drop(columns=[c for c in merged.columns if c.endswith("_runner") or c == "_key"], errors="ignore")

'''

if "def merge_live_runner_prices(live):" not in text:
    text = text.replace("def diagnostics(audit):", helper + "\ndef diagnostics(audit):")

old = '''    live = read_csv(LIVE)
    terminal = read_csv(TERMINAL)
'''

new = '''    live = read_csv(LIVE)
    live = merge_live_runner_prices(live)
    terminal = read_csv(TERMINAL)
'''

if old not in text:
    raise SystemExit("main live read block not found")

text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
print("patched V3 live runner price merge")
