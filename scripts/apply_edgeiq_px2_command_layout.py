from pathlib import Path

tsx = Path(r".\src\components\workspaces\RaceCommandWorkspace.tsx")
css = Path(r".\src\styles\edgeiqProductTerminalV1.css")

new_tsx = r'''import { buildCommandWorkspaceSummary } from "../../services/commandWorkspaceSummaryService";

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

  const executiveSummary = `${selectedRaceLabel} is assessed through EDGEiQ's race intelligence framework using current ratings, tactical position, surface evidence, market alignment and confidence signals. The briefing below separates opportunity, risk and context so the user can understand the race before making any decision.`;

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

          <div className="edgeiq-px2-assessment-grid">
            <article className="edgeiq-px2-assessment opportunity">
              <span>Highest Rated</span>
              <div>
                <b>{topRated ? saddle(topRated.row) === 999 ? "-" : saddle(topRated.row) : "-"}</b>
                <strong>{topRated ? horse(topRated.row) : "Pending"}</strong>
              </div>
              <p>Current Rating {topRated && runnerEpiValue(topRated) !== null ? renderMetricValue(runnerEpiValue(topRated), 1) : "Pending"} · Projection {topRated && projectedRating(topRated) !== null ? renderMetricValue(projectedRating(topRated), 1) : "Pending"}</p>
            </article>

            <article className="edgeiq-px2-assessment overlay">
              <span>Primary Overlay</span>
              <div>
                <b>{bestValue ? saddle(bestValue.row) === 999 ? "-" : saddle(bestValue.row) : "-"}</b>
                <strong>{bestValue ? horse(bestValue.row) : "Pending"}</strong>
              </div>
              <p>EDGEiQ Price {bestValue ? money(fairPrice(bestValue.row, bestValue.bet)) : "Pending"} · Overlay {bestValue ? pct(edgePct(bestValue.row, bestValue.bet)) : "Pending"}</p>
            </article>

            <article className="edgeiq-px2-assessment risk">
              <span>Principal Risk</span>
              <div>
                <b>!</b>
                <strong>{raceKeyRisk || "Pending"}</strong>
              </div>
              <p>Risk assessment based on tactical position, race shape and current evidence.</p>
            </article>

            <article className="edgeiq-px2-assessment surface">
              <span>Surface Assessment</span>
              <div>
                <b>{headerCondition}</b>
                <strong>{trueTrackRating}</strong>
              </div>
              <p>Track playing {trackPlaying !== "Pending" ? trackPlaying : trackLengths}</p>
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
'''

tsx.write_text(new_tsx, encoding="utf-8")

