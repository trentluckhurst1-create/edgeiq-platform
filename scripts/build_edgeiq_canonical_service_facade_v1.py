from pathlib import Path

services = Path("src/edgeiq-os/services")
services.mkdir(parents=True, exist_ok=True)

canonical = {
  "RaceFileService.ts": '''
export { buildRaceFileV2 as buildRaceFile } from "./race-file-v2";
export type {
  RaceFileModelV1,
  RaceFileRunnerProfile,
  HistoricalRun,
  OfficialRaceData,
  OfficialRunnerData,
  EdgeiqSpeedProfileSplit,
} from "./race-file-model";
''',

  "SpeedProfileService.ts": '''
export { buildSpeedProfile } from "./speed-profile";
export type { SpeedProfileModel } from "./speed-profile";
''',

  "TrackSignatureService.ts": '''
export { buildTrackSignature } from "./track-signature";
export type { TrackSignatureModel } from "./track-signature";
''',

  "PressureService.ts": '''
export { buildPressureEngine } from "./pressure-engine";
export type { PressureEngineModel, PressureBand } from "./pressure-engine";
''',

  "TempoService.ts": '''
export { buildTempoEngine } from "./tempo-engine";
export type { TempoEngineModel, TempoBand } from "./tempo-engine";
''',

  "PositionService.ts": '''
export { buildPositionEngine } from "./position-engine";
export type { PositionEngineModel } from "./position-engine";
''',

  "CommandService.ts": '''
export { buildCommandViewModel } from "./command-view-model";
export type { CommandViewModel } from "./command-view-model";
''',

  "EvidenceService.ts": '''
export * from "./evidence";
''',

  "RunnerDNAService.ts": '''
export { RunnerDNAAdapter } from "./adapters/RunnerDNAAdapter";
export * from "./evidence/modules/runnerDnaEvidence";
''',

  "RaceFlowService.ts": '''
export { RaceShapeAdapter } from "./adapters/RaceShapeAdapter";
export { buildRaceFlowReport } from "./intelligence-report";
''',

  "MarketBehaviourService.ts": '''
export { MarketAdapter } from "./adapters/MarketAdapter";
export * from "./narrative/marketRelationship";
''',

  "RaceStrengthService.ts": '''
export type RaceStrengthBreakdown = {
  overall: number;
  speedQuality: number;
  pressureQuality: number;
  depth: number;
  finishStrength: number;
  historicalPercentile: number;
};

export function buildRaceStrengthBreakdown(): RaceStrengthBreakdown {
  return {
    overall: 0,
    speedQuality: 0,
    pressureQuality: 0,
    depth: 0,
    finishStrength: 0,
    historicalPercentile: 0,
  };
}
''',

  "RunRatingService.ts": '''
export type RunRatingBreakdown = {
  overall: number;
  early: number;
  mid: number;
  late: number;
  efficiency: number;
  pressureResponse: number;
};

export function buildRunRatingBreakdown(): RunRatingBreakdown {
  return {
    overall: 0,
    early: 0,
    mid: 0,
    late: 0,
    efficiency: 0,
    pressureResponse: 0,
  };
}
''',
}

for name, content in canonical.items():
    (services / name).write_text(content.strip() + "\n", encoding="utf-8")

(services / "index.ts").write_text('''
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
'''.strip() + "\n", encoding="utf-8")

print("[EDGEIQ] Canonical production service facade built")
