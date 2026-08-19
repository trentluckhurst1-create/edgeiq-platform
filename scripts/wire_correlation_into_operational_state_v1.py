from pathlib import Path

types = Path("src/edgeiq-os/services/operational-state/OperationalRaceStateTypes.ts")
text = types.read_text(encoding="utf-8")

if "OperationalCorrelation" not in text:
    text = text.replace(
'''export interface IntelligenceCoverageItem {
  key: string;
  label: string;
  coveragePct: number;
  status: IntelligenceStatus;
}
''',
'''export interface IntelligenceCoverageItem {
  key: string;
  label: string;
  coveragePct: number;
  status: IntelligenceStatus;
}

export interface OperationalCorrelation {
  agreementScore: number;
  agreementBand: string;
  operationalConfidence: number;
  operationalPriority: string;
  reinforcement: string[];
  conflicts: string[];
  supportingModules: string[];
}
'''
    )

    text = text.replace(
'''  coverage: IntelligenceCoverageItem[];
  status: IntelligenceStatus;
}''',
'''  coverage: IntelligenceCoverageItem[];
  correlation: OperationalCorrelation;
  status: IntelligenceStatus;
}'''
    )

types.write_text(text, encoding="utf-8")

service = Path("src/edgeiq-os/services/operational-state/OperationalRaceStateService.ts")
text = service.read_text(encoding="utf-8")

if 'from "../operational-correlation"' not in text:
    text = text.replace(
'import { buildCoverageFromModules } from "../intelligence-coverage";',
'import { buildCoverageFromModules } from "../intelligence-coverage";\nimport { buildOperationalCorrelation } from "../operational-correlation";'
    )

if "const correlation = buildOperationalCorrelation();" not in text:
    text = text.replace(
"  const alerts = buildSystemAlerts();",
"  const alerts = buildSystemAlerts();\n  const correlation = buildOperationalCorrelation();"
    )

if "correlation," not in text:
    text = text.replace(
"    coverage: buildCoverageFromModules(moduleOutputs),",
"    coverage: buildCoverageFromModules(moduleOutputs),\n    correlation,"
    )

service.write_text(text, encoding="utf-8")

print("[EDGEIQ] Operational correlation wired into race state")
