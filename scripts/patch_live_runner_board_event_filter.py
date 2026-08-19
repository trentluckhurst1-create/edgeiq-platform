from pathlib import Path

path = Path(r".\scripts\build_edgeiq_live_runner_board_v1.py")
text = path.read_text(encoding="utf-8")

text = text.replace(
'''.sort_values(["horse_canon", "sportsbet_price_num"], na_position="last")
    .drop_duplicates("horse_canon", keep="first")''',
'''.sort_values(["horse_canon", "sportsbet_price_num"], na_position="last")
    .drop_duplicates(["horse_canon", "event_id"], keep="first")'''
)

old = '''merged = merged.merge(
    live_small,
    on=["horse_canon"],
    how="left",
    suffixes=("", "_live")
)'''

new = '''# IMPORTANT:
# Sportsbet racecard pages may not expose track cleanly, but they DO expose event_id.
# We first map live prices by horse only, then HARD FILTER to the captured Sportsbet event race_no.
# This prevents cross-meeting contamination like FLYING NIC appearing at HORSHAM.
merged = merged.merge(
    live_small,
    on=["horse_canon"],
    how="left",
    suffixes=("", "_live")
)

if "race_no" in merged.columns and "race_no_live" in merged.columns:
    pass

if "event_id" in merged.columns and "race_no" in merged.columns:
    live_race_nos = set()
    try:
        live_race_nos = set(int(float(x)) for x in live_small.get("race_no", []) if str(x).strip() not in ["", "nan", "None"])
    except Exception:
        live_race_nos = set()

    if live_race_nos:
        merged.loc[~merged["race_no"].apply(lambda x: int(float(x)) if str(x).strip() not in ["", "nan", "None"] else -999).isin(live_race_nos), [
            "sportsbet_price_num",
            "market_mover",
            "recent_odds_fluctuations",
            "bookmaker",
            "mobile_silk_image",
            "event_id",
            "market_id",
            "timestamp",
        ]] = ""'''

if old not in text:
    raise SystemExit("LIVE MERGE BLOCK NOT FOUND")

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")

print("PATCHED LIVE RUNNER BOARD TO PREVENT CROSS-RACE CONTAMINATION")
