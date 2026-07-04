from pathlib import Path

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
text = path.read_text(encoding="utf-8")

services_dir = root / "src" / "services"
services_dir.mkdir(exist_ok=True)

service = services_dir / "edgeiqDataLoader.ts"
service.write_text(r'''import { FILES } from "../config/edgeiqFiles";
import { loadCsv, type CsvRow } from "../utils/edgeiqCsv";

export type EdgeIQData = {
  runner: CsvRow[];
  runnerIntel: CsvRow[];
  v8: CsvRow[];
  bet: CsvRow[];
  rel: CsvRow[];
  cards: CsvRow[];
  briefing: CsvRow[];
  marketIntel: CsvRow[];
  verdict: CsvRow[];
  trackIntel: CsvRow[];
  horseDrawer: CsvRow[];
  runnerDnaDrawer: CsvRow[];
  explainability: CsvRow[];
  connection: CsvRow[];
  factorScorecard: CsvRow[];
  limited: CsvRow[];
  intelligenceScore: CsvRow[];
  customerIntelligence: CsvRow[];
  intelligenceSummary: CsvRow[];
  raceDayIntelligence: CsvRow[];
  runnerProfile: CsvRow[];
  formIntelligence: CsvRow[];
  runnerForm: CsvRow[];
  runnerFormHistory: CsvRow[];
  historyMaster: CsvRow[];
  historyDetail: CsvRow[];
  horseCareer: CsvRow[];
  horserchetype: CsvRow[];
  horseTrajectory: CsvRow[];
  horseProjection: CsvRow[];
  campaignIntelligence: CsvRow[];
  hiddenGem: CsvRow[];
  raceShapeFallback: CsvRow[];
  mapEnrichment: CsvRow[];
  chaosIndex: CsvRow[];
  opportunityScore: CsvRow[];
  commandEnrichment: CsvRow[];
  formEnrichment: CsvRow[];
  ratingsHeatmap: CsvRow[];
  productMeetings: CsvRow[];
  raceList: CsvRow[];
  meetingCalendar: CsvRow[];
  liveTrackIntelligence: CsvRow[];
  trackMapManifest: CsvRow[];
  nexusContextual: CsvRow[];
  nexusContextualFallback: CsvRow[];
  formSectionalProfile: CsvRow[];
  gearProfile: CsvRow[];
  labPriceEngine: CsvRow[];
};

export async function loadEdgeIQData(): Promise<EdgeIQData> {
  const [
    runner, runnerIntel, v8, bet, rel, cards, briefing, marketIntel, verdict, trackIntel,
    horseDrawer, runnerDnaDrawer, explainability, connection, factorScorecard, limited,
    intelligenceScore, customerIntelligence, intelligenceSummary, raceDayIntelligence,
    runnerProfile, formIntelligence, runnerForm, runnerFormHistory, historyMaster,
    historyDetail, horseCareer, horserchetype, horseTrajectory, horseProjection,
    campaignIntelligence, hiddenGem, raceShapeFallback, mapEnrichment, chaosIndex,
    opportunityScore, commandEnrichment, formEnrichment, ratingsHeatmap, productMeetings,
    raceList, meetingCalendar, liveTrackIntelligence, trackMapManifest, nexusContextual,
    nexusContextualFallback, formSectionalProfile, gearProfile, labPriceEngine
  ] = await Promise.all([
    loadCsv(FILES.runnerBoard),
    loadCsv(FILES.runnerIntel),
    loadCsv(FILES.v8),
    loadCsv(FILES.betQuality),
    loadCsv(FILES.reliability),
    loadCsv(FILES.intelligenceCards),
    loadCsv(FILES.briefing),
    loadCsv(FILES.marketIntel),
    loadCsv(FILES.verdict),
    loadCsv(FILES.trackIntel),
    loadCsv(FILES.horseDrawer),
    loadCsv(FILES.runnerDnaDrawer),
    loadCsv(FILES.explainability),
    loadCsv(FILES.connectionIntelligence),
    loadCsv(FILES.factorScorecard),
    loadCsv(FILES.limited),
    loadCsv(FILES.intelligenceScore),
    loadCsv(FILES.customerIntelligence),
    loadCsv(FILES.intelligenceSummary),
    loadCsv(FILES.raceDayIntelligence),
    loadCsv(FILES.runnerProfile),
    loadCsv(FILES.formIntelligence),
    loadCsv(FILES.runnerForm),
    loadCsv(FILES.runnerFormHistory),
    loadCsv(FILES.historyMaster),
    loadCsv(FILES.historyDetail),
    loadCsv(FILES.horseCareer),
    loadCsv(FILES.horserchetype),
    loadCsv(FILES.horseTrajectory),
    loadCsv(FILES.horseProjection),
    loadCsv(FILES.campaignIntelligence),
    loadCsv(FILES.hiddenGem),
    loadCsv(FILES.raceShapeFallback),
    loadCsv(FILES.mapEnrichment),
    loadCsv(FILES.chaosIndex),
    loadCsv(FILES.opportunityScore),
    loadCsv(FILES.commandEnrichment),
    loadCsv(FILES.formEnrichment),
    loadCsv(FILES.ratingsHeatmap),
    loadCsv(FILES.productMeetings),
    loadCsv(FILES.raceList),
    loadCsv(FILES.meetingCalendar),
    loadCsv(FILES.liveTrackIntelligence),
    loadCsv(FILES.trackMapManifest),
    loadCsv(FILES.nexusContextual),
    loadCsv(FILES.nexusContextualFallback),
    loadCsv(FILES.formSectionalProfile),
    loadCsv(FILES.gearProfile),
    loadCsv(FILES.labPriceEngine),
  ]);

  return {
    runner, runnerIntel, v8, bet, rel, cards, briefing, marketIntel, verdict, trackIntel,
    horseDrawer, runnerDnaDrawer, explainability, connection, factorScorecard, limited,
    intelligenceScore, customerIntelligence, intelligenceSummary, raceDayIntelligence,
    runnerProfile, formIntelligence, runnerForm, runnerFormHistory, historyMaster,
    historyDetail, horseCareer, horserchetype, horseTrajectory, horseProjection,
    campaignIntelligence, hiddenGem, raceShapeFallback, mapEnrichment, chaosIndex,
    opportunityScore, commandEnrichment, formEnrichment, ratingsHeatmap, productMeetings,
    raceList, meetingCalendar, liveTrackIntelligence, trackMapManifest, nexusContextual,
    nexusContextualFallback, formSectionalProfile, gearProfile, labPriceEngine
  };
}
''', encoding="utf-8")

