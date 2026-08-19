import { findLiveRunnerSnapshot, liveRaceRunnerSnapshot } from "./live-race-data-snapshot";
import type { RaceFileModelV1, HistoricalRun } from "./race-file-model";
import { getOperationalRaceState } from "./intelligence-orchestrator";
import { buildPressureEngine } from "./pressure-engine";
import { buildTempoEngine } from "./tempo-engine";
import { buildPositionEngine } from "./position-engine";
import { buildSpeedProfile } from "./speed-profile";
import { buildTrackSignature } from "./track-signature";

function sampleRun(index: number, runner: string): HistoricalRun {
  return {
    date: index === 0 ? "2026-06-12" : "2026-05-25",
    track: index === 0 ? "FLEM" : "CAUL",
    race: index === 0 ? "BM84 HCP" : "BM78 HCP",
    distance: index === 0 ? "1400m" : "1300m",
    raceClass: index === 0 ? "BM84" : "BM78",
    condition: index === 0 ? "GOOD 4" : "SOFT 5",
    barrier: index + 3,
    weight: index === 0 ? "58.0kg" : "57.5kg",
    jockey: index === 0 ? "J Allen" : "B Melham",
    sp: index === 0 ? "$5.50" : "$7.00",
    finish: index === 0 ? "2nd" : "4th",
    margin: index === 0 ? "0.4L" : "1.8L",
    officialRaceTime: index === 0 ? "1:22.36" : "1:16.88",
    edgeiqRaceStrength: index === 0 ? 87.4 : 82.1,
    edgeiqRunRating: index === 0 ? 89.6 : 84.8,
    relativePerformance: index === 0 ? "+2.7" : "+0.8",
    positionInRunning: {
      jump: "8th",
      m800: "7th",
      m600: "5th",
      m400: "4th",
      m200: "2nd",
      finish: index === 0 ? "2nd" : "4th",
    },
    speedProfile: [
      { marker: "800m", position: "7th", lengthsVsStandard: "+2.3L", expected: "+2.8L", variance: "+0.5L" },
      { marker: "600m", position: "5th", lengthsVsStandard: "+1.6L", expected: "+2.2L", variance: "+0.6L" },
      { marker: "400m", position: "4th", lengthsVsStandard: "+0.8L", expected: "+1.3L", variance: "+0.5L" },
      { marker: "200m", position: "2nd", lengthsVsStandard: "+0.2L", expected: "+0.6L", variance: "+0.4L" },
      { marker: "FINISH", position: index === 0 ? "2nd" : "4th", lengthsVsStandard: index === 0 ? "-0.1L" : "+1.0L", expected: "+0.0L", variance: index === 0 ? "-0.1L" : "+1.0L" },
    ],
    pressureRating: index === 0 ? 91 : 84,
    tempoRating: index === 0 ? 88 : 80,
    trackSignatureMatch: index === 0 ? "92%" : "81%",
    raceFlowMatch: index === 0 ? "Positive" : "Reference",
  };
}

export function buildRaceFileV2(): RaceFileModelV1 {
  const state = getOperationalRaceState();
  const pressure = buildPressureEngine(state);
  const tempo = buildTempoEngine(state);
  const position = buildPositionEngine(state);
  const speed = buildSpeedProfile(state);
  const track = buildTrackSignature(state);

  const names =
    liveRaceRunnerSnapshot.length > 0
      ? liveRaceRunnerSnapshot.map((runner) => runner.runner).filter(Boolean)
      : ["Runner 1", "Runner 2", "Runner 3", "Runner 4"];

  return {
    officialRace: {
      meeting: state.meetingName,
      raceNumber: state.raceNumber,
      raceName: state.raceName,
      distance: state.distance,
      raceClass: state.raceClass,
      trackCondition: state.trackCondition,
      rail: state.rail,
      officialRaceTime: "Pending result",
      prizeMoney: "Race file",
    },
    raceRead: {
      raceFlow: position.position,
      pressure: pressure.band,
      tempo: tempo.band,
      trackSignature: track.todayPattern,
      speedProfile: speed.confidence,
      confidence: pressure.confidence,
    },
    field: names.map((runner, index) => {
      const liveRunner = findLiveRunnerSnapshot(runner);

      return {
      official: {
        no: index + 1,
        runner,
        barrier: index + 2,
        weight: `${58 - index * 0.5}kg`,
        jockey: liveRunner?.jockey || (runner as any)?.jockey || (runner as any)?.official?.jockey || "Not listed",
        trainer: liveRunner?.trainer || (runner as any)?.trainer || (runner as any)?.official?.trainer || "Not listed",
        market: liveRunner?.market || (runner as any)?.market || (runner as any)?.official?.market || "Pending",
        status: "ACTIVE",
      },
      edgeRating: liveRunner?.edgeRating || (index === 0 ? "89.6" : index < 3 ? "84.0" : "Developing"),
      runnerDNA: liveRunner?.runnerDNA || (runner as any)?.runnerDNA || "Awaiting DNA",
      speedProfile: index === 0 ? speed.confidence : index < 3 ? "Strong" : "Developing",
      trackSignature: index === 0 ? track.todayPattern : "Reference",
      raceFlow: index === 0 ? "Positive" : "Monitoring",
      marketBehaviour: liveRunner?.market ? "Live market available" : "Market pending",
      assessment:
        index === 0
          ? "Key chance profile. Past form is available and should be tested against today's race."
          : "Capable profile, but needs the right race shape before taking a firm view.",
      historicalRuns: [sampleRun(0, runner), sampleRun(1, runner)],
    };
    }),
  };
}
