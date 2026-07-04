from pathlib import Path
import re

p = Path(".\\src\\components\\RaceIntelligenceScreen.tsx")
s = p.read_text(encoding="utf-8")

checkpoint = Path(".\\checkpoints\\RaceIntelligenceScreen_CHECKPOINT_BEFORE_HERO_GRID_REWORK_V2_20260623.tsx")
checkpoint.write_text(s, encoding="utf-8")

# Make hero section 3 columns
s = s.replace(
    'gridTemplateColumns: "170px 1fr"',
    'gridTemplateColumns: "220px 1fr 1fr"',
    1
)

# Replace the 4 tile block with positive/risk signal columns
old = '''
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 8 }}>
                <div style={valueTileStyle}><span style={miniLabelStyle}>Stable Intent</span><strong style={{ ...miniValueStyle, color: cellTone(selectedStableIntentBand) }}>{selectedIsScratched ? "SCRATCHED" : selectedStableIntentBand}</strong></div>
                <div style={valueTileStyle}><span style={miniLabelStyle}>Context Signals</span><strong style={{ ...miniValueStyle, color: "#7dd3fc" }}>{selectedIsScratched ? "SCRATCHED" : selectedContextSignalCount}</strong></div>
                <div style={valueTileStyle}><span style={miniLabelStyle}>DNA</span><strong style={{ ...miniValueStyle, color: cellTone(selectedCustomerDnaBand) }}>{selectedIsScratched ? "SCRATCHED" : selectedCustomerDnaBand}</strong></div>
                <div style={valueTileStyle}><span style={miniLabelStyle}>Verdict</span><strong style={{ ...miniValueStyle, color: cellTone(selectedEdgeiqBand) }}>{selectedIsScratched ? "SCRATCHED" : selectedEdgeiqVerdict || "--"}</strong></div>
              </div>
'''

new = '''
              <div style={{ ...valueTileStyle, padding: 12 }}>
                <span style={{ ...miniLabelStyle, color: "#86efac" }}>
                  Positive Signals
                </span>

                <div style={{ display: "grid", gap: 7, marginTop: 10 }}>
                  {selectedEdgeiqReasons.length ? (
                    selectedEdgeiqReasons.map((item, index) => (
                      <div
                        key={`positive-signal-${index}`}
                        style={{
                          display: "grid",
                          gridTemplateColumns: "8px 1fr",
                          gap: 10,
                          alignItems: "center",
                        }}
                      >
                        <div style={intelligenceDotStyle("#22c55e")} />
                        <span style={{ color: "#dbe7fb", fontSize: 11, lineHeight: 1.35 }}>
                          {item}
                        </span>
                      </div>
                    ))
                  ) : (
                    <span style={{ color: "#94a3b8", fontSize: 11 }}>
                      No positive signals loaded.
                    </span>
                  )}
                </div>
              </div>

              <div style={{ ...valueTileStyle, padding: 12 }}>
                <span style={{ ...miniLabelStyle, color: "#fca5a5" }}>
                  Risk Signals
                </span>

                <div style={{ display: "grid", gap: 7, marginTop: 10 }}>
                  {selectedEdgeiqRisks.length ? (
                    selectedEdgeiqRisks.map((item, index) => (
                      <div
                        key={`risk-signal-${index}`}
                        style={{
                          display: "grid",
                          gridTemplateColumns: "8px 1fr",
                          gap: 10,
                          alignItems: "center",
                        }}
                      >
                        <div style={intelligenceDotStyle("#ef4444")} />
                        <span style={{ color: "#dbe7fb", fontSize: 11, lineHeight: 1.35 }}>
                          {item}
                        </span>
                      </div>
                    ))
                  ) : (
                    <span style={{ color: "#94a3b8", fontSize: 11 }}>
                      No risks loaded.
                    </span>
                  )}
                </div>
              </div>
'''

if old not in s:
    raise SystemExit("[PATCH FAILED] hero block not found")

s = s.replace(old, new, 1)

# Remove duplicated Why Inspect / Risks block
pattern = re.compile(
    r'\n\s*<div style=\{\{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 \}\}>.*?</div>\s*</div>\s*',
    re.DOTALL
)

matches = pattern.findall(s)
if matches:
    s = s.replace(matches[0], "\n", 1)

p.write_text(s, encoding="utf-8")

print("[HERO_GRID_REWORK_V2] COMPLETE")
print(f"checkpoint={checkpoint}")
