from pathlib import Path

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
text = path.read_text(encoding="utf-8")

service = root / "src" / "services" / "historyService.ts"

start = text.index("function historyDateText(row: Row | undefined): string {")
end = text.index("\nfunction ordinal(value: number | null): string {", start)

block = text[start:end]

service_text = '''import type { CsvRow } from "../utils/edgeiqCsv";
import { cleanHorseLoose, cleanTrack, money, num } from "../utils/edgeiqFormat";
import { firstNum, firstText, raceNo, track } from "../utils/raceRowHelpers";

type Row = CsvRow;

''' + block

service_text = service_text.replace("function ", "export function ")

service.write_text(service_text, encoding="utf-8")

text = text[:start] + text[end:]

import_line = 'import { compactHistoryLine, findHistoryMasterRowsForRunner, formatHistoryDate, hasHistoricalRating, historyBarrierText, historyClassText, historyDateText, historyDateValue, historyDetailMergeKey, historyDetailMergeKeyLoose, historyDistanceText, historyFieldSizeText, historyFinishText, historyGoingText, historyJockeyText, historyRaceNoText, historyRaceStrengthText, historyRatingValue, historyRunnerLookupKey, historyRunKey, historySpText, historyTrackText, historyWeightText, mergeRunnerHistoryRows, ratedHistoryRows, ratingVariance, renderStaticMetricValue } from "../services/historyService";'

if import_line not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines) + "\n"

path.write_text(text, encoding="utf-8")
print("[HISTORY_SERVICE_EXTRACT] complete")
