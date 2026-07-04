from pathlib import Path

path = Path(r".\src\terminal\tabs\MarketTab.tsx")
text = path.read_text(encoding="utf-8")

insert_marker = "function buildMarketFlow(tapeRows: Row[], selectedTrack: string, selectedRaceNo: string): MarketFlow {"

visible_helper = r'''
function buildMarketFlowFromRows(rows: MarketRunner[]): MarketFlow {
  const active = rows.filter((row) => !row.isScratched && row.live !== null && row.open !== null && row.open > 0);

  if (!active.length) return emptyMarketFlow();

  let firmingMoves = 0;
  let driftingMoves = 0;
  let stableMoves = 0;

  let largestFirm = "-";
  let largestFirmDelta: number | null = null;
  let largestDrift = "-";
  let largestDriftDelta: number | null = null;

  active.forEach((row) => {
    const live = row.live ?? 0;
    const open = row.open ?? 0;
    const delta = live - open;

    if (Math.abs(delta) < 0.001) {
      stableMoves += 1;
      return;
    }

    if (delta < 0) {
      firmingMoves += 1;
      if (largestFirmDelta === null || delta < largestFirmDelta) {
        largestFirmDelta = delta;
        largestFirm = row.horse;
      }
      return;
    }

    driftingMoves += 1;
    if (largestDriftDelta === null || delta > largestDriftDelta) {
      largestDriftDelta = delta;
      largestDrift = row.horse;
    }
  });

  const netFlow = firmingMoves - driftingMoves;

  const state =
    netFlow >= 4
      ? "AGGRESSIVE SUPPORT"
      : netFlow >= 2
        ? "SUPPORT"
        : netFlow <= -4
          ? "AGGRESSIVE DRIFT"
          : netFlow <= -2
            ? "DRIFTING"
            : "BALANCED";

  return {
    firmingMoves,
    driftingMoves,
    stableMoves,
    netFlow,
    largestFirm,
    largestFirmDelta,
    largestDrift,
    largestDriftDelta,
    state,
  };
}

'''

if "function buildMarketFlowFromRows" not in text:
    text = text.replace(insert_marker, visible_helper + insert_marker)

text = text.replace(
    'setMarketFlow(buildMarketFlow(tapeRows, selectedTrack, selectedRaceNo));',
    'setMarketFlow(buildMarketFlowFromRows(nextRows));'
)

text = text.replace(
    '<em>latest tape</em>',
    '<em>open to live</em>'
)

path.write_text(text, encoding="utf-8")
print("MARKET FLOW NOW USES VISIBLE OPEN TO LIVE ROWS")