css_block = r'''

/* EDGEiQ PX-2 — Race Brief real software layout */
.edgeiq-px2-command {
  display: grid !important;
  gap: 16px !important;
  padding: 0 !important;
}

.edgeiq-px2-topbar,
.edgeiq-px2-panel {
  background: linear-gradient(180deg, rgba(9, 20, 30, .96), rgba(4, 10, 16, .92)) !important;
  border: 1px solid rgba(116, 216, 198, .12) !important;
  border-radius: 18px !important;
  box-shadow: 0 22px 70px rgba(0,0,0,.26) !important;
}

.edgeiq-px2-topbar {
  min-height: 118px !important;
  padding: 22px 24px !important;
  display: grid !important;
  grid-template-columns: minmax(0, 1fr) minmax(520px, .78fr) !important;
  gap: 24px !important;
  align-items: center !important;
}

.edgeiq-px2-kicker,
.edgeiq-px2-section-head > span,
.edgeiq-px2-assessment > span,
.edgeiq-px2-market-row > span,
.edgeiq-px2-metric-grid span {
  color: var(--edge-accent) !important;
  font-size: 10px !important;
  font-weight: 850 !important;
  letter-spacing: .20em !important;
  text-transform: uppercase !important;
}

.edgeiq-px2-topbar h1 {
  margin: 8px 0 7px !important;
  color: var(--edge-text) !important;
  font-size: 34px !important;
  line-height: .98 !important;
  letter-spacing: -.04em !important;
  font-weight: 650 !important;
  text-transform: uppercase !important;
}

.edgeiq-px2-topbar p,
.edgeiq-px2-section-head p,
.edgeiq-px2-copy,
.edgeiq-px2-assessment p,
.edgeiq-px2-footer em {
  color: var(--edge-text-2) !important;
}

.edgeiq-px2-topbar p {
  margin: 0 !important;
  font-size: 13px !important;
  letter-spacing: .03em !important;
}

.edgeiq-px2-status-grid {
  display: grid !important;
  grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
  gap: 10px !important;
}

.edgeiq-px2-status-grid article,
.edgeiq-px2-assessment,
.edgeiq-px2-metric-grid article,
.edgeiq-px2-facts div {
  background: rgba(255,255,255,.025) !important;
  border: 1px solid rgba(116,216,198,.09) !important;
  border-radius: 14px !important;
  padding: 13px 14px !important;
}

.edgeiq-px2-status-grid span {
  display: block !important;
  color: var(--edge-muted) !important;
  font-size: 10px !important;
  letter-spacing: .16em !important;
  text-transform: uppercase !important;
}

.edgeiq-px2-status-grid strong {
  display: block !important;
  margin-top: 7px !important;
  color: var(--edge-text) !important;
  font-size: 15px !important;
  font-weight: 600 !important;
}

.edgeiq-px2-grid {
  display: grid !important;
  grid-template-columns: minmax(0, 1.08fr) minmax(360px, .92fr) !important;
  gap: 16px !important;
  align-items: start !important;
}

.edgeiq-px2-panel {
  padding: 20px !important;
  min-width: 0 !important;
}

.edgeiq-px2-brief,
.edgeiq-px2-contenders {
  grid-column: 1 / -1 !important;
}

.edgeiq-px2-section-head {
  display: flex !important;
  gap: 13px !important;
  align-items: flex-start !important;
  margin-bottom: 16px !important;
}

.edgeiq-px2-section-head > span {
  width: 36px !important;
  height: 28px !important;
  display: grid !important;
  place-items: center !important;
  border: 1px solid rgba(116,216,198,.18) !important;
  border-radius: 9px !important;
  background: rgba(116,216,198,.07) !important;
  flex: 0 0 auto !important;
}

.edgeiq-px2-section-head strong {
  display: block !important;
  color: var(--edge-text) !important;
  font-size: 14px !important;
  letter-spacing: .13em !important;
  text-transform: uppercase !important;
}

.edgeiq-px2-section-head p {
  margin: 5px 0 0 !important;
  font-size: 12px !important;
}

.edgeiq-px2-copy {
  max-width: 980px !important;
  margin: 0 0 18px 49px !important;
  font-size: 14px !important;
  line-height: 1.62 !important;
}

.edgeiq-px2-assessment-grid {
  display: grid !important;
  grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
  gap: 12px !important;
}

.edgeiq-px2-assessment {
  min-height: 142px !important;
  position: relative !important;
  overflow: hidden !important;
}

.edgeiq-px2-assessment::before {
  content: "" !important;
  position: absolute !important;
  inset: 0 auto 0 0 !important;
  width: 3px !important;
  background: rgba(116,216,198,.42) !important;
}

.edgeiq-px2-assessment.overlay::before,
.edgeiq-px2-assessment.opportunity::before { background: rgba(74,222,128,.60) !important; }
.edgeiq-px2-assessment.risk::before { background: rgba(248,113,113,.70) !important; }
.edgeiq-px2-assessment.surface::before { background: rgba(96,165,250,.62) !important; }

.edgeiq-px2-assessment div {
  display: flex !important;
  gap: 10px !important;
  align-items: center !important;
  margin: 14px 0 10px !important;
}

.edgeiq-px2-assessment b {
  min-width: 34px !important;
  height: 34px !important;
  display: grid !important;
  place-items: center !important;
  border-radius: 10px !important;
  background: rgba(116,216,198,.08) !important;
  border: 1px solid rgba(116,216,198,.14) !important;
  color: var(--edge-accent) !important;
  font-size: 13px !important;
}

.edgeiq-px2-assessment strong {
  color: var(--edge-text) !important;
  font-size: 17px !important;
  line-height: 1.1 !important;
  font-weight: 650 !important;
  text-transform: uppercase !important;
}

.edgeiq-px2-assessment p {
  margin: 0 !important;
  font-size: 12px !important;
  line-height: 1.45 !important;
}

.edgeiq-px2-intel-list {
  display: grid !important;
  gap: 10px !important;
}

.edgeiq-px2-intel-list p {
  margin: 0 !important;
  display: grid !important;
  grid-template-columns: 8px minmax(0, 1fr) !important;
  gap: 11px !important;
  align-items: start !important;
  color: var(--edge-text-2) !important;
  font-size: 13px !important;
  line-height: 1.5 !important;
  padding: 10px 0 !important;
  border-bottom: 1px solid rgba(116,216,198,.07) !important;
}

.edgeiq-px2-intel-list i {
  width: 8px !important;
  height: 8px !important;
  margin-top: 5px !important;
  border-radius: 999px !important;
  background: var(--edge-accent) !important;
  box-shadow: 0 0 18px rgba(116,216,198,.42) !important;
}

.edgeiq-px2-map {
  position: relative !important;
  min-height: 260px !important;
  border: 1px solid rgba(116,216,198,.10) !important;
  border-radius: 16px !important;
  background:
    linear-gradient(90deg, rgba(116,216,198,.08), transparent 24%, transparent 76%, rgba(248,113,113,.05)),
    rgba(0,0,0,.18) !important;
  overflow: hidden !important;
}

.edgeiq-px2-lanes {
  position: absolute !important;
  inset: 0 !important;
  display: grid !important;
  grid-template-columns: repeat(5, 1fr) !important;
  pointer-events: none !important;
}

.edgeiq-px2-lanes span {
  border-right: 1px solid rgba(116,216,198,.07) !important;
  color: rgba(235,241,247,.25) !important;
  font-size: 10px !important;
  letter-spacing: .13em !important;
  text-transform: uppercase !important;
  padding: 12px !important;
}

.edgeiq-px2-map button {
  position: absolute !important;
  transform: translate(-50%, -50%) !important;
  width: 30px !important;
  height: 30px !important;
  border: 1px solid rgba(116,216,198,.38) !important;
  border-radius: 999px !important;
  background: rgba(5,12,18,.96) !important;
  color: var(--edge-text) !important;
  font-size: 12px !important;
  font-weight: 850 !important;
  cursor: pointer !important;
}

.edgeiq-px2-map button:hover {
  border-color: rgba(116,216,198,.72) !important;
  background: rgba(116,216,198,.16) !important;
}

.edgeiq-px2-facts,
.edgeiq-px2-metric-grid {
  display: grid !important;
  grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  gap: 10px !important;
  margin-top: 12px !important;
}

.edgeiq-px2-facts span {
  color: var(--edge-muted) !important;
  font-size: 10px !important;
  letter-spacing: .14em !important;
  text-transform: uppercase !important;
}

.edgeiq-px2-facts strong,
.edgeiq-px2-metric-grid strong {
  display: block !important;
  margin-top: 7px !important;
  color: var(--edge-text) !important;
  font-size: 15px !important;
  font-weight: 600 !important;
}

.edgeiq-px2-market-row {
  display: grid !important;
  grid-template-columns: 150px minmax(0, 1fr) 120px !important;
  gap: 12px !important;
  align-items: center !important;
  min-height: 48px !important;
  border-bottom: 1px solid rgba(116,216,198,.08) !important;
}

.edgeiq-px2-market-row em {
  color: var(--edge-text) !important;
  font-style: normal !important;
  font-size: 13px !important;
}

.edgeiq-px2-market-row strong {
  color: var(--edge-accent) !important;
  font-size: 13px !important;
  text-align: right !important;
}

.edgeiq-px2-table {
  overflow-x: auto !important;
  border: 1px solid rgba(116,216,198,.08) !important;
  border-radius: 14px !important;
}

.edgeiq-px2-row {
  display: grid !important;
  grid-template-columns: 48px 48px minmax(180px, 1.25fr) 54px minmax(120px,.8fr) minmax(130px,.9fr) 82px 82px 88px 86px 82px 74px !important;
  gap: 10px !important;
  align-items: center !important;
  min-width: 1120px !important;
  min-height: 44px !important;
  padding: 0 12px !important;
  border: 0 !important;
  border-bottom: 1px solid rgba(116,216,198,.07) !important;
  background: transparent !important;
  color: var(--edge-text-2) !important;
  text-align: left !important;
}

.edgeiq-px2-row.head {
  min-height: 36px !important;
  background: rgba(0,0,0,.22) !important;
  color: var(--edge-muted) !important;
  font-size: 10px !important;
  letter-spacing: .13em !important;
  text-transform: uppercase !important;
}

button.edgeiq-px2-row {
  cursor: pointer !important;
}

button.edgeiq-px2-row:hover {
  background: rgba(116,216,198,.045) !important;
}

.edgeiq-px2-row strong {
  color: var(--edge-text) !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
}

.edgeiq-px2-row span {
  font-size: 12px !important;
  font-variant-numeric: tabular-nums !important;
}

.edgeiq-px2-row .positive {
  color: rgba(74,222,128,.96) !important;
}

.edgeiq-px2-row .risk {
  color: rgba(248,113,113,.92) !important;
}

.edgeiq-px2-field-link {
  margin-top: 14px !important;
  border: 1px solid rgba(116,216,198,.26) !important;
  background: rgba(116,216,198,.07) !important;
  color: var(--edge-accent) !important;
  border-radius: 12px !important;
  padding: 11px 15px !important;
  font-size: 11px !important;
  font-weight: 850 !important;
  letter-spacing: .14em !important;
  text-transform: uppercase !important;
  cursor: pointer !important;
}

.edgeiq-px2-footer {
  display: flex !important;
  gap: 12px !important;
  align-items: center !important;
  justify-content: center !important;
  color: var(--edge-muted) !important;
  font-size: 10px !important;
  letter-spacing: .16em !important;
  text-transform: uppercase !important;
}

.edgeiq-px2-footer span,
.edgeiq-px2-footer b {
  color: var(--edge-accent) !important;
  font-weight: 850 !important;
}

@media (max-width: 1280px) {
  .edgeiq-px2-topbar,
  .edgeiq-px2-grid,
  .edgeiq-px2-assessment-grid {
    grid-template-columns: 1fr !important;
  }

  .edgeiq-px2-status-grid,
  .edgeiq-px2-metric-grid,
  .edgeiq-px2-facts {
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  }

  .edgeiq-px2-copy {
    margin-left: 0 !important;
  }
}

@media (max-width: 760px) {
  .edgeiq-px2-status-grid,
  .edgeiq-px2-metric-grid,
  .edgeiq-px2-facts {
    grid-template-columns: 1fr !important;
  }

  .edgeiq-px2-market-row {
    grid-template-columns: 1fr !important;
    gap: 4px !important;
    padding: 10px 0 !important;
  }

  .edgeiq-px2-market-row strong {
    text-align: left !important;
  }
}
'''

existing_css = css.read_text(encoding="utf-8")
if "EDGEiQ PX-2 — Race Brief real software layout" not in existing_css:
    css.write_text(existing_css + css_block, encoding="utf-8")

print("[PX2_COMMAND_LAYOUT] RaceCommandWorkspace rewritten and CSS appended")
