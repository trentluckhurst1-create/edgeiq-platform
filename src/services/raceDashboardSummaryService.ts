import type { CsvRow } from "../utils/edgeiqCsv";
import { firstText, horse } from "../utils/raceRowHelpers";
import { edgePct, fairPrice, livePrice, winPct } from "./marketPricingService";
import { limitedAdjustedPrice } from "./runnerMetricsService";

type Row = CsvRow;

type RankedRunner = {
  row: Row;
  bet?: Row;
  modelRank?: number | null;
  [key: string]: any;
};

export function buildRaceDashboardSummary(params: {
  activeRaceRows: RankedRunner[];
  rankedEnriched: RankedRunner[];
  marketIntel: Row | undefined;
  mostLikelyWinner: string;
  mostLikelyFair: number | null;
  bestValue: string;
  bestValueEdge: number | null;
  raceClarity: string;
  displayExpectedTempo: string;
  bettingConfidence: string;
  band: (row: Row | undefined, keys: string[], fallback?: string) => string;
  bandColor: (value: string) => string;
}) {
  const {
    activeRaceRows,
    rankedEnriched,
    marketIntel,
    mostLikelyWinner,
    mostLikelyFair,
    bestValue,
    bestValueEdge,
    raceClarity,
    displayExpectedTempo,
    bettingConfidence,
    band,
    bandColor,
  } = params;

  const livePriceRowCount = activeRaceRows.filter((item) => (livePrice(item.row, item.bet) ?? 0) > 0).length;
  const overlayCountComputed = activeRaceRows.filter((item) => (edgePct(item.row, item.bet) ?? -999) > 0).length;
  const strongOverlayCountComputed = activeRaceRows.filter((item) => (edgePct(item.row, item.bet) ?? -999) >= 10).length;

  const topModelRow =
    [...activeRaceRows].sort(
      (a, b) =>
        (a.modelRank ?? 999) - (b.modelRank ?? 999) ||
        (winPct(b.row, b.bet) ?? -1) - (winPct(a.row, a.bet) ?? -1)
    )[0] || rankedEnriched[0];

  const bestValueItem =
    [...activeRaceRows].sort((a, b) => (edgePct(b.row, b.bet) ?? -999) - (edgePct(a.row, a.bet) ?? -999))[0] || topModelRow;

  const topWinChanceRunner = mostLikelyWinner || (topModelRow ? horse(topModelRow.row) : "");
  const topWinChanceFair =
    mostLikelyFair ?? (topModelRow ? limitedAdjustedPrice(topModelRow) ?? fairPrice(topModelRow.row, topModelRow.bet) : null);
  const bestValueRunner = bestValue || (bestValueItem ? horse(bestValueItem.row) : "");
  const bestValueEdgeDisplay = bestValueEdge ?? (bestValueItem ? edgePct(bestValueItem.row, bestValueItem.bet) : null);

  const marketEfficiency = band(marketIntel, ["market_efficiency"], livePriceRowCount ? "LIVE" : "PENDING");
  const overlayCountDisplay = firstText(marketIntel, ["overlay_count"], activeRaceRows.length ? String(overlayCountComputed) : "-");
  const strongOverlayCountDisplay = firstText(marketIntel, ["strong_overlay_count"], activeRaceRows.length ? String(strongOverlayCountComputed) : "-");

  const marketStatus =
    livePriceRowCount === 0
      ? "WITING FEED"
      : livePriceRowCount === activeRaceRows.length
      ? "TB LIVE"
      : "PARTIAL MRKET";

  const marketStatusTone =
    marketStatus === "TB LIVE" ? "#3ee68f" : marketStatus === "PARTIAL MRKET" ? "#ffffff" : "#ffffff";

  const marketEfficiencyTone =
    marketEfficiency === "LIVE" ? "#3ee68f" : marketEfficiency === "PENDING" ? "#ffffff" : bandColor(marketEfficiency);

  const chaosBand = firstText(params as any, ["chaos_band"], "");
  void chaosBand;

  const raceAssessmentNarrative = (() => {
    const clarityText = raceClarity === "-" ? "Race shape is still forming" : `Race is ${raceClarity}`;
    const tempoText = displayExpectedTempo === "-" ? "tempo is still settling" : `${displayExpectedTempo} tempo is expected`;
    const leaderText =
      topWinChanceRunner && bestValueRunner
        ? topWinChanceRunner === bestValueRunner
          ? "Performance Index currently places several runners under consideration."
          : "Performance Index and market pricing indicate several runners warrant investigation."
        : topWinChanceRunner
        ? "Performance Index is beginning to separate the field."
        : bestValueRunner
        ? "Market pricing differs from the Performance Index across parts of the field."
        : "No standout runner is established yet.";
    const confidenceText = bettingConfidence === "-" ? "Confidence is still forming." : `Confidence is ${bettingConfidence}.`;
    const marketText =
      marketStatus === "WITING FEED"
        ? "TB prices are not available yet."
        : `Market pricing is ${marketEfficiency.toLowerCase()} across the field.`;
    return `${clarityText} with ${tempoText}. ${leaderText} ${confidenceText} ${marketText}`;
  })();

  return {
    livePriceRowCount,
    overlayCountComputed,
    strongOverlayCountComputed,
    topModelRow,
    bestValueItem,
    topWinChanceRunner,
    topWinChanceFair,
    bestValueRunner,
    bestValueEdgeDisplay,
    marketEfficiency,
    overlayCountDisplay,
    strongOverlayCountDisplay,
    marketStatus,
    marketStatusTone,
    marketEfficiencyTone,
    raceAssessmentNarrative,
  };
}
