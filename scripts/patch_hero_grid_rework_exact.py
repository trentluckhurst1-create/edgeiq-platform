from pathlib import Path

p = Path(".\src\components\RaceIntelligenceScreen.tsx")
s = p.read_text(encoding="utf-8")

checkpoint = Path(".\checkpoints\RaceIntelligenceScreen_CHECKPOINT_BEFORE_HERO_GRID_REWORK_EXACT_20260623.tsx")
checkpoint.write_text(s, encoding="utf-8")

old = '''            <div style={{ display: "grid", gridTemplateColumns: "170px 1fr", gap: 12, alignItems: "stretch", marginBottom: 10 }}>
              <div style={{ ...valueTileStyle, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", minHeight: 104 }}>
                <span style={{ ...miniLabelStyle, marginBottom: 5 }}>EDGEIQ SCORE</span>
                <strong style={{ fontSize: 38, lineHeight: 1, color: cellTone(selectedEdgeiqBand), letterSpacing: "-.04em" }}>
                  {selectedIsScratched ? "SCR" : selectedEdgeiqScore}
                </strong>
                <span style={{ marginTop: 8, color: cellTone(selectedEdgeiqBand), fontWeight: 1000, fontSize: 12 }}>{selectedIsScratched ? "SCRATCHED" : selectedEdgeiqBand}</span>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 8 }}>
                <div style={valueTileStyle}><span style={miniLabelStyle}>Stable Intent</span><strong style={{ ...miniValueStyle, color: cellTone(selectedStableIntentBand) }}>{selectedIsScratched ? "SCRATCHED" : selectedStableIntentBand}</strong></div>
                <div style={valueTileStyle}><span style={miniLabelStyle}>Context Signals</span><strong style={{ ...miniValueStyle, color: "#7dd3fc" }}>{selectedIsScratched ? "SCRATCHED" : selectedContextSignalCount}</strong></div>
                <div style={valueTileStyle}><span style={miniLabelStyle}>DNA</span><strong style={{ ...miniValueStyle, color: cellTone(selectedCustomerDnaBand) }}>{selectedIsScratched ? "SCRATCHED" : selectedCustomerDnaBand}</strong></div>
                <div style={valueTileStyle}><span style={miniLabelStyle}>Verdict</span><strong style={{ ...miniValueStyle, color: cellTone(selectedEdgeiqBand) }}>{selectedIsScratched ? "SCRATCHED" : selectedEdgeiqVerdict || "--"}</strong></div>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div style={{ ...valueTileStyle, padding: 10 }}>
                <span style={{ ...miniLabelStyle, color: "#86efac" }}>Why inspect</span>
                <div style={{ display: "grid", gap: 5, marginTop: 7 }}>
                  {selectedEdgeiqReasons.length ? selectedEdgeiqReasons.map((item, index) => (
                    <span key={`edgeiq-reason-${index}`} style={{ color: "#dbe7fb", fontSize: 11, lineHeight: 1.35 }}>• {item}</span>
                  )) : <span style={{ color: "#94a3b8", fontSize: 11 }}>No customer intelligence reasons loaded.</span>}
                </div>
              </div>

              <div style={{ ...valueTileStyle, padding: 10 }}>
                <span style={{ ...miniLabelStyle, color: "#fca5a5" }}>Risks</span>
                <div style={{ display: "grid", gap: 5, marginTop: 7 }}>
                  {selectedEdgeiqRisks.length ? selectedEdgeiqRisks.map((item, index) => (
                    <span key={`edgeiq-risk-${index}`} style={{ color: "#dbe7fb", fontSize: 11, lineHeight: 1.35 }}>• {item}</span>
                  )) : <span style={{ color: "#94a3b8", fontSize: 11 }}>No customer intelligence risks loaded.</span>}
                </div>
              </div>
            </div>'''

new = '''            <div style={{ display: "grid", gridTemplateColumns: "220px 1fr 1fr", gap: 12, alignItems: "stretch", marginBottom: 10 }}>
              <div style={{ ...valueTileStyle, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", minHeight: 146 }}>
                <span style={{ ...miniLabelStyle, marginBottom: 6 }}>EDGEIQ SCORE</span>
                <strong style={{ fontSize: 48, lineHeight: 1, color: cellTone(selectedEdgeiqBand), letterSpacing: "-.05em" }}>
                  {selectedIsScratched ? "SCR" : selectedEdgeiqScore}
                </strong>
                <span style={{ marginTop: 10, color: cellTone(selectedEdgeiqBand), fontWeight: 1000, fontSize: 13 }}>{selectedIsScratched ? "SCRATCHED" : selectedEdgeiqBand}</span>
                <span style={{ marginTop: 8, color: "#94a3b8", fontSize: 10.5, fontWeight: 800 }}>{selectedIsScratched ? "NO ACTION" : selectedEdgeiqVerdict || "--"}</span>
              </div>

              <div style={{ ...valueTileStyle, padding: 12 }}>
                <span style={{ ...miniLabelStyle, color: "#86efac" }}>Positive Signals</span>
                <div style={{ display: "grid", gap: 7, marginTop: 10 }}>
                  {selectedEdgeiqReasons.length ? selectedEdgeiqReasons.map((item, index) => (
                    <div key={`positive-signal-${index}`} style={{ display: "grid", gridTemplateColumns: "8px 1fr", gap: 10, alignItems: "center" }}>
                      <div style={intelligenceDotStyle("#22c55e")} />
                      <span style={{ color: "#dbe7fb", fontSize: 11, lineHeight: 1.35 }}>{item}</span>
                    </div>
                  )) : (
                    <span style={{ color: "#94a3b8", fontSize: 11 }}>No positive signals loaded.</span>
                  )}
                </div>
              </div>

              <div style={{ ...valueTileStyle, padding: 12 }}>
                <span style={{ ...miniLabelStyle, color: "#fca5a5" }}>Risk Signals</span>
                <div style={{ display: "grid", gap: 7, marginTop: 10 }}>
                  {selectedEdgeiqRisks.length ? selectedEdgeiqRisks.map((item, index) => (
                    <div key={`risk-signal-${index}`} style={{ display: "grid", gridTemplateColumns: "8px 1fr", gap: 10, alignItems: "center" }}>
                      <div style={intelligenceDotStyle("#ef4444")} />
                      <span style={{ color: "#dbe7fb", fontSize: 11, lineHeight: 1.35 }}>{item}</span>
                    </div>
                  )) : (
                    <span style={{ color: "#94a3b8", fontSize: 11 }}>No risks loaded.</span>
                  )}
                </div>
              </div>
            </div>'''

if old not in s:
    raise SystemExit("[PATCH FAILED] exact hero block not found")

s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")

print("[HERO_GRID_REWORK_EXACT] COMPLETE")
print(f"checkpoint={checkpoint}")
