from pathlib import Path
import sys

FILE = Path("scripts") / "build_edgeiq_horse_profile_v1.py"

if not FILE.exists():
    print(f"ERROR: File not found: {FILE}")
    sys.exit(1)

text = FILE.read_text(encoding="utf-8-sig")

count = text.count("`n")

if count == 0:
    print("No literal PowerShell newline sequences found.")
    sys.exit(1)

text = text.replace("`n", "\n")

FILE.write_text(text, encoding="utf-8-sig")

print("=" * 80)
print("STEP202 HORSE PROFILE NEWLINE REPAIR")
print("=" * 80)
print(f"File repaired : {FILE}")
print(f"Replacements  : {count}")
print()
print("STATUS : PASS")

sys.exit(0)
