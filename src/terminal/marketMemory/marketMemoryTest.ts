import { buildMarketMemory } from "./marketMemoryEngine";

const sampleRows = [
  {
    horse: "REAL HEIR",
    track: "MOE",
    race_no: "R8",
    best_odds: 5.5,
    previous_price: 7.0,
  },
  {
    horse: "THINK ABOUT HER",
    track: "MOE",
    race_no: "R8",
    best_odds: 26,
    previous_price: 18,
  },
];

const snapshots = buildMarketMemory(sampleRows);

console.log("====================================");
console.log("EDGEIQ MARKET MEMORY SNAPSHOT");
console.log("====================================");

console.table(snapshots);
