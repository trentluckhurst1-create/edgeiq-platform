from pathlib import Path
import re

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DOCS = ROOT / "docs"
OUT = DOCS / "meeting_universe_pipeline_audit_v1.txt"

interesting = (
    "meeting_universe",
    "three_day",
    "graphql",
    "GetRacesForMeet",
    "race_fields",
    "runner_board",
    "TAB_DIRECT_API",
    "accept",
    "field",
)

results = []

for py in ROOT.rglob("*.py"):
    try:
        text = py.read_text(encoding="utf-8-sig", errors="ignore")
    except Exception:
        continue

    score = 0
    hits = []

    for token in interesting:
        if token.lower() in text.lower():
            score += 1
            hits.append(token)

    if score:
        results.append((score, py, hits, text.splitlines()))

results.sort(reverse=True, key=lambda x: x[0])

lines = []
lines.append("EDGEIQ MEETING UNIVERSE PIPELINE AUDIT")
lines.append("="*120)

for score, path, hits, src in results[:40]:
    lines.append("")
    lines.append("="*120)
    lines.append(str(path.relative_to(ROOT)))
    lines.append(f"SCORE={score}")
    lines.append("TOKENS=" + ", ".join(hits))

    for i,line in enumerate(src, start=1):
        lower = line.lower()
        if any(t.lower() in lower for t in hits):
            start = max(1,i-3)
            end = min(len(src),i+3)
            lines.append(f"\n--- Around line {i} ---")
            for j in range(start,end+1):
                lines.append(f"{j:04d}: {src[j-1]}")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines), encoding="utf-8")

print("\n".join(lines))
print("")
print(f"OUTPUT={OUT}")
print("MEETING_UNIVERSE_PIPELINE_AUDIT_COMPLETE")
