from pathlib import Path
from datetime import datetime, timezone
import csv
import shutil

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
TSX = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
INDEX_CSS = ROOT / "src" / "index.css"
PRODUCT_CSS = ROOT / "src" / "styles" / "edgeiqProductTerminalV1.css"
TSX_CHECKPOINT = ROOT / "src" / "components" / "RaceIntelligenceScreen_CHECKPOINT_PRE_PRODUCT_RACE_PAGE_ROUTING_V1_20260630.tsx"
INDEX_CHECKPOINT = ROOT / "src" / "index_CHECKPOINT_PRE_PRODUCT_RACE_PAGE_ROUTING_V1_20260630.css"
PRODUCT_CSS_CHECKPOINT = ROOT / "src" / "styles" / "edgeiqProductTerminalV1_CHECKPOINT_PRE_PRODUCT_RACE_PAGE_ROUTING_V1_20260630.css"
SUMMARY = ROOT / "public" / "data" / "edgeiq_product_race_page_routing_v1_summary.csv"
REPORT = ROOT / "public" / "data" / "edgeiq_product_race_page_routing_v1_report.txt"

PRODUCT_NAV_BLOCK = '''      <section className="edgeiq-race-product-shell" aria-label="EDGEiQ race workspace">
        <div className="edgeiq-race-product-topbar">
          <button type="button" className="edgeiq-race-brand" onClick={() => updateProductView("HOME")}>
            <span className="edgeiq-race-brand-mark">EDGEiQ</span>
            <span className="edgeiq-race-brand-subtitle">Racing Intelligence</span>
          </button>

          <nav className="edgeiq-race-primary-nav" aria-label="Race navigation">
            {intelModeTabs.map((tab) => (
              <button
                key={`product-race-nav-${tab.mode}`}
                type="button"
                className={`edgeiq-race-nav-button ${intelMode === tab.mode ? "is-active" : ""}`}
                onClick={() => setIntelMode(tab.mode)}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          <div className="edgeiq-race-account-panel">
            <span>EDGEiQ</span>
            <strong>{selectedShellMeeting?.meetingStatus || "LIVE WORKSPACE"}</strong>
            <button type="button" onClick={() => updateProductView("MEETING")}>Meeting</button>
          </div>
        </div>

        <div className="edgeiq-race-identity-card">
          <div className="edgeiq-race-identity-main">
            <span className="edgeiq-race-kicker">Race Workspace</span>
            <h1>{track(header)} R{raceNo(header)}</h1>
            <div className="edgeiq-race-identity-meta" aria-label="Race details">
              <span>{distance(header)}</span>
              {raceClass(header) !== "—" && <span>{raceClass(header)}</span>}
              <span>{trackCondition(header).toUpperCase()}</span>
              <span>{activeRaceRows.length} runners</span>
              {railDisplay !== "—" && <span>Rail {railDisplay}</span>}
            </div>
          </div>

          <div className="edgeiq-race-identity-source">
            <span className="edgeiq-race-status-pill good">Data {`${activeRaceRows.length}/${raceRows.length || activeRaceRows.length}`} runners</span>
            <span className="edgeiq-race-status-pill info">Engine active</span>
            <span className={livePriceRowCount > 0 ? "edgeiq-race-status-pill good" : "edgeiq-race-status-pill source"}>{livePriceRowCount > 0 ? `Market ${marketStatus}` : "Market source unavailable"}</span>
            <span className="edgeiq-race-status-pill info">Confidence {bettingConfidence}</span>
          </div>
        </div>
      </section>

'''

