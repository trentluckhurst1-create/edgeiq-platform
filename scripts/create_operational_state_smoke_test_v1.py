from pathlib import Path

test = Path("src/edgeiq-os/services/operational-state/OperationalRaceStateSmokeTest.ts")

test.write_text(r'''
import { getOperationalRaceState } from "../intelligence-orchestrator";

const state = getOperationalRaceState();

console.log("STATUS", state.status);
console.log("CONFIDENCE", state.confidence);
console.log("SITUATION", state.currentSituation);
console.log("EVIDENCE_COUNT", state.evidence.length);
console.log("FEED_HEALTH", state.feedHealth.map((item) => `${item.label}:${item.status}`).join(" | "));
console.log("COVERAGE", state.coverage.map((item) => `${item.label}:${item.coveragePct}`).join(" | "));
''', encoding="utf-8")

print("[EDGEIQ] Smoke test created")
