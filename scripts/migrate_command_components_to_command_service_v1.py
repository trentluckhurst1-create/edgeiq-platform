from pathlib import Path

services = Path("src/edgeiq-os/services")
components = [
    Path("src/edgeiq-os/command/components/AgreementMatrix.tsx"),
    Path("src/edgeiq-os/command/components/ConfidenceProfile.tsx"),
    Path("src/edgeiq-os/command/components/IntelligenceTimeline.tsx"),
    Path("src/edgeiq-os/command/components/CommandExecutiveBrief.tsx"),
]

(services / "CommandService.ts").write_text(r'''
import { buildCommandViewModel } from "./command-view-model";
import { buildAgreementMatrix } from "./agreement-matrix";
import { buildConfidenceProfile } from "./confidence-profile";
import { buildIntelligenceTimeline } from "./intelligence-timeline";

export type { CommandViewModel } from "./command-view-model";
export type { AgreementMatrix, AgreementItem } from "./agreement-matrix";
export type { ConfidenceProfile, ConfidenceSignal } from "./confidence-profile";
export type { IntelligenceTimeline, TimelineEvent } from "./intelligence-timeline";

export const CommandService = {
  buildViewModel: buildCommandViewModel,
  buildAgreementMatrix,
  buildConfidenceProfile,
  buildIntelligenceTimeline,
};

export {
  buildCommandViewModel,
  buildAgreementMatrix,
  buildConfidenceProfile,
  buildIntelligenceTimeline,
};
'''.lstrip(), encoding="utf-8")

for path in components:
    if not path.exists():
        continue

    text = path.read_text(encoding="utf-8")

    text = text.replace(
        'import { buildAgreementMatrix } from "../../services";',
        'import { CommandService } from "../../services/CommandService";'
    )

    text = text.replace(
        'import { buildConfidenceProfile } from "../../services";',
        'import { CommandService } from "../../services/CommandService";'
    )

    text = text.replace(
        'import { buildIntelligenceTimeline } from "../../services";',
        'import { CommandService } from "../../services/CommandService";'
    )

    text = text.replace(
        'import { buildAgreementMatrix } from "../../services/CommandService";',
        'import { CommandService } from "../../services/CommandService";'
    )

    text = text.replace(
        'import { buildConfidenceProfile } from "../../services/CommandService";',
        'import { CommandService } from "../../services/CommandService";'
    )

    text = text.replace(
        'import { buildIntelligenceTimeline } from "../../services/CommandService";',
        'import { CommandService } from "../../services/CommandService";'
    )

    text = text.replace("const matrix = buildAgreementMatrix();", "const matrix = CommandService.buildAgreementMatrix();")
    text = text.replace("const profile = buildConfidenceProfile();", "const profile = CommandService.buildConfidenceProfile();")
    text = text.replace("const timeline = buildIntelligenceTimeline();", "const timeline = CommandService.buildIntelligenceTimeline();")

    text = text.replace("const agreement = buildAgreementMatrix();", "const agreement = CommandService.buildAgreementMatrix();")
    text = text.replace("const confidence = buildConfidenceProfile();", "const confidence = CommandService.buildConfidenceProfile();")

    path.write_text(text, encoding="utf-8")

print("[EDGEIQ] Command components migrated to CommandService object")
