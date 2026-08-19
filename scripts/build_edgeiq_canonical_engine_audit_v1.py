from pathlib import Path
import re
from collections import defaultdict

ROOT = Path(".")
SRC = ROOT / "src"

ENGINE_PATTERNS = {
    "RaceFile": [r"race[-_]?file"],
    "RunnerHistory": [r"runner.*history", r"history.*runner", r"runner.*profile", r"runner.*metric"],
    "RunnerDNA": [r"runner.*dna", r"\bdna\b"],
    "SpeedProfile": [r"speed.*profile", r"standard.*time", r"length.*standard"],
    "TrackSignature": [r"track.*signature"],
    "RaceFlow": [r"race.*flow", r"race.*shape"],
    "RaceStrength": [r"race.*strength"],
    "RunRating": [r"run.*rating", r"performance.*rating"],
    "Pressure": [r"pressure"],
    "Tempo": [r"tempo"],
    "Position": [r"position"],
    "MarketBehaviour": [r"market"],
    "Command": [r"command"],
    "Evidence": [r"evidence"],
}

OUT = ROOT / "public" / "data"
OUT.mkdir(parents=True, exist_ok=True)

report = []

for engine, patterns in ENGINE_PATTERNS.items():
    matches = []

    for f in SRC.rglob("*"):
        if f.suffix not in (".ts", ".tsx"):
            continue

        rel = f.relative_to(ROOT).as_posix().lower()

        for p in patterns:
            if re.search(p, rel):
                matches.append(f.relative_to(ROOT).as_posix())
                break

    report.append(f"{engine}: {len(matches)}")
    for m in sorted(matches):
        report.append(f"    {m}")
    report.append("")

(Path(OUT / "edgeiq_canonical_engine_audit_v1.txt")).write_text(
    "\n".join(report),
    encoding="utf-8"
)

print("[EDGEIQ] Canonical Engine Audit built")
print(OUT / "edgeiq_canonical_engine_audit_v1.txt")