start = text.index(" useEffect(() => {")
end_marker = "\n\n const selectedTrack ="
end = text.index(end_marker, start)

replacement = r''' useEffect(() => {
 let active = true;

 async function run(): Promise<void> {
 setLoading(true);

 const data = await loadEdgeIQData();

 if (!active) return;

 setRunnerRows(data.runner);
 setRunnerIntelRows(data.runnerIntel);
 setV8Rows(data.v8);
 setBetRows(data.bet);
 setReliabilityRows(data.rel);
 setIntelligenceCardRows(data.cards);
 setBriefingRows(data.briefing);
 setMarketIntelRows(data.marketIntel);
 setVerdictRows(data.verdict);
 setTrackIntelRows(data.trackIntel);
 setHorseDrawerRows(data.horseDrawer);
 setRunnerDnaDrawerRows(data.runnerDnaDrawer);
 setExplainabilityRows(data.explainability);
 setConnectionRows(data.connection);
 setFactorScorecardRows(data.factorScorecard);
 setLimitedRows(data.limited);
 setCustomerIntelligenceRows(data.customerIntelligence);
 setIntelligenceSummaryRows(data.intelligenceSummary);
 setRaceDayIntelligenceRows(data.raceDayIntelligence);
 setRunnerProfileRows(data.runnerProfile);
 setFormIntelligenceRows(data.formIntelligence);
 setRunnerFormRows(data.runnerForm);
 setRunnerFormHistoryRows(data.runnerFormHistory);
 setHistoryMasterRows(data.historyMaster);
 setHistoryDetailRows(data.historyDetail);
 setHorseCareerRows(data.horseCareer);
 setHorserchetypeRows(data.horserchetype);
 setHorseTrajectoryRows(data.horseTrajectory);
 setHorseProjectionRows(data.horseProjection);
 setCampaignIntelligenceRows(data.campaignIntelligence);
 setHiddenGemRows(data.hiddenGem);
 setRaceShapeFallbackRows(data.raceShapeFallback);
 setMapEnrichmentRows(data.mapEnrichment);
 setChaosIndexRows(data.chaosIndex);
 setOpportunityScoreRows(data.opportunityScore);
 setCommandEnrichmentRows(data.commandEnrichment);
 setFormEnrichmentRows(data.formEnrichment);
 setRatingsHeatmapRows(data.ratingsHeatmap);
 setProductMeetingRows(data.productMeetings);
 setRaceListRows(data.raceList);
 setMeetingCalendarRows(data.meetingCalendar);
 setLiveTrackIntelligenceRows(data.liveTrackIntelligence);
 setTrackMapManifestRows(data.trackMapManifest);
 setNexusContextualRows(data.nexusContextual.length ? data.nexusContextual : data.nexusContextualFallback);
 setFormSectionalProfileRows(data.formSectionalProfile);
 setGearProfileRows(data.gearProfile);
 setLabPriceEngineRows(data.labPriceEngine);
 setIntelligenceScoreRows(data.intelligenceScore);
 setLoading(false);
 }

 run();

 return () => {
 active = false;
 };
 }, []);'''

text = text[:start] + replacement + text[end:]

text = text.replace('import { FILES } from "../config/edgeiqFiles";\n', '')
text = text.replace('import { loadCsv, parseCsv, type CsvRow } from "../utils/edgeiqCsv";', 'import { parseCsv, type CsvRow } from "../utils/edgeiqCsv";')

import_line = 'import { loadEdgeIQData } from "../services/edgeiqDataLoader";'
if import_line not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines) + "\n"

path.write_text(text, encoding="utf-8")

print("[DATA_LOADER_EXTRACT] complete")
