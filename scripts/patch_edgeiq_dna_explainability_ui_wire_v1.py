from pathlib import Path

path = Path("./src/components/RaceIntelligenceScreen.tsx")
backup = Path("./src/components/RaceIntelligenceScreen_BEFORE_DNA_EXPLAINABILITY_UI_WIRE_V1.tsx")

backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

text = path.read_text(encoding="utf-8")

old_vars = '''  const selectedDnaNarrative = selected ? firstText(selected.dna, ["runner_dna_v6_2_narrative", "runner_dna_v6_1_narrative"], "") : "";'''

new_vars = '''  const selectedDnaNarrative = selected ? firstText(selected.dna, ["impact_explanation", "runner_dna_v6_2_narrative", "runner_dna_v6_1_narrative"], "") : "";
  const selectedPositive1Factor = selected ? firstText(selected.dna, ["positive_1_factor"], "—").replace(/_/g, " ").toUpperCase() : "—";
  const selectedPositive1Impact = selected ? firstText(selected.dna, ["positive_1_impact"], "—") : "—";
  const selectedPositive2Factor = selected ? firstText(selected.dna, ["positive_2_factor"], "—").replace(/_/g, " ").toUpperCase() : "—";
  const selectedPositive2Impact = selected ? firstText(selected.dna, ["positive_2_impact"], "—") : "—";
  const selectedPositive3Factor = selected ? firstText(selected.dna, ["positive_3_factor"], "—").replace(/_/g, " ").toUpperCase() : "—";
  const selectedPositive3Impact = selected ? firstText(selected.dna, ["positive_3_impact"], "—") : "—";
  const selectedNegative1Factor = selected ? firstText(selected.dna, ["negative_1_factor"], "—").replace(/_/g, " ").toUpperCase() : "—";
  const selectedNegative1Impact = selected ? firstText(selected.dna, ["negative_1_impact"], "—") : "—";
  const selectedNegative2Factor = selected ? firstText(selected.dna, ["negative_2_factor"], "—").replace(/_/g, " ").toUpperCase() : "—";
  const selectedNegative2Impact = selected ? firstText(selected.dna, ["negative_2_impact"], "—") : "—";
  const selectedNegative3Factor = selected ? firstText(selected.dna, ["negative_3_factor"], "—").replace(/_/g, " ").toUpperCase() : "—";
  const selectedNegative3Impact = selected ? firstText(selected.dna, ["negative_3_impact"], "—") : "—";'''

if old_vars not in text:
    raise SystemExit("Could not find selectedDnaNarrative variable block")

text = text.replace(old_vars, new_vars)

old_grid = '''              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
                <div style={miniTileStyle}>
                  <span style={miniLabelStyle}>Strongest</span>
                  <strong style={{ ...miniValueStyle, color: selectedIsScratched ? "#94a3b8" : "#7dd3fc" }}>
                    {selectedIsScratched ? "—" : selectedStrongestFactor}
                  </strong>
                  <em style={{ color: "#94a3b8", fontSize: 10, fontStyle: "normal" }}>{selectedIsScratched ? "" : selectedStrongestFactorScore}</em>
                </div>
                <div style={miniTileStyle}>
                  <span style={miniLabelStyle}>Weakest</span>
                  <strong style={{ ...miniValueStyle, color: selectedIsScratched ? "#94a3b8" : "#f5c451" }}>
                    {selectedIsScratched ? "—" : selectedWeakestFactor}
                  </strong>
                  <em style={{ color: "#94a3b8", fontSize: 10, fontStyle: "normal" }}>{selectedIsScratched ? "" : selectedWeakestFactorScore}</em>
                </div>
              </div>'''

new_grid = '''              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
                <div style={{ ...miniTileStyle, gap: 5 }}>
                  <span style={{ ...miniLabelStyle, color: "#7dd3fc" }}>Top Positives</span>
                  {selectedIsScratched ? (
                    <strong style={{ ...miniValueStyle, color: "#94a3b8" }}>—</strong>
                  ) : (
                    [
                      { factor: selectedPositive1Factor, impact: selectedPositive1Impact },
                      { factor: selectedPositive2Factor, impact: selectedPositive2Impact },
                      { factor: selectedPositive3Factor, impact: selectedPositive3Impact },
                    ].map((item, index) => (
                      <div key={`positive-${index}-${item.factor}`} style={{ display: "flex", justifyContent: "space-between", gap: 6, alignItems: "center" }}>
                        <strong style={{ color: "#eaf2ff", fontSize: 10.5, fontWeight: 900, letterSpacing: ".03em" }}>{item.factor}</strong>
                        <em style={{ color: "#5eead4", fontSize: 10.5, fontStyle: "normal", fontWeight: 900 }}>{item.impact}</em>
                      </div>
                    ))
                  )}
                </div>
                <div style={{ ...miniTileStyle, gap: 5 }}>
                  <span style={{ ...miniLabelStyle, color: "#f5c451" }}>Top Risks</span>
                  {selectedIsScratched ? (
                    <strong style={{ ...miniValueStyle, color: "#94a3b8" }}>—</strong>
                  ) : (
                    [
                      { factor: selectedNegative1Factor, impact: selectedNegative1Impact },
                      { factor: selectedNegative2Factor, impact: selectedNegative2Impact },
                      { factor: selectedNegative3Factor, impact: selectedNegative3Impact },
                    ].map((item, index) => (
                      <div key={`negative-${index}-${item.factor}`} style={{ display: "flex", justifyContent: "space-between", gap: 6, alignItems: "center" }}>
                        <strong style={{ color: "#eaf2ff", fontSize: 10.5, fontWeight: 900, letterSpacing: ".03em" }}>{item.factor}</strong>
                        <em style={{ color: "#f87171", fontSize: 10.5, fontStyle: "normal", fontWeight: 900 }}>{item.impact}</em>
                      </div>
                    ))
                  )}
                </div>
              </div>'''

if old_grid not in text:
    raise SystemExit("Could not find old Strongest/Weakest DNA grid block")

text = text.replace(old_grid, new_grid)

text = text.replace("EDGEiQ DNA Read", "EDGEiQ DNA Explanation")
text = text.replace("DNA Factor Breakdown", "DNA Factor Scorecard")

path.write_text(text, encoding="utf-8")

print("[DNA_EXPLAINABILITY_UI_WIRE_V1] COMPLETE")
print(f"backup={backup}")
print(f"updated={path}")
