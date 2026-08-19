import { getOperationalRaceState } from "./intelligence-orchestrator";
import { buildSpeedProfile } from "./speed-profile";
import { buildTrackSignature } from "./track-signature";
import { buildPressureEngine } from "./pressure-engine";
import { buildTempoEngine } from "./tempo-engine";
import { buildPositionEngine } from "./position-engine";

export type RaceFileRunner = {
  no: number;
  runner: string;
  barrier: number;
  rating: string;
  form: string;
  speedProfile: string;
  runnerDNA: string;
  market: string;
  assessment: string;
};

export type RaceFileModel = {
  race: {
    meeting: string;
    raceNumber: number;
    raceName: string;
    distance: string;
    className: string;
    condition: string;
    rail: string;
  };
  raceRead: {
    pressure: string;
    tempo: string;
    position: string;
    trackSignature: string;
    speedProfile: string;
  };
  runners: RaceFileRunner[];
};

export function buildRaceFile(): RaceFileModel {
  const state = getOperationalRaceState();
  const speed = buildSpeedProfile(state);
  const track = buildTrackSignature(state);
  const pressure = buildPressureEngine(state);
  const tempo = buildTempoEngine(state);
  const position = buildPositionEngine(state);

  const runnerNames = [
    state.referenceRunner,
    "Runner Profile 2",
    "Runner Profile 3",
    "Runner Profile 4",
    "Runner Profile 5",
    "Runner Profile 6",
    "Runner Profile 7",
    "Runner Profile 8",
  ].filter(Boolean);

  const runners = runnerNames.map((runner, index) => ({
    no: index + 1,
    runner,
    barrier: index + 2,
    rating: index === 0 ? "Primary watch" : index < 3 ? "Positive" : "Developing",
    form: index === 0 ? "Consistent" : index < 4 ? "Mixed" : "Unknown",
    speedProfile: index === 0 ? speed.confidence : index < 3 ? "Strong" : "Developing",
    runnerDNA: index === 0 ? "Aligned" : index < 4 ? "Neutral" : "Watch",
    market: index === 0 ? "Monitor" : index < 3 ? "Neutral" : "Unconfirmed",
    assessment: index === 0 ? "Key reference runner" : index < 3 ? "Contender profile" : "Needs evidence",
  }));

  return {
    race: {
      meeting: state.meetingName,
      raceNumber: state.raceNumber,
      raceName: state.raceName,
      distance: state.distance,
      className: state.raceClass,
      condition: state.trackCondition,
      rail: state.rail,
    },
    raceRead: {
      pressure: pressure.band,
      tempo: tempo.band,
      position: position.position,
      trackSignature: track.todayPattern,
      speedProfile: speed.confidence,
    },
    runners,
  };
}
