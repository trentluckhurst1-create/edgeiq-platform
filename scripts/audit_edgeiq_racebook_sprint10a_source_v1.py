from pathlib import Path

targets = [
    "src/edgeiq-os/race/RaceFileV3.tsx",
    "src/edgeiq-os/services/RaceFileService.ts",
    "src/edgeiq-os/services/RunRatingService.ts",
    "src/edgeiq-os/services/RaceStrengthService.ts",
    "src/edgeiq-os/services/CompareService.ts",
    "src/edgeiq-os/services/index.ts",
]

out = []

for target in targets:
    p = Path(target)
    out.append("")
    out.append("=" * 90)
    out.append(target)
    out.append("=" * 90)
    if p.exists():
        text = p.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        for i, line in enumerate(lines[:260], 1):
            out.append(f"{i:04d}: {line}")
        if len(lines) > 260:
            out.append(f"... TRUNCATED AT 260 LINES OF {len(lines)}")
    else:
        out.append("MISSING")

Path("EDGEIQ_RACEBOOK_SPRINT10A_SOURCE_AUDIT.txt").write_text("\n".join(out), encoding="utf-8")
print("[EDGEIQ] RaceBook Sprint 10A source audit written")
