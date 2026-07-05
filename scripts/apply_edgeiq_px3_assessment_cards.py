from pathlib import Path

path = Path(r".\src\components\workspaces\RaceCommandWorkspace.tsx")
text = path.read_text(encoding="utf-8")

old = '''          <div className="edgeiq-px2-assessment-grid">
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
          </div>'''

new = '''          <div className="edgeiq-px2-assessment-grid edgeiq-px3-assessment-grid">
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
          </div>'''

if old not in text:
    raise SystemExit("[PX3_CARDS] Could not find assessment card block")

text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
print("[PX3_CARDS] Assessment cards redesigned")
