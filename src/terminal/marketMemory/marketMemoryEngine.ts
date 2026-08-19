export type MarketMemoryRow = {
  horse: string;
  track: string;
  race: string;
  currentPrice: number;
  previousPrice: number;
  movementPct: number;
  movementType: string;
  timestamp: string;
};

export function classifyMovement(currentPrice: number, previousPrice: number): string {
  const delta = currentPrice - previousPrice;

  if (delta <= -0.40) return "STEAM";
  if (delta >= 0.40) return "DRIFT";

  return "HOLD";
}

export function calculateMovementPct(
  currentPrice: number,
  previousPrice: number
): number {
  if (!previousPrice || previousPrice <= 0) return 0;

  return ((currentPrice - previousPrice) / previousPrice) * 100;
}

export function buildMarketMemory(rows: any[]): MarketMemoryRow[] {
  return rows.map((row: any) => {
    const current =
      Number(
        row.best_odds ??
        row.market_price ??
        row.price ??
        0
      ) || 0;

    const previous =
      Number(
        row.previous_price ??
        row.opening_price ??
        current
      ) || current;

    return {
      horse: String(row.horse ?? ""),
      track: String(row.track ?? ""),
      race: String(row.race_no ?? ""),
      currentPrice: current,
      previousPrice: previous,
      movementPct: calculateMovementPct(current, previous),
      movementType: classifyMovement(current, previous),
      timestamp: new Date().toISOString(),
    };
  });
}
