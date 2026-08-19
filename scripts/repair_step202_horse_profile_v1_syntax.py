from pathlib import Path
import sys

FILE = Path("scripts") / "build_edgeiq_horse_profile_v1.py"

text = FILE.read_text(encoding="utf-8-sig")

old = (
    'valid_rating_all = g[g["rating"].notna()].copy()`n'
    '        valid_rating = valid_rating_all[~valid_rating_all["is_backfilled"]].copy()'
)

new = (
    'valid_rating_all = g[g["rating"].notna()].copy()\n'
    '        valid_rating = valid_rating_all[~valid_rating_all["is_backfilled"]].copy()'
)

if old not in text:
    print("Expected text not found.")
    sys.exit(1)

text = text.replace(old, new, 1)

FILE.write_text(text, encoding="utf-8-sig")

print("Syntax repaired.")
