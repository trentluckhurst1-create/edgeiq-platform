from __future__ import annotations

from datetime import datetime

from edgeiq_beta_readiness_common_v1 import PUBLIC_DATA, ROOT, read_text, write_json, write_text


PASS_MARKER = "EDGEIQ_DATA_WIRING_V1_PASS"
TXT_OUT = PUBLIC_DATA / "edgeiq_data_wiring_v1.txt"
JSON_OUT = PUBLIC_DATA / "edgeiq_data_wiring_v1.json"


CHECKS = [
    ("FORM_GUIDE_ENRICHED", "src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx", ["loadFormGuideEnrichedFeed", "normaliseFormGuideRace"]),
    ("FORM_EPI", "src/edgeiq-os/race/services/formGuideNormaliser.ts", ["epi:", "metricText(enriched?.epi"]),
    ("FORM_EDGEIQ_PRICE", "src/edgeiq-os/race/services/formGuideNormaliser.ts", ["edgeiqPrice:", "formatPrice(enriched?.edgeiqPrice"]),
    ("FORM_MARKET", "src/edgeiq-os/race/services/formGuideNormaliser.ts", ["marketPrice:", "formatPrice(enriched?.marketPrice"]),
    ("FORM_EARLY_SPEED", "src/edgeiq-os/race/services/formGuideNormaliser.ts", ["earlySpeed:", "metricText(enriched?.earlySpeed"]),
    ("FORM_LATE_SPEED", "src/edgeiq-os/race/services/formGuideNormaliser.ts", ["late:", "metricText(enriched?.lateSpeed"]),
    ("FORM_SUITABILITY", "src/edgeiq-os/race/services/formGuideNormaliser.ts", ["suitabilityScore:", "metricText(enriched?.suitability"]),
    ("FORM_MOMENTUM", "src/edgeiq-os/race/services/formGuideNormaliser.ts", ["formMomentum:", "metricText(enriched?.formMomentum"]),
    ("MAP_TERMINAL", "src/edgeiq-os/race/components/MapWorkspace.tsx", ["loadMapTerminalFeed", "buildMapViewModel"]),
    ("MAP_RUNNER_CONTEXT", "src/edgeiq-os/race/components/MapWorkspace.tsx", ["runnerJockey", "runnerTrainer", "runnerWeight", "runnerMarket"]),
    ("MARKET_TERMINAL", "src/edgeiq-os/race/components/MarketWorkspace.tsx", ["loadMarketTerminalFeed", "buildMarketViewModel"]),
    ("OVERVIEW_TERMINAL", "src/edgeiq-os/race/components/OverviewWorkspace.tsx", ["loadOverviewTerminalFeed", "buildOverviewViewModel"]),
    ("INSIGHTS_TERMINAL", "src/edgeiq-os/race/components/InsightsWorkspace.tsx", ["loadInsightsTerminalFeed", "buildInsightsViewModel"]),
    ("EPI_TERMINAL", "src/edgeiq-os/race/components/EpiWorkspaceWorkspace.tsx", ["loadEpiWorkspaceTerminalFeed", "buildEpiWorkspaceViewModel"]),
]


def main() -> int:
    generated = datetime.now().isoformat(timespec="seconds")
    checks = []
    fail_count = 0
    for name, path, needles in CHECKS:
        source = read_text(ROOT / path)
        missing = [needle for needle in needles if needle not in source]
        status = "FAIL" if missing else "PASS"
        if missing:
            fail_count += 1
        checks.append({"name": name, "status": status, "file": path, "missing": missing})

    status = "PASS" if fail_count == 0 else "FAIL"
    payload = {"audit": "edgeiq_data_wiring_v1", "generated_at": generated, "status": status, "pass_marker": PASS_MARKER if status == "PASS" else "", "checks": checks}
    write_json(JSON_OUT, payload)
    lines = ["EDGEiQ Data Wiring V1", f"Generated: {generated}", f"Status: {status}"]
    if status == "PASS":
        lines.append(PASS_MARKER)
    lines.append("")
    for check in checks:
        lines.append(f"[{check['status']}] {check['name']} {check['file']} missing={check['missing']}")
    write_text(TXT_OUT, "\n".join(lines) + "\n")
    print(PASS_MARKER if status == "PASS" else "EDGEIQ_DATA_WIRING_V1_FAIL")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
