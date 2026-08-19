from pathlib import Path

targets = [
    Path("src/edgeiq-os/race/RaceFileV2.tsx"),
    Path("src/edgeiq-os/race/RaceFilePanel.tsx"),
    Path("src/edgeiq-os/race/EdgeiqRaceWorkspace.tsx"),
    Path("src/edgeiq-os/command/components/CommandExecutiveBrief.tsx"),
    Path("src/edgeiq-os/command/components/CommandOperationalStack.tsx"),
    Path("src/edgeiq-os/command/components/AgreementMatrix.tsx"),
    Path("src/edgeiq-os/command/components/ConfidenceProfile.tsx"),
    Path("src/edgeiq-os/command/components/IntelligenceTimeline.tsx"),
]

replacements = {
    '../services/race-file-v2': '../services/RaceFileService',
    '../services/speed-profile': '../services/SpeedProfileService',
    '../services/track-signature': '../services/TrackSignatureService',
    '../services/pressure-engine': '../services/PressureService',
    '../services/tempo-engine': '../services/TempoService',
    '../services/position-engine': '../services/PositionService',
    '../services/intelligence-report': '../services/RaceFlowService',
    '../../services/agreement-matrix': '../../services',
    '../../services/confidence-profile': '../../services',
    '../../services/intelligence-timeline': '../../services',
    '../../services/pressure-engine': '../../services/PressureService',
    '../../services/tempo-engine': '../../services/TempoService',
    '../../services/position-engine': '../../services/PositionService',
    '../../services/speed-profile': '../../services/SpeedProfileService',
    '../../services/track-signature': '../../services/TrackSignatureService',
    '../../services/intelligence-report': '../../services/RaceFlowService',
}

for path in targets:
    if not path.exists():
        continue

    text = path.read_text(encoding="utf-8")

    for old, new in replacements.items():
        text = text.replace(old, new)

    path.write_text(text, encoding="utf-8")

print("[EDGEIQ] Migrated EDGEiQ OS imports to canonical service facade")
