from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
RACE_INTEL = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceIntelligenceWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"

def patch_race_intel() -> None:
    text = RACE_INTEL.read_text(encoding="utf-8", errors="replace")
    replacements = {
        'fallback = "â€”"': 'fallback = "-"',
        'raceNo || "â€”"': 'raceNo || "-"',
        '<strong>RACE {raceNo || "â€”"}</strong>': '<strong>RACE {raceNo || "-"}</strong>',
        '<span>â€”</span>': '<span>-</span>',
        '<em>â€”</em>': '<em>-</em>',
        'runner.scratched ? "â€”"': 'runner.scratched ? "-"',
        '<th>EARLY SPEED</th>': '<th>SPD</th>',
        '<th>EDGEIQ PRICE</th>': '<th>EDGEIQ</th>',
        'data-edgeiq-race-workspace-v1="locked"': 'data-edgeiq-race-workspace-v1="repair-v1"',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    RACE_INTEL.write_text(text, encoding="utf-8")


def patch_css() -> None:
    css = CSS.read_text(encoding="utf-8", errors="replace")
    locked_marker = "/* EDGEIQ RACE WORKSPACE V1 LOCKED SPECIFICATION */"
    repair_marker = "/* EDGEIQ RACE WORKSPACE V1 REPAIR - live shell scope */"
    if locked_marker in css and repair_marker not in css:
        start = css.index(locked_marker)
        locked_block = css[start:].strip()
        scoped_block = locked_block.replace(locked_marker, repair_marker).replace(".edgeiq-os .eiq-race-v1", ".eiq-approved-shell .eiq-race-v1")
        css = css.rstrip() + "\n\n" + scoped_block + "\n"
    if "/* EDGEIQ RACE WORKSPACE V1 REPAIR - tab and lane hardening */" not in css:
        css += r'''

/* EDGEIQ RACE WORKSPACE V1 REPAIR - tab and lane hardening */
.eiq-approved-shell .eiq-race-workspace--race {
  width: 100% !important;
  max-width: none !important;
  display: grid !important;
  gap: 12px !important;
  background: #f4f6f9 !important;
}
.eiq-approved-shell .eiq-race-workspace--race > .eiq-context-tabs {
  display: grid !important;
  grid-template-columns: repeat(11, minmax(78px, 1fr)) !important;
  width: 100% !important;
  min-height: 44px !important;
  margin: 0 0 10px !important;
  padding: 4px !important;
  border: 1px solid #dde5ef !important;
  border-radius: 5px !important;
  background: #ffffff !important;
  overflow: hidden !important;
}
.eiq-approved-shell .eiq-race-workspace--race > .eiq-context-tabs button {
  min-height: 38px !important;
  border: 0 !important;
  border-right: 1px solid #e5eaf1 !important;
  border-radius: 0 !important;
  background: #ffffff !important;
  color: #42526e !important;
  font-size: 10px !important;
  font-weight: 800 !important;
  letter-spacing: 0 !important;
  text-transform: uppercase !important;
  white-space: nowrap !important;
}
.eiq-approved-shell .eiq-race-workspace--race > .eiq-context-tabs button.is-active,
.eiq-approved-shell .eiq-race-workspace--race > .eiq-context-tabs button:hover {
  background: #f7fbff !important;
  color: #0b4ea2 !important;
  box-shadow: inset 0 -2px 0 #0b4ea2 !important;
}
.eiq-approved-shell .eiq-race-v1__speed-grid {
  display: grid !important;
  grid-template-columns: 1fr !important;
  gap: 8px !important;
}
.eiq-approved-shell .eiq-race-v1__speed-zone {
  min-height: 40px !important;
  display: grid !important;
  grid-template-columns: 92px minmax(0, 1fr) !important;
  align-items: center !important;
  gap: 10px !important;
  padding: 0 !important;
  border: 0 !important;
  background: transparent !important;
}
.eiq-approved-shell .eiq-race-v1__speed-zone > strong {
  color: #637083 !important;
  font-size: 11px !important;
  font-weight: 900 !important;
}
.eiq-approved-shell .eiq-race-v1__speed-zone > div {
  position: relative !important;
  min-height: 30px !important;
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  padding: 3px 8px !important;
  border: 1px solid #d5e3f3 !important;
  border-radius: 999px !important;
  background: linear-gradient(90deg, #d9ebff 0%, #eef5ff 52%, #f8fafc 100%) !important;
  overflow: hidden !important;
}
.eiq-approved-shell .eiq-race-v1__speed-zone > div::after {
  content: "" !important;
  position: absolute !important;
  left: 10px !important;
  right: 10px !important;
  top: 50% !important;
  height: 2px !important;
  transform: translateY(-50%) !important;
  background: #9bc7f5 !important;
}
.eiq-approved-shell .eiq-race-v1__speed-zone span {
  position: relative !important;
  z-index: 1 !important;
  min-height: 24px !important;
  max-width: 180px !important;
  display: inline-flex !important;
  align-items: center !important;
  gap: 6px !important;
  padding: 0 8px !important;
  border: 1px solid #0b4ea2 !important;
  border-radius: 999px !important;
  background: #ffffff !important;
  color: #0d1b3d !important;
  font-size: 11px !important;
  font-weight: 800 !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}
.eiq-approved-shell .eiq-race-v1__speed-zone b,
.eiq-approved-shell .eiq-race-v1__speed-zone em {
  color: #0b4ea2 !important;
  flex: 0 0 auto !important;
}
.eiq-approved-shell .eiq-race-v1__table th:nth-child(9)::after { content: "" !important; }
@media (max-width: 1366px) {
  .eiq-approved-shell .eiq-race-workspace--race > .eiq-context-tabs { grid-template-columns: repeat(6, minmax(96px, 1fr)) !important; }
}
'''
    CSS.write_text(css, encoding="utf-8")


def main() -> None:
    patch_race_intel()
    patch_css()
    print("Race workspace repair applied")

if __name__ == "__main__":
    main()
