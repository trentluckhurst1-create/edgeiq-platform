from pathlib import Path
import re

path = Path(r".\src\components\SpeedMapTab.tsx")

text = path.read_text(encoding="utf-8")

# CLEAN UGLY TITLE BLOCK
text = re.sub(
    r'EDGEIQ TRUE SPEED MAP',
    '200m Settling Map',
    text
)

text = re.sub(
    r'VIC - Left-handed - rail to wide positioning',
    'Projected settling positions after first 200m',
    text
)

# REMOVE FAKE CLUTTER LABELS
remove_blocks = [
    "TRACK",
    "CONFIDENCE",
    "COLLAPSE",
    "PREFERRED"
]

for block in remove_blocks:
    text = text.replace(block, "")

# BETTER COLUMN LABELS
text = text.replace("LEADER", "LEAD")
text = text.replace("MIDFIELD", "MID")
text = text.replace("BACKMARKER", "BACK")

path.write_text(text, encoding="utf-8")

css = Path(r".\src\edgeiq-speedmap-v2.css")

css_text = css.read_text(encoding="utf-8")

css_text += """

/* CLEAN SPEED MAP V4 */

.edgeiq-speedmap-shell {
  background:
    linear-gradient(
      180deg,
      rgba(5,10,24,0.98) 0%,
      rgba(3,7,18,0.98) 100%
    ) !important;

  border: 1px solid rgba(59,130,246,0.16) !important;
}

.edgeiq-speedmap-header h2 {
  font-size: 36px !important;
  font-weight: 900 !important;
  letter-spacing: -0.04em !important;
  color: #ffffff !important;
}

.edgeiq-speedmap-header p {
  color: rgba(255,255,255,0.55) !important;
  font-size: 12px !important;
}

.edgeiq-map-column {
  background:
    linear-gradient(
      180deg,
      rgba(15,23,42,0.96) 0%,
      rgba(5,10,24,0.98) 100%
    ) !important;

  border-radius: 14px !important;
}

.edgeiq-map-column-title {
  font-size: 11px !important;
  font-weight: 900 !important;
  letter-spacing: 0.14em !important;
  color: rgba(255,255,255,0.82) !important;
}

.edgeiq-map-runner {
  min-height: 36px !important;
  border-radius: 10px !important;
  background: rgba(15,23,42,0.92) !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
}

.edgeiq-map-runner:hover {
  transform: translateY(-1px);
  border-color: rgba(59,130,246,0.45) !important;
}

.edgeiq-map-runner-name {
  font-size: 11px !important;
  font-weight: 800 !important;
  color: #ffffff !important;
}

.edgeiq-map-runner-barrier {
  color: rgba(255,255,255,0.45) !important;
  font-size: 10px !important;
}

.edgeiq-speedmap-grid {
  opacity: 0.08 !important;
}

.edgeiq-map-column.lead {
  border-top: 2px solid #22c55e !important;
}

.edgeiq-map-column.onpace {
  border-top: 2px solid #3b82f6 !important;
}

.edgeiq-map-column.mid {
  border-top: 2px solid #f59e0b !important;
}

.edgeiq-map-column.back {
  border-top: 2px solid #a855f7 !important;
}
"""

css.write_text(css_text, encoding="utf-8")

print("CLEAN SPEED MAP V4 APPLIED")
