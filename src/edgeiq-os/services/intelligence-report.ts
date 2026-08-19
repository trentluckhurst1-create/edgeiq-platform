import type { IntelligenceReportModel } from "../intelligence";
import type { OperationalRaceState } from "./operational-state";
import { getOperationalRaceState } from "./intelligence-orchestrator";
import { buildPressureEngine } from "./pressure-engine";
import { buildTempoEngine } from "./tempo-engine";
import { buildPositionEngine } from "./position-engine";
import { buildSpeedProfile } from "./speed-profile";
import { buildTrackSignature } from "./track-signature";

export function buildRaceFlowReport(
  raceState: OperationalRaceState = getOperationalRaceState(),
): IntelligenceReportModel {
  const pressure = buildPressureEngine(raceState);
  const tempo = buildTempoEngine(raceState);
  const position = buildPositionEngine(raceState);
  const speed = buildSpeedProfile(raceState);
  const track = buildTrackSignature(raceState);

  return {
    title: "RaceFlow",
    assessment: `${pressure.summary} ${tempo.raceRead}`,
    operationalMeaning: `${pressure.tacticalRead} ${position.tacticalRead}`,
    supportingEngines: [
      { label: "Pressure Engine", status: pressure.band },
      { label: "Tempo Engine", status: tempo.band },
      { label: "Position Engine", status: position.position },
      { label: "SpeedProfile", status: speed.confidence },
      { label: "TrackSignature", status: track.todayPattern },
    ],
    evidence: [
      { label: "Pressure Engine", value: pressure.band, detail: pressure.summary },
      { label: "Tempo Engine", value: tempo.band, detail: tempo.expectedChange },
      { label: "Position Engine", value: position.position, detail: position.summary },
      { label: "Lane Read", value: position.lane, detail: "Lane evidence is shown without proprietary weighting." },
      { label: "SpeedProfile", value: speed.confidence, detail: speed.assessment },
      { label: "TrackSignature", value: track.todayPattern, detail: track.assessment },
    ],
    watch: [
      ...pressure.watch.slice(0, 2),
      ...tempo.watch.slice(0, 2),
      ...position.watch.slice(0, 2),
    ],
    confidence: pressure.confidence,
    lastUpdated: "Live",
  };
}

export function buildSpeedProfileReport(
  raceState: OperationalRaceState = getOperationalRaceState(),
): IntelligenceReportModel {
  const speed = buildSpeedProfile(raceState);

  return {
    title: "SpeedProfile",
    assessment: speed.assessment,
    operationalMeaning: speed.operationalMeaning,
    supportingEngines: [
      { label: "Launch", status: speed.launch },
      { label: "Cruise", status: speed.cruise },
      { label: "Pressure Response", status: speed.pressureResponse },
      { label: "Finish Strength", status: speed.finishStrength },
      { label: "Recovery", status: speed.recovery },
    ],
    evidence: [
      { label: "Launch", value: speed.launch, detail: "Early acceleration profile." },
      { label: "Cruise", value: speed.cruise, detail: "Sustained travel through the race." },
      { label: "Pressure Response", value: speed.pressureResponse, detail: "Ability to maintain efficiency under pressure." },
      { label: "Finish Strength", value: speed.finishStrength, detail: "Late-race closing capability." },
      { label: "Recovery", value: speed.recovery, detail: "Ability to absorb the race shape." },
    ],
    watch: speed.watch,
    confidence: speed.confidence,
    lastUpdated: "Live",
  };
}

export function buildTrackSignatureReport(
  raceState: OperationalRaceState = getOperationalRaceState(),
): IntelligenceReportModel {
  const track = buildTrackSignature(raceState);

  return {
    title: "TrackSignature",
    assessment: track.assessment,
    operationalMeaning: track.operationalMeaning,
    supportingEngines: [
      { label: "Rail", status: track.rail },
      { label: "Surface", status: track.surface },
      { label: "Moisture", status: track.moisture },
      { label: "Today Pattern", status: track.todayPattern },
    ],
    evidence: [
      { label: "Rail", value: track.rail, detail: "Rail setup included as evidence." },
      { label: "Surface", value: track.surface, detail: "Current track condition." },
      { label: "Wind", value: track.wind, detail: "Environment component reserved for active feed." },
      { label: "Moisture", value: track.moisture, detail: "Moisture influence interpreted at assessment level." },
      { label: "Historical Pattern", value: track.historicalPattern, detail: "Historical bias evidence reserved." },
      { label: "Today Pattern", value: track.todayPattern, detail: "Current-day pattern status." },
    ],
    watch: track.watch,
    confidence: track.confidence,
    lastUpdated: "Live",
  };
}
