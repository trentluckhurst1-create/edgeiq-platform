from pathlib import Path

checks = {
    "RaceFileV3": Path("src/edgeiq-os/race/RaceFileV3.tsx"),
    "RaceFileService": Path("src/edgeiq-os/services/RaceFileService.ts"),
    "CompareService": Path("src/edgeiq-os/services/CompareService.ts"),
    "CSS": Path("src/edgeiq-os/styles/edgeiqOsV2.css"),
}

required = [
    "Professional Form Guide",
    "Official Form Guide",
    "EDGEIQ Evidence",
    "Today's Relevance",
    "Evidence View",
    "Form View",
    "Open Historical Race Book",
    "buildAssignmentComparison",
    "professionalForm",
    "evidenceRuns",
    "eiq-pro-form-card",
]

missing = []

combined = ""
for name, path in checks.items():
    if not path.exists():
        missing.append(f"{name}: missing file")
        continue
    combined += path.read_text(encoding="utf-8", errors="ignore") + "\n"

for token in required:
    if token not in combined:
        missing.append(token)

if missing:
    print("[EDGEIQ_PRO_FORM_SMOKE] FAIL")
    for item in missing:
        print("MISSING:", item)
    raise SystemExit(1)

print("[EDGEIQ_PRO_FORM_SMOKE] PASS")
print("Professional Historical Form Engine sections present")
