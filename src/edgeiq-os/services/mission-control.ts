import { getOperationalRaceState } from "./intelligence-orchestrator";

export type MissionControlModel = {
  meetingCount: number;
  raceCount: number;
  runnerCount: number;

  highestConfidence: {
    label: string;
    value: string;
  };

  largestOverlay: {
    label: string;
    value: string;
  };

  weatherWatch: {
    label: string;
    value: string;
  };

  operationalFocus: {
    label: string;
    value: string;
  };
};

export function buildMissionControlModel(): MissionControlModel {

  const raceState = getOperationalRaceState();

  const meetingName = raceState.meetingName ?? "Victoria";

  const raceName =
    raceState.raceName ??
    `${meetingName} R${raceState.raceNumber}`;

  return {

    meetingCount: 1,

    raceCount: 1,

    runnerCount: raceState.evidence.length,

    highestConfidence: {
      label: raceName,
      value: raceState.confidence >= 80
        ? "Very High"
        : raceState.confidence >= 65
          ? "High"
          : "Developing",
    },

    largestOverlay: {
      label: raceState.referenceRunner,
      value: raceState.decision.state,
    },

    weatherWatch: {
      label: raceState.trackCondition,
      value: raceState.rail,
    },

    operationalFocus: {
      label: raceState.decision.headline,
      value: raceState.decision.state,
    },

  };

}
