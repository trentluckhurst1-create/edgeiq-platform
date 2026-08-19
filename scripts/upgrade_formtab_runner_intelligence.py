from pathlib import Path

path = Path(r".\src\components\FormTab.tsx")
text = path.read_text(encoding="utf-8")

old = '''            <div className="summary-grid">
              <div><span>1LS</span><strong>{rating(selectedSummary?.ls1 ?? selected?.ls1)}</strong></div>
              <div><span>2LS</span><strong>{rating(selectedSummary?.ls2 ?? selected?.ls2)}</strong></div>
              <div><span>3LS</span><strong>{rating(selectedSummary?.ls3 ?? selected?.ls3)}</strong></div>
              <div><span>Peak</span><strong>{rating(selectedSummary?.peak ?? selected?.peak)}</strong></div>
              <div><span>Avg3</span><strong>{rating(selectedSummary?.avg3)}</strong></div>
              <div><span>Runs</span><strong>{selectedSummary?.officialRunCount ?? "-"}</strong></div>

              <div><span>Run Style</span><strong className="standard-above">{selected?.run_style_cluster || selected?.sectional_profile || "-"}</strong></div>
              <div><span>Late Power</span><strong className="standard-above">{selected?.late_power_index != null ? selected.late_power_index.toFixed(0) : "-"}</strong></div>
              <div><span>Tempo Fit</span><strong>{selected?.tempo_fit || "-"}</strong></div>
              <div><span>Burst Rating</span><strong>{selected?.burst_index != null ? selected.burst_index.toFixed(0) : "-"}</strong></div>
              <div><span>Fatigue Risk</span><strong className="standard-below">{selected?.fatigue_risk_index != null ? selected?.fatigue_risk_index.toFixed(0) : "-"}</strong></div>
              <div><span>Sectional Weapon</span><strong className="standard-above">{selected?.sectional_weapon_score != null ? selected?.sectional_weapon_score.toFixed(0) : "-"}</strong></div>
            </div>'''

new = '''            <div className="summary-grid">
              <div><span>LIVE</span><strong>{price(selected?.marketPrice)}</strong></div>
              <div><span>FAIR</span><strong>{price(selected?.ratedPrice)}</strong></div>
              <div><span>EDGE</span><strong className="standard-above">{selected?.edgePct != null ? `${selected.edgePct.toFixed(1)}%` : "-"}</strong></div>
              <div><span>ACTION</span><strong className="standard-above">{selected ? (selected.edgePct != null && selected.edgePct >= 15 ? "EXECUTE" : selected.edgePct != null && selected.edgePct >= 7 ? "WATCH" : "PASS") : "-"}</strong></div>

              <div><span>1LS</span><strong>{rating(selectedSummary?.ls1 ?? selected?.ls1)}</strong></div>
              <div><span>PEAK</span><strong>{rating(selectedSummary?.peak ?? selected?.peak)}</strong></div>
              <div><span>AVG3</span><strong>{rating(selectedSummary?.avg3)}</strong></div>
              <div><span>RUNS</span><strong>{selectedSummary?.officialRunCount ?? "-"}</strong></div>

              <div><span>STYLE</span><strong>{selected?.run_style_cluster || selected?.sectional_profile || "-"}</strong></div>
              <div><span>LATE PWR</span><strong>{selected?.late_power_index != null ? selected.late_power_index.toFixed(0) : "-"}</strong></div>
              <div><span>TEMPO</span><strong>{selected?.tempo_fit || "-"}</strong></div>
              <div><span>BURST</span><strong>{selected?.burst_index != null ? selected.burst_index.toFixed(0) : "-"}</strong></div>

              <div><span>FATIGUE</span><strong className="standard-below">{selected?.fatigue_risk_index != null ? selected?.fatigue_risk_index.toFixed(0) : "-"}</strong></div>
              <div><span>SECTIONAL</span><strong className="standard-above">{selected?.sectional_weapon_score != null ? selected?.sectional_weapon_score.toFixed(0) : "-"}</strong></div>
              <div><span>CONF</span><strong>{selected?.modelConfidenceScore != null ? selected.modelConfidenceScore.toFixed(0) : "-"}</strong></div>
              <div><span>MAP</span><strong>{selected?.run_style_cluster || "-"}</strong></div>
            </div>'''

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")

print("=" * 80)
print("FORMTAB RUNNER INTELLIGENCE PANEL UPGRADED")
print("=" * 80)