RACE_TAB_HEADER = '''        <div className="edgeiq-race-tab-hero">
          <div>
            <span className="edgeiq-race-kicker">RACE</span>
            <h2>Race Intelligence</h2>
            <p>{raceAssessmentNarrative || customerBriefingNarrative || briefingNarrative || "Race intelligence is loaded for this field."}</p>
          </div>
          <div className="edgeiq-race-tab-scoreline">
            <span>{track(header)} R{raceNo(header)}</span>
            <strong>{activeRaceRows.length} runners</strong>
          </div>
        </div>

        <div className="edgeiq-race-card-grid" aria-label="Race intelligence summary cards">
          <article className="edgeiq-race-product-card">
            <span>Race Shape Preview</span>
            <strong>{selectedRaceShapeLabel || displayExpectedTempo || "Tactical"}</strong>
            <em>{displayExpectedTempo !== "—" ? `${displayExpectedTempo} tempo` : "Tempo source loaded"}</em>
          </article>
          <article className="edgeiq-race-product-card">
            <span>Pressure Profile</span>
            <strong>{speedMapPressureRisk || selectedRacePressureDisplay || "Standard"}</strong>
            <em>{chaosChipLabel || "Pressure read from current map"}</em>
          </article>
          <article className="edgeiq-race-product-card">
            <span>Setup Advantage</span>
            <strong>{commandBestValue ? horse(commandBestValue.row) : "No setup edge"}</strong>
            <em>{opportunityChipLabel || "No forced market call"}</em>
          </article>
          <article className="edgeiq-race-product-card">
            <span>Evidence Confidence</span>
            <strong>{bettingConfidence}</strong>
            <em>{marketStatus ? `Market ${marketStatus}` : "Source-aware evidence read"}</em>
          </article>
          <article className="edgeiq-race-product-card feature">
            <span>Race Narrative</span>
            <strong>{raceStory || raceAssessmentNarrative || "Race read loaded"}</strong>
            <em>{customerBriefingNarrative || briefingNarrative || "EDGEiQ explains the race shape before the market context."}</em>
          </article>
        </div>
'''

