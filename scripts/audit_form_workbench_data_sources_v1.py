from pathlib import Path
import re

files = [
  "src/edgeiq-os/services/race-file-v2.ts",
  "src/edgeiq-os/services/race-file-model.ts",
  "src/edgeiq-os/services/RaceFileService.ts",
  "src/edgeiq-os/race/RaceFileV3.tsx",
]

out = []
for f in files:
    p = Path(f)
    out.append(f"\n\n===== {f} =====")
    if not p.exists():
        out.append("MISSING")
        continue
    txt = p.read_text(encoding="utf-8", errors="ignore")
    for term in [
        "Production runner pending",
        "Primary stable",
        "Primary jockey",
        "Monitor",
        "Aligned",
        "official:",
        "field:",
        "historicalRuns",
        "runnerDNA",
        "market",
        "trainer",
        "jockey",
        "barrier",
        "weight",
    ]:
        if term in txt:
            out.append(f"FOUND: {term}")
    lines = txt.splitlines()
    for i, line in enumerate(lines, start=1):
        if any(x in line for x in ["Production runner pending", "Primary stable", "Primary jockey", "Monitor", "Aligned"]):
            out.append(f"L{i}: {line.strip()}")

Path("public/data/edgeiq_form_workbench_data_audit_v1.txt").write_text("\n".join(out), encoding="utf-8")
print("[EDGEIQ] Data audit written: public/data/edgeiq_form_workbench_data_audit_v1.txt")
