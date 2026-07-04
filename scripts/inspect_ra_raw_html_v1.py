from pathlib import Path

ROOT = Path.cwd()
RAW_DIR = ROOT / "outputs" / "ra_active_profile_backfill"

print("=" * 100)
print("RAW RA HTML INSPECTION")
print("=" * 100)

for path in RAW_DIR.glob("*.html"):

    text = path.read_text(encoding="utf-8", errors="ignore")

    print()
    print("-" * 100)
    print(path.name)
    print("LEN:", len(text))
    print()
    print(text[:2000])