CSS_APPEND = r'''

/* EDGEiQ Product Race Page Routing V1 */
.edgeiq-race-product-shell {
  position: relative;
  display: grid;
  gap: 18px;
  margin-bottom: 18px;
  border: 1px solid rgba(42,245,220,.24);
  border-radius: 18px;
  padding: 18px;
  background:
    radial-gradient(circle at 8% 0%, rgba(42,245,220,.14), transparent 34rem),
    radial-gradient(circle at 88% 12%, rgba(245,196,81,.12), transparent 28rem),
    linear-gradient(135deg, rgba(3,12,24,.96), rgba(8,21,38,.92));
  box-shadow: 0 20px 60px rgba(0,0,0,.28), inset 0 1px 0 rgba(255,255,255,.04);
  overflow: hidden;
}

.edgeiq-race-product-shell::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(90deg, rgba(42,245,220,.14), transparent 28%, transparent 72%, rgba(245,196,81,.10));
  opacity: .42;
}

.edgeiq-race-product-topbar {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(180px, .8fr) minmax(430px, 1.5fr) minmax(170px, .7fr);
  gap: 16px;
  align-items: center;
}

.edgeiq-race-brand {
  border: 1px solid rgba(42,245,220,.30);
  border-radius: 14px;
  background: rgba(3,10,22,.72);
  min-height: 62px;
  padding: 12px 14px;
  display: grid;
  gap: 2px;
  justify-items: start;
  cursor: pointer;
}

.edgeiq-race-brand-mark {
  color: #ffffff;
  font-size: 22px;
  font-weight: 1000;
  letter-spacing: .08em;
}

.edgeiq-race-brand-subtitle {
  color: #2af5dc;
  font-size: 10px;
  font-weight: 1000;
  letter-spacing: .22em;
  text-transform: uppercase;
}

.edgeiq-race-primary-nav {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 8px;
  padding: 8px;
  border: 1px solid rgba(80,120,180,.24);
  border-radius: 16px;
  background: rgba(2,8,20,.58);
}

.edgeiq-race-nav-button {
  border: 1px solid rgba(80,120,180,.25);
  border-radius: 12px;
  min-height: 46px;
  background: rgba(5,12,22,.72);
  color: #a9b8ca;
  font-size: 11px;
  font-weight: 1000;
  letter-spacing: .16em;
  text-transform: uppercase;
  cursor: pointer;
  transition: border-color .18s ease, background .18s ease, color .18s ease, transform .18s ease;
}

.edgeiq-race-nav-button:hover,
.edgeiq-race-nav-button.is-active {
  border-color: rgba(42,245,220,.62);
  background: linear-gradient(180deg, rgba(15,47,58,.92), rgba(6,22,34,.88));
  color: #eaffff;
  box-shadow: 0 0 0 1px rgba(42,245,220,.16), 0 12px 28px rgba(42,245,220,.10);
}

.edgeiq-race-account-panel {
  border: 1px solid rgba(245,196,81,.26);
  border-radius: 14px;
  background: rgba(5,12,22,.70);
  min-height: 62px;
  padding: 10px 12px;
  display: grid;
  gap: 3px;
  justify-items: end;
  text-align: right;
}

.edgeiq-race-account-panel span {
  color: #94a3b8;
  font-size: 10px;
  font-weight: 950;
  letter-spacing: .18em;
  text-transform: uppercase;
}

.edgeiq-race-account-panel strong {
  color: #fde68a;
  font-size: 12px;
  font-weight: 1000;
  text-transform: uppercase;
}

.edgeiq-race-account-panel button {
  border: 1px solid rgba(125,211,252,.26);
  border-radius: 999px;
  background: rgba(15,23,42,.78);
  color: #dbeafe;
  font-size: 10px;
  font-weight: 950;
  text-transform: uppercase;
  padding: 5px 9px;
  cursor: pointer;
}

.edgeiq-race-identity-card {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, .75fr);
  gap: 18px;
  align-items: end;
  border: 1px solid rgba(80,120,180,.22);
  border-radius: 16px;
  padding: 18px;
  background: linear-gradient(135deg, rgba(7,18,34,.86), rgba(4,11,21,.78));
}

.edgeiq-race-kicker {
  display: block;
  color: #2af5dc;
  font-size: 10.5px;
  font-weight: 1000;
  letter-spacing: .24em;
  text-transform: uppercase;
  margin-bottom: 7px;
}

.edgeiq-race-identity-main h1,
.edgeiq-race-tab-hero h2 {
  margin: 0;
  color: #ffffff;
  letter-spacing: .02em;
  line-height: 1;
}

.edgeiq-race-identity-main h1 { font-size: 42px; }
.edgeiq-race-tab-hero h2 { font-size: 27px; }

.edgeiq-race-identity-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
  margin-top: 12px;
}

.edgeiq-race-identity-meta span {
  border: 1px solid rgba(80,120,180,.28);
  border-radius: 999px;
  background: rgba(5,12,22,.64);
  color: #dbeafe;
  padding: 7px 10px;
  font-size: 11px;
  font-weight: 1000;
  text-transform: uppercase;
  letter-spacing: .09em;
}

.edgeiq-race-identity-source {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.edgeiq-race-tab-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  align-items: end;
  margin-bottom: 16px;
}

.edgeiq-race-tab-hero p {
  max-width: 920px;
  margin: 10px 0 0;
  color: #c6d3e2;
  font-size: 14px;
  line-height: 1.5;
}

.edgeiq-race-tab-scoreline {
  min-width: 180px;
  border: 1px solid rgba(245,196,81,.24);
  border-radius: 14px;
  background: rgba(245,196,81,.08);
  padding: 12px;
  display: grid;
  gap: 4px;
  text-align: right;
}

.edgeiq-race-tab-scoreline span {
  color: #94a3b8;
  font-size: 10px;
  font-weight: 950;
  text-transform: uppercase;
  letter-spacing: .12em;
}

.edgeiq-race-tab-scoreline strong {
  color: #fde68a;
  font-size: 18px;
  font-weight: 1000;
}

.edgeiq-race-card-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.edgeiq-race-product-card {
  border: 1px solid rgba(80,120,180,.26);
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(8,20,34,.90), rgba(3,10,22,.82));
  padding: 14px;
  display: grid;
  gap: 8px;
  min-height: 132px;
}

.edgeiq-race-product-card.feature {
  grid-column: span 4;
  min-height: 116px;
  border-color: rgba(42,245,220,.28);
  background:
    radial-gradient(circle at 0% 0%, rgba(42,245,220,.12), transparent 22rem),
    linear-gradient(180deg, rgba(8,20,34,.92), rgba(3,10,22,.84));
}

.edgeiq-race-product-card span {
  color: #94a3b8;
  font-size: 10px;
  font-weight: 1000;
  letter-spacing: .13em;
  text-transform: uppercase;
}

.edgeiq-race-product-card strong {
  color: #ffffff;
  font-size: 18px;
  font-weight: 1000;
  line-height: 1.2;
}

.edgeiq-race-product-card em {
  color: #a9b8ca;
  font-size: 12px;
  line-height: 1.35;
  font-style: normal;
}

.edgeiq-product-race .edgeiq-field-workspace,
.edgeiq-product-race .edgeiq-map-workspace,
.edgeiq-product-race .edgeiq-insights-workspace,
.edgeiq-product-race .edgeiq-market-workspace,
.edgeiq-product-race .edgeiq-results-workspace,
.edgeiq-product-race .edgeiq-command-workspace {
  border-radius: 16px !important;
}

@media (max-width: 1100px) {
  .edgeiq-race-product-topbar,
  .edgeiq-race-identity-card,
  .edgeiq-race-tab-hero {
    grid-template-columns: 1fr;
  }
  .edgeiq-race-account-panel,
  .edgeiq-race-identity-source {
    justify-items: start;
    justify-content: flex-start;
    text-align: left;
  }
  .edgeiq-race-card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .edgeiq-race-product-card.feature {
    grid-column: span 2;
  }
}

@media (max-width: 720px) {
  .edgeiq-race-primary-nav {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .edgeiq-race-card-grid {
    grid-template-columns: 1fr;
  }
  .edgeiq-race-product-card.feature {
    grid-column: span 1;
  }
}
'''


