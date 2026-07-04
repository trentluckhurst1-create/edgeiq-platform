type Row = Record<string, any>;
type SelectedRunnerLike = {
  row: Row;
  runnerCareer?: Row;
  runnerrchetype?: Row;
  runnerTrajectory?: Row;
  runnerProjection?: Row;
  campaign?: Row;
  hiddenGem?: Row;
  formEnrichment?: Row;
  runnerHistory?: Row[];
  runnerProfile?: Row;
  [key: string]: any;
};

export function buildSelectedRunnerProfile(params: {
  selected: SelectedRunnerLike | undefined;
  selectedIsScratched: boolean;
  selectedProfileCareerStarts: string;
  selectedProfileCareerWins: string;
  selectedProfileCareerPlaces: string;
  selectedHorserchetype: string;
  selectedDistanceProfile: string;
  selectedHistoricalRun: Row | undefined;

  firstText: (row: Row | undefined, keys: string[], fallback?: string) => string;
  firstNum: (row: Row | undefined, keys: string[]) => number | null;
  renderMetricValue: (value: number | null, digits?: number, signed?: boolean) => string;
  customerPerformanceNarrative: (value: string) => string;
  performanceIntelligenceLabel: (label: string, actionable?: boolean, historical?: boolean) => string;
  formatCampaignStage: (stage: number | null, label: string) => string;
  formatCampaignWindow: (start: number | null, end: number | null) => string;
  ratedHistoryRows: (rows: Row[]) => Row[];
  historyDateValue: (row: Row | undefined) => number;
  historyRatingValue: (row: Row | undefined) => number | null;
  historyRunKey: (row: Row | undefined) => string;
  formatHistoryDate: (value: string) => string;
  historyDateText: (row: Row | undefined) => string;
  drawerValue: (value: string) => string;
  historyTrackText: (row: Row | undefined) => string;
  historyDistanceText: (row: Row | undefined) => string;
  historyClassText: (row: Row | undefined) => string;
  historyGoingText: (row: Row | undefined) => string;
  historyJockeyText: (row: Row | undefined) => string;
  historyFinishText: (row: Row | undefined) => string;
  historySpText: (row: Row | undefined) => string;
  historyRaceNoText: (row: Row | undefined) => string;
  historyFieldSizeText: (row: Row | undefined) => string;
  historyBarrierText: (row: Row | undefined) => string;
  historyWeightText: (row: Row | undefined) => string;
  historyRaceStrengthText: (row: Row | undefined) => string;
  ordinal: (value: number | null) => string;
  projectionRatingValue: (item: SelectedRunnerLike) => number | null;
  num: (value: unknown) => number | null;
}) {
 const {
  selected,
  selectedIsScratched,
  selectedProfileCareerStarts,
  selectedProfileCareerWins,
  selectedProfileCareerPlaces,
  selectedHorserchetype,
  selectedDistanceProfile,
  selectedHistoricalRun,
  firstText,
  firstNum,
  renderMetricValue,
  customerPerformanceNarrative,
  performanceIntelligenceLabel,
  formatCampaignStage,
  formatCampaignWindow,
  ratedHistoryRows,
  historyDateValue,
  historyRatingValue,
  historyRunKey,
  formatHistoryDate,
  historyDateText,
  drawerValue,
  historyTrackText,
  historyDistanceText,
  historyClassText,
  historyGoingText,
  historyJockeyText,
  historyFinishText,
  historySpText,
  historyRaceNoText,
  historyFieldSizeText,
  historyBarrierText,
  historyWeightText,
  historyRaceStrengthText,
  ordinal,
  projectionRatingValue,
  num,
 } = params;

 const selectedCareerIntel = selected?.runnerCareer;
 const selectedrchetypeIntel = selected?.runnerrchetype;
 const selectedTrajectoryIntel = selected?.runnerTrajectory;
 const selectedProjectionIntel = selected?.runnerProjection;
 const selectedCampaignIntel = selected?.campaign;
 const selectedHiddenGemIntel = selected?.hiddenGem;
 const selectedCareerStartsDisplay = selected
 ? firstText(selectedCareerIntel, ["career_starts"], selectedProfileCareerStarts)
 : "-";
 const selectedCareerWinsDisplay = selected
 ? firstText(selectedCareerIntel, ["career_wins"], selectedProfileCareerWins)
 : "-";
 const selectedCareerPlacesDisplay = selected
 ? firstText(selectedCareerIntel, ["career_places"], selectedProfileCareerPlaces)
 : "-";
 const selectedCareerPeakRating = selected ? firstNum(selectedCareerIntel, ["peak_rating"]) : null;
 const selectedCareerverageRating = selected ? firstNum(selectedCareerIntel, ["average_rating"]) : null;
 const selectedCareerMedianRating = selected ? firstNum(selectedCareerIntel, ["median_rating"]) : null;
 const selectedCareerLatestRating = selected ? firstNum(selectedCareerIntel, ["latest_rating"]) : null;
 const selectedCareerLast5verage = selected ? firstNum(selectedCareerIntel, ["last_5_average"]) : null;
 const selectedCareerLast10verage = selected ? firstNum(selectedCareerIntel, ["last_10_average"]) : null;
 const selectedCareerPercentile = selected ? firstNum(selectedCareerIntel, ["career_rating_percentile"]) : null;
 const selectedCareerConsistency = selected ? firstNum(selectedCareerIntel, ["consistency_score"]) : null;
 const selectedCareerVolatility = selected ? firstNum(selectedCareerIntel, ["volatility_score"]) : null;
 const selectedCareerBand = selected
 ? firstText(selectedCareerIntel, ["rating_band"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedCareerTrend = selected
 ? firstText(selectedCareerIntel, ["career_trend"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedCareerBestTrack = selected ? firstText(selectedCareerIntel, ["best_track"], "-") : "-";
 const selectedCareerBestDistance = selected ? firstText(selectedCareerIntel, ["best_distance"], "-") : "-";
 const selectedCareerBestCondition = selected ? firstText(selectedCareerIntel, ["best_condition"], "-") : "-";
 const selectedCareerBestClass = selected ? firstText(selectedCareerIntel, ["best_class"], "-") : "-";
 const selectedCareerWorstTrack = selected ? firstText(selectedCareerIntel, ["worst_track"], "-") : "-";
 const selectedCareerWorstDistance = selected ? firstText(selectedCareerIntel, ["worst_distance"], "-") : "-";
 const selectedCareerWorstCondition = selected ? firstText(selectedCareerIntel, ["worst_condition"], "-") : "-";
 const selectedCareerPeakDate = selected ? firstText(selectedCareerIntel, ["peak_date"], "-") : "-";
 const selectedCareerPeakTrack = selected ? firstText(selectedCareerIntel, ["peak_track"], "-") : "-";
 const selectedCareerPeakDistance = selected ? firstText(selectedCareerIntel, ["peak_distance"], "-") : "-";
 const selectedCareerPeakClass = selected ? firstText(selectedCareerIntel, ["peak_class"], "-") : "-";
 const selectedCareerDaysSincePeak = selected ? firstText(selectedCareerIntel, ["days_since_peak"], "-") : "-";
 const selectedCampaignProfile = selected
 ? firstText(selectedCampaignIntel, ["campaign_profile"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedCampaignProfileBand = selected
 ? firstText(selectedCampaignIntel, ["campaign_profile_band"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedCampaignCurrentPrepStage = selected ? firstNum(selectedCampaignIntel, ["current_prep_stage"]) : null;
 const selectedCampaignPrepStageLabel = selected
 ? firstText(selectedCampaignIntel, ["prep_stage_label"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedCampaignPeakWindowStart = selected ? firstNum(selectedCampaignIntel, ["peak_window_start"]) : null;
 const selectedCampaignPeakWindowEnd = selected ? firstNum(selectedCampaignIntel, ["peak_window_end"]) : null;
 const selectedCampaignRiskScore = selected ? firstNum(selectedCampaignIntel, ["campaign_risk_score"]) : null;
 const selectedCampaignRiskBand = selected
 ? firstText(selectedCampaignIntel, ["campaign_risk_band"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedCampaignEvidenceStatus = selected
 ? firstText(selectedCampaignIntel, ["evidence_status"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedCampaignNarrative = selected
 ? firstText(selectedCampaignIntel, ["campaign_narrative"], "Limited campaign history available.")
 : "Limited campaign history available.";
 const selectedCampaignHistoryRuns = selected ? firstNum(selectedCampaignIntel, ["history_runs_used"]) : null;
 const selectedCampaignStageSampleCount = selected ? firstNum(selectedCampaignIntel, ["prep_stage_sample_count"]) : null;
 const selectedCampaignPrepDisplay = formatCampaignStage(selectedCampaignCurrentPrepStage, selectedCampaignPrepStageLabel);
 const selectedCampaignPeakWindowDisplay = formatCampaignWindow(selectedCampaignPeakWindowStart, selectedCampaignPeakWindowEnd);
 const selectedHiddenGemDisplayBand = selected
 ? firstText(selectedHiddenGemIntel, ["customer_display_band"], "NO_SIGNL").replace(/_/g, " ").toUpperCase()
 : "NO SIGNAL";
 const selectedHiddenGemctionable = selected
 ? firstText(selectedHiddenGemIntel, ["actionable_watch_flag"], "NO").toUpperCase() === "YES"
 : false;
 const selectedHiddenGemHistorical = selected
 ? firstText(selectedHiddenGemIntel, ["historical_watch_flag"], "NO").toUpperCase() === "YES"
 : false;
 const selectedHiddenGemRecencyBand = selected
 ? firstText(selectedHiddenGemIntel, ["hidden_gem_recency_band"], "NONE").replace(/_/g, " ").toUpperCase()
 : "NONE";
 const selectedHiddenGemDaysSince = selected ? firstNum(selectedHiddenGemIntel, ["days_since_hidden_gem"]) : null;
 const selectedHiddenGemScore = selected ? firstNum(selectedHiddenGemIntel, ["recency_adjusted_hidden_gem_score", "last_hidden_gem_score"]) : null;
 const selectedHiddenGemTrigger = selected ? firstText(selectedHiddenGemIntel, ["last_hidden_gem_trigger"], "") : "";
 const selectedHiddenGemNarrative = selected
 ? customerPerformanceNarrative(firstText(selectedHiddenGemIntel, ["hidden_gem_narrative"], "Neutral recent performance intelligence."))
 : "Neutral recent performance intelligence.";
 const selectedHiddenGemDate = selected ? firstText(selectedHiddenGemIntel, ["last_hidden_gem_date"], "-") : "-";
 const selectedHiddenGemTrack = selected ? firstText(selectedHiddenGemIntel, ["last_hidden_gem_track"], "-") : "-";
 const selectedHiddenGemRaceNo = selected ? firstText(selectedHiddenGemIntel, ["last_hidden_gem_race_no"], "-") : "-";
 const selectedHiddenGemLoaded = !!selectedHiddenGemIntel;
 const selectedPerformanceIntelligenceBand = performanceIntelligenceLabel(
 selectedHiddenGemDisplayBand,
 selectedHiddenGemctionable,
 selectedHiddenGemHistorical
 );
 const selectedHiddenGemStatusDisplay = selectedIsScratched
 ? "SCRATCHED"
 : selectedHiddenGemctionable
 ? selectedPerformanceIntelligenceBand
 : selectedHiddenGemHistorical
 ? "IMPROVING"
 : selectedHiddenGemLoaded
 ? "NEUTRAL"
 : "NEUTRAL";
 const selectedHiddenGemgeDisplay = selectedHiddenGemDaysSince === null ? "-" : `${renderMetricValue(selectedHiddenGemDaysSince, 0)}d`;
 const selectedCareerrchetype = selected
 ? firstText(selectedrchetypeIntel, ["horse_archetype"], selectedHorserchetype).replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedDevelopmentStage = selected
 ? firstText(selectedrchetypeIntel, ["development_stage"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedImprovementProfile = selected
 ? firstText(selectedrchetypeIntel, ["improvement_profile"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedConsistencyProfile = selected
 ? firstText(selectedrchetypeIntel, ["consistency_profile"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedFreshnessProfile = selected
 ? firstText(selectedrchetypeIntel, ["freshness_profile"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedrchetypeDistanceProfile = selected
 ? firstText(selectedrchetypeIntel, ["distance_profile"], selectedDistanceProfile).replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedSeasonalityProfile = selected
 ? firstText(selectedrchetypeIntel, ["seasonality_profile"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedCareerPeakgeStage = selected
 ? firstText(selectedrchetypeIntel, ["career_peak_age"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedRunsSincePeak = selected ? firstText(selectedrchetypeIntel, ["runs_since_peak"], "-") : "-";
 const selectedPeakTrend = selected
 ? firstText(selectedrchetypeIntel, ["peak_trend"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedCareerLast3verage = selected ? firstNum(selectedrchetypeIntel, ["last_3_average"]) : null;
 const selectedCareerPercentileScore = selected
 ? firstNum(selectedrchetypeIntel, ["career_percentile"]) ?? selectedCareerPercentile
 : null;
 const selectedBoomOrBustFlag = selected
 ? firstText(selectedrchetypeIntel, ["boom_or_bust_flag"], "NO").toUpperCase()
 : "NO";
 const selectedLateMaturerFlag = selected
 ? firstText(selectedrchetypeIntel, ["late_maturer_flag"], "NO").toUpperCase()
 : "NO";
 const selectedEarlyMaturerFlag = selected
 ? firstText(selectedrchetypeIntel, ["early_maturer_flag"], "NO").toUpperCase()
 : "NO";
 const selectedImproverFlag = selected
 ? firstText(selectedrchetypeIntel, ["improver_flag"], "NO").toUpperCase()
 : "NO";
 const selectedRegressorFlag = selected
 ? firstText(selectedrchetypeIntel, ["regressor_flag"], "NO").toUpperCase()
 : "NO";
 const selectedTrajectoryDirection = selected
 ? firstText(selectedTrajectoryIntel, ["trajectory_direction"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedTrajectoryStrength = selected
 ? firstText(selectedTrajectoryIntel, ["trajectory_strength"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedTrajectoryScore = selected ? firstNum(selectedTrajectoryIntel, ["trajectory_score"]) : null;
 const selectedPointsOffPeak = selected ? firstNum(selectedTrajectoryIntel, ["points_off_peak"]) : null;
 const selectedPercentOfPeak = selected ? firstNum(selectedTrajectoryIntel, ["percent_of_peak"]) : null;
 const selectedRunsSincePeakDisplay = selected
 ? firstText(selectedTrajectoryIntel, ["runs_since_peak"], selectedRunsSincePeak)
 : "-";
 const selectedDaysSincePeakDisplay = selected
 ? firstText(selectedTrajectoryIntel, ["days_since_peak"], selectedCareerDaysSincePeak)
 : "-";
 const selectedImprovementLast3 = selected ? firstNum(selectedTrajectoryIntel, ["improvement_last_3"]) : null;
 const selectedImprovementLast5 = selected ? firstNum(selectedTrajectoryIntel, ["improvement_last_5"]) : null;
 const selectedImprovementLast10 = selected ? firstNum(selectedTrajectoryIntel, ["improvement_last_10"]) : null;
 const selectedBounceRisk = selected
 ? firstText(selectedTrajectoryIntel, ["bounce_risk"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedRegressionRisk = selected
 ? firstText(selectedTrajectoryIntel, ["regression_risk"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedBreakoutPotential = selected
 ? firstText(selectedTrajectoryIntel, ["breakout_potential"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedCareerPhase = selected
 ? firstText(selectedTrajectoryIntel, ["career_phase"], selectedDevelopmentStage).replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedProjectionOutlookBand = selected
 ? firstText(selectedProjectionIntel, ["projection_band"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedProjectionOutlookConfidence = selected
 ? firstText(selectedProjectionIntel, ["projection_confidence"], "-").replace(/_/g, " ").toUpperCase()
 : "-";
 const selectedNextRunProjection = selected
 ? firstNum(selectedProjectionIntel, ["next_run_projection"]) ?? firstNum(selectedTrajectoryIntel, ["next_run_projection"])
 : null;
 const selectedCeilingProjection = selected
 ? firstNum(selectedProjectionIntel, ["ceiling_projection"]) ?? firstNum(selectedTrajectoryIntel, ["ceiling_projection"])
 : null;
 const selectedFloorProjection = selected
 ? firstNum(selectedProjectionIntel, ["floor_projection"]) ?? firstNum(selectedTrajectoryIntel, ["floor_projection"])
 : null;
 const selectedExpectedImprovement = selected ? firstNum(selectedProjectionIntel, ["expected_improvement"]) : null;
 const selectedExpectedRegression = selected ? firstNum(selectedProjectionIntel, ["expected_regression"]) : null;
 const selectedImprovementProbability = selected ? firstNum(selectedProjectionIntel, ["improvement_probability"]) : null;
 const selectedRegressionProbability = selected ? firstNum(selectedProjectionIntel, ["regression_probability"]) : null;
 const selectedPeakRevisitProbability = selected ? firstNum(selectedProjectionIntel, ["peak_revisit_probability"]) : null;
 const selectedBreakoutProbability = selected ? firstNum(selectedProjectionIntel, ["breakout_probability"]) : null;
 const selectedBounceProbability = selected ? firstNum(selectedProjectionIntel, ["bounce_probability"]) : null;
 const selectedRunsToPeakEstimate = selected ? firstText(selectedProjectionIntel, ["runs_to_peak_estimate"], "-") : "-";
 const selectedDaysToPeakEstimate = selected ? firstText(selectedProjectionIntel, ["days_to_peak_estimate"], "-") : "-";

 const selectedRunnerForm = selected?.formEnrichment || selected?.row || {};
 const selectedRunnerHistory = selected?.runnerHistory || [];
 const selectedRatedHistory = ratedHistoryRows(selectedRunnerHistory);
 const selectedRatedHistoryChronological = [...selectedRatedHistory].sort((a, b) => historyDateValue(a) - historyDateValue(b));
 const selectedRecentRatedHistory = selectedRatedHistory.slice(0, 5);
 const selectedRecentRatedHistoryChronological = selectedRecentRatedHistory.slice().reverse();
 const selectedHistoryLastRun = selectedRecentRatedHistory[0];
 const selectedHistoryPeakRun = selectedRatedHistory.length
 ? [...selectedRatedHistory].sort((a, b) => (historyRatingValue(b) ?? 0) - (historyRatingValue(a) ?? 0))[0]
 : undefined;
 const selectedFormSignal = selected ? firstText(selectedRunnerForm, ["form_signal"], "-") : "-";
 const selectedFormCycle = selected ? firstText(selectedRunnerForm, ["form_cycle"], "-") : "-";
 const selectedRatingTrend = selected ? firstText(selectedRunnerForm, ["rating_trend"], "-") : "-";
 const selectedRatingTrendDelta = selected ? firstText(selectedRunnerForm, ["rating_trend_delta"], "-") : "-";
 const selectedLastStartRatingValue = selected
 ? historyRatingValue(selectedHistoryLastRun) ?? firstNum(selectedRunnerForm, ["form_last_start_rating", "last_start_rating", "rating_1"])
 : null;
 const selectedAVGRatingLast5Value = selected
 ? (selectedRecentRatedHistory.length
 ? selectedRecentRatedHistory.reduce((sum, historyRow) => sum + (historyRatingValue(historyRow) ?? 0), 0) / selectedRecentRatedHistory.length
 : null)
 ?? firstNum(selectedRunnerForm, ["form_avg_rating_last5", "avg_rating_last5"])
 : null;
 const selectedBestRatingLast5Value = selected
 ? (selectedHistoryPeakRun ? historyRatingValue(selectedHistoryPeakRun) : null)
 ?? firstNum(selectedRunnerForm, ["form_peak_rating_last5", "best_rating_last5", "peak_rating"])
 : null;
 const selectedLastStartRating = selectedLastStartRatingValue === null ? "-" : renderMetricValue(selectedLastStartRatingValue, 1);
 const selectedAVGRatingLast5 = selectedAVGRatingLast5Value === null ? "-" : renderMetricValue(selectedAVGRatingLast5Value, 1);
 const selectedBestRatingLast5 = selectedBestRatingLast5Value === null ? "-" : renderMetricValue(selectedBestRatingLast5Value, 1);
 const selectedRating1 = selected ? firstNum(selectedRunnerForm, ["rating_1"]) : null;
 const selectedRating2 = selected ? firstNum(selectedRunnerForm, ["rating_2"]) : null;
 const selectedRating3 = selected ? firstNum(selectedRunnerForm, ["rating_3"]) : null;
 const selectedRating4 = selected ? firstNum(selectedRunnerForm, ["rating_4"]) : null;
 const selectedRating5 = selected ? firstNum(selectedRunnerForm, ["rating_5"]) : null;
 const selectedRecentRatingsFromForm = [selectedRating5, selectedRating4, selectedRating3, selectedRating2, selectedRating1].filter((value): value is number => value !== null && Number.isFinite(value));
 const selectedRecentRatingsFromHistory = selectedRecentRatedHistoryChronological
 .map((historyRow) => historyRatingValue(historyRow))
 .filter((value): value is number => value !== null && Number.isFinite(value));
 const selectedRecentRatings = selectedRecentRatingsFromHistory.length
 ? selectedRecentRatingsFromHistory
 : selectedRecentRatingsFromForm;
 const selectedFormNarrative = selected ? firstText(selectedRunnerForm, ["performance_intelligence_narrative", "form_narrative"], "") : "";
 const selectedFormPerformanceLabel = selected
 ? performanceIntelligenceLabel(firstText(selectedRunnerForm, ["performance_intelligence_label"], selectedPerformanceIntelligenceBand))
 : "NEUTRAL";
 const selectedFormRunCards = selectedIsScratched
 ? []
 : selectedRecentRatedHistory.length
 ? selectedRecentRatedHistory.slice(0, 5).map((historyRow, index) => ({
 key: `history-${index}-${historyRunKey(historyRow)}`,
 title: `${index + 1}LS`,
 date: formatHistoryDate(historyDateText(historyRow)),
 track: drawerValue(historyTrackText(historyRow)),
 distance: drawerValue(historyDistanceText(historyRow)),
 raceClass: drawerValue(historyClassText(historyRow)),
 going: drawerValue(historyGoingText(historyRow)),
 jockey: drawerValue(historyJockeyText(historyRow)),
 barrier: drawerValue(firstText(historyRow, ["barrier", "draw", "barrier_number"], "-")),
 finishingPosition: drawerValue(historyFinishText(historyRow)),
 beatenMargin: drawerValue(firstText(historyRow, ["margin"], "-")),
 sp: drawerValue(historySpText(historyRow)),
 rating: historyRatingValue(historyRow),
 settledPosition: drawerValue(firstText(historyRow, ["settling_position", "pos_800", "pos_400"], "-")),
 raceShape: firstText(selectedRunnerForm, ["race_shape"], "-").replace(/_/g, " ").toUpperCase(),
 pacePressure: firstText(selectedRunnerForm, ["pace_pressure"], "-").replace(/_/g, " ").toUpperCase(),
 sectionalRank: drawerValue(firstText(historyRow, ["closing_sectional_rank"], "-")),
 againstBias: firstText(selectedRunnerForm, [`last_start_${index + 1}_against_bias_flag`, "against_bias_flag"], "-").replace(/_/g, " ").toUpperCase(),
 performanceLabel: performanceIntelligenceLabel(firstText(selectedRunnerForm, [`last_start_${index + 1}_performance_label`, "performance_intelligence_label"], selectedFormPerformanceLabel)),
 }))
 : Array.from({ length: 5 }, (_, index) => {
 const prefix = `last_start_${index + 1}_`;
 return {
 key: `form-v2-${index}`,
 title: `${index + 1}LS`,
 date: firstText(selectedRunnerForm, [`${prefix}date`], ""),
 track: firstText(selectedRunnerForm, [`${prefix}track`], ""),
 distance: firstText(selectedRunnerForm, [`${prefix}distance`], ""),
 raceClass: firstText(selectedRunnerForm, [`${prefix}class`], ""),
 going: firstText(selectedRunnerForm, [`${prefix}going`, `${prefix}condition`, `${prefix}track_condition`], ""),
 jockey: firstText(selectedRunnerForm, [`${prefix}jockey`, `${prefix}rider`], ""),
 barrier: firstText(selectedRunnerForm, [`${prefix}barrier`, `${prefix}draw`], ""),
 finishingPosition: firstText(selectedRunnerForm, [`${prefix}finishing_position`], ""),
 beatenMargin: firstText(selectedRunnerForm, [`${prefix}beaten_margin`], ""),
 sp: firstText(selectedRunnerForm, [`${prefix}SP`], ""),
 rating: firstNum(selectedRunnerForm, [`${prefix}rating`]),
 settledPosition: firstText(selectedRunnerForm, [`${prefix}settled_position`], ""),
 raceShape: firstText(selectedRunnerForm, ["race_shape"], "-").replace(/_/g, " ").toUpperCase(),
 pacePressure: firstText(selectedRunnerForm, ["pace_pressure"], "-").replace(/_/g, " ").toUpperCase(),
 sectionalRank: firstText(selectedRunnerForm, [`${prefix}sectional_rank`], ""),
 againstBias: firstText(selectedRunnerForm, [`${prefix}against_bias_flag`], "-").replace(/_/g, " ").toUpperCase(),
 performanceLabel: performanceIntelligenceLabel(firstText(selectedRunnerForm, [`${prefix}performance_label`, "performance_intelligence_label"], selectedFormPerformanceLabel)),
 };
 }).filter((run) => run.date || run.track || run.finishingPosition || run.rating !== null);
 const selectedTodayProjectionFigure = selected ? projectionRatingValue(selected) : null;
 const selectedHistoricalRunDate = selectedHistoricalRun ? formatHistoryDate(historyDateText(selectedHistoricalRun)) : "-";
 const selectedHistoricalRunTrack = selectedHistoricalRun ? drawerValue(historyTrackText(selectedHistoricalRun)) : "N/";
 const selectedHistoricalRunRaceNo = selectedHistoricalRun ? drawerValue(historyRaceNoText(selectedHistoricalRun)) : "N/";
 const selectedHistoricalRunDistance = selectedHistoricalRun ? drawerValue(historyDistanceText(selectedHistoricalRun)) : "N/";
 const selectedHistoricalRunClass = selectedHistoricalRun ? drawerValue(historyClassText(selectedHistoricalRun)) : "N/";
 const selectedHistoricalRunCondition = selectedHistoricalRun ? drawerValue(historyGoingText(selectedHistoricalRun)) : "N/";
 const selectedHistoricalRunPosition = selectedHistoricalRun ? drawerValue(historyFinishText(selectedHistoricalRun)) : "N/";
 const selectedHistoricalRunFieldSize = selectedHistoricalRun ? drawerValue(historyFieldSizeText(selectedHistoricalRun)) : "N/";
 const selectedHistoricalRunBarrier = selectedHistoricalRun ? drawerValue(historyBarrierText(selectedHistoricalRun)) : "N/";
 const selectedHistoricalRunJockey = selectedHistoricalRun ? drawerValue(historyJockeyText(selectedHistoricalRun)) : "N/";
 const selectedHistoricalRunWeight = selectedHistoricalRun ? drawerValue(historyWeightText(selectedHistoricalRun)) : "N/";
 const selectedHistoricalRunSp = selectedHistoricalRun ? drawerValue(historySpText(selectedHistoricalRun)) : "N/";
 const selectedHistoricalRunFigure = selectedHistoricalRun ? historyRatingValue(selectedHistoricalRun) : null;
 const selectedHistoricalRunRaceStrength = selectedHistoricalRun ? drawerValue(historyRaceStrengthText(selectedHistoricalRun)) : "N/";
 const selectedHistoricalRunRaceStrengthValue = selectedHistoricalRun ? num(historyRaceStrengthText(selectedHistoricalRun)) : null;
 const selectedHistoricalRunMargin = selectedHistoricalRun ? drawerValue(firstText(selectedHistoricalRun, ["margin"], "-")) : "N/";
 const selectedHistoricalRunPos800 = selectedHistoricalRun ? drawerValue(firstText(selectedHistoricalRun, ["pos_800"], "-")) : "N/";
 const selectedHistoricalRunPos400 = selectedHistoricalRun ? drawerValue(firstText(selectedHistoricalRun, ["pos_400"], "-")) : "N/";
 const selectedHistoricalTodayDifference =
 selectedHistoricalRunFigure !== null && selectedTodayProjectionFigure !== null
 ? selectedTodayProjectionFigure - selectedHistoricalRunFigure
 : null;
 const selectedHistoricalComparisonMax = Math.max(70, selectedHistoricalRunFigure ?? 0, selectedTodayProjectionFigure ?? 0);
 const selectedHistoricalRunSummaryLine = selectedHistoricalRun
 ? [
 selectedHistoricalRunTrack,
 selectedHistoricalRunRaceNo === "N/" ? "" : `R${selectedHistoricalRunRaceNo}`,
 selectedHistoricalRunDistance,
 selectedHistoricalRunClass,
 ]
 .filter((value) => value && value !== "N/")
 .join(" | ")
 : "";
 const selectedHistoricalCareerRank = selectedHistoricalRun
 ? [...selectedRatedHistory]
 .sort((a, b) => (historyRatingValue(b) ?? 0) - (historyRatingValue(a) ?? 0))
 .findIndex((historyRow) => historyRunKey(historyRow) === historyRunKey(selectedHistoricalRun)) + 1
 : 0;
 const selectedHistoricalCareerRankDisplay =
 selectedHistoricalCareerRank > 0 ? ordinal(selectedHistoricalCareerRank) : "N/";
 const selectedHistoricalRunSequence = selectedHistoricalRun
 ? selectedRatedHistoryChronological.findIndex((historyRow) => historyRunKey(historyRow) === historyRunKey(selectedHistoricalRun)) + 1
 : 0;
 const selectedCareerPeakRunSequence = selectedHistoryPeakRun
 ? selectedRatedHistoryChronological.findIndex((historyRow) => historyRunKey(historyRow) === historyRunKey(selectedHistoryPeakRun)) + 1
 : 0;
 const selectedHistoricalRunsBeforePeak =
 selectedHistoricalRunSequence > 0 && selectedCareerPeakRunSequence > 0
 ? selectedCareerPeakRunSequence - selectedHistoricalRunSequence
 : null;
 const selectedTodayVsCareerPeakDifference =
 selectedCareerPeakRating !== null && selectedTodayProjectionFigure !== null
 ? selectedTodayProjectionFigure - selectedCareerPeakRating
 : null;
 const selectedTodayVsCareerPeakNarrative = !selected
 ? ""
 : selectedIsScratched
 ? "Runner scratched."
 : selectedCareerPeakRating !== null && selectedTodayProjectionFigure !== null
 ? `Today's projection is ${Math.abs(selectedTodayVsCareerPeakDifference ?? 0) <= 3 ? "within" : "outside"} ${renderMetricValue(Math.abs(selectedTodayVsCareerPeakDifference ?? 0), 1)} points of career peak.`
 : "Career peak comparison not available from the current historical record.";
 const selectedHistoricalCareerNarrative =
 selectedHistoricalRunFigure !== null && selectedHistoricalCareerRank > 0 && selectedRatedHistory.length
 ? `This run rated ${renderMetricValue(selectedHistoricalRunFigure, 1)} and ranks as the horse's ${ordinal(selectedHistoricalCareerRank)} best career performance from ${selectedRatedHistory.length} rated runs.`
 : "Career rank for this historical run is not available.";
 const selectedHistoricalPeakTimingNarrative = !selectedHistoricalRun
 ? ""
 : selectedHistoricalRunsBeforePeak === null
 ? "Peak timing for this historical run is not available."
 : selectedHistoricalRunsBeforePeak > 0
 ? `This was run number ${selectedHistoricalRunSequence} before the horse reached its career peak on start ${selectedCareerPeakRunSequence}.`
 : selectedHistoricalRunsBeforePeak === 0
 ? "This historical run is the horse's career peak performance."
 : `This came ${Math.abs(selectedHistoricalRunsBeforePeak)} runs after the horse's career peak.`;
 const selectedHistoricalPeakPercent = selectedHistoricalRunFigure !== null && selectedCareerPeakRating
 ? Math.round((selectedHistoricalRunFigure / selectedCareerPeakRating) * 100)
 : null;
 const selectedHistoricalPeakPercentNarrative =
 selectedHistoricalPeakPercent === null
 ? "Peak-percentage comparison unavailable."
 : `This figure is ${selectedHistoricalPeakPercent}% of career peak.`;
 const selectedHistoricalFreshnessNarrative = !selected || selectedIsScratched
 ? "Runner scratched."
 : selectedFreshnessProfile === "PEK THIRD UP"
 ? "This horse historically improves third-up."
 : selectedFreshnessProfile !== "-" && selectedFreshnessProfile !== "NO PTTERN"
 ? `Freshness pattern: ${selectedFreshnessProfile}.`
 : "No strong freshness pattern identified from the historical record.";
 const selectedHistoricalrchetypeNarrative = !selected || selectedIsScratched
 ? "Runner scratched."
 : selectedCareerrchetype !== "-"
 ? `This horse is classified as a ${selectedCareerrchetype}.`
 : "Horse archetype classification is unavailable.";
 const selectedPointsOffPeakNarrative = !selected || selectedIsScratched
 ? "Runner scratched."
 : selectedPointsOffPeak === null
 ? "Points-off-peak comparison unavailable."
 : `This horse is currently ${renderMetricValue(selectedPointsOffPeak, 1)} points below career peak.`;
 const selectedTrajectoryNarrative = !selected || selectedIsScratched
 ? "Runner scratched."
 : selectedTrajectoryDirection !== "-"
 ? `Trajectory: ${selectedTrajectoryDirection}.`
 : "Trajectory direction is unavailable.";
 const selectedBreakoutNarrative = !selected || selectedIsScratched
 ? "Runner scratched."
 : selectedBreakoutPotential !== "-"
 ? `Breakout Potential: ${selectedBreakoutPotential}.`
 : "Breakout potential is unavailable.";
 const selectedCareerPhaseNarrative = !selected || selectedIsScratched
 ? "Runner scratched."
 : selectedCareerPhase !== "-"
 ? `Career Phase: ${selectedCareerPhase}.`
 : "Career phase is unavailable.";
 const selectedProjectionImprovementNarrative = !selected || selectedIsScratched
 ? "Runner scratched."
 : selectedImprovementProbability === null
 ? "Improvement probability is not available from the current projection engine."
 : `This horse has a ${renderMetricValue(selectedImprovementProbability, 0)}% probability of improving next start.`;
 const selectedProjectionCeilingNarrative = !selected || selectedIsScratched
 ? "Runner scratched."
 : selectedCeilingProjection === null
 ? "Projected ceiling is unavailable."
 : `Projected ceiling: ${renderMetricValue(selectedCeilingProjection, 1)}.`;
 const selectedProjectionNextRunNarrative = !selected || selectedIsScratched
 ? "Runner scratched."
 : selectedNextRunProjection === null
 ? "Expected next-run rating is unavailable."
 : `Expected next-run rating: ${renderMetricValue(selectedNextRunProjection, 1)}.`;
 const selectedProjectionRiskNarrative = !selected || selectedIsScratched
 ? "Runner scratched."
 : selectedRegressionProbability === null
 ? "Regression probability is unavailable."
 : `Regression probability: ${renderMetricValue(selectedRegressionProbability, 0)}%.`;

 return {
  selectedCareerIntel,
  selectedrchetypeIntel,
  selectedTrajectoryIntel,
  selectedProjectionIntel,
  selectedCampaignIntel,
  selectedHiddenGemIntel,
  selectedCareerStartsDisplay,
  selectedCareerWinsDisplay,
  selectedCareerPlacesDisplay,
  selectedCareerPeakRating,
  selectedCareerverageRating,
  selectedCareerMedianRating,
  selectedCareerLatestRating,
  selectedCareerLast5verage,
  selectedCareerLast10verage,
  selectedCareerConsistency,
  selectedCareerVolatility,
  selectedCareerBand,
  selectedCareerTrend,
  selectedCareerBestTrack,
  selectedCareerBestDistance,
  selectedCareerBestCondition,
  selectedCareerBestClass,
  selectedCareerWorstTrack,
  selectedCareerWorstDistance,
  selectedCareerWorstCondition,
  selectedCareerPeakDate,
  selectedCareerPeakTrack,
  selectedCareerPeakDistance,
  selectedCareerPeakClass,
  selectedCampaignProfile,
  selectedCampaignProfileBand,
  selectedCampaignCurrentPrepStage,
  selectedCampaignPrepStageLabel,
  selectedCampaignPeakWindowStart,
  selectedCampaignPeakWindowEnd,
  selectedCampaignRiskScore,
  selectedCampaignRiskBand,
  selectedCampaignEvidenceStatus,
  selectedCampaignNarrative,
  selectedCampaignHistoryRuns,
  selectedCampaignStageSampleCount,
  selectedCampaignPrepDisplay,
  selectedCampaignPeakWindowDisplay,
  selectedHiddenGemDisplayBand,
  selectedHiddenGemctionable,
  selectedHiddenGemHistorical,
  selectedHiddenGemRecencyBand,
  selectedHiddenGemDaysSince,
  selectedHiddenGemScore,
  selectedHiddenGemTrigger,
  selectedHiddenGemNarrative,
  selectedHiddenGemDate,
  selectedHiddenGemTrack,
  selectedHiddenGemRaceNo,
  selectedHiddenGemLoaded,
  selectedHiddenGemStatusDisplay,
  selectedPerformanceIntelligenceBand,
  selectedHiddenGemgeDisplay,
  selectedCareerrchetype,
  selectedDevelopmentStage,
  selectedImprovementProfile,
  selectedConsistencyProfile,
  selectedFreshnessProfile,
  selectedrchetypeDistanceProfile,
  selectedSeasonalityProfile,
  selectedCareerPeakgeStage,
  selectedRunsSincePeak,
  selectedPeakTrend,
  selectedCareerLast3verage,
  selectedCareerPercentileScore,
  selectedBoomOrBustFlag,
  selectedLateMaturerFlag,
  selectedEarlyMaturerFlag,
  selectedImproverFlag,
  selectedRegressorFlag,
  selectedTrajectoryDirection,
  selectedTrajectoryStrength,
  selectedTrajectoryScore,
  selectedPointsOffPeak,
  selectedPercentOfPeak,
  selectedRunsSincePeakDisplay,
  selectedDaysSincePeakDisplay,
  selectedImprovementLast3,
  selectedImprovementLast5,
  selectedImprovementLast10,
  selectedBounceRisk,
  selectedRegressionRisk,
  selectedBreakoutPotential,
  selectedCareerPhase,
  selectedProjectionOutlookBand,
  selectedProjectionOutlookConfidence,
  selectedNextRunProjection,
  selectedCeilingProjection,
  selectedFloorProjection,
  selectedExpectedImprovement,
  selectedExpectedRegression,
  selectedImprovementProbability,
  selectedRegressionProbability,
  selectedPeakRevisitProbability,
  selectedBreakoutProbability,
  selectedBounceProbability,
  selectedRunsToPeakEstimate,
  selectedDaysToPeakEstimate,
  selectedRunnerForm,
  selectedRunnerHistory,
  selectedRatedHistory,
  selectedRatedHistoryChronological,
  selectedRecentRatedHistory,
  selectedRecentRatedHistoryChronological,
  selectedHistoryLastRun,
  selectedHistoryPeakRun,
  selectedFormSignal,
  selectedFormCycle,
  selectedRatingTrend,
  selectedRatingTrendDelta,
  selectedLastStartRatingValue,
  selectedAVGRatingLast5Value,
  selectedBestRatingLast5Value,
  selectedLastStartRating,
  selectedAVGRatingLast5,
  selectedBestRatingLast5,
  selectedRating1,
  selectedRating2,
  selectedRating3,
  selectedRating4,
  selectedRating5,
  selectedRecentRatingsFromForm,
  selectedRecentRatingsFromHistory,
  selectedRecentRatings,
  selectedFormNarrative,
  selectedFormPerformanceLabel,
  selectedFormRunCards,
  selectedTodayProjectionFigure,
  selectedHistoricalRunDate,
  selectedHistoricalRunTrack,
  selectedHistoricalRunRaceNo,
  selectedHistoricalRunDistance,
  selectedHistoricalRunClass,
  selectedHistoricalRunCondition,
  selectedHistoricalRunPosition,
  selectedHistoricalRunFieldSize,
  selectedHistoricalRunBarrier,
  selectedHistoricalRunJockey,
  selectedHistoricalRunWeight,
  selectedHistoricalRunSp,
  selectedHistoricalRunFigure,
  selectedHistoricalRunRaceStrength,
  selectedHistoricalRunRaceStrengthValue,
  selectedHistoricalRunMargin,
  selectedHistoricalRunPos800,
  selectedHistoricalRunPos400,
  selectedHistoricalTodayDifference,
  selectedHistoricalComparisonMax,
  selectedHistoricalRunSummaryLine,
  selectedHistoricalCareerRank,
  selectedHistoricalCareerRankDisplay,
  selectedHistoricalRunSequence,
  selectedCareerPeakRunSequence,
  selectedHistoricalRunsBeforePeak,
  selectedTodayVsCareerPeakDifference,
  selectedTodayVsCareerPeakNarrative,
  selectedHistoricalCareerNarrative,
  selectedHistoricalPeakTimingNarrative,
  selectedHistoricalPeakPercent,
  selectedHistoricalPeakPercentNarrative,
  selectedHistoricalFreshnessNarrative,
  selectedHistoricalrchetypeNarrative,
  selectedPointsOffPeakNarrative,
  selectedTrajectoryNarrative,
  selectedBreakoutNarrative,
  selectedCareerPhaseNarrative,
  selectedProjectionImprovementNarrative,
  selectedProjectionCeilingNarrative,
  selectedProjectionNextRunNarrative,
  selectedProjectionRiskNarrative,
 };
}


