from pathlib import Path

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
text = path.read_text(encoding="utf-8")

service = root / "src" / "services" / "historyIndexService.ts"
service.write_text(r'''import type { CsvRow } from "../utils/edgeiqCsv";
import { cleanHorseLoose, cleanTrack } from "../utils/edgeiqFormat";
import { firstText, raceNo, track } from "../utils/raceRowHelpers";

type Row = CsvRow;

export function buildHistoryIndexes(params: {
  historyMasterRows: Row[];
  historyDetailRows: Row[];
  runnerFormHistoryRows: Row[];
  horseCareerRows: Row[];
  horserchetypeRows: Row[];
  horseTrajectoryRows: Row[];
  horseProjectionRows: Row[];
  historyRunnerLookupKey: (row: Row | undefined) => string;
  historyDateValue: (row: Row | undefined) => number;
  historyDetailMergeKey: (row: Row | undefined) => string;
  historyDetailMergeKeyLoose: (row: Row | undefined) => string;
}) {
  const {
    historyMasterRows,
    historyDetailRows,
    runnerFormHistoryRows,
    horseCareerRows,
    horserchetypeRows,
    horseTrajectoryRows,
    horseProjectionRows,
    historyRunnerLookupKey,
    historyDateValue,
    historyDetailMergeKey,
    historyDetailMergeKeyLoose,
  } = params;

  const historyMasterByHorse = new Map<string, Row[]>();
  historyMasterRows.forEach((historyRow) => {
    const historyKey = historyRunnerLookupKey(historyRow);
    if (!historyKey) return;
    const existing = historyMasterByHorse.get(historyKey);
    if (existing) existing.push(historyRow);
    else historyMasterByHorse.set(historyKey, [historyRow]);
  });
  historyMasterByHorse.forEach((rows) => rows.sort((a, b) => historyDateValue(b) - historyDateValue(a)));

  const historyMasterByTrackRaceHorse = new Map<string, Row[]>();
  historyMasterRows.forEach((historyRow) => {
    const historyKey = historyRunnerLookupKey(historyRow);
    const trackKey = cleanTrack(track(historyRow));
    const raceKey = raceNo(historyRow);
    const compositeKey = historyKey && trackKey && raceKey ? [historyKey, trackKey, raceKey].join("|") : "";
    if (!compositeKey) return;
    const existing = historyMasterByTrackRaceHorse.get(compositeKey);
    if (existing) existing.push(historyRow);
    else historyMasterByTrackRaceHorse.set(compositeKey, [historyRow]);
  });
  historyMasterByTrackRaceHorse.forEach((rows) => rows.sort((a, b) => historyDateValue(b) - historyDateValue(a)));

  const historyDetailByHorse = new Map<string, Row[]>();
  historyDetailRows.forEach((historyRow) => {
    const historyKey = historyRunnerLookupKey(historyRow);
    if (!historyKey) return;
    const existing = historyDetailByHorse.get(historyKey);
    if (existing) existing.push(historyRow);
    else historyDetailByHorse.set(historyKey, [historyRow]);
  });
  historyDetailByHorse.forEach((rows) => rows.sort((a, b) => historyDateValue(b) - historyDateValue(a)));

  const historyDetailByMergeKey = new Map<string, Row>();
  historyDetailRows.forEach((historyRow) => {
    const mergeKey = historyDetailMergeKey(historyRow);
    if (mergeKey && !historyDetailByMergeKey.has(mergeKey)) historyDetailByMergeKey.set(mergeKey, historyRow);
  });

  const historyDetailByLooseMergeKey = new Map<string, Row>();
  historyDetailRows.forEach((historyRow) => {
    const mergeKey = historyDetailMergeKeyLoose(historyRow);
    if (mergeKey && !historyDetailByLooseMergeKey.has(mergeKey)) historyDetailByLooseMergeKey.set(mergeKey, historyRow);
  });

  const runnerFormHistoryByHorse = new Map<string, Row[]>();
  runnerFormHistoryRows.forEach((historyRow) => {
    const historyKey = historyRunnerLookupKey(historyRow);
    if (!historyKey) return;
    const existing = runnerFormHistoryByHorse.get(historyKey);
    if (existing) existing.push(historyRow);
    else runnerFormHistoryByHorse.set(historyKey, [historyRow]);
  });
  runnerFormHistoryByHorse.forEach((rows) => rows.sort((a, b) => historyDateValue(b) - historyDateValue(a)));

  const horseCareerByHorse = new Map<string, Row>();
  horseCareerRows.forEach((careerRow) => {
    const horseKey = cleanHorseLoose(firstText(careerRow, ["horse_key"], "")) || cleanHorseLoose(firstText(careerRow, ["horse"], ""));
    if (!horseKey || horseCareerByHorse.has(horseKey)) return;
    horseCareerByHorse.set(horseKey, careerRow);
  });

  const horserchetypeByHorse = new Map<string, Row>();
  horserchetypeRows.forEach((archetypeRow) => {
    const horseKey = cleanHorseLoose(firstText(archetypeRow, ["horse_key"], "")) || cleanHorseLoose(firstText(archetypeRow, ["horse"], ""));
    if (!horseKey || horserchetypeByHorse.has(horseKey)) return;
    horserchetypeByHorse.set(horseKey, archetypeRow);
  });

  const horseTrajectoryByHorse = new Map<string, Row>();
  horseTrajectoryRows.forEach((trajectoryRow) => {
    const horseKey = cleanHorseLoose(firstText(trajectoryRow, ["horse_key"], "")) || cleanHorseLoose(firstText(trajectoryRow, ["horse"], ""));
    if (!horseKey || horseTrajectoryByHorse.has(horseKey)) return;
    horseTrajectoryByHorse.set(horseKey, trajectoryRow);
  });

  const horseProjectionByHorse = new Map<string, Row>();
  horseProjectionRows.forEach((projectionRow) => {
    const horseKey = cleanHorseLoose(firstText(projectionRow, ["horse_key"], "")) || cleanHorseLoose(firstText(projectionRow, ["horse"], ""));
    if (!horseKey || horseProjectionByHorse.has(horseKey)) return;
    horseProjectionByHorse.set(horseKey, projectionRow);
  });

  return {
    historyMasterByHorse,
    historyMasterByTrackRaceHorse,
    historyDetailByHorse,
    historyDetailByMergeKey,
    historyDetailByLooseMergeKey,
    runnerFormHistoryByHorse,
    horseCareerByHorse,
    horserchetypeByHorse,
    horseTrajectoryByHorse,
    horseProjectionByHorse,
  };
}
''', encoding="utf-8")

