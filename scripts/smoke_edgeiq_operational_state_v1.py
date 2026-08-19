
from pathlib import Path

checks = {
    "OperationalRaceStateService.ts": [
        "composeOperationalBriefing",
        "registerProductionAdapterSlots",
        "buildCoverageFromModules",
        "buildSystemAlerts",
    ],
    "EdgeiqCommandWorkspace.tsx": [
        "getOperationalRaceState",
        "raceState.evidence",
        "OperationsRailV2",
    ],
    "EvidenceDrawer.tsx": [
        "OperationalEvidenceItem",
        "evidence.find",
    ],
    "OperationsRailV2.tsx": [
        "OperationalRaceState",
        "raceState.feedHealth",
        "raceState.feedHealth",
        "raceState.decision",
    ],
}

base = Path("src/edgeiq-os")
failures = []

for filename, needles in checks.items():
    matches = list(base.rglob(filename))
    if not matches:
        failures.append(f"MISSING_FILE::{filename}")
        continue

    text = matches[0].read_text(encoding="utf-8", errors="ignore")
    for needle in needles:
        if needle not in text:
            failures.append(f"MISSING_TOKEN::{filename}::{needle}")

if failures:
    print("[EDGEIQ_OS_SMOKE] FAIL")
    for failure in failures:
        print(failure)
    raise SystemExit(1)

print("[EDGEIQ_OS_SMOKE] PASS")
print("COMMAND is wired to OperationalRaceState, operational evidence workspace, briefing composer, and OperationsRailV2.")