def copy_checkpoint(source: Path, target: Path) -> bool:
    if source.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return True
    return False


def replace_between(text: str, start_marker: str, end_marker: str, replacement: str, label: str):
    start = text.find(start_marker)
    if start == -1:
        return text, False, f"{label}_START_NOT_FOUND"
    end = text.find(end_marker, start)
    if end == -1:
        return text, False, f"{label}_END_NOT_FOUND"
    return text[:start] + replacement + text[end:], True, f"{label}_REPLACED"


def replace_first_after(text: str, anchor: str, target: str, replacement: str, label: str):
    anchor_pos = text.find(anchor)
    if anchor_pos == -1:
        return text, False, f"{label}_ANCHOR_NOT_FOUND"
    target_pos = text.find(target, anchor_pos)
    if target_pos == -1:
        return text, False, f"{label}_TARGET_NOT_FOUND"
    return text[:target_pos] + replacement + text[target_pos + len(target):], True, f"{label}_REPLACED"


def main():
    checkpoints = {
        "tsx": copy_checkpoint(TSX, TSX_CHECKPOINT),
        "index_css": copy_checkpoint(INDEX_CSS, INDEX_CHECKPOINT),
        "product_css": copy_checkpoint(PRODUCT_CSS, PRODUCT_CSS_CHECKPOINT),
    }

    text = TSX.read_text(encoding="utf-8")
    original_text = text

    old_nav_start = '      <section className="edgeiq-workspace-tabs edgeiq-primary-product-tabs"'
    old_nav_end = '      {intelMode === "COMMAND" ? ('
    text, nav_done, nav_status = replace_between(text, old_nav_start, old_nav_end, PRODUCT_NAV_BLOCK, "PRODUCT_RACE_NAV")

    old_race_title = '''        <div style={titleStyle}>
          <span>Intelligence Brief</span>
          <em>Structured race briefing built from pace, profile and connection evidence</em>
        </div>
'''
    text, race_tab_done, race_tab_status = replace_first_after(
        text,
        '<section className="edgeiq-command-workspace" style={evidenceSectionStyle}>',
        old_race_title,
        RACE_TAB_HEADER,
        "RACE_TAB_PRODUCT_HEADER",
    )

    map_anchor = '      {intelMode === "MAP" ? (() => {'
    text, map_class_done, map_class_status = replace_first_after(
        text,
        map_anchor,
        '<section style={workspaceSectionStyle}>',
        '<section className="edgeiq-map-workspace" style={workspaceSectionStyle}>',
        "MAP_WORKSPACE_CLASS",
    )

    runner_anchor = '      {intelMode === "RUNNERS" ? ('
    text, field_class_done, field_class_status = replace_first_after(
        text,
        runner_anchor,
        '<section style={evidenceSectionStyle}>',
        '<section className="edgeiq-field-workspace" style={evidenceSectionStyle}>',
        "FIELD_WORKSPACE_CLASS",
    )

    TSX.write_text(text, encoding="utf-8")

    css = PRODUCT_CSS.read_text(encoding="utf-8") if PRODUCT_CSS.exists() else ""
    css_marker = "/* EDGEiQ Product Race Page Routing V1 */"
    css_changed = False
    if css_marker not in css:
        PRODUCT_CSS.write_text(css.rstrip() + CSS_APPEND + "\n", encoding="utf-8")
        css_changed = True

    after = TSX.read_text(encoding="utf-8")
    legacy_terms = ["EDGEIQ RACING", "OVERVIEW", "TRACKING", "RACE PAGE", "edgeiq-command-header", "edgeiq-primary-product-tabs"]
    legacy_hits = {term: (term.lower() in after.lower()) for term in legacy_terms}
    product_nav_ok = all(term in after for term in ["edgeiq-race-product-topbar", "edgeiq-race-primary-nav", "setIntelMode(tab.mode)"])
    race_opens_ok = 'updateProductView("RACE")' in after and 'setIntelMode("COMMAND")' in after
    race_tab_ok = all(term in after for term in ["Race Shape Preview", "Pressure Profile", "Setup Advantage", "Evidence Confidence", "Race Narrative", "edgeiq-race-card-grid"])
    chrome_removed = not any(legacy_hits.values())
    status = "PRODUCT_RACE_PAGE_ROUTING_V1_APPLIED" if product_nav_ok and race_opens_ok and race_tab_ok and chrome_removed else "PRODUCT_RACE_PAGE_ROUTING_V1_REVIEW_REQUIRED"

    rows = [
        {"metric": "status", "value": status},
        {"metric": "tsx_checkpoint", "value": str(TSX_CHECKPOINT.relative_to(ROOT))},
        {"metric": "index_checkpoint", "value": str(INDEX_CHECKPOINT.relative_to(ROOT))},
        {"metric": "product_css_checkpoint", "value": str(PRODUCT_CSS_CHECKPOINT.relative_to(ROOT))},
        {"metric": "tsx_checkpoint_created", "value": "YES" if checkpoints["tsx"] else "NO"},
        {"metric": "index_checkpoint_created", "value": "YES" if checkpoints["index_css"] else "NO"},
        {"metric": "product_css_checkpoint_created", "value": "YES" if checkpoints["product_css"] else "NO"},
        {"metric": "race_nav_replaced", "value": "YES" if nav_done else "NO"},
        {"metric": "race_nav_status", "value": nav_status},
        {"metric": "race_tab_rebuilt", "value": "YES" if race_tab_done and race_tab_ok else "NO"},
        {"metric": "race_tab_status", "value": race_tab_status},
        {"metric": "map_workspace_product_class", "value": "YES" if map_class_done else "NO"},
        {"metric": "map_workspace_status", "value": map_class_status},
        {"metric": "field_workspace_product_class", "value": "YES" if field_class_done else "NO"},
        {"metric": "field_workspace_status", "value": field_class_status},
        {"metric": "product_css_changed", "value": "YES" if css_changed else "NO"},
        {"metric": "legacy_chrome_removed", "value": "YES" if chrome_removed else "NO"},
        {"metric": "old_secondary_race_page_tab_removed", "value": "YES" if not legacy_hits["RACE PAGE"] else "NO"},
        {"metric": "old_tabs_removed", "value": "YES" if not legacy_hits["OVERVIEW"] and not legacy_hits["TRACKING"] else "NO"},
        {"metric": "legacy_ticker_removed", "value": "YES" if not legacy_hits["EDGEIQ RACING"] else "NO"},
        {"metric": "top_product_nav_controls_tabs", "value": "YES" if product_nav_ok else "NO"},
        {"metric": "race_opens_directly_to_race_page", "value": "YES" if race_opens_ok else "NO"},
        {"metric": "new_tabs_retained", "value": "YES" if all(f'label: "{label}"' in after for label in ["RACE", "FIELD", "MAP", "INSIGHTS", "MARKET", "RESULTS"]) else "NO"},
        {"metric": "ui_only", "value": "YES"},
        {"metric": "backend_data_changed", "value": "NO"},
        {"metric": "pricing_changed", "value": "NO"},
        {"metric": "probability_changed", "value": "NO"},
        {"metric": "v6_1_changed", "value": "NO"},
        {"metric": "v7_2g2_changed", "value": "NO"},
        {"metric": "csv_schemas_changed", "value": "NO"},
        {"metric": "completed_at", "value": datetime.now(timezone.utc).isoformat()},
    ]

    with SUMMARY.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(rows)

    with REPORT.open("w", encoding="utf-8") as f:
        f.write("EDGEiQ Product Race Page Routing + Style Rebuild V1\n")
        f.write(f"Status: {status}\n\n")
        f.write("Checkpoints created:\n")
        f.write(f"- {TSX_CHECKPOINT.relative_to(ROOT)}\n")
        f.write(f"- {INDEX_CHECKPOINT.relative_to(ROOT)}\n")
        f.write(f"- {PRODUCT_CSS_CHECKPOINT.relative_to(ROOT)}\n\n")
        f.write("Changes:\n")
        f.write(f"- Product race nav replaced: {'YES' if nav_done else 'NO'} ({nav_status})\n")
        f.write(f"- RACE tab rebuilt with product cards: {'YES' if race_tab_done and race_tab_ok else 'NO'} ({race_tab_status})\n")
        f.write(f"- MAP/FIELD product classes added: MAP {'YES' if map_class_done else 'NO'}, FIELD {'YES' if field_class_done else 'NO'}\n")
        f.write(f"- Product shell CSS appended: {'YES' if css_changed else 'NO'}\n\n")
        f.write("Validation:\n")
        for term, hit in legacy_hits.items():
            f.write(f"- Legacy marker {term}: {'FOUND' if hit else 'ABSENT'}\n")
        f.write(f"- Top product nav controls tabs: {'YES' if product_nav_ok else 'NO'}\n")
        f.write(f"- Race opens to RACE/COMMAND: {'YES' if race_opens_ok else 'NO'}\n")
        f.write(f"- RACE cards present: {'YES' if race_tab_ok else 'NO'}\n\n")
        f.write("Safety confirmations:\n")
        f.write("- UI only: YES\n")
        f.write("- Backend data changed: NO\n")
        f.write("- Pricing changed: NO\n")
        f.write("- Probability changed: NO\n")
        f.write("- V6.1 changed: NO\n")
        f.write("- V7.2G2 changed: NO\n")
        f.write("- CSV schemas changed: NO\n")

    print(status)


if __name__ == "__main__":
    main()
