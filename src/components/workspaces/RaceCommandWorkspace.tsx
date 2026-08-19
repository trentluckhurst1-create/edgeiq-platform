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
    raceFieldSize,
    runnerEpiValue,
    projectedRating,
    raceStandardValue,
    averageRating,
    raceShapeText,
    raceStrengthText,
    raceQualityText,
    racePacePressure,
    raceMapAdvantage,
    raceKeyRisk,
    trackPlaying,
    trueTrackRating,
    trackLengths,
    topRated,
    bestValue,
    favourite,
    secondFavourite,
    priceTimestamp,
    flucFor,
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

  const executiveSummary = `${selectedRaceLabel} profiles as a ${raceShapeText || "developing"} race with ${racePacePressure || "pending"} pressure expected. ${topRated ? horse(topRated.row) : "The highest-rated runner"} leads the current EDGEiQ assessment, while ${bestValue ? horse(bestValue.row) : "market overlay signals"} remain the primary value reference. Surface conditions are assessed as ${headerCondition || "pending"}, with tactical position, rating strength and market alignment forming the core evidence base.`;

  return (
    <section className="edgeiq-px2-command edgeiq-product-section" aria-label="EDGEiQ Race Brief">
      <header className="edgeiq-px2-topbar">
        <div>
          <span className="edgeiq-px2-kicker">Race Brief</span>
          <h1>{selectedRaceLabel}</h1>
          <p>{raceClass(header)} · {distance(header)} · {headerCondition} · Rail {headerRail}</p>
        </div>

        <div className="edgeiq-px2-status-grid">
          <article>
            <span>Time</span>
            <strong>{activeRaceStartText || "Time TBC"}</strong>
          </article>
          <article>
            <span>Jump</span>
            <strong>{firstText(header, ["minutes_to_jump", "time_to_jump", "jump_countdown"], "Pending")}</strong>
          </article>
          <article>
            <span>Confidence</span>
            <strong>{bettingConfidence !== "-" ? bettingConfidence : "Pending"}</strong>
          </article>
          <article>
            <span>Updated</span>
            <strong>{priceTimestamp || "Pending"}</strong>
          </article>
        </div>
      </header>

      <div className="edgeiq-px2-grid">
        <section className="edgeiq-px2-panel edgeiq-px2-brief">
          <div className="edgeiq-px2-section-head">
            <span>01</span>
            <div>
              <strong>Race Brief</strong>
              <p>Executive race assessment and primary intelligence signals.</p>
            </div>
          </div>

          <p className="edgeiq-px2-copy">{executiveSummary}</p>

          <div className="edgeiq-px2-assessment-grid edgeiq-px3-assessment-grid">
            <article className="edgeiq-px2-assessment edgeiq-px3-assessment opportunity">
              <span>Highest Rated</span>
              <div className="edgeiq-px3-runner-hero">
                <b>#{topRated ? saddle(topRated.row) === 999 ? "-" : saddle(topRated.row) : "-"}</b>
                <strong>{topRated ? horse(topRated.row) : "Pending"}</strong>
              </div>
              <section className="edgeiq-px3-card-metrics">
                <div><em>{topRated && runnerEpiValue(topRated) !== null ? renderMetricValue(runnerEpiValue(topRated), 1) : "Pending"}</em><span>Current Rating</span></div>
                <div><em>{topRated && projectedRating(topRated) !== null ? renderMetricValue(projectedRating(topRated), 1) : "Pending"}</em><span>Projection</span></div>
                <div><em>{bettingConfidence !== "-" ? bettingConfidence : "Pending"}</em><span>Confidence</span></div>
              </section>
            </article>

            <article className="edgeiq-px2-assessment edgeiq-px3-assessment overlay">
              <span>Primary Overlay</span>
              <div className="edgeiq-px3-runner-hero">
                <b>#{bestValue ? saddle(bestValue.row) === 999 ? "-" : saddle(bestValue.row) : "-"}</b>
                <strong>{bestValue ? horse(bestValue.row) : "Pending"}</strong>
              </div>
              <section className="edgeiq-px3-card-metrics">
                <div><em>{bestValue ? money(fairPrice(bestValue.row, bestValue.bet)) : "Pending"}</em><span>EDGEiQ Price</span></div>
                <div><em>{bestValue ? marketMoney(livePrice(bestValue.row, bestValue.bet)) : "Pending"}</em><span>Market Price</span></div>
                <div className="is-opportunity"><em>{bestValue ? pct(edgePct(bestValue.row, bestValue.bet)) : "Pending"}</em><span>Overlay</span></div>
              </section>
            </article>

            <article className="edgeiq-px2-assessment edgeiq-px3-assessment risk">
              <span>Principal Risk</span>
              <div className="edgeiq-px3-risk-hero">
                <b>!</b>
                <strong>{raceKeyRisk || "Pending"}</strong>
              </div>
              <p>Risk assessment based on tactical position, race shape and current evidence.</p>
              <small>Monitor runners dependent on tempo, cover and late-race pressure.</small>
            </article>

            <article className="edgeiq-px2-assessment edgeiq-px3-assessment surface">
              <span>Surface Assessment</span>
              <div className="edgeiq-px3-surface-hero">
                <b>{headerCondition}</b>
                <strong>{trueTrackRating}</strong>
              </div>
              <section className="edgeiq-px3-card-metrics">
                <div><em>{trackPlaying !== "Pending" ? trackPlaying : trackLengths}</em><span>Track Playing</span></div>
                <div><em>{headerRail}</em><span>Rail</span></div>
                <div><em>{raceMapAdvantage}</em><span>Favoured Pattern</span></div>
              </section>
            </article>
          </div>
        </section>

        <section className="edgeiq-px2-panel edgeiq-px2-key">
          <div className="edgeiq-px2-section-head">
            <span>02</span>
            <div>
              <strong>Key Intelligence</strong>
              <p>Model-derived observations that matter for this race.</p>
            </div>
          </div>
          <div className="edgeiq-px2-intel-list">
            {whatMatters.map((item, index) => (
              <p key={`px2-intel-${index}`}><i />{item}</p>
            ))}
          </div>
        </section>

        <section className="edgeiq-px2-panel edgeiq-px2-tactical">
          <div className="edgeiq-px2-section-head">
            <span>03</span>
            <div>
              <strong>Tactical Projection</strong>
              <p>Projected race shape and running-position structure.</p>
            </div>
          </div>

          <div className="edgeiq-px2-map">
            <div className="edgeiq-px2-lanes">
              {["Lead", "On Speed", "Midfield", "Back", "Widest Back"].map((lane) => <span key={`px2-lane-${lane}`}>{lane}</span>)}
            </div>
            {raceMiniMapRows.map((item) => {
              const role = paceMapRole(item);
              const rolePosition: Record<string, number> = { LEADER: 12, "ON PACE": 31, MIDFIELD: 50, BACKMARKER: 70 };
              const runnerBarrier = Number(barrier(item.row) || 1);
              const runnerNo = firstText(item.row, ["runner_number", "saddlecloth", "number", "tab_number", "runner_no", "horse_number"], "-");
              const laneX = role === "BACKMARKER" && runnerBarrier >= Math.max(8, raceFieldSize - 1) ? 89 : rolePosition[role] || 50;
              return (
                <button
                  type="button"
                  key={`px2-map-${runnerRowKey(item.row)}`}
                  style={{ left: `${laneX}%`, top: `${22 + ((runnerBarrier + Number(runnerNo || 0)) % 4) * 18}%` }}
                  onClick={() => { setSelectedKey(runnerRowKey(item.row)); setIntelMode("FORM"); }}
                >
                  {runnerNo}
                </button>
              );
            })}
          </div>

          <div className="edgeiq-px2-facts">
            <div><span>Expected Leader</span><strong>{expectedLeader ? `${saddle(expectedLeader.row) === 999 ? "-" : saddle(expectedLeader.row)}. ${horse(expectedLeader.row)}` : "Pending"}</strong></div>
            <div><span>Pressure Rating</span><strong>{racePacePressure}</strong></div>
            <div><span>Favoured Pattern</span><strong>{raceMapAdvantage}</strong></div>
            <div><span>Scenario</span><strong>{raceShapeText}</strong></div>
          </div>
        </section>

        <section className="edgeiq-px2-panel edgeiq-px2-market">
          <div className="edgeiq-px2-section-head">
            <span>04</span>
            <div>
              <strong>Market Intelligence</strong>
              <p>Live market structure compared with EDGEiQ assessment.</p>
            </div>
          </div>

          {[
            ["Market Leader", favourite ? `${saddle(favourite.row)}. ${horse(favourite.row)}` : "Pending Market", favourite ? marketMoney(livePrice(favourite.row, favourite.bet)) : "Pending"],
            ["Secondary Market Line", secondFavourite ? `${saddle(secondFavourite.row)}. ${horse(secondFavourite.row)}` : "Pending Market", secondFavourite ? marketMoney(livePrice(secondFavourite.row, secondFavourite.bet)) : "Pending"],
            ["Primary Overlay", bestValue ? `${saddle(bestValue.row)}. ${horse(bestValue.row)}` : "Pending", bestValue ? money(fairPrice(bestValue.row, bestValue.bet)) : "Pending"],
            ["Market Stability", bettingConfidence !== "-" ? bettingConfidence : "Pending", priceTimestamp || "Pending"],
          ].map(([label, name, value]) => (
            <div className="edgeiq-px2-market-row" key={`px2-market-${label}`}>
              <span>{label}</span>
              <em>{name}</em>
              <strong>{value}</strong>
            </div>
          ))}
        </section>

        <section className="edgeiq-px2-panel edgeiq-px2-metrics">
          <div className="edgeiq-px2-section-head">
            <span>05</span>
            <div>
              <strong>Race Metrics</strong>
              <p>Race-level benchmarks for standard, depth and pressure.</p>
            </div>
          </div>

          <div className="edgeiq-px2-metric-grid">
            {[
              ["Race Standard", raceStandardValue === null ? "Pending" : renderMetricValue(raceStandardValue, 1)],
              ["Field Standard", averageRating === null ? "Pending" : renderMetricValue(averageRating, 1)],
              ["Race Quality", raceQualityText],
              ["Pressure Rating", racePacePressure],
              ["Field Depth", raceStrengthText],
              ["Sectional Strength", sectionalWeaponValue(topRated) === null ? "Pending" : "High"],
            ].map(([label, value]) => (
              <article key={`px2-metric-${label}`}>
                <span>{label}</span>
                <strong>{value}</strong>
              </article>
            ))}
          </div>
        </section>

        <section className="edgeiq-px2-panel edgeiq-px2-contenders">
          <div className="edgeiq-px2-section-head">
            <span>06</span>
            <div>
              <strong>Primary Contenders</strong>
              <p>Highest-priority runners in the current EDGEiQ race assessment.</p>
            </div>
          </div>

          <div className="edgeiq-px2-table">
            <div className="edgeiq-px2-row head" role="row">
              {["NO", "SILK", "RUNNER", "BAR", "JOCKEY", "TRAINER", "CURRENT", "PROJ", "EDGEIQ", "OVERLAY", "LIVE", "FLUC"].map((label) => <span key={`px2-head-${label}`}>{label}</span>)}
            </div>

            {raceTopThreeRows.map((item) => {
              const fluc = flucFor(item);
              const overlay = edgePct(item.row, item.bet);
              return (
                <button
                  type="button"
                  className="edgeiq-px2-row"
                  role="row"
                  key={`px2-contender-${runnerRowKey(item.row)}`}
                  onClick={() => { setSelectedKey(runnerRowKey(item.row)); setIntelMode("FORM"); }}
                >
                  <span>{saddle(item.row) === 999 ? "-" : saddle(item.row)}</span>
                  <span className="edgeiq-field-silk" aria-label={`${horse(item.row)} silk`}><i /></span>
                  <strong>{horse(item.row)}</strong>
                  <span>{barrier(item.row)}</span>
                  <span>{firstText(item.row, ["jockey", "jockey_name", "rider"], "-")}</span>
                  <span>{firstText(item.row, ["trainer", "trainer_name"], "-")}</span>
                  <span>{runnerEpiValue(item) === null ? "Pending" : renderMetricValue(runnerEpiValue(item), 1)}</span>
                  <span>{projectedRating(item) === null ? "Pending" : renderMetricValue(projectedRating(item), 1)}</span>
                  <span>{money(fairPrice(item.row, item.bet))}</span>
                  <span className={(overlay ?? 0) > 0 ? "positive" : "risk"}>{overlay === null ? "Pending" : pct(overlay)}</span>
                  <span>{marketMoney(livePrice(item.row, item.bet))}</span>
                  <span>{fluc === null ? "Pending" : pct(fluc)}</span>
                </button>
              );
            })}
          </div>

          <button type="button" className="edgeiq-px2-field-link" onClick={() => setIntelMode("RUNNERS")}>Open Field Analysis</button>
        </section>
      </div>

      <footer className="edgeiq-px2-footer">
        <span>EDGEiQ Race Brief</span>
        <b>Racing Intelligence Operating System</b>
        <em>Explainable intelligence before prediction</em>
      </footer>
    </section>
  );
}
