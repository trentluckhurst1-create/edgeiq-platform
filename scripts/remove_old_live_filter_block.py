from pathlib import Path

path = Path(r".\scripts\build_edgeiq_live_runner_board_v1.py")
text = path.read_text(encoding="utf-8")

start = text.find('if "race_no" in merged.columns and "race_no_live" in merged.columns:')
end = text.find('rows = []', start)

if start == -1 or end == -1:
    raise SystemExit("OLD RACE_NO FILTER BLOCK NOT FOUND")

text = text[:start] + '''
# Old horse-only race_no filter removed.
# Live merge is now strict on track + race_no + horse_canon, so no blanking block is required.

''' + text[end:]

path.write_text(text, encoding="utf-8")
print("REMOVED OLD RACE_NO BLANKING FILTER")
