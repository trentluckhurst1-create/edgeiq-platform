import type { CsvRow } from "../utils/edgeiqCsv";
import { firstNum } from "../utils/raceRowHelpers";

type RankedInput = {
  row: CsvRow;
  bet?: CsvRow;
  [key: string]: any;
};

export function buildRankedEnriched<T extends RankedInput>(params: {
  enriched: T[];
  runnerRowKey: (row: CsvRow) => string;
  winPct: (row: CsvRow, bet?: CsvRow) => number | null;
}): Array<T & { modelRank: number | null }> {
  const { enriched, runnerRowKey, winPct } = params;

  const fallbackOrder = [...enriched]
    .sort((a, b) => {
      const rawProb = firstNum(a.row, ["V6_1_RESERCH_probability"]);
      const rawProbB = firstNum(b.row, ["V6_1_RESERCH_probability"]);
      const prob = winPct(a.row, a.bet) ?? (rawProb === null ? -1 : rawProb * 100);
      const probB = winPct(b.row, b.bet) ?? (rawProbB === null ? -1 : rawProbB * 100);
      return probB - prob;
    })
    .map((item, index) => [runnerRowKey(item.row), index + 1] as const);

  const fallbackRankMap = new Map<string, number>(fallbackOrder);

  return enriched.map((item) => {
    const explicitRank =
      firstNum(item.row, ["V6_1_RESERCH_price_rank", "price_rank", "final_probability_rank_used", "runner_rank"]) ??
      fallbackRankMap.get(runnerRowKey(item.row)) ??
      null;

    return {
      ...item,
      modelRank: explicitRank === null ? null : Math.max(1, Math.round(explicitRank)),
    };
  });
}
