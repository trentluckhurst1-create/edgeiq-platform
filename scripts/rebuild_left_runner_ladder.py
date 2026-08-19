from pathlib import Path
import re

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

pattern = r'''<section className="edgeiq-race-left terminal-card">[\s\S]*?</section>\s*<section className="edgeiq-race-centre">'''

replacement = '''<section className="edgeiq-race-left terminal-card">
                <div className="edgeiq-panel-title">RUNNER DECISION LADDER</div>

                <div className="edgeiq-runner-ladder-head">
                  <span>#</span>
                  <span>HORSE</span>
                  <span>LIVE</span>
                  <span>FAIR</span>
                  <span>EDGE</span>
                  <span>MAP</span>
                  <span>ACTION</span>
                </div>

                <div className="edgeiq-runner-decision-table">
                  {(currentRace?.rows ?? []).filter((row) => !row.isScratched).map((row) => {
                    const action = runnerDecision(row);
                    const edge = saneOverlay(row.edgePct);
                    const map = row.run_style_cluster || row.sectional_profile || "-";

                    return (
                      <button
                        key={row.id}
                        type="button"
                        className={`edgeiq-runner-decision-row ${selectedRunner?.id === row.id ? "active" : ""}`}
                        onClick={() => setSelectedHorseKey(row.horseKey)}
                      >
                        <span className="num">{row.horseNo ?? "-"}</span>
                        <span className="runner">{row.horse}</span>
                        <span className="price">{row.marketPrice ? row.marketPrice.toFixed(2) : "-"}</span>
                        <span className="price">{row.ratedPrice ? row.ratedPrice.toFixed(2) : "-"}</span>
                        <strong className={edge !== null && edge > 0 ? "edge-pos" : "edge-muted"}>
                          {edge === null ? "-" : `${edge.toFixed(1)}%`}
                        </strong>
                        <span className="map">{map}</span>
                        <span className={`action action-${action.toLowerCase()}`}>{action}</span>
                      </button>
                    );
                  })}
                </div>
              </section>

              <section className="edgeiq-race-centre">'''

text2 = re.sub(pattern, replacement, text, count=1)

if text2 == text:
    raise SystemExit("LEFT PANEL BLOCK REPLACEMENT FAILED")

path.write_text(text2, encoding="utf-8")

print("REBUILT LEFT RUNNER DECISION LADDER")
