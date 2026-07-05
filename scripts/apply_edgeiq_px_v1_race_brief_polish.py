from pathlib import Path

path = Path("src/components/workspaces/RaceCommandWorkspace.tsx")
text = path.read_text(encoding="utf-8")

replacements = {
  "EDGEiQ Race Intelligence": "EDGEiQ Race Briefing",
  "Race Overview": "Race Brief",
  "Top Rated": "Highest Rated",
  "Best Value": "Primary Overlay",
  "Track Condition": "Surface Assessment",
  "Race Shape": "Tactical Projection",
  "What Matters Today": "Key Intelligence",
  "Speed Map Preview": "Projected Running Positions",
  "Quick Market Snapshot": "Market Intelligence",
  "Key Stats At A Glance": "Race Metrics",
  "Top 3 Rankings": "Primary Contenders",
  "EPI Rating": "Current Rating",
  "Projected Rating": "Projection",
  "Fair Price": "EDGEiQ Price",
  "Edge": "Overlay",
  "Favourite": "Market Leader",
  "2nd Fav": "Secondary Market Line",
  "Market Confidence": "Market Stability",
  "Race Rating": "Race Standard",
  "Average Field Rating": "Field Standard",
  "Tempo Pressure": "Pressure Rating",
  "Sectional Quality": "Sectional Strength",
  "View Full Field": "Open Field Analysis",
  "Data is modelled and subject to change": "Explainable racing intelligence",
}

for old, new in replacements.items():
    text = text.replace(old, new)

text = text.replace(
'''<section className="edgeiq-race-v3-overview">
<strong>Race Brief</strong>
{overviewCards.map(([label, value]) => <div key={`race-v3-overview-${label}`}><span>{label}</span><em>{value && value !== "-" ? value : "Pending"}</em></div>)}
</section>''',
'''<section className="edgeiq-race-v3-overview edgeiq-race-brief-executive">
<strong>Race Brief</strong>
<p className="edgeiq-race-brief-copy">
{raceShapeText !== "Pending" ? `Projected race pattern: ${raceShapeText}. ` : "Race pattern assessment pending. "}
{racePacePressure !== "Pending" ? `Pressure profile: ${racePacePressure}. ` : ""}
{raceMapAdvantage && raceMapAdvantage !== "Pending" ? `Likely tactical advantage: ${raceMapAdvantage}.` : ""}
</p>
{overviewCards.map(([label, value]) => <div key={`race-v3-overview-${label}`}><span>{label}</span><em>{value && value !== "-" ? value : "Pending"}</em></div>)}
</section>'''
)

path.write_text(text, encoding="utf-8")

css_path = Path("src/styles/edgeiqProductTerminalV1.css")
css = css_path.read_text(encoding="utf-8")

append = r'''

/* EDGEiQ PX V1 — Race Brief professional hierarchy */
.edgeiq-race-brief-executive {
  padding: 18px !important;
  border: 1px solid rgba(255, 255, 255, 0.10) !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.045), rgba(255,255,255,0.018)),
    rgba(7, 11, 18, 0.92) !important;
}

.edgeiq-race-brief-executive > strong {
  letter-spacing: 0.16em !important;
  text-transform: uppercase !important;
}

.edgeiq-race-brief-copy {
  margin: 8px 0 12px !important;
  color: rgba(235, 241, 247, 0.86) !important;
  font-size: 13px !important;
  line-height: 1.55 !important;
  max-width: 760px !important;
}

.edgeiq-race-v3-card span,
.edgeiq-race-v3-panel > strong {
  letter-spacing: 0.13em !important;
  text-transform: uppercase !important;
}

.edgeiq-race-v3-card strong,
.edgeiq-race-v3-card b,
.edgeiq-race-v3-panel em {
  font-variant-numeric: tabular-nums !important;
}

.edgeiq-race-v3-foot {
  letter-spacing: 0.14em !important;
  text-transform: uppercase !important;
  color: rgba(235, 241, 247, 0.62) !important;
}
'''

if "EDGEiQ PX V1 — Race Brief professional hierarchy" not in css:
    css_path.write_text(css + append, encoding="utf-8")

print("[PX_V1] Race Brief language and hierarchy polish applied")
