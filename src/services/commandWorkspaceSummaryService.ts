type Row = Record<string, any>;
type EnrichedRunnerLike = {
  row: Row;
  bet?: Row;
  ratingsHeatmap?: Row;
  mapEnrichment?: Row;
  [key: string]: any;
};

export function buildCommandWorkspaceSummary(params: {
  activeRaceRows: EnrichedRunnerLike[];
  displayExpectedTempo: string;
  fallbackTempoLabel: string;
  bettingConfidence: string;
  trackIntel: Row | undefined;
  header: Row;
  railDisplay: string;
  shellTrack: string;
  selectedRaceNo: string;

  isScratched: (item: EnrichedRunnerLike) => boolean;
  firstNum: (row: Row | undefined, keys: string[]) => number | null;
  firstText: (row: Row | undefined, keys: string[], fallback?: string) => string;
  projectionRatingValue: (item: EnrichedRunnerLike) => number | null;
  edgePct: (row: Row, bet?: Row) => number | null;
  livePrice: (row: Row, bet?: Row) => number | null;
  paceMapRole: (item: EnrichedRunnerLike) => string;
  barrier: (row: Row) => string;
  num: (value: unknown) => number | null;
  trackCondition: (row: Row) => string;
  track: (row: Row) => string;
  raceNo: (row: Row) => string;
  raceClass: (row: Row) => string;
}) {
 const {
  activeRaceRows,
  displayExpectedTempo,
  fallbackTempoLabel,
  bettingConfidence,
  trackIntel,
  header,
  railDisplay,
  shellTrack,
  selectedRaceNo,
  isScratched,
  firstNum,
  firstText,
  projectionRatingValue,
  edgePct,
  livePrice,
  paceMapRole,
  barrier,
  num,
  trackCondition,
  track,
  raceNo,
  raceClass,
 } = params;

 const raceRowsForTab = activeRaceRows.filter((item) => !isScratched(item));
 const raceFieldSize = raceRowsForTab.length || activeRaceRows.length;
 const runnerEpiValue = (item: EnrichedRunnerLike) => firstNum(item.ratingsHeatmap, ["runner_rating", "epi", "performance_index"]) ?? projectionRatingValue(item);
 const projectedRating = (item: EnrichedRunnerLike) => projectionRatingValue(item);
 const raceStandardValue = activeRaceRows.map((item) => firstNum(item.ratingsHeatmap, ["expected_rating"])).find((value) => value !== null) ?? null;
 const runnerRatings = activeRaceRows.map((item) => runnerEpiValue(item)).filter((value): value is number => value !== null);
 const ratingSpread = runnerRatings.length ? Math.max(...runnerRatings) - Math.min(...runnerRatings) : null;
 const averageRating = runnerRatings.length ? runnerRatings.reduce((sum, value) => sum + value, 0) / runnerRatings.length : null;
 const raceShapeText = displayExpectedTempo !== "-" ? displayExpectedTempo : fallbackTempoLabel !== "-" ? fallbackTempoLabel : "Balanced";
 const raceStrengthText = ratingSpread === null ? "Pending" : ratingSpread >= 12 ? "Deep" : ratingSpread >= 7 ? "Competitive" : "Even";
 const raceQualityText = averageRating === null ? "Pending" : averageRating >= 82 ? "High" : averageRating >= 68 ? "Solid" : "Building";
 const cleanWeight = (row: Row) => firstText(row, ["weight", "allocated_weight", "handicap_weight", "weight_carried", "runner_weight", "weight_kg", "wgt"], "-");
 const weightValues = activeRaceRows.map((item) => num(cleanWeight(item.row))).filter((value): value is number => value !== null);
 const weightRange = weightValues.length ? `${Math.min(...weightValues).toFixed(1)} - ${Math.max(...weightValues).toFixed(1)}kg` : "Pending";
 const raceMapSource = activeRaceRows.map((item) => item.mapEnrichment).find(Boolean) || {};
 const racePacePressure = firstText(raceMapSource, ["race_pressure_band_v3", "race_pressure_band_v2", "race_pressure_band_display"], raceShapeText);
 const raceMapAdvantage = firstText(raceMapSource, ["pace_advantage_display_v3", "pace_advantage_display"], "Balanced");
 const raceKeyRisk = firstText(raceMapSource, ["race_shape_verdict_v3", "race_shape_verdict_v2"], "");
 const trackPlaying = firstText(trackIntel, ["track_playing", "track_pattern", "track_advantage_summary"], "Pending");
 const trueTrackRating = firstText(trackIntel, ["edgeiq_true_track_rating", "true_track_rating", "track_rating_true"], trackCondition(header));
 const trackLengths = firstText(trackIntel, ["lengths_faster_slower", "track_lengths_delta", "track_speed_delta"], "Pending");
 const topRated = [...activeRaceRows].sort((a, b) => (runnerEpiValue(b) ?? -999) - (runnerEpiValue(a) ?? -999))[0];
 const bestValue = [...activeRaceRows].filter((item) => edgePct(item.row, item.bet) !== null).sort((a, b) => (edgePct(b.row, b.bet) ?? -999) - (edgePct(a.row, a.bet) ?? -999))[0];
 const openPriceFor = (item: EnrichedRunnerLike) => firstNum({ ...(item.row || {}), ...(item.bet || {}) }, ["open_price", "opening_price", "display_open_price", "market_open_price"]);
 const livePriceRows = [...activeRaceRows].filter((item) => livePrice(item.row, item.bet) !== null).sort((a, b) => (livePrice(a.row, a.bet) ?? 999) - (livePrice(b.row, b.bet) ?? 999));
 const favourite = livePriceRows[0];
 const secondFavourite = livePriceRows[1];
 const priceTimestamp = firstText(header, ["price_timestamp", "market_timestamp", "last_updated", "updated_at"], "");
 const flucFor = (item: EnrichedRunnerLike) => {
 const open = openPriceFor(item);
 const current = livePrice(item.row, item.bet);
 return open !== null && current !== null && open > 0 ? ((current - open) / open) * 100 : null;
 };
 const raceTopThreeRows = [...activeRaceRows].sort((a, b) => (runnerEpiValue(b) ?? -999) - (runnerEpiValue(a) ?? -999)).slice(0, 3);
 const raceMiniMapRows = [...activeRaceRows].sort((a, b) => {
 const roleOrder: Record<string, number> = { LEADER: 1, "ON PACE": 2, MIDFIELD: 3, BACKMARKER: 4 };
 const aRole = roleOrder[paceMapRole(a)] || 9;
 const bRole = roleOrder[paceMapRole(b)] || 9;
 if (aRole !== bRole) return aRole - bRole;
 const aBarrier = Number(barrier(a.row) || 999);
 const bBarrier = Number(barrier(b.row) || 999);
 return aBarrier - bBarrier;
 }).slice(0, 12);
 const expectedLeader = raceMiniMapRows.find((item) => paceMapRole(item) === "LEADER") || raceMiniMapRows[0];
 const whatMatters = [
 racePacePressure !== "-" ? `${racePacePressure} tempo expected.` : "",
 raceMapAdvantage !== "-" ? `${raceMapAdvantage} map advantage in play.` : "",
 trackLengths !== "Pending" ? `Track playing ${trackLengths}.` : "",
 runnerRatings.length >= 3 ? "Two or more high-rating runners shape the race." : "",
 bettingConfidence !== "-" ? `Market confidence ${bettingConfidence.toLowerCase()}.` : "Market confidence pending.",
 raceKeyRisk,
 ].filter((value) => value && value !== "-").slice(0, 5);
 const headerCondition = trackCondition(header);
 const headerRail = railDisplay !== "-" ? railDisplay : "Pending";
 const selectedRaceLabel = `${track(header) || shellTrack} > R${raceNo(header) || selectedRaceNo}`;
 const overviewCards = [
 ["Prizemoney", firstText(header, ["prizemoney", "prize_money", "total_prizemoney"], "Pending")],
 ["Class", raceClass(header)],
 ["Weight Range", weightRange],
 ["Acceptances", String(activeRaceRows.length)],
 ["Scratchings", String(activeRaceRows.filter(isScratched).length)],
 ];

 return {
  raceRowsForTab,
  raceFieldSize,
  runnerEpiValue,
  projectedRating,
  raceStandardValue,
  runnerRatings,
  ratingSpread,
  averageRating,
  raceShapeText,
  raceStrengthText,
  raceQualityText,
  cleanWeight,
  weightValues,
  weightRange,
  raceMapSource,
  racePacePressure,
  raceMapAdvantage,
  raceKeyRisk,
  trackPlaying,
  trueTrackRating,
  trackLengths,
  topRated,
  bestValue,
  openPriceFor,
  livePriceRows,
  favourite,
  secondFavourite,
  priceTimestamp,
  flucFor,
  open,
  raceTopThreeRows,
  raceMiniMapRows,
  expectedLeader,
  whatMatters,
  headerCondition,
  headerRail,
  selectedRaceLabel,
  overviewCards,
 };
}


