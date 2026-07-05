import { buildCommandWorkspaceSummary } from "../../services/commandWorkspaceSummaryService";

type RaceCommandWorkspaceProps = {
  activeRaceRows: any[];
  displayExpectedTempo: any;
  fallbackTempoLabel: any;
  bettingConfidence: any;
  trackIntel: any;
  header: any;
  railDisplay: any;
  shellTrack: any;
  selectedRaceNo: any;
  isScratched: any;
  firstNum: any;
  firstText: any;
  projectionRatingValue: any;
  edgePct: any;
  livePrice: any;
  paceMapRole: any;
  barrier: any;
  num: any;
  trackCondition: any;
  track: any;
  raceNo: any;
  raceClass: any;
  distance: any;
  activeRaceStartText: any;
  horse: any;
  saddle: any;
  renderMetricValue: any;
  money: any;
  fairPrice: any;
  pct: any;
  sectionalWeaponValue: any;
  runnerRowKey: any;
  setSelectedKey: any;
  setIntelMode: any;
  marketMoney: any;
};

export function RaceCommandWorkspace({
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
  distance,
  activeRaceStartText,
  horse,
  saddle,
  renderMetricValue,
  money,
  fairPrice,
  pct,
  sectionalWeaponValue,
  runnerRowKey,
  setSelectedKey,
  setIntelMode,
  marketMoney,
}: RaceCommandWorkspaceProps) {
const {
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
 } = buildCommandWorkspaceSummary({
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
 });
 return (
 <section className="edgeiq-race-v3 edgeiq-product-section" aria-label="EDGEiQ Race Briefing">
 <div className="edgeiq-race-v3-header">
 <div>
 <h1>{selectedRaceLabel}</h1>
 <div className="edgeiq-race-v3-meta"><span>{raceClass(header)}</span><span>{distance(header)}</span><span>{activeRaceStartText || "Time TBC"}</span></div>
 <div className="edgeiq-race-v3-submeta"><span>{headerCondition}</span><span>Rail {headerRail}</span><span>{firstText(header, ["minutes_to_jump", "time_to_jump", "jump_countdown"], "Pending to jump")}</span></div>
 </div>
 <section className="edgeiq-race-v3-overview">
 <strong>Race Brief</strong>
 {overviewCards.map(([label, value]) => <div key={`race-v3-overview-${label}`}><span>{label}</span><em>{value && value !== "-" ? value : "Pending"}</em></div>)}
 </section>
 </div>
 <div className="edgeiq-race-v3-hero-cards">
 <article className="edgeiq-race-v3-card top-rated">
 <span>Highest Rated</span>
 <div className="edgeiq-race-v3-runner-feature"><span className="edgeiq-field-silk" aria-label={`${topRated ? horse(topRated.row) : "Runner"} silk`}><i /></span><b>{topRated ? saddle(topRated.row) === 999 ? "-" : saddle(topRated.row) : "-"}</b><strong>{topRated ? horse(topRated.row) : "Pending"}</strong></div>
 <div className="edgeiq-race-v3-card-pair"><em>Current Rating <b>{topRated && runnerEpiValue(topRated) !== null ? renderMetricValue(runnerEpiValue(topRated), 1) : "Pending"}</b></em><em>Projection <b>{topRated && projectedRating(topRated) !== null ? renderMetricValue(projectedRating(topRated), 1) : "Pending"}</b></em></div>
 </article>
 <article className="edgeiq-race-v3-card best-value">
 <span>Primary Overlay</span>
 <div className="edgeiq-race-v3-runner-feature"><span className="edgeiq-field-silk" aria-label={`${bestValue ? horse(bestValue.row) : "Runner"} silk`}><i /></span><b>{bestValue ? saddle(bestValue.row) === 999 ? "-" : saddle(bestValue.row) : "-"}</b><strong>{bestValue ? horse(bestValue.row) : "Pending"}</strong></div>
 <div className="edgeiq-race-v3-card-pair"><em>EDGEiQ Price <b>{bestValue ? money(fairPrice(bestValue.row, bestValue.bet)) : "Pending Market"}</b></em><em>Overlay <b>{bestValue ? pct(edgePct(bestValue.row, bestValue.bet)) : "Pending"}</b></em></div>
 </article>
 <article className="edgeiq-race-v3-card">
 <span>Surface Assessment</span>
 <em>Official</em><strong>{headerCondition}</strong>
 <em>EDGEiQ True Track Rating</em><b>{trueTrackRating}</b>
 <small>Track playing {trackPlaying !== "Pending" ? trackPlaying : trackLengths}</small>
 </article>
 <article className="edgeiq-race-v3-card">
 <span>Tactical Projection</span>
 <em>Pressure</em><strong>{racePacePressure}</strong>
 <em>Tactical Projection</em><b>{raceShapeText}</b>
 <small>On-speed: {raceMapAdvantage} | Backmarkers: {raceKeyRisk || "Pending"}</small>
 </article>
 </div>
 <div className="edgeiq-race-v3-mid-grid">
 <section className="edgeiq-race-v3-panel edgeiq-race-v3-matters">
 <strong>Key Intelligence</strong>
 {whatMatters.map((item, index) => <p key={`race-v3-matter-${index}`}><i />{item}</p>)}
 </section>
 <section className="edgeiq-race-v3-panel edgeiq-race-v3-speed">
 <strong>Projected Running Positions</strong>
 <div className="edgeiq-race-v3-speed-map">
 <div className="edgeiq-race-v3-lanes">{["Lead","On Speed","Midfield","Back","Widest Back"].map((lane) => <span key={`race-v3-lane-${lane}`}>{lane}</span>)}</div>
 {raceMiniMapRows.map((item) => {
 const role = paceMapRole(item);
 const rolePosition: Record<string, number> = { LEADER: 12, "ON PACE": 31, MIDFIELD: 50, BACKMARKER: 70 };
 const runnerBarrier = Number(barrier(item.row) || 1);
 const runnerNo = firstText(item.row, ["runner_number", "saddlecloth", "number", "tab_number", "runner_no", "horse_number"], "-");
 const laneX = role === "BACKMARKER" && runnerBarrier >= Math.max(8, raceFieldSize - 1) ? 89 : rolePosition[role] || 50;
 return <button type="button" key={`race-v3-mini-map-${runnerRowKey(item.row)}`} style={{ left: `${laneX}%`, top: `${22 + ((runnerBarrier + Number(runnerNo || 0)) % 4) * 18}%` }} onClick={() => { setSelectedKey(runnerRowKey(item.row)); setIntelMode("FORM"); }}>{runnerNo}</button>;
 })}
 </div>
 <footer><span>Expected Leader: {expectedLeader ? `${saddle(expectedLeader.row) === 999 ? "-" : saddle(expectedLeader.row)}. ${horse(expectedLeader.row)}` : "Pending"}</span><span>Expected Tempo: <b>{racePacePressure}</b></span></footer>
 </section>
 <section className="edgeiq-race-v3-panel edgeiq-race-v3-market">
 <strong>Market Intelligence</strong>
 <div><span>Market Leader</span><em>{favourite ? `${saddle(favourite.row)}. ${horse(favourite.row)}` : "Pending Market"}</em><b>{favourite ? marketMoney(livePrice(favourite.row, favourite.bet)) : "Pending Market"}</b></div>
 <div><span>Secondary Market Line</span><em>{secondFavourite ? `${saddle(secondFavourite.row)}. ${horse(secondFavourite.row)}` : "Pending Market"}</em><b>{secondFavourite ? marketMoney(livePrice(secondFavourite.row, secondFavourite.bet)) : "Pending Market"}</b></div>
 <div><span>Primary Overlay</span><em>{bestValue ? `${saddle(bestValue.row)}. ${horse(bestValue.row)}` : "Pending"}</em><b>{bestValue ? money(fairPrice(bestValue.row, bestValue.bet)) : "Pending Market"}</b></div>
 <div><span>Market Stability</span><em>{bettingConfidence !== "-" ? bettingConfidence : "Pending"}</em><b>{priceTimestamp || "Pending Market"}</b></div>
 </section>
 <section className="edgeiq-race-v3-panel edgeiq-race-v3-stats">
 <strong>Race Metrics</strong>
 {[["Race Standard", raceStandardValue === null ? "Pending" : renderMetricValue(raceStandardValue, 1)], ["Field Standard", averageRating === null ? "Pending" : renderMetricValue(averageRating, 1)], ["Race Quality", raceQualityText], ["Pressure Rating", racePacePressure], ["Field Depth", raceStrengthText], ["Sectional Strength", sectionalWeaponValue(topRated) === null ? "Pending" : "High"]].map(([label, value]) => <div key={`race-v3-stat-${label}`}><span>{label}</span><em>{value}</em></div>)}
 </section>
 </div>
 <section className="edgeiq-race-v3-panel edgeiq-race-v3-rankings">
 <strong>Primary Contenders</strong>
 <div className="edgeiq-race-v3-rank-row head" role="row">{["NO","SILK","RUNNER","BARRIER","JOCKEY","TRAINER","EPI","PROJECTED","FAIR PRICE","EDGE","LIVE","FLUC"].map((label) => <span key={`race-v3-rank-head-${label}`}>{label}</span>)}</div>
 {raceTopThreeRows.map((item) => {
 const fluc = flucFor(item);
 return <button type="button" className="edgeiq-race-v3-rank-row" role="row" key={`race-v3-rank-${runnerRowKey(item.row)}`} onClick={() => { setSelectedKey(runnerRowKey(item.row)); setIntelMode("FORM"); }}>
 <span>{saddle(item.row) === 999 ? "-" : saddle(item.row)}</span>
 <span className="edgeiq-field-silk" aria-label={`${horse(item.row)} silk`}><i /></span>
 <strong>{horse(item.row)}</strong>
 <span>{barrier(item.row)}</span>
 <span>{firstText(item.row, ["jockey", "jockey_name", "rider"], "-")}</span>
 <span>{firstText(item.row, ["trainer", "trainer_name"], "-")}</span>
 <span>{runnerEpiValue(item) === null ? "Pending" : renderMetricValue(runnerEpiValue(item), 1)}</span>
 <span>{projectedRating(item) === null ? "Pending" : renderMetricValue(projectedRating(item), 1)}</span>
 <span>{money(fairPrice(item.row, item.bet))}</span>
 <span className={(edgePct(item.row, item.bet) ?? 0) > 0 ? "positive" : ""}>{edgePct(item.row, item.bet) === null ? "Pending" : pct(edgePct(item.row, item.bet))}</span>
 <span>{marketMoney(livePrice(item.row, item.bet))}</span>
 <span>{fluc === null ? "Pending Market" : pct(fluc)}</span>
 </button>;
 })}
 <button type="button" className="edgeiq-race-v3-field-link" onClick={() => setIntelMode("RUNNERS")}>Open Field Analysis</button>
 </section>
 <footer className="edgeiq-race-v3-foot">EDGEiQ Race Briefing <span>|</span> Explainable racing intelligence</footer>
 </section>
 );
}

