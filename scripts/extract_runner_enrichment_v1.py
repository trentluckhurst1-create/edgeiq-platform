from pathlib import Path

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
text = path.read_text(encoding="utf-8")

service = root / "src" / "services" / "runnerEnrichmentService.ts"
service.write_text(r'''import { cleanHorse, cleanHorseLoose, cleanTrack, num } from "../utils/edgeiqFormat";
import type { CsvRow } from "../utils/edgeiqCsv";
import { firstText, horse, raceNo, track } from "../utils/raceRowHelpers";

type Row = CsvRow;

export function buildEnrichedRunners(params: {
  raceRows: Row[];
  formEnrichmentRows: Row[];
  runnerIntelRows: Row[];
  v8Rows: Row[];
  betRows: Row[];
  reliabilityRows: Row[];
  horseDrawerRows: Row[];
  runnerDnaDrawerRows: Row[];
  explainabilityRows: Row[];
  connectionRows: Row[];
  limitedRows: Row[];
  customerIntelligenceRows: Row[];
  intelligenceSummaryRows: Row[];
  raceDayIntelligenceRows: Row[];
  runnerProfileRows: Row[];
  formIntelligenceRows: Row[];
  runnerFormRows: Row[];
  horseCareerByHorse: Map<string, Row>;
  horserchetypeByHorse: Map<string, Row>;
  horseTrajectoryByHorse: Map<string, Row>;
  horseProjectionByHorse: Map<string, Row>;
  campaignIntelligenceRows: Row[];
  hiddenGemRows: Row[];
  commandEnrichmentRows: Row[];
  mapEnrichmentRows: Row[];
  ratingsHeatmapRows: Row[];
  nexusContextualRows: Row[];
  historyMasterByHorse: Map<string, Row[]>;
  historyMasterByTrackRaceHorse: Map<string, Row[]>;
  historyDetailByHorse: Map<string, Row[]>;
  runnerFormHistoryByHorse: Map<string, Row[]>;
  historyDetailByMergeKey: Map<string, Row>;
  historyDetailByLooseMergeKey: Map<string, Row>;
  intelligenceScoreRows: Row[];
  factorScorecardRows: Row[];

  findSidecar: (rows: Row[], base: Row) => Row | undefined;
  findDnaSidecar: (rows: Row[], base: Row) => Row | undefined;
  findConnectionSidecar: (rows: Row[], base: Row) => Row | undefined;
  findSidecarByRaceHorse: (rows: Row[], base: Row) => Row | undefined;
  findCampaignSidecar: (rows: Row[], base: Row) => Row | undefined;
  findHiddenGemForRunner: (rows: Row[], base: Row) => Row | undefined;
  findCommandEnrichmentSidecar: (rows: Row[], base: Row) => Row | undefined;
  findNexusContextualSidecar: (rows: Row[], base: Row) => Row | undefined;
  findFormEnrichmentSidecar: (rows: Row[], base: Row) => Row | undefined;
  findHistoryMasterRowsForRunner: (row: Row, byHorse: Map<string, Row[]>, byTrackRaceHorse: Map<string, Row[]>) => Row[];
  mergeRunnerHistoryRows: (
    masterRows: Row[],
    detailRows: Row[],
    formRows: Row[],
    detailByMergeKey: Map<string, Row>,
    detailByLooseMergeKey: Map<string, Row>
  ) => Row[];
}) {
  const {
    raceRows,
    formEnrichmentRows,
    runnerIntelRows,
    v8Rows,
    betRows,
    reliabilityRows,
    horseDrawerRows,
    runnerDnaDrawerRows,
    explainabilityRows,
    connectionRows,
    limitedRows,
    customerIntelligenceRows,
    intelligenceSummaryRows,
    raceDayIntelligenceRows,
    runnerProfileRows,
    formIntelligenceRows,
    runnerFormRows,
    horseCareerByHorse,
    horserchetypeByHorse,
    horseTrajectoryByHorse,
    horseProjectionByHorse,
    campaignIntelligenceRows,
    hiddenGemRows,
    commandEnrichmentRows,
    mapEnrichmentRows,
    ratingsHeatmapRows,
    nexusContextualRows,
    historyMasterByHorse,
    historyMasterByTrackRaceHorse,
    historyDetailByHorse,
    runnerFormHistoryByHorse,
    historyDetailByMergeKey,
    historyDetailByLooseMergeKey,
    intelligenceScoreRows,
    factorScorecardRows,
    findSidecar,
    findDnaSidecar,
    findConnectionSidecar,
    findSidecarByRaceHorse,
    findCampaignSidecar,
    findHiddenGemForRunner,
    findCommandEnrichmentSidecar,
    findNexusContextualSidecar,
    findFormEnrichmentSidecar,
    findHistoryMasterRowsForRunner,
    mergeRunnerHistoryRows,
  } = params;

  const formDirectMap = new Map<string, Row>();

  formEnrichmentRows.forEach((formRow) => {
    const directKey = [
      firstText(formRow, ["race_date"], ""),
      cleanTrack(firstText(formRow, ["track"], "")),
      String(firstText(formRow, ["race_no"], "")).replace(/^R/i, ""),
      cleanHorseLoose(firstText(formRow, ["horse_key"], "")) || cleanHorseLoose(firstText(formRow, ["horse"], "")),
    ].join("|");

    formDirectMap.set(directKey, formRow);
  });

  return raceRows.map((row) => {
    const runnerIntel = findSidecar(runnerIntelRows, row);
    const v8 = findSidecar(v8Rows, row);
    const bet = findSidecar(betRows, row);
    const rel = findSidecar(reliabilityRows, row);
    const drawer = findSidecar(horseDrawerRows, row);
    const dna = findDnaSidecar(runnerDnaDrawerRows, row);
    const explainability = findSidecar(explainabilityRows, row);
    const connection = findConnectionSidecar(connectionRows, row);
    const limited = findSidecar(limitedRows, row);
    const customerIntel = findSidecar(customerIntelligenceRows, row);
    const intelligenceSummary = findSidecarByRaceHorse(intelligenceSummaryRows, row);
    const raceDayIntelligence = findSidecarByRaceHorse(raceDayIntelligenceRows, row);
    const runnerProfile = findSidecarByRaceHorse(runnerProfileRows, row);
    const formIntelligence = findSidecarByRaceHorse(formIntelligenceRows, row);
    const runnerForm = findSidecarByRaceHorse(runnerFormRows, row);

    const runnerHistoryKey =
      cleanHorseLoose(firstText(row, ["horse_key"], "")) ||
      cleanHorseLoose(horse(row));

    const runnerCareer = horseCareerByHorse.get(runnerHistoryKey);
    const runnerrchetype = horserchetypeByHorse.get(runnerHistoryKey);
    const runnerTrajectory = horseTrajectoryByHorse.get(runnerHistoryKey);
    const runnerProjection = horseProjectionByHorse.get(runnerHistoryKey);
    const campaign = findCampaignSidecar(campaignIntelligenceRows, row);
    const hiddenGem = findHiddenGemForRunner(hiddenGemRows, row);
    const commandEnrichment = findCommandEnrichmentSidecar(commandEnrichmentRows, row);
    const mapEnrichment = findSidecarByRaceHorse(mapEnrichmentRows, row);
    const ratingsHeatmap = findSidecarByRaceHorse(ratingsHeatmapRows, row);
    const nexusContextual = findNexusContextualSidecar(nexusContextualRows, row);

    const formDirectKey = [
      firstText(row, ["race_date"], ""),
      cleanTrack(firstText(row, ["track"], "")),
      String(firstText(row, ["race_no"], "")).replace(/^R/i, ""),
      cleanHorseLoose(firstText(row, ["horse_key"], "")) || cleanHorseLoose(firstText(row, ["horse"], "")),
    ].join("|");

    const formEnrichment =
      formDirectMap.get(formDirectKey) ||
      findFormEnrichmentSidecar(formEnrichmentRows, row);

    const runnerHistoryMaster = findHistoryMasterRowsForRunner(row, historyMasterByHorse, historyMasterByTrackRaceHorse);
    const runnerHistoryDetail = historyDetailByHorse.get(runnerHistoryKey) || [];
    const runnerHistoryForm = runnerFormHistoryByHorse.get(runnerHistoryKey) || [];

    const runnerHistory = mergeRunnerHistoryRows(
      runnerHistoryMaster,
      runnerHistoryDetail,
      runnerHistoryForm,
      historyDetailByMergeKey,
      historyDetailByLooseMergeKey,
    );

    const intel = findSidecar(intelligenceScoreRows, row);
    const rowJoinKey = firstText(dna, ["join_key"], "") || firstText(row, ["join_key"], "");

    const factorRows = factorScorecardRows
      .filter((factorRow) => {
        const factorJoinKey = firstText(factorRow, ["join_key"], "");
        if (rowJoinKey && factorJoinKey) return factorJoinKey === rowJoinKey;
        return cleanTrack(track(factorRow)) === cleanTrack(track(row)) && raceNo(factorRow) === raceNo(row) && cleanHorse(horse(factorRow)) === cleanHorse(horse(row));
      })
      .sort((a, b) => (num(a.factor_order) ?? 999) - (num(b.factor_order) ?? 999));

    return {
      row,
      runnerIntel,
      v8,
      bet,
      rel,
      drawer,
      dna,
      explainability,
      connection,
      limited,
      intel,
      customerIntel,
      intelligenceSummary,
      raceDayIntelligence,
      runnerProfile,
      formIntelligence,
      runnerForm,
      runnerHistory,
      runnerCareer,
      runnerrchetype,
      runnerTrajectory,
      runnerProjection,
      campaign,
      hiddenGem,
      commandEnrichment,
      mapEnrichment,
      formEnrichment,
      ratingsHeatmap,
      nexusContextual,
      factorRows,
    };
  });
}
''', encoding="utf-8")

