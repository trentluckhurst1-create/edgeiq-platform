from pathlib import Path

path = Path(r".\scripts\build_edgeiq_live_runner_board_v1.py")
text = path.read_text(encoding="utf-8")

needle = 'live["horse_canon"] = live["horse"].apply(canon)'

insert = r'''
live["horse_canon"] = live["horse"].apply(canon)

# EDGEIQ FIX:
# Sportsbet live capture does not always include race_date.
# Infer live race_date from the card by taking the earliest matching active race_date
# for track + race_no. This prevents SWAN HILL R1 across multiple days bleeding together.
if "race_date" not in live.columns or live["race_date"].astype(str).str.strip().eq("").all():
    date_lookup = (
        card[["track", "race_no", "race_date"]]
        .drop_duplicates()
        .sort_values(["track", "race_no", "race_date"])
        .groupby(["track", "race_no"], dropna=False)["race_date"]
        .first()
        .reset_index()
    )
    live = live.drop(columns=["race_date"], errors="ignore").merge(
        date_lookup,
        on=["track", "race_no"],
        how="left",
    )
'''

if insert.strip() not in text:
    if needle not in text:
        raise SystemExit("Could not find live horse_canon line")
    text = text.replace(needle, insert)

path.write_text(text, encoding="utf-8")
print("Inserted live race_date inference")
