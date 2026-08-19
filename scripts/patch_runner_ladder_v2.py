from pathlib import Path
import re

css_path = Path(r".\src\index.css")
css = css_path.read_text(encoding="utf-8")

# Make left ladder compact + elite terminal style
css += """

/* =========================================================
   EDGEIQ RUNNER LADDER V2
   ========================================================= */

.edgeiq-runner-ladder-head {
  grid-template-columns: 24px minmax(120px,1fr) 48px 48px 52px !important;
}

.edgeiq-runner-ladder-head span:nth-child(6),
.edgeiq-runner-ladder-head span:nth-child(7) {
  display: none !important;
}

.edgeiq-runner-decision-row {
  grid-template-columns: 24px minmax(120px,1fr) 48px 48px 52px !important;
  min-height: 28px !important;
  padding: 0 7px !important;
  border-bottom: 1px solid rgba(40,55,75,.38) !important;
}

.edgeiq-runner-decision-row .map,
.edgeiq-runner-decision-row .action {
  display: none !important;
}

.edgeiq-runner-decision-row .runner {
  font-size: 10px !important;
  letter-spacing: .02em !important;
}

.edgeiq-runner-decision-row .price,
.edgeiq-runner-decision-row .edge-pos,
.edgeiq-runner-decision-row .edge-muted {
  font-size: 10px !important;
  font-variant-numeric: tabular-nums !important;
}

.edgeiq-runner-decision-row.active {
  background:
    linear-gradient(
      90deg,
      rgba(16,185,129,.22) 0%,
      rgba(10,18,32,.96) 70%
    ) !important;
}

.edgeiq-runner-decision-table {
  scrollbar-width: thin;
}

.edgeiq-runner-decision-table::-webkit-scrollbar {
  width: 6px;
}

.edgeiq-runner-decision-table::-webkit-scrollbar-thumb {
  background: rgba(80,110,140,.55);
  border-radius: 999px;
}

"""

css_path.write_text(css, encoding="utf-8")

print("=" * 80)
print("RUNNER LADDER CLEANED + COMPACTED")
print("=" * 80)
