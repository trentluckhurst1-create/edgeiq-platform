from pathlib import Path

path = Path("src/edgeiq-os/services/operational-state/OperationalRaceStateService.ts")
text = path.read_text(encoding="utf-8")

if 'buildOperationalCorrelation' not in text:
    text = text.replace(
        'import { buildCoverageFromModules } from "../intelligence-coverage";',
        'import { buildCoverageFromModules } from "../intelligence-coverage";\nimport { buildOperationalCorrelation } from "../operational-correlation";'
    )

if "const correlation = buildOperationalCorrelation(moduleOutputs);" not in text:
    text = text.replace(
        "  const alerts = buildSystemAlerts();",
        "  const alerts = buildSystemAlerts();\n  const correlation = buildOperationalCorrelation(moduleOutputs);"
    )

path.write_text(text, encoding="utf-8")

print("[EDGEIQ] correlation variable inserted")
