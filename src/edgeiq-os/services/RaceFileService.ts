import { buildRaceFileV2 } from "./race-file-v2";
import { buildRaceStrengthBreakdown } from "./RaceStrengthService";
import { buildRunRatingBreakdown } from "./RunRatingService";
import { buildAssignmentComparison } from "./CompareService";

export type {
  RaceFileModelV1,
  RaceFileRunnerProfile,
  HistoricalRun,
  OfficialRaceData,
  OfficialRunnerData,
  EdgeiqSpeedProfileSplit,
} from "./race-file-model";

function buildRunNarrative(run: any, runRating: any, raceStrength: any, assignment: any): string {
  if (assignment.score >= 88 && runRating.overall >= 86 && raceStrength.overall >= 80) {
    return "Strong historical evidence for today's assignment.";
  }

  if (runRating.overall >= 88 && String(run?.finish ?? "").toUpperCase() !== "1ST") {
    return "Strong in defeat. The performance rated better than the finishing position suggests.";
  }

  if (assignment.score >= 80) {
    return "Relevant historical assignment with usable evidence for today.";
  }

  if (raceStrength.overall < 62) {
    return "Form line requires caution due to weaker race strength.";
  }

  return "Background form. Useful context, but not a primary match for today.";
}

export function buildProfessionalRaceBook() {
  const file = buildRaceFileV2();

  const today = {
    race: `${file.officialRace.meeting} R${file.officialRace.raceNumber}`,
    distance: file.officialRace.distance,
    className: file.officialRace.raceClass,
    condition: file.officialRace.trackCondition,
    rail: file.officialRace.rail,
    pressure: file.raceRead.pressure,
    tempo: file.raceRead.tempo,
    trackSignature: file.raceRead.trackSignature,
    speedProfile: file.raceRead.speedProfile,
  };

  const field = file.field.map((runner: any) => {
    const historicalRuns = (runner.historicalRuns ?? []).map((run: any) => {
      const runRating = buildRunRatingBreakdown(run);
      const raceStrength = buildRaceStrengthBreakdown(run);
      const assignment = buildAssignmentComparison(today, run);

      return {
        ...run,
        professionalForm: {
          official: {
            date: run.date,
            track: run.track,
            race: run.race,
            distance: run.distance,
            raceClass: run.raceClass,
            condition: run.condition,
            rail: run.rail ?? "Not recorded",
            barrier: run.barrier,
            weight: run.weight,
            jockey: run.jockey,
            sp: run.sp,
            finish: run.finish,
            margin: run.margin,
            officialRaceTime: run.officialRaceTime,
            winnerTime: run.winnerTime ?? "Not recorded",
            fieldSize: run.fieldSize ?? "Not recorded",
          },
          evidence: {
            runRating,
            raceStrength,
            speedProfile: run.speedProfile,
            pressure: run.pressureRating,
            tempo: run.tempoRating,
            trackSignature: run.trackSignatureMatch,
            raceFlow: run.raceFlowMatch,
            runnerDNA: runner.runnerDNA,
            narrative: buildRunNarrative(run, runRating, raceStrength, assignment),
          },
          assignment,
        },
      };
    });

    return {
      ...runner,
      historicalRuns,
      evidenceRuns: [...historicalRuns].sort(
        (a: any, b: any) =>
          (b.professionalForm?.assignment?.score ?? 0) -
          (a.professionalForm?.assignment?.score ?? 0)
      ),
    };
  });

  return {
    ...file,
    field,
    raceBook: {
      official: {
        meeting: file.officialRace.meeting,
        raceNumber: file.officialRace.raceNumber,
        raceName: file.officialRace.raceName,
        distance: file.officialRace.distance,
        raceClass: file.officialRace.raceClass,
        trackCondition: file.officialRace.trackCondition,
        rail: file.officialRace.rail,
        officialRaceTime: file.officialRace.officialRaceTime ?? "Pending",
        prizeMoney: file.officialRace.prizeMoney ?? "Pending",
        fieldSize: file.field.length,
      },
      intelligence: {
        raceFlow: file.raceRead.raceFlow,
        pressure: file.raceRead.pressure,
        tempo: file.raceRead.tempo,
        trackSignature: file.raceRead.trackSignature,
        speedProfile: file.raceRead.speedProfile,
        confidence: file.raceRead.confidence,
        raceStrength: buildRaceStrengthBreakdown(),
        runRating: buildRunRatingBreakdown(),
      },
    },
  };
}

export const RaceFileService = {
  build: buildRaceFileV2,
  buildRaceBook: buildProfessionalRaceBook,
};

export { buildRaceFileV2, buildRaceFileV2 as buildRaceFile };