start = text.index(" const enriched = useMemo(() => {")
end = text.index("\n\n const rankedEnriched = useMemo", start)

replacement = r''' const enriched = useMemo(() => buildEnrichedRunners({
  raceRows,
  formEnrichmentRows,
  runnerIntelRows,
  v8Rows,
  betRows,
  reliabilityRows,
  horseDrawerRows,
  runnerDnaDrawerRows,
  explainabilityRows,
  connectionRows,
  limitedRows,
  customerIntelligenceRows,
  intelligenceSummaryRows,
  raceDayIntelligenceRows,
  runnerProfileRows,
  formIntelligenceRows,
  runnerFormRows,
  horseCareerByHorse,
  horserchetypeByHorse,
  horseTrajectoryByHorse,
  horseProjectionByHorse,
  campaignIntelligenceRows,
  hiddenGemRows,
  commandEnrichmentRows,
  mapEnrichmentRows,
  ratingsHeatmapRows,
  nexusContextualRows,
  historyMasterByHorse,
  historyMasterByTrackRaceHorse,
  historyDetailByHorse,
  runnerFormHistoryByHorse,
  historyDetailByMergeKey,
  historyDetailByLooseMergeKey,
  intelligenceScoreRows,
  factorScorecardRows,
  findSidecar,
  findDnaSidecar,
  findConnectionSidecar,
  findSidecarByRaceHorse,
  findCampaignSidecar,
  findHiddenGemForRunner,
  findCommandEnrichmentSidecar,
  findNexusContextualSidecar,
  findFormEnrichmentSidecar,
  findHistoryMasterRowsForRunner,
  mergeRunnerHistoryRows,
 }), [raceRows, runnerIntelRows, v8Rows, betRows, reliabilityRows, horseDrawerRows, runnerDnaDrawerRows, explainabilityRows, connectionRows, factorScorecardRows, limitedRows, intelligenceScoreRows, customerIntelligenceRows, intelligenceSummaryRows, runnerProfileRows, formIntelligenceRows, runnerFormRows, historyMasterByHorse, historyMasterByTrackRaceHorse, historyDetailByHorse, historyDetailByMergeKey, historyDetailByLooseMergeKey, runnerFormHistoryByHorse, horseCareerByHorse, horserchetypeByHorse, horseTrajectoryByHorse, horseProjectionByHorse, campaignIntelligenceRows, hiddenGemRows, commandEnrichmentRows, mapEnrichmentRows, formEnrichmentRows, ratingsHeatmapRows, nexusContextualRows]);'''

text = text[:start] + replacement + text[end:]

import_line = 'import { buildEnrichedRunners } from "../services/runnerEnrichmentService";'
if import_line not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines) + "\n"

path.write_text(text, encoding="utf-8")
print("[RUNNER_ENRICHMENT_EXTRACT] complete")
