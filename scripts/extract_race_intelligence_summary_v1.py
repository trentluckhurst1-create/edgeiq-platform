from pathlib import Path

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
text = path.read_text(encoding="utf-8")

service = root / "src" / "services" / "raceIntelligenceSummaryService.ts"
service.write_text(r'''import type { CsvRow } from "../utils/edgeiqCsv";
import { text } from "../utils/edgeiqFormat";
import { distance, firstNum, firstText, integer, raceClass, railPosition, trackCondition } from "../utils/raceRowHelpers";

type Row = CsvRow;

export function buildRaceIntelligenceSummary(params: {
  header: Row | undefined;
  currentRace?: any;
  rankedEnriched: any[];

  intelligenceCardRows: Row[];
  briefingRows: Row[];
  marketIntelRows: Row[];
  verdictRows: Row[];
  trackIntelRows: Row[];
  raceShapeFallbackRows: Row[];
  chaosIndexRows: Row[];
  opportunityScoreRows: Row[];

  findRaceSidecar: (rows: Row[], base: Row) => Row | undefined;
  findRaceShapeFallbackForRace: (rows: Row[], base: Row) => Row | undefined;
  band: (row: Row | undefined, keys: string[], fallback?: string) => string;
  trackDnaHeadline: (style: string) => string;
  humanBarrierPhrase: (barrier: string) => string;
  humanTrackStyle: (style: string) => string;
  buildBriefingNarrative: (
    raceClarity: string,
    displayExpectedTempo: string,
    bettingConfidence: string,
    mostLikelyWinner: string,
    mostLikelyFair: number | null,
    bestValue: string,
    bestValueEdge: number | null
  ) => string;
  isScratched: (item: any) => boolean;
}) {
  const {
    header,
    currentRace,
    rankedEnriched,
    intelligenceCardRows,
    briefingRows,
    marketIntelRows,
    verdictRows,
    trackIntelRows,
    raceShapeFallbackRows,
    chaosIndexRows,
    opportunityScoreRows,
    findRaceSidecar,
    findRaceShapeFallbackForRace,
    band,
    trackDnaHeadline,
    humanBarrierPhrase,
    humanTrackStyle,
    buildBriefingNarrative,
    isScratched,
  } = params;

  const intelligenceCard = header ? findRaceSidecar(intelligenceCardRows, header) : undefined;
  const briefing = header ? findRaceSidecar(briefingRows, header) : undefined;
  const marketIntel = header ? findRaceSidecar(marketIntelRows, header) : undefined;
  const verdict = header ? findRaceSidecar(verdictRows, header) : undefined;
  const trackIntel = header ? findRaceSidecar(trackIntelRows, header) : undefined;
  const raceShapeFallback = header ? findRaceShapeFallbackForRace(raceShapeFallbackRows, header) : undefined;
  const chaosIndex = header ? findRaceSidecar(chaosIndexRows, header) : undefined;
  const opportunityScore = header ? findRaceSidecar(opportunityScoreRows, header) : undefined;

  const raceClarity = band(intelligenceCard, ["race_clarity_band_v1", "race_clarity"], "-");
  const expectedTempo = band(intelligenceCard, ["expected_tempo_band_v1", "expected_tempo"], "-");
  const fallbackRaceShapeLabel = firstText(raceShapeFallback, ["race_shape_label"], "-").replace(/_/g, " ").toUpperCase();
  const fallbackTempoLabel = firstText(raceShapeFallback, ["tempo_label"], "-").replace(/_/g, " ").toUpperCase();
  const fallbackPressureLabel = firstText(raceShapeFallback, ["pressure_risk"], "-").replace(/_/g, " ").toUpperCase();
  const fallbackPacedvantageLabel = firstText(raceShapeFallback, ["pace_advantage_label"], "");
  const fallbackRaceShapeNarrative = firstText(raceShapeFallback, ["race_shape_narrative"], "");
  const displayExpectedTempo = expectedTempo !== "-" ? expectedTempo : fallbackTempoLabel;
  const bettingConfidence = band(intelligenceCard, ["betting_confidence_band_v1", "betting_confidence"], "-");
  const raceStory = firstText(intelligenceCard, ["race_story_v1", "race_story"], "");

  const mostLikelyWinner =
    firstText(verdict, ["most_likely_winner", "likely_winner", "top_pick"], "") ||
    firstText(briefing, ["most_likely_winner", "likely_winner", "top_pick"], "");

  const bestValue =
    firstText(verdict, ["best_value", "best_current_value", "best_value_runner"], "") ||
    firstText(briefing, ["best_value", "best_current_value", "best_value_runner"], "");

  const mostLikelyFair =
    firstNum(briefing, ["most_likely_fair", "top_pick_fair"]) ??
    firstNum(verdict, ["most_likely_fair", "top_pick_fair"]);

  const bestValueEdge =
    firstNum(briefing, ["top_value_edge", "best_value_edge", "best_current_value_edge"]) ??
    firstNum(verdict, ["top_value_edge", "best_value_edge", "best_current_value_edge"]);

  const bestBet = firstText(verdict, ["best_bet", "bet_recommendation", "verdict_bet"], "WATCH").toUpperCase();
  const verdictNarrative = firstText(verdict, ["verdict_narrative", "race_verdict", "verdict_comment", "narrative"], "");
  const briefingNarrative = firstText(briefing, ["race_briefing", "briefing", "race_briefing_text", "briefing_text"], "");
  const marketComment = firstText(marketIntel, ["market_comment", "market_intelligence", "market_narrative"], "");

  const trackProfile = firstText(trackIntel, ["track_dna_style"], "NO PROFILE");
  const trackBarrier = firstText(trackIntel, ["track_dna_barrier"], "");
  const trackMovement = firstText(trackIntel, ["track_dna_movement"], "");
  const trackDnaConfidence = band(trackIntel, ["track_dna_confidence"], "-");
  const trackDnaSampleWinners = firstText(trackIntel, ["track_dna_sample_winners"], "");

  const bestTrackFitRunner = firstText(trackIntel, ["best_track_fit_runner"], "-");
  const bestTrackFitScore = firstText(trackIntel, ["best_track_fit_score"], "-");
  const eliteFitCount = firstText(trackIntel, ["elite_fit_count"], "0");
  const strongFitCount = firstText(trackIntel, ["strong_fit_count"], "0");
  const positiveFitCount = firstText(trackIntel, ["positive_fit_count"], "0");
  const negativeFitCount = firstText(trackIntel, ["negative_fit_count"], "0");
  const poorFitCount = firstText(trackIntel, ["poor_fit_count"], "0");
  const trackdvantageSummary = firstText(trackIntel, ["track_advantage_summary"], "");
  const trackRiskSummary = firstText(trackIntel, ["track_risk_summary"], "");
  const trackIntelligenceComment = firstText(trackIntel, ["track_intelligence_comment"], "");

  const conditionLabel = header ? `${trackCondition(header).toUpperCase()} / ${distance(header)} / ${raceClass(header)}` : "-";
  const railDisplay =
    header && railPosition(header) !== "-"
      ? railPosition(header)
      : text(currentRace?.rail_position || currentRace?.rail || currentRace?.railPosition) || "-";

  const trackRiskCount =
    integer(trackRiskSummary) ??
    ((integer(negativeFitCount) ?? 0) + (integer(poorFitCount) ?? 0) || null);

  const trackDnaHeaderCopy = trackDnaHeadline(trackProfile);
  const trackDnaFitContext =
    trackProfile.toUpperCase() === "NO PROFILE"
      ? conditionLabel
      : `${trackDnaHeaderCopy}${humanBarrierPhrase(trackBarrier) ? ` | ${humanBarrierPhrase(trackBarrier)}` : ""}`;

  const customerTrackdvantage =
    trackProfile.toUpperCase() === "NO PROFILE"
      ? "No clear historical track pattern is available for this setup."
      : `This setup historically favours ${humanTrackStyle(trackProfile)}${humanBarrierPhrase(trackBarrier) ? ` from ${humanBarrierPhrase(trackBarrier)}` : ""}.${bestTrackFitRunner && bestTrackFitRunner !== "-" ? ` Best profile match: ${bestTrackFitRunner}.` : ""}`;

  const customerTrackRisk =
    trackRiskCount && trackRiskCount > 0
      ? `${trackRiskCount} runners clash with today's historical profile.`
      : trackRiskSummary || "No major profile risks stand out for this race.";

  const customerTrackInsight =
    trackIntelligenceComment
      ? `Track influence: ${trackDnaConfidence}.${trackDnaSampleWinners ? ` Historical sample: ${trackDnaSampleWinners} winners.` : ""}${integer(positiveFitCount) !== null && trackRiskCount !== null ? ` Clear fits: ${positiveFitCount}. Profile risks: ${trackRiskCount}.` : ""}`
      : `Track influence: ${trackDnaConfidence}.${trackDnaSampleWinners ? ` Historical sample: ${trackDnaSampleWinners} winners.` : ""}`;

  const customerBriefingNarrative = buildBriefingNarrative(
    raceClarity,
    displayExpectedTempo,
    bettingConfidence,
    mostLikelyWinner,
    mostLikelyFair,
    bestValue,
    bestValueEdge,
  );

  const activeRaceRows = rankedEnriched.filter((item) => !isScratched(item));

  return {
    intelligenceCard,
    briefing,
    marketIntel,
    verdict,
    trackIntel,
    raceShapeFallback,
    chaosIndex,
    opportunityScore,
    raceClarity,
    expectedTempo,
    fallbackRaceShapeLabel,
    fallbackTempoLabel,
    fallbackPressureLabel,
    fallbackPacedvantageLabel,
    fallbackRaceShapeNarrative,
    displayExpectedTempo,
    bettingConfidence,
    raceStory,
    mostLikelyWinner,
    bestValue,
    mostLikelyFair,
    bestValueEdge,
    bestBet,
    verdictNarrative,
    briefingNarrative,
    marketComment,
    trackProfile,
    trackBarrier,
    trackMovement,
    trackDnaConfidence,
    trackDnaSampleWinners,
    bestTrackFitRunner,
    bestTrackFitScore,
    eliteFitCount,
    strongFitCount,
    positiveFitCount,
    negativeFitCount,
    poorFitCount,
    trackdvantageSummary,
    trackRiskSummary,
    trackIntelligenceComment,
    conditionLabel,
    railDisplay,
    trackRiskCount,
    trackDnaHeaderCopy,
    trackDnaFitContext,
    customerTrackdvantage,
    customerTrackRisk,
    customerTrackInsight,
    customerBriefingNarrative,
    activeRaceRows,
  };
}
''', encoding="utf-8")

