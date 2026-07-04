import { FILES } from "../config/edgeiqFiles";
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
