from pathlib import Path

path = Path(".\scripts\build_edgeiq_live_runner_board_v1.py")

text = path.read_text(encoding="utf-8")

old = """
merged = racecard.merge(
    live_small,
    on="horse_key",
    how="left"
)
"""

new = """
merge_keys = ["horse_key"]

if "track" in racecard.columns and "track" in live_small.columns:
    merge_keys.append("track")

if "race_no" in racecard.columns and "race_no" in live_small.columns:
    merge_keys.append("race_no")

print("=" * 100)
print("MERGE KEYS")
print("=" * 100)
print(merge_keys)

merged = racecard.merge(
    live_small,
    on=merge_keys,
    how="left"
)
"""

if old not in text:
    raise SystemExit("OLD MERGE BLOCK NOT FOUND")

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")

print("LIVE RUNNER BOARD MERGE PATCHED")
