from pathlib import Path
import re

path = Path(r".\src\components\SpeedMapTab.tsx")

text = path.read_text(encoding="utf-8")

# REMOVE THE FAKE BOX METRICS
patterns = [
    r'<div className="edgeiq-speedmap-metric-grid">.*?</div>\s*</div>',
]

for pattern in patterns:
    text = re.sub(pattern, '', text, flags=re.S)

# INSERT CLEAN HEADER STRIP
insert_anchor = 'Projected settling positions after first 200m'

replacement = '''Projected settling positions after first 200m</p>

      <div className="edgeiq-speedmap-summary-strip">
        <div className="edgeiq-summary-pill">
          <span>RUNNERS</span>
          <strong>{runners.length}</strong>
        </div>

        <div className="edgeiq-summary-pill">
          <span>TEMPO</span>
          <strong>{tempoLabel}</strong>
        </div>

        <div className="edgeiq-summary-pill">
          <span>PRESSURE</span>
          <strong>{pacePressureScore}/100</strong>
        </div>

        <div className="edgeiq-summary-pill">
          <span>SHAPE</span>
          <strong>{raceShapeLabel}</strong>
        </div>
      </div>'''

text = text.replace(insert_anchor, replacement)

path.write_text(text, encoding="utf-8")

css = Path(r".\src\edgeiq-speedmap-v2.css")

css_text = css.read_text(encoding="utf-8")

css_text += """

/* CLEAN SUMMARY STRIP */

.edgeiq-speedmap-summary-strip {
  display: flex;
  gap: 10px;
  margin-top: 14px;
  margin-bottom: 18px;
}

.edgeiq-summary-pill {
  min-width: 110px;
  padding: 10px 12px;
  border-radius: 12px;
  background:
    linear-gradient(
      180deg,
      rgba(15,23,42,0.96) 0%,
      rgba(5,10,24,0.98) 100%
    );

  border: 1px solid rgba(59,130,246,0.16);
}

.edgeiq-summary-pill span {
  display: block;
  font-size: 9px;
  letter-spacing: 0.14em;
  color: rgba(255,255,255,0.45);
  margin-bottom: 4px;
  font-weight: 800;
}

.edgeiq-summary-pill strong {
  font-size: 18px;
  font-weight: 900;
  color: #ffffff;
}

/* REMOVE GIANT EMPTY LOOK */

.edgeiq-map-column {
  min-height: 380px !important;
}

.edgeiq-map-column-body {
  padding-top: 10px !important;
}

/* BETTER SPACING */

.edgeiq-speedmap-shell {
  padding: 18px !important;
}

/* REMOVE WEAK TEXT */

.edgeiq-speedmap-header p {
  opacity: 0.78 !important;
}

/* CLEAN LIVE MARKET MOVERS */

.edgeiq-market-movers-shell {
  margin-top: 14px !important;
  border-radius: 14px !important;
  border: 1px solid rgba(59,130,246,0.12) !important;
}
"""

css.write_text(css_text, encoding="utf-8")

print("APPLIED CLEAN SPEEDMAP HEADER REBUILD")
