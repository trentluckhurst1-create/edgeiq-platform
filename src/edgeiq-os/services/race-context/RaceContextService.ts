import type { EdgeiqRaceContext } from "./RaceContextTypes";

export function getCommandRaceContext(): EdgeiqRaceContext {
  return {
    raceId: "BENDIGO_R5",
    track: "Bendigo",
    raceNo: "R5",
    raceLabel: "Bendigo R5",
    distance: "1400m",
    className: "BM64",
    trackCondition: "Good 4",
    railPosition: "Rail True",
    raceTime: "18:09:12",
    updatedAt: "18:09:12",
    feedHealth: "Healthy",
    scratchings: "None",
    confidenceBand: "High",
    referenceRunner: {
      name: "ALEGRON",
      number: "7",
      jockey: "J. Allen",
      trainer: "M. Moroney",
      marketPrice: "$8.50",
      previousMarketPrice: "$9.50",
    },
    weather: {
      state: "Stable",
      detail: "Low disruption signal",
    },
  };
}
