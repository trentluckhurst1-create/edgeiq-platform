export type SnapshotRow = {
  horse: string;
  timestamp: string;
  marketPrice: number;
  ratedPrice: number;
  overlayPct: number;
};

export type SnapshotSeries = {
  horse: string;
  snapshots: SnapshotRow[];
};

function num(value: unknown): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function buildSnapshotRow(row: any): SnapshotRow {
  const marketPrice =
    num(row.best_odds) ||
    num(row.market_price) ||
    num(row.price);

  const ratedPrice =
    num(row.calculated_price) ||
    num(row.rated_price) ||
    num(row.rating_price);

  const overlayPct =
    ratedPrice > 0
      ? ((marketPrice - ratedPrice) / ratedPrice) * 100
      : 0;

  return {
    horse: String(row.horse ?? ""),
    timestamp: new Date().toISOString(),
    marketPrice,
    ratedPrice,
    overlayPct,
  };
}

export function appendSnapshot(
  existing: SnapshotSeries[],
  rows: any[]
): SnapshotSeries[] {
  const next = [...existing];

  rows.forEach((row: any) => {
    const snapshot = buildSnapshotRow(row);

    const existingSeries = next.find(
      (item) => item.horse === snapshot.horse
    );

    if (existingSeries) {
      existingSeries.snapshots.push(snapshot);

      existingSeries.snapshots =
        existingSeries.snapshots.slice(-25);
    } else {
      next.push({
        horse: snapshot.horse,
        snapshots: [snapshot],
      });
    }
  });

  return next;
}

export function latestOverlayVelocity(
  series: SnapshotSeries
): number {
  if (series.snapshots.length < 2) return 0;

  const latest =
    series.snapshots[series.snapshots.length - 1];

  const previous =
    series.snapshots[series.snapshots.length - 2];

  return latest.overlayPct - previous.overlayPct;
}
