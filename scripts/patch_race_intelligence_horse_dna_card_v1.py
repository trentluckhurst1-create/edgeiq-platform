from pathlib import Path

path = Path("src/components/RaceIntelligenceScreen.tsx")
s = path.read_text(encoding="utf-8")

old_vars = '''  const selectedLatePower = selected
    ? firstNum(selected.runnerIntel, ["late_power_index"]) ?? firstNum(selected.drawer, ["late_power_index"])
    : null;
'''

new_vars = '''  const selectedLatePower = selected
    ? firstNum(selected.runnerIntel, ["late_power_index"]) ?? firstNum(selected.drawer, ["late_power_index"])
    : null;
  const selectedCareerStarts = selected ? firstText(selected.drawer, ["career_starts_profile"], "—") : "—";
  const selectedCareerWins = selected ? firstText(selected.drawer, ["career_wins_profile"], "—") : "—";
  const selectedCareerPlaces = selected ? firstText(selected.drawer, ["career_places_profile"], "—") : "—";
  const selectedLast5Form = selected ? firstText(selected.drawer, ["last_5_form_profile"], "—") : "—";
  const selectedProfileQuality = selected ? firstText(selected.drawer, ["profile_quality"], "—").replace(/_/g, " ").toUpperCase() : "—";
  const selectedDominantRunStyle = selected ? firstText(selected.drawer, ["dominant_run_style", "run_style"], "—").replace(/_/g, " ").toUpperCase() : "—";
  const selectedSectionalStrengthRating = selected ? firstText(selected.drawer, ["sectional_strength_rating"], "—") : "—";
  const selectedSectionalStrengthBand = selected ? firstText(selected.drawer, ["sectional_strength_band"], "—").replace(/_/g, " ").toUpperCase() : "—";
'''

if "selectedCareerStarts" not in s:
    if old_vars not in s:
        raise SystemExit("Could not find selectedLatePower block")
    s = s.replace(old_vars, new_vars)

old_card = '''            <div style={breakdownCardStyle}>
              <div style={{ ...metricRowStyle, marginBottom: 2 }}>
                <span>Performance Factors</span>
                <span style={breakdownPill(selectedIsScratched ? "SCRATCHED" : "LIVE")}>{selectedIsScratched ? "SCRATCHED" : "LIVE"}</span>
              </div>
'''

new_card = '''            <div style={breakdownCardStyle}>
              <div style={{ ...metricRowStyle, marginBottom: 2 }}>
                <span>Horse DNA</span>
                <span style={breakdownPill(selectedIsScratched ? "SCRATCHED" : selectedProfileQuality)}>{selectedIsScratched ? "SCRATCHED" : selectedProfileQuality}</span>
              </div>
              <div style={metricRowStyle}>
                <span>Career</span>
                <strong style={selectedIsScratched ? { color: "#94a3b8" } : undefined}>
                  {selectedIsScratched ? "—" : `${selectedCareerStarts}: ${selectedCareerWins}-${selectedCareerPlaces}`}
                </strong>
              </div>
              <div style={metricRowStyle}>
                <span>Last 5</span>
                <strong style={selectedIsScratched ? { color: "#94a3b8" } : undefined}>{selectedIsScratched ? "—" : selectedLast5Form}</strong>
              </div>
              <div style={metricRowStyle}>
                <span>Run Style</span>
                <strong style={selectedIsScratched ? { color: "#94a3b8" } : { color: cellTone(selectedDominantRunStyle) }}>{selectedIsScratched ? "—" : selectedDominantRunStyle}</strong>
              </div>
              <div style={metricRowStyle}>
                <span>Sectional DNA</span>
                <strong style={selectedIsScratched ? { color: "#94a3b8" } : { color: cellTone(selectedSectionalStrengthBand) }}>
                  {selectedIsScratched ? "—" : `${selectedSectionalStrengthBand}${selectedSectionalStrengthRating !== "—" ? ` ${Number(selectedSectionalStrengthRating).toFixed(1)}` : ""}`}
                </strong>
              </div>
              <div style={{ color: "#94a3b8", fontSize: 11, lineHeight: 1.4 }}>
                Warehouse-backed career profile, run style and sectional DNA.
              </div>
            </div>

            <div style={breakdownCardStyle}>
              <div style={{ ...metricRowStyle, marginBottom: 2 }}>
                <span>Performance Factors</span>
                <span style={breakdownPill(selectedIsScratched ? "SCRATCHED" : "LIVE")}>{selectedIsScratched ? "SCRATCHED" : "LIVE"}</span>
              </div>
'''

if "<span>Horse DNA</span>" not in s:
    if old_card not in s:
        raise SystemExit("Could not find Performance Factors card")
    s = s.replace(old_card, new_card, 1)

path.write_text(s, encoding="utf-8")
print("[FORCE_HORSE_DNA_PATCH] COMPLETE")
