import {
  appendSnapshot,
  latestOverlayVelocity,
} from "./snapshotHistoryEngine";

const snapshots = appendSnapshot([], [
  {
    horse: "REAL HEIR",
    best_odds: 5.5,
    calculated_price: 4.2,
  },
  {
    horse: "THINK ABOUT HER",
    best_odds: 15,
    calculated_price: 9,
  },
]);

console.log("====================================");
console.log("EDGEIQ SNAPSHOT HISTORY");
console.log("====================================");

console.table(
  snapshots.map((row) => ({
    horse: row.horse,
    points: row.snapshots.length,
    velocity: latestOverlayVelocity(row),
  }))
);
