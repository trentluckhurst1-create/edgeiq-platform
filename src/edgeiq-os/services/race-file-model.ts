export type OfficialRaceData = {
  meeting: string;
  raceNumber: number;
  raceName: string;
  distance: string;
  raceClass: string;
  trackCondition: string;
  rail: string;
  officialRaceTime?: string;
  prizeMoney?: string;
};

export type OfficialRunnerData = {
  no: number;
  runner: string;
  barrier: number | string;
  weight: string;
  jockey: string;
  trainer: string;
  market: string;
  status: "ACTIVE" | "SCRATCHED";
};

export type EdgeiqSpeedProfileSplit = {
  marker: "800m" | "600m" | "400m" | "200m" | "FINISH";
  position: string;
  lengthsVsStandard: string;
  expected: string;
  variance: string;
};

export type HistoricalRun = {
  date: string;
  track: string;
  race: string;
  distance: string;
  raceClass: string;
  condition: string;
  barrier: number | string;
  weight: string;
  jockey: string;
  sp: string;
  finish: string;
  margin: string;
  officialRaceTime: string;

  edgeiqRaceStrength: number;
  edgeiqRunRating: number;
  relativePerformance: string;

  positionInRunning: {
    jump: string;
    m800: string;
    m600: string;
    m400: string;
    m200: string;
    finish: string;
  };

  speedProfile: EdgeiqSpeedProfileSplit[];

  pressureRating: number;
  tempoRating: number;
  trackSignatureMatch: string;
  raceFlowMatch: string;
};

export type RaceFileRunnerProfile = {
  official: OfficialRunnerData;
  edgeRating: string;
  runnerDNA: string;
  speedProfile: string;
  trackSignature: string;
  raceFlow: string;
  marketBehaviour: string;
  assessment: string;
  historicalRuns: HistoricalRun[];
};

export type RaceFileModelV1 = {
  officialRace: OfficialRaceData;
  raceRead: {
    raceFlow: string;
    pressure: string;
    tempo: string;
    trackSignature: string;
    speedProfile: string;
    confidence: string;
  };
  field: RaceFileRunnerProfile[];
};
