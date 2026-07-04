from pathlib import Path

path = Path(r".\scripts\build_edgeiq_live_runner_board_v1.py")
text = path.read_text(encoding="utf-8")

old = '''card["track"] = card["track"].astype(str).str.upper().str.strip()
live_small["track"] = live_small["track"].astype(str).str.upper().str.strip()
card["race_no"] = card["race_no"].astype(str).str.replace(".0", "", regex=False).str.strip()
live_small["race_no"] = live_small["race_no"].astype(str).str.replace(".0", "", regex=False).str.strip()'''

new = '''merged["track"] = merged["track"].astype(str).str.upper().str.strip()
live_small["track"] = live_small["track"].astype(str).str.upper().str.strip()
merged["race_no"] = merged["race_no"].astype(str).str.replace(".0", "", regex=False).str.strip()
live_small["race_no"] = live_small["race_no"].astype(str).str.replace(".0", "", regex=False).str.strip()'''

if old not in text:
    raise SystemExit("NORMALISATION BLOCK NOT FOUND")

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")

print("FIXED MERGE KEY NORMALISATION TO USE MERGED DATAFRAME")
