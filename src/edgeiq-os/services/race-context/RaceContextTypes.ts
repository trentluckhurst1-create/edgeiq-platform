export type EdgeiqRaceContext = {
  raceId: string;
  track: string;
  raceNo: string;
  raceLabel: string;
  distance: string;
  className: string;
  trackCondition: string;
  railPosition: string;
  raceTime: string;
  updatedAt: string;
  feedHealth: string;
  scratchings: string;
  confidenceBand: string;
  referenceRunner: {
    name: string;
    number: string;
    jockey: string;
    trainer: string;
    marketPrice: string;
    previousMarketPrice: string;
  };
  weather: {
    state: string;
    detail: string;
  };
};
