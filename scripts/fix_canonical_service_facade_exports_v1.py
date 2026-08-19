from pathlib import Path

services = Path("src/edgeiq-os/services")

patches = {
    "CommandService.ts": '''
export { buildCommandViewModel } from "./command-view-model";
export type { CommandViewModel } from "./command-view-model";
export { buildAgreementMatrix } from "./agreement-matrix";
export type { AgreementMatrix, AgreementItem } from "./agreement-matrix";
export { buildConfidenceProfile } from "./confidence-profile";
export type { ConfidenceProfile, ConfidenceSignal } from "./confidence-profile";
export { buildIntelligenceTimeline } from "./intelligence-timeline";
export type { IntelligenceTimeline, TimelineEvent } from "./intelligence-timeline";
''',

    "RaceFlowService.ts": '''
export {
  buildRaceFlowReport,
  buildSpeedProfileReport,
  buildTrackSignatureReport,
} from "./intelligence-report";
export { RaceShapeAdapter } from "./adapters/RaceShapeAdapter";
''',

    "RaceFileService.ts": '''
export {
  buildRaceFileV2,
  buildRaceFileV2 as buildRaceFile,
} from "./race-file-v2";
export type {
  RaceFileModelV1,
  RaceFileRunnerProfile,
  HistoricalRun,
  OfficialRaceData,
  OfficialRunnerData,
  EdgeiqSpeedProfileSplit,
} from "./race-file-model";
''',

    "index.ts": '''
export * from "./RaceFileService";
export * from "./SpeedProfileService";
export * from "./TrackSignatureService";
export * from "./PressureService";
export * from "./TempoService";
export * from "./PositionService";
export * from "./CommandService";
export * from "./EvidenceService";
export * from "./RunnerDNAService";
export * from "./RaceFlowService";
export * from "./MarketBehaviourService";
export * from "./RaceStrengthService";
export * from "./RunRatingService";
''',
}

for filename, content in patches.items():
    (services / filename).write_text(content.strip() + "\n", encoding="utf-8")

print("[EDGEIQ] Canonical service facade exports repaired")
