from pathlib import Path

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
text = path.read_text(encoding="utf-8")

service = root / "src" / "services" / "rankingService.ts"
service.write_text(r'''import type { CsvRow } from "../utils/edgeiqCsv";
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
''', encoding="utf-8")

old = ''' const rankedEnriched = useMemo(() => {
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
 }, [enriched]);
'''

new = ''' const rankedEnriched = useMemo(() => buildRankedEnriched({
  enriched,
  runnerRowKey,
  winPct,
 }), [enriched]);
'''

if old not in text:
    raise SystemExit("[ERROR] rankedEnriched block not found")

text = text.replace(old, new, 1)

import_line = 'import { buildRankedEnriched } from "../services/rankingService";'
if import_line not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines) + "\n"

path.write_text(text, encoding="utf-8")
print("[RANKING_SERVICE_EXTRACT] complete")