start = text.index(" const historyMasterByHorse = useMemo(() => {")
end = text.index("\n const formEnrichmentByRunnerKey = useMemo(() => {", start)

replacement = r''' const {
  historyMasterByHorse,
  historyMasterByTrackRaceHorse,
  historyDetailByHorse,
  historyDetailByMergeKey,
  historyDetailByLooseMergeKey,
  runnerFormHistoryByHorse,
  horseCareerByHorse,
  horserchetypeByHorse,
  horseTrajectoryByHorse,
  horseProjectionByHorse,
 } = useMemo(() => buildHistoryIndexes({
  historyMasterRows,
  historyDetailRows,
  runnerFormHistoryRows,
  horseCareerRows,
  horserchetypeRows,
  horseTrajectoryRows,
  horseProjectionRows,
  historyRunnerLookupKey,
  historyDateValue,
  historyDetailMergeKey,
  historyDetailMergeKeyLoose,
 }), [historyMasterRows, historyDetailRows, runnerFormHistoryRows, horseCareerRows, horserchetypeRows, horseTrajectoryRows, horseProjectionRows]);'''

text = text[:start] + replacement + text[end:]

import_line = 'import { buildHistoryIndexes } from "../services/historyIndexService";'
if import_line not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines) + "\n"

path.write_text(text, encoding="utf-8")
print("[HISTORY_INDEX_SERVICE_EXTRACT] complete")
