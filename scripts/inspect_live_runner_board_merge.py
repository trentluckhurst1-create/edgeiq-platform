from pathlib import Path

path = Path(r".\scripts\build_edgeiq_live_runner_board_v1.py")
text = path.read_text(encoding="utf-8")

print("=" * 100)
print("CURRENT MERGE REFERENCES")
print("=" * 100)

for i, line in enumerate(text.splitlines(), start=1):
    if ".merge(" in line or "live_small" in line or "horse_canon" in line:
        print(f"{i}: {line}")

print("=" * 100)
print("NO PATCH APPLIED YET - PASTE THIS OUTPUT")
print("=" * 100)
