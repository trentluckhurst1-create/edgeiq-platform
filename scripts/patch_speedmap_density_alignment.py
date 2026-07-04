from pathlib import Path
import re

css_path = Path(r".\src\edgeiq-speedmap-v2.css")
css = css_path.read_text(encoding="utf-8")

# Tighten row height and improve terminal density
css = re.sub(
    r"\.edgeiq-speed-row\s*\{[^}]*\}",
    """.edgeiq-speed-row {
  display: grid;
  grid-template-columns: 34px 180px 150px 70px 54px minmax(420px, 1fr);
  align-items: center;
  gap: 10px;
  min-height: 28px;
  padding: 4px 12px;
  border-bottom: 1px solid rgba(120,140,170,0.08);
}""",
    css,
    flags=re.S,
)

# Reduce bar height slightly for cleaner institutional look
css = re.sub(
    r"\.edgeiq-speed-bar-wrap\s*\{[^}]*height:\s*20px;",
    """.edgeiq-speed-bar-wrap {
  position: relative;
  grid-column: 6 / -1;
  height: 16px;""",
    css,
    flags=re.S,
)

# Cleaner number alignment
css += """

.edgeiq-speed-row .spd {
  text-align: right;
  padding-right: 6px;
  font-variant-numeric: tabular-nums;
}

.edgeiq-speed-row .barrier {
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.edgeiq-speed-row .horse {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.edgeiq-speed-row .jockey {
  font-size: 11px;
  opacity: 0.92;
}

.edgeiq-speed-table {
  overflow-x: hidden;
}
"""

css_path.write_text(css, encoding="utf-8")

print("=" * 80)
print("SPEED MAP DENSITY + ALIGNMENT PATCHED")
print("=" * 80)
