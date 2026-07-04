from pathlib import Path

path = Path(r".\scripts\build_edgeiq_live_runner_board_v1.py")
text = path.read_text(encoding="utf-8")

old = '''live_small = live[
    [
        "horse_canon",
        "horse",
        "sportsbet_price_num",
        "market_mover",
        "recent_odds_fluctuations",
        "bookmaker",
        "mobile_silk_image",
        "event_id",
        "market_id",
        "timestamp",
    ]
].copy()'''

new = '''for optional_col in [
    "market_mover",
    "recent_odds_fluctuations",
    "bookmaker",
    "mobile_silk_image",
    "event_id",
    "market_id",
    "timestamp",
]:
    if optional_col not in live.columns:
        live[optional_col] = ""

live_small = live[
    [
        "horse_canon",
        "horse",
        "sportsbet_price_num",
        "market_mover",
        "recent_odds_fluctuations",
        "bookmaker",
        "mobile_silk_image",
        "event_id",
        "market_id",
        "timestamp",
    ]
].copy()'''

if old not in text:
    raise SystemExit("LIVE_SMALL BLOCK NOT FOUND")

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")

print("LIVE RUNNER BOARD SCRIPT PATCHED FOR NORMALISED SPORTSBET FILE")
