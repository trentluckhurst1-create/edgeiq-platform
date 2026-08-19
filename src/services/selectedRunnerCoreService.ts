type Row = Record<string, any>;
type SelectedRunnerLike = {
  row: Row;
  bet?: Row;
  explainability?: Row;
  customerIntel?: Row;
  intelligenceSummary?: Row;
  raceDayIntelligence?: Row;
  connection?: Row;
  modelRank?: number | null;
  [key: string]: any;
};

export function buildSelectedRunnerCore(params: {
  selected: SelectedRunnerLike | undefined;
  topModelRow: SelectedRunnerLike | undefined;
  activeRaceRows: SelectedRunnerLike[];

  displayExpectedTempo: string;
  fallbackRaceShapeLabel: string;
  fallbackTempoLabel: string;
  fallbackPressureLabel: string;
  fallbackPacedvantageLabel: string;
  fallbackRaceShapeNarrative: string;
  raceAssessmentNarrative: string;
  raceClarity: string;

  isScratched: (item: SelectedRunnerLike) => boolean;
  displayBetValue: (item: SelectedRunnerLike) => string;
  displayGradeValue: (item: SelectedRunnerLike) => string;
  limitedScoreValue: (item: SelectedRunnerLike) => string;
  computedLimitedScore: (item: SelectedRunnerLike) => number;
  connectionSourceRow: (item: SelectedRunnerLike) => Row | undefined;
  hasConnectionPayload: (row: Row | undefined) => boolean;
  evidenceFlag: (row: Row | undefined, keys: string[]) => boolean;
  limitedDecisionValue: (item: SelectedRunnerLike) => string;
  displayBetQualityValue: (item: SelectedRunnerLike) => string;

  firstText: (row: Row | undefined, keys: string[], fallback?: string) => string;
  firstNum: (row: Row | undefined, keys: string[]) => number | null;
  renderMetricValue: (value: number | null, digits?: number, signed?: boolean) => string;
  text: (value: unknown) => string;
}) {
 const {
  selected,
  topModelRow,
  activeRaceRows,
  displayExpectedTempo,
  fallbackRaceShapeLabel,
  fallbackTempoLabel,
  fallbackPressureLabel,
  fallbackPacedvantageLabel,
  fallbackRaceShapeNarrative,
  raceAssessmentNarrative,
  raceClarity,
  isScratched,
  displayBetValue,
  displayGradeValue,
  limitedScoreValue,
  computedLimitedScore,
  connectionSourceRow,
  hasConnectionPayload,
  evidenceFlag,
  limitedDecisionValue,
  displayBetQualityValue,
  firstText,
  firstNum,
  renderMetricValue,
  text,
 } = params;

 const selectedIsScratched = selected ? isScratched(selected) : false;
 const selectedModelRank = selected?.modelRank ?? null;
 const selectedDisplayBet = selected ? displayBetValue(selected) : "-";
 const selectedDisplayGrade = selected ? displayGradeValue(selected) : "-";
 const selectedLimitedScore = selected ? limitedScoreValue(selected) : "";
 const selectedLimitedScoreNumeric = selected ? computedLimitedScore(selected) : null;
 const selectedExplainability = selected?.explainability;
 const selectedCustomerIntel = selected?.customerIntel;
 const selectedIntelligenceSummary = selected?.intelligenceSummary;
 const selectedRaceDayIntelligence = selected?.raceDayIntelligence;
 const selectedEdgeiqScore = selected ? firstText(selectedCustomerIntel, ["edgeiq_score"], "-") : "-";
 const selectedEdgeiqBandRaw = selected ? firstText(selectedCustomerIntel, ["edgeiq_band"], "-") : "-";
 const selectedEdgeiqBand = selectedEdgeiqBandRaw.replace(/_/g, " ").toUpperCase();
 const selectedEdgeiqVerdict = selected ? firstText(selectedCustomerIntel, ["edgeiq_verdict"], "") : "";
 const selectedEdgeiqReasonsRaw = selected ? firstText(selectedCustomerIntel, ["primary_reasons"], "") : "";
 const selectedEdgeiqRisksRaw = selected ? firstText(selectedCustomerIntel, ["primary_risks"], "") : "";
 const selectedEdgeiqReasons = selectedEdgeiqReasonsRaw.split("|").map((x) => x.trim()).filter(Boolean).slice(0, 4);
 const selectedEdgeiqRisks = selectedEdgeiqRisksRaw.split("|").map((x) => x.trim()).filter(Boolean).slice(0, 4);
 const selectedStableIntentBandRaw = selected ? firstText(selectedCustomerIntel, ["stable_intent_band"], "-") : "-";
 const selectedStableIntentBand = selectedStableIntentBandRaw.replace(/_/g, " ").toUpperCase();
 const selectedContextSignalCount = selected ? firstText(selectedCustomerIntel, ["context_signal_count"], "-") : "-";
 const selectedCustomerDnaBandRaw = selected ? firstText(selectedCustomerIntel, ["dna_band"], "-") : "-";
 const selectedCustomerDnaBand = selectedCustomerDnaBandRaw.replace(/_/g, " ").toUpperCase();
 const selectedIntelligenceSummaryTitle = selected ? firstText(selectedIntelligenceSummary, ["intelligence_summary_title"], "") : "";
 const selectedIntelligenceSummaryText = selected ? firstText(selectedIntelligenceSummary, ["intelligence_summary_text"], "") : "";
 const selectedIntelligencectionText = selected ? firstText(selectedIntelligenceSummary, ["customer_action_text"], "") : "";
 const selectedRaceDayCondition = selected ? firstText(selectedRaceDayIntelligence, ["track_condition"], "-") : "-";
 const selectedRaceDayRail = selected ? firstText(selectedRaceDayIntelligence, ["rail_clean"], "-") : "-";
 const selectedRaceDayTempo = selected ? firstText(selectedRaceDayIntelligence, ["tempo_clean"], "-") : "-";
 const selectedRaceDayPressure = selected ? firstText(selectedRaceDayIntelligence, ["map_pressure"], "-") : "-";
 const selectedRaceDayTrackProfile = selected ? firstText(selectedRaceDayIntelligence, ["track_profile_clean"], "-") : "-";
 const selectedRaceDayTrackConfidence = selected ? firstText(selectedRaceDayIntelligence, ["track_confidence_clean"], "-") : "-";
 const selectedRaceDayRead = selected ? firstText(selectedRaceDayIntelligence, ["race_day_read_clean"], "") : "";

 const selectedConnectionSource = selected ? connectionSourceRow(selected) : undefined;
 const selectedConnectionLoaded = selected ? hasConnectionPayload(selectedConnectionSource) : false;
 const selectedRaceExplainability = selectedExplainability ?? topModelRow?.explainability ?? activeRaceRows[0]?.explainability;
 const selectedExplainabilityModelRankRaw = selected ? firstText(selectedExplainability, ["model_rank"], "") : "";
 const selectedExplainabilityModelRank = selectedIsScratched
 ? "SCRATCHED"
 : selectedExplainabilityModelRankRaw
 ? `#${selectedExplainabilityModelRankRaw.replace(/^#/, "")}`
 : selectedModelRank
 ? `#${selectedModelRank}`
 : "-";
 const selectedExplainabilityConfidenceBand = selected
 ? firstText(selectedExplainability, ["confidence_band"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedExplainabilityConfidenceScore = selected
 ? firstNum(selectedExplainability, ["final_confidence_score"]) ?? selectedLimitedScoreNumeric
 : null;
 const selectedExplainabilityTrendLabel = selected
 ? firstText(selectedExplainability, ["trend_label"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedExplainabilityTrendDelta = selected ? firstNum(selectedExplainability, ["rating_trend_delta"]) : null;
 const selectedExplainabilityTrendDisplay = selectedIsScratched
 ? "SCRATCHED"
 : selectedExplainabilityTrendLabel !== "-" && selectedExplainabilityTrendDelta !== null
 ? `${selectedExplainabilityTrendLabel} (${renderMetricValue(selectedExplainabilityTrendDelta, 2, true)})`
 : selectedExplainabilityTrendLabel !== "-"
 ? selectedExplainabilityTrendLabel
 : selectedExplainabilityTrendDelta !== null
 ? renderMetricValue(selectedExplainabilityTrendDelta, 2, true)
 : "-";
 const selectedExplainabilityRaceTempo = selected
 ? firstText(selectedExplainability, ["race_tempo"], displayExpectedTempo)
 : displayExpectedTempo;
 const selectedExplainabilityRaceShape = selected
 ? firstText(selectedExplainability, ["race_shape_label"], fallbackRaceShapeLabel !== "-" ? fallbackRaceShapeLabel : raceClarity)
 : fallbackRaceShapeLabel !== "-" ? fallbackRaceShapeLabel : raceClarity;
 const selectedExplainabilityWhy = selected ? firstText(selectedExplainability, ["why_ranked_here"], "") : "";
 const selectedExplainabilityConfidenceExplanation = selected ? firstText(selectedExplainability, ["confidence_explanation"], "") : "";
 const selectedExplainabilityTrendSummary = selected ? firstText(selectedExplainability, ["trend_summary"], "") : "";
 const selectedConnectionBand = selected
 ? firstText(selectedConnectionSource, ["connection_band"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedConnectionEvidenceQuality = selected
 ? firstText(selectedConnectionSource, ["evidence_quality"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedConnectionEvidenceStatus = selected
 ? firstText(selectedConnectionSource, ["connection_evidence_status"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedExplainabilityConnectionScore = selected ? firstNum(selectedConnectionSource, ["connection_score"]) : null;
 const selectedConnectionngleLabel = (value: string): string => {
 const label = value.toUpperCase();
 if (label.includes("JOCKEY")) return "Jockey Pattern";
 if (label.includes("COMBO") || label.includes("PRTNERSHIP") || label.includes("TRINER/JOCKEY")) return "Partnership Pattern";
 if (label.includes("MRKET") || label.includes("SP") || label.includes("/E") || label.includes("ROI")) return "Market Pattern";
 if (label.includes("PREP")) return "Preparation Pattern";
 return "Trainer Pattern";
 };
 const selectedConnectionngles = selectedIsScratched
 ? []
 : [
 firstText(selectedConnectionSource, ["edgeiq_connection_angle_summary"], ""),
 firstText(selectedConnectionSource, ["connection_angle_1"], ""),
 firstText(selectedConnectionSource, ["connection_angle_2"], ""),
 firstText(selectedConnectionSource, ["connection_angle_3"], ""),
 ]
 .filter((value) => {
 const normalized = value.trim().toUpperCase();
 return normalized && normalized !== "-" && normalized !== "LIMITED SMPLE";
 })
 .map((value) => ({ label: selectedConnectionngleLabel(value), value }));
 const selectedConnectionReadPatterns = selectedIsScratched
 ? []
 : [
 { label: "Trainer Pattern", value: firstText(selectedConnectionSource, ["trainer_track_read"], "") },
 { label: "Trainer Pattern", value: firstText(selectedConnectionSource, ["trainer_distance_read"], "") },
 { label: "Preparation Pattern", value: firstText(selectedConnectionSource, ["trainer_prep_read"], "") },
 { label: "Market Pattern", value: firstText(selectedConnectionSource, ["trainer_market_read"], "") },
 { label: "Jockey Pattern", value: firstText(selectedConnectionSource, ["jockey_track_read"], "") },
 { label: "Jockey Pattern", value: firstText(selectedConnectionSource, ["jockey_distance_read"], "") },
 { label: "Partnership Pattern", value: firstText(selectedConnectionSource, ["combo_read"], "") },
 ].filter((item) => {
 const normalized = item.value.trim().toUpperCase();
 return normalized && normalized !== "-" && normalized !== "LIMITED SMPLE" && !normalized.startsWith("NOT PPLICBLE");
 }).slice(0, 3);
 const selectedConnectionEvidencePatterns = selectedConnectionngles.length
 ? selectedConnectionngles
 : selectedConnectionReadPatterns;
 const selectedConnectionRisk = selectedIsScratched
 ? ""
 : firstText(selectedConnectionSource, ["connection_risk_1"], "");
 const selectedConnectionRiskMeaningful = (() => {
 const normalized = selectedConnectionRisk.trim().toUpperCase();
 return !!normalized && normalized !== "-" && normalized !== "EVIDENCE SMPLE IS LIMITED.";
 })();
 const selectedConnectionPositiveItems = selectedIsScratched
 ? []
 : [
 { factor: firstText(selectedConnectionSource, ["connection_positive_1"], ""), value: firstText(selectedConnectionSource, ["connection_positive_1_value"], "") },
 { factor: firstText(selectedConnectionSource, ["connection_positive_2"], ""), value: firstText(selectedConnectionSource, ["connection_positive_2_value"], "") },
 ].filter((item) => item.factor);
 const selectedConnectionRiskItems = selectedIsScratched
 ? []
 : [
 { factor: firstText(selectedConnectionSource, ["connection_risk_1"], ""), value: firstText(selectedConnectionSource, ["connection_risk_1_value"], "") },
 ].filter((item) => item.factor);
 const selectedConnectionNarrative = selected
 ? firstText(selectedConnectionSource, ["edgeiq_connection_angle_summary", "connection_summary_for_decision_engine", "connection_narrative"], "")
 : "";
 const selectedMergedMarketvailable = selected ? evidenceFlag(selected.row, ["edgeiq_market_evidence_available"]) : false;
 const selectedMergedMarketSummary = selected ? firstText(selected.row, ["edgeiq_market_signal_summary"], "") : "";
 const selectedMergedHiddenGemvailable = selected ? evidenceFlag(selected.row, ["edgeiq_hidden_gem_evidence_available"]) : false;
 const selectedMergedHiddenGemSummary = selected ? firstText(selected.row, ["edgeiq_hidden_gem_summary"], "") : "";
 const selectedConnectionMarketLabel = selected
 ? firstText(selectedConnectionSource, ["market_expectation_label"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedConnectionSpDelta = selected ? firstNum(selectedConnectionSource, ["sp_expectation_delta"]) : null;
 const selectedConnectionTrainerTrackSr = selected ? firstNum(selectedConnectionSource, ["trainer_track_sr"]) : null;
 const selectedConnectionJockeyTrackSr = selected ? firstNum(selectedConnectionSource, ["jockey_track_sr"]) : null;
 const selectedConnectionComboSr = selected ? firstNum(selectedConnectionSource, ["combo_sr"]) : null;
 const selectedConnectionComboTrackSr = selected ? firstNum(selectedConnectionSource, ["combo_track_sr"]) : null;
 const selectedConnectionSpSampleStarts = selected ? firstNum(selectedConnectionSource, ["sp_sample_starts"]) : null;
 const selectedExplainabilitySupports = selectedIsScratched
 ? []
 : [
 { factor: firstText(selectedExplainability, ["positive_1"], ""), value: firstText(selectedExplainability, ["positive_1_value"], "") },
 { factor: firstText(selectedExplainability, ["positive_2"], ""), value: firstText(selectedExplainability, ["positive_2_value"], "") },
 { factor: firstText(selectedExplainability, ["positive_3"], ""), value: firstText(selectedExplainability, ["positive_3_value"], "") },
 ].filter((item) => item.factor);
 const selectedExplainabilityRisks = selectedIsScratched
 ? []
 : [
 { factor: firstText(selectedExplainability, ["risk_1"], ""), value: firstText(selectedExplainability, ["risk_1_value"], "") },
 { factor: firstText(selectedExplainability, ["risk_2"], ""), value: firstText(selectedExplainability, ["risk_2_value"], "") },
 { factor: firstText(selectedExplainability, ["risk_3"], ""), value: firstText(selectedExplainability, ["risk_3_value"], "") },
 ].filter((item) => item.factor);
 const selectedRaceShapeLabel = firstText(
 selectedRaceExplainability,
 ["race_shape_label"],
 fallbackRaceShapeLabel !== "-" ? fallbackRaceShapeLabel : raceClarity,
 ).replace(/_/g, " ").toUpperCase();
 const selectedRaceTempoLabel = firstText(
 selectedRaceExplainability,
 ["race_tempo"],
 displayExpectedTempo,
 ).replace(/_/g, " ").toUpperCase();
 const selectedRacePacedvantageRunner = firstText(selectedRaceExplainability, ["pace_advantage_runner"], "");
 const selectedRaceLatePowerBeneficiary = firstText(selectedRaceExplainability, ["late_power_beneficiary"], "");
 const selectedRacePressureRiskRunner = firstText(selectedRaceExplainability, ["pressure_risk_runner"], "");
 const selectedRaceShapeStory = firstText(
 selectedRaceExplainability,
 ["race_shape_story"],
 fallbackRaceShapeNarrative || raceAssessmentNarrative,
 );
 const raceShapeFallbackLoaded = [fallbackRaceShapeLabel, fallbackTempoLabel, fallbackPressureLabel, fallbackRaceShapeNarrative]
 .some((value) => {
 const parsed = text(value);
 return parsed !== "" && parsed !== "-";
 });
 const selectedRacePacedvantageDisplay = selectedRacePacedvantageRunner || fallbackPacedvantageLabel || "";
 const selectedRacePressureDisplay = selectedRacePressureRiskRunner || (fallbackPressureLabel !== "-" ? fallbackPressureLabel : "");
 const selectedRaceShapeStoryDisplay = selectedRaceShapeStory || fallbackRaceShapeNarrative || raceAssessmentNarrative;
 const selectedLimitedDecision = selected ? limitedDecisionValue(selected) : "-";
 const selectedBetQuality = selected ? displayBetQualityValue(selected) : "-";

 return {
  selectedIsScratched,
  selectedModelRank,
  selectedDisplayBet,
  selectedDisplayGrade,
  selectedLimitedScore,
  selectedLimitedScoreNumeric,
  selectedExplainability,
  selectedCustomerIntel,
  selectedIntelligenceSummary,
  selectedRaceDayIntelligence,
  selectedEdgeiqScore,
  selectedEdgeiqBandRaw,
  selectedEdgeiqBand,
  selectedEdgeiqVerdict,
  selectedEdgeiqReasonsRaw,
  selectedEdgeiqRisksRaw,
  selectedEdgeiqReasons,
  selectedEdgeiqRisks,
  selectedStableIntentBandRaw,
  selectedStableIntentBand,
  selectedContextSignalCount,
  selectedCustomerDnaBandRaw,
  selectedCustomerDnaBand,
  selectedIntelligenceSummaryTitle,
  selectedIntelligenceSummaryText,
  selectedIntelligencectionText,
  selectedRaceDayCondition,
  selectedRaceDayRail,
  selectedRaceDayTempo,
  selectedRaceDayPressure,
  selectedRaceDayTrackProfile,
  selectedRaceDayTrackConfidence,
  selectedRaceDayRead,
  selectedConnectionSource,
  selectedConnectionLoaded,
  selectedRaceExplainability,
  selectedExplainabilityModelRankRaw,
  selectedExplainabilityModelRank,
  selectedExplainabilityConfidenceBand,
  selectedExplainabilityConfidenceScore,
  selectedExplainabilityTrendLabel,
  selectedExplainabilityTrendDelta,
  selectedExplainabilityTrendDisplay,
  selectedExplainabilityRaceTempo,
  selectedExplainabilityRaceShape,
  selectedExplainabilityWhy,
  selectedExplainabilityConfidenceExplanation,
  selectedExplainabilityTrendSummary,
  selectedConnectionBand,
  selectedConnectionEvidenceQuality,
  selectedConnectionEvidenceStatus,
  selectedExplainabilityConnectionScore,
  selectedConnectionngles,
  selectedConnectionReadPatterns,
  selectedConnectionEvidencePatterns,
  selectedConnectionRisk,
  selectedConnectionRiskMeaningful,
  selectedConnectionPositiveItems,
  selectedConnectionRiskItems,
  selectedConnectionNarrative,
  selectedMergedMarketvailable,
  selectedMergedMarketSummary,
  selectedMergedHiddenGemvailable,
  selectedMergedHiddenGemSummary,
  selectedConnectionMarketLabel,
  selectedConnectionSpDelta,
  selectedConnectionTrainerTrackSr,
  selectedConnectionJockeyTrackSr,
  selectedConnectionComboSr,
  selectedConnectionComboTrackSr,
  selectedConnectionSpSampleStarts,
  selectedExplainabilitySupports,
  selectedExplainabilityRisks,
  selectedRaceShapeLabel,
  selectedRaceTempoLabel,
  selectedRacePacedvantageRunner,
  selectedRaceLatePowerBeneficiary,
  selectedRacePressureRiskRunner,
  selectedRaceShapeStory,
  selectedRacePacedvantageDisplay,
  selectedRacePressureDisplay,
  selectedRaceShapeStoryDisplay,
  selectedLimitedDecision,
  selectedBetQuality,
  raceShapeFallbackLoaded,
 };
}

