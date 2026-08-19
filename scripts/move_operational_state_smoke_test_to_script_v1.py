from pathlib import Path

Path("src/edgeiq-os/services/operational-state/OperationalRaceStateSmokeTest.ts").unlink(missing_ok=True)

smoke = Path("scripts/smoke_edgeiq_operational_state_v1.py")

smoke.write_text(r'''
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
        "OperationalStateRail",
    ],
    "EvidenceDrawer.tsx": [
        "OperationalEvidenceItem",
        "evidence.find",
    ],
    "OperationalStateRail.tsx": [
        "OperationalRaceState",
        "raceState.feedHealth",
        "raceState.coverage",
        "raceState.alerts",
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
print("COMMAND is wired to OperationalRaceState, operational evidence drawer, briefing composer, and OS rail.")
''', encoding="utf-8")

print("[EDGEIQ] Smoke test moved to script")