start = text.index(" const intelligenceCard = useMemo(() => {")
end = text.index("\n useEffect(() => {", start)

replacement = r''' const {
  intelligenceCard,
  briefing,
  marketIntel,
  verdict,
  trackIntel,
  raceShapeFallback,
  chaosIndex,
  opportunityScore,
  raceClarity,
  expectedTempo,
  fallbackRaceShapeLabel,
  fallbackTempoLabel,
  fallbackPressureLabel,
  fallbackPacedvantageLabel,
  fallbackRaceShapeNarrative,
  displayExpectedTempo,
  bettingConfidence,
  raceStory,
  mostLikelyWinner,
  bestValue,
  mostLikelyFair,
  bestValueEdge,
  bestBet,
  verdictNarrative,
  briefingNarrative,
  marketComment,
  trackProfile,
  trackBarrier,
  trackMovement,
  trackDnaConfidence,
  trackDnaSampleWinners,
  bestTrackFitRunner,
  bestTrackFitScore,
  eliteFitCount,
  strongFitCount,
  positiveFitCount,
  negativeFitCount,
  poorFitCount,
  trackdvantageSummary,
  trackRiskSummary,
  trackIntelligenceComment,
  conditionLabel,
  railDisplay,
  trackRiskCount,
  trackDnaHeaderCopy,
  trackDnaFitContext,
  customerTrackdvantage,
  customerTrackRisk,
  customerTrackInsight,
  customerBriefingNarrative,
  activeRaceRows,
 } = useMemo(() => buildRaceIntelligenceSummary({
  header,
  currentRace: props.currentRace,
  rankedEnriched,
  intelligenceCardRows,
  briefingRows,
  marketIntelRows,
  verdictRows,
  trackIntelRows,
  raceShapeFallbackRows,
  chaosIndexRows,
  opportunityScoreRows,
  findRaceSidecar,
  findRaceShapeFallbackForRace,
  band,
  trackDnaHeadline,
  humanBarrierPhrase,
  humanTrackStyle,
  buildBriefingNarrative,
  isScratched,
 }), [header, props.currentRace, rankedEnriched, intelligenceCardRows, briefingRows, marketIntelRows, verdictRows, trackIntelRows, raceShapeFallbackRows, chaosIndexRows, opportunityScoreRows]);'''

text = text[:start] + replacement + text[end:]

import_line = 'import { buildRaceIntelligenceSummary } from "../services/raceIntelligenceSummaryService";'
if import_line not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines) + "\n"

path.write_text(text, encoding="utf-8")
print("[RACE_INTELLIGENCE_SUMMARY_EXTRACT] complete")
