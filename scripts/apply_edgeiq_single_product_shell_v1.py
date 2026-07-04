from pathlib import Path
from datetime import datetime, timezone
import csv
import re
import shutil

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
TSX = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
INDEX_CSS = ROOT / "src" / "index.css"
PRODUCT_CSS = ROOT / "src" / "styles" / "edgeiqProductTerminalV1.css"
TSX_CHECKPOINT = ROOT / "src" / "components" / "RaceIntelligenceScreen_CHECKPOINT_PRE_SINGLE_PRODUCT_SHELL_V1_20260630.tsx"
INDEX_CHECKPOINT = ROOT / "src" / "index_CHECKPOINT_PRE_SINGLE_PRODUCT_SHELL_V1_20260630.css"
CSS_CHECKPOINT = ROOT / "src" / "styles" / "edgeiqProductTerminalV1_CHECKPOINT_PRE_SINGLE_PRODUCT_SHELL_V1_20260630.css"
SUMMARY = ROOT / "public" / "data" / "edgeiq_single_product_shell_v1_summary.csv"
REPORT = ROOT / "public" / "data" / "edgeiq_single_product_shell_v1_report.txt"
AUDIT_SUMMARY = ROOT / "public" / "data" / "edgeiq_duplicate_shell_blocks_v1_summary.csv"

MARKET_BLOCK = '''      {intelMode === "ADVANCED" ? (() => {
        const marketRows = [...activeRaceRows]
          .filter((item) => !isScratched(item))
          .sort((a, b) => (a.modelRank ?? 999) - (b.modelRank ?? 999));
        const marketConnected = livePriceRowCount > 0;
        const marketTableRows = marketRows.slice(0, 12);
        return (
          <section className="edgeiq-market-workspace edgeiq-product-section" style={workspaceSectionStyle}>
            <div className="edgeiq-product-section-title">
              <span>MARKET</span>
              <em>Market/source state, fair-price context and timestamp-aware availability</em>
            </div>

            <div className="edgeiq-product-grid edgeiq-market-status-grid">
              <article className="edgeiq-product-card">
                <span>Market Source State</span>
                <strong>{marketConnected ? "Connected" : "Unavailable"}</strong>
                <em>{marketConnected ? `${livePriceRowCount}/${activeRaceRows.length} runners with market reference` : "No timestamp-safe live market source is available for this race."}</em>
              </article>
              <article className="edgeiq-product-card">
                <span>Fair Price Context</span>
                <strong>{displayEdgeiqPriceCount}/{displayEvidenceFieldSize}</strong>
                <em>EDGEiQ fair-price context is shown without changing pricing logic.</em>
              </article>
              <article className="edgeiq-product-card">
                <span>Market Alignment</span>
                <strong>{marketStatus}</strong>
                <em>{marketConnected ? "Market reference available for comparison." : "Alignment is intentionally muted while the market source is unavailable."}</em>
              </article>
            </div>

            {!marketConnected ? (
              <div className="edgeiq-product-empty">Market source unavailable. Live/fair price context will appear when timestamp-safe market data is loaded.</div>
            ) : null}

            <div className="edgeiq-product-section-title compact">
              <span>Price Table</span>
              <em>Runner-level price context, not a recommendation layer</em>
            </div>
            <div className="edgeiq-product-table" role="table" aria-label="Market price context">
              <div role="row" className="edgeiq-product-table-header">
                <span>Rank</span><span>Runner</span><span>EDGEiQ Price</span><span>Market</span><span>Context</span>
              </div>
              {marketTableRows.map((item) => (
                <div role="row" key={`market-product-row-${runnerRowKey(item.row)}`} className="edgeiq-product-table-row">
                  <span>{item.modelRank ? `#${item.modelRank}` : "—"}</span>
                  <strong>{horse(item.row)}</strong>
                  <span>{money(limitedAdjustedPrice(item) ?? fairPrice(item.row, item.bet))}</span>
                  <span>{money(livePrice(item.row, item.bet))}</span>
                  <span>{decision(item.row, item.bet)}</span>
                </div>
              ))}
            </div>
          </section>
        );
      })() : null}
'''

RESULTS_BLOCK = '''      {intelMode === "RESULTS" ? (
        <section className="edgeiq-results-workspace edgeiq-product-section" style={workspaceSectionStyle}>
          <div className="edgeiq-product-section-title">
            <span>RESULTS</span>
            <em>Official result and post-race review</em>
          </div>
          <div className="edgeiq-product-grid edgeiq-results-card-grid">
            <article className="edgeiq-product-card">
              <span>Official Result</span>
              <strong>Pending</strong>
              <em>Results and post-race review will appear once official results are available.</em>
            </article>
            <article className="edgeiq-product-card">
              <span>Post-Race Review</span>
              <strong>Not available yet</strong>
              <em>EDGEiQ keeps post-race review separate from pre-race intelligence.</em>
            </article>
          </div>
        </section>
      ) : null}
'''

CSS_APPEND = r'''

/* EDGEiQ Single Product Shell V1 */
.edgeiq-product-app {
  min-height: 100vh;
}

.edgeiq-product-topbar,
.edgeiq-product-nav,
.edgeiq-product-race-hero,
.edgeiq-product-section,
.edgeiq-product-grid,
.edgeiq-product-table {
  box-sizing: border-box;
}

.edgeiq-product-user-chip {
  justify-items: end;
}

.edgeiq-product-user-chip em {
  color: #94a3b8;
  font-size: 10px;
  font-style: normal;
  font-weight: 900;
  letter-spacing: .10em;
  text-transform: uppercase;
}

.edgeiq-product-section-title {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: end;
  padding-bottom: 12px;
  margin-bottom: 14px;
  border-bottom: 1px solid rgba(80,120,180,.24);
}

.edgeiq-product-section-title.compact {
  margin-top: 6px;
}

.edgeiq-product-section-title span {
  color: #ffffff;
  font-size: 14px;
  font-weight: 1000;
  letter-spacing: .16em;
  text-transform: uppercase;
}

.edgeiq-product-section-title em {
  color: #94a3b8;
  font-size: 11px;
  font-style: normal;
  line-height: 1.35;
  text-align: right;
}

.edgeiq-product-card {
  border: 1px solid rgba(80,120,180,.27);
  border-radius: 15px;
  background: linear-gradient(180deg, rgba(8,20,34,.88), rgba(3,10,22,.78));
  padding: 14px;
  display: grid;
  gap: 8px;
}

.edgeiq-product-card span {
  color: #94a3b8;
  font-size: 10px;
  font-weight: 1000;
  letter-spacing: .13em;
  text-transform: uppercase;
}

.edgeiq-product-card strong {
  color: #ffffff;
  font-size: 17px;
  font-weight: 1000;
  line-height: 1.15;
}

.edgeiq-product-card em {
  color: #a9b8ca;
  font-size: 11.5px;
  font-style: normal;
  line-height: 1.35;
}

.edgeiq-product-empty {
  border: 1px solid rgba(245,158,11,.30);
  border-radius: 14px;
  background: rgba(245,158,11,.08);
  color: #fed7aa;
  padding: 14px;
  font-size: 13px;
  font-weight: 850;
}

.edgeiq-market-status-grid,
.edgeiq-results-card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.edgeiq-results-card-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.edgeiq-product-table {
  display: grid;
  gap: 6px;
  overflow-x: auto;
}

.edgeiq-product-table-header,
.edgeiq-product-table-row {
  display: grid;
  grid-template-columns: 70px minmax(220px, 1fr) 130px 120px minmax(160px, .8fr);
  gap: 10px;
  align-items: center;
  min-width: 780px;
}

.edgeiq-product-table-header {
  padding: 9px 10px;
  color: #94a3b8;
  font-size: 10px;
  font-weight: 1000;
  letter-spacing: .10em;
  text-transform: uppercase;
  border-bottom: 1px solid rgba(80,120,180,.28);
}

.edgeiq-product-table-row {
  border: 1px solid rgba(80,120,180,.20);
  border-radius: 12px;
  background: rgba(5,12,22,.70);
  padding: 10px;
  color: #cbd5e1;
  font-size: 12px;
  font-weight: 850;
}

.edgeiq-product-table-row strong {
  color: #ffffff;
  font-size: 12.5px;
  font-weight: 1000;
}

@media (max-width: 980px) {
  .edgeiq-market-status-grid,
  .edgeiq-results-card-grid {
    grid-template-columns: 1fr;
  }
  .edgeiq-product-section-title {
    display: grid;
    align-items: start;
  }
  .edgeiq-product-section-title em {
    text-align: left;
  }
}
'''


def read_summary_value(path: Path, key: str) -> str:
    if not path.exists():
        return ""
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("metric") == key:
                return row.get("value", "")
    return ""


def preserve_checkpoint(source: Path, target: Path) -> bool:
    if target.exists():
        return True
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target.exists()


def replace_between(text: str, start_marker: str, end_marker: str, replacement: str):
    start = text.find(start_marker)
    if start == -1:
        return text, False
    end = text.find(end_marker, start)
    if end == -1:
        return text, False
    return text[:start] + replacement + text[end:], True


def replace_first_after(text: str, anchor: str, target: str, replacement: str):
    pos = text.find(anchor)
    if pos == -1:
        return text, False
    target_pos = text.find(target, pos)
    if target_pos == -1:
        return text, False
    return text[:target_pos] + replacement + text[target_pos + len(target):], True


def main():
    before_visible_risks = read_summary_value(AUDIT_SUMMARY, "visible_risk_count")
    before_old_meeting = read_summary_value(AUDIT_SUMMARY, "old_meeting_selector_visible")
    before_old_tabs = read_summary_value(AUDIT_SUMMARY, "old_tab_strip_visible")

    checkpoints = {
        "tsx": preserve_checkpoint(TSX, TSX_CHECKPOINT),
        "index_css": preserve_checkpoint(INDEX_CSS, INDEX_CHECKPOINT),
        "product_css": preserve_checkpoint(PRODUCT_CSS, CSS_CHECKPOINT),
    }

    text = TSX.read_text(encoding="utf-8")
    changes = []

    replacements = [
        ('<div className="edgeiq-product-race edgeiq-product-surface" style={pageStyle}>', '<div className="edgeiq-product-app edgeiq-product-race edgeiq-product-surface" style={pageStyle}>', "race_root_product_app"),
        ('<div className="edgeiq-race-product-topbar">', '<div className="edgeiq-race-product-topbar edgeiq-product-topbar">', "topbar_product_class"),
        ('<nav className="edgeiq-race-primary-nav" aria-label="Race navigation">', '<nav className="edgeiq-race-primary-nav edgeiq-product-nav" aria-label="Race navigation">', "nav_product_class"),
        ('<div className="edgeiq-race-hero-premium">', '<div className="edgeiq-race-hero-premium edgeiq-product-race-hero">', "race_hero_product_class"),
        ('<div className="edgeiq-race-system-status-grid" aria-label="Source and system status">', '<div className="edgeiq-race-system-status-grid edgeiq-product-grid" aria-label="Source and system status">', "status_grid_product_class"),
        ('<section className="edgeiq-race-premium-workspace">', '<section className="edgeiq-race-premium-workspace edgeiq-product-section">', "race_workspace_product_class"),
        ('<div className="edgeiq-race-intel-card-grid" aria-label="Race intelligence cards">', '<div className="edgeiq-race-intel-card-grid edgeiq-product-grid" aria-label="Race intelligence cards">', "race_card_grid_product_class"),
        ('<div className="edgeiq-race-bottom-grid">', '<div className="edgeiq-race-bottom-grid edgeiq-product-grid">', "race_bottom_grid_product_class"),
        ('<section className="edgeiq-field-workspace" style={evidenceSectionStyle}>', '<section className="edgeiq-field-workspace edgeiq-product-section" style={evidenceSectionStyle}>', "field_main_product_class"),
        ('<section className="edgeiq-map-workspace" style={workspaceSectionStyle}>', '<section className="edgeiq-map-workspace edgeiq-product-section" style={workspaceSectionStyle}>', "map_product_class"),
        ('<section className="edgeiq-insights-workspace" style={workspaceSectionStyle}>', '<section className="edgeiq-insights-workspace edgeiq-product-section" style={workspaceSectionStyle}>', "insights_product_class"),
    ]
    for old, new, label in replacements:
        if old in text and new not in text:
            text = text.replace(old, new, 1)
            changes.append(label)

    account_old = '''          <div className="edgeiq-race-account-panel">
            <span>EDGEiQ</span>
            <strong>{selectedShellMeeting?.meetingStatus || "LIVE WORKSPACE"}</strong>
            <button type="button" onClick={() => updateProductView("MEETING")}>Meeting</button>
          </div>'''
    account_new = '''          <div className="edgeiq-race-account-panel edgeiq-product-user-chip" aria-label="User account">
            <span>Account</span>
            <strong>trent@edgeiq</strong>
            <em>Race workspace</em>
          </div>'''
    if account_old in text:
        text = text.replace(account_old, account_new, 1)
        changes.append("account_chip_replaced")

    if '<span>{activeRaceRows.length} runners</span>\n                {railDisplay !== "—"' in text:
        text = text.replace('<span>{activeRaceRows.length} runners</span>\n                {railDisplay !== "—"', '<span>{activeRaceRows.length} runners</span>\n                {raceDate(header) !== "—" && <span>{raceDate(header)}</span>}\n                {railDisplay !== "—"', 1)
        changes.append("meeting_date_added")

    race_copy_replacements = [
        ('<strong>{raceSetupRunner ? horse(raceSetupRunner.row) : "None identified"}</strong>', '<strong>{raceSetupRunner ? "Profile edge present" : "None identified"}</strong>'),
        ('raceSetupRunner ? `${horse(raceSetupRunner.row)} has the clearest setup profile from the loaded evidence.` : "No setup advantage currently identified."', 'raceSetupRunner ? "A runner has the clearest setup profile from the loaded evidence." : "No setup advantage currently identified."'),
        ('.join(" Â· ")', '.join(" | ")'),
    ]
    for old, new in race_copy_replacements:
        if old in text:
            text = text.replace(old, new)
            changes.append("race_copy_cleaned")

    if '<span>EDGEiQ Ratings Table</span>' in text:
        text = text.replace('<span>EDGEiQ Ratings Table</span>', '<span>FIELD</span>', 1)
        changes.append("field_title_rebranded")
    if '<em>Performance ratings and market reference</em>' in text:
        text = text.replace('<em>Performance ratings and market reference</em>', '<em>Runner list, profile evidence and current race context</em>', 1)
        changes.append("field_subtitle_rebranded")
    if '<span>MAP WORKSPACE</span>' in text:
        text = text.replace('<span>MAP WORKSPACE</span>', '<span>Speed Map</span>', 1)
        changes.append("map_title_rebranded")

    old_subtabs = '(["DNA", "PROFILE", "FORM", "CONNECTIONS", "EXPLAINABILITY"] as RunnerSubMode[])'
    new_subtabs = '(["PROFILE", "FORM", "DNA", "CONNECTIONS", "EXPLAINABILITY"] as RunnerSubMode[])'
    if old_subtabs in text:
        text = text.replace(old_subtabs, new_subtabs, 1)
        changes.append("field_subtabs_reordered")
    old_mode_label = '''                  {mode}'''
    new_mode_label = '''                  {mode === "EXPLAINABILITY" ? "EVIDENCE" : mode}'''
    if old_mode_label in text:
        text = text.replace(old_mode_label, new_mode_label, 1)
        changes.append("field_evidence_label")

    # Product class for selected runner detail section.
    runner_detail_anchor = '      {selected && intelMode === "RUNNERS" ? (\n        <section\n          style={'
    if runner_detail_anchor in text:
        text = text.replace(runner_detail_anchor, '      {selected && intelMode === "RUNNERS" ? (\n        <section\n          className="edgeiq-field-workspace edgeiq-product-section"\n          style={', 1)
        changes.append("field_detail_product_class")

    # Replace old MARKET details panel with a product MARKET page.
    text, market_replaced = replace_between(text, '      {selected && intelMode === "ADVANCED" ? (', '      {intelMode === "RESULTS" ? (', MARKET_BLOCK)
    if market_replaced:
        changes.append("market_page_rebuilt")

    # Replace RESULTS with product cards.
    text, results_replaced = replace_between(text, '      {intelMode === "RESULTS" ? (', '      <section style={{ ...panelStyle, overflowX: "auto", display: "none" }}>', RESULTS_BLOCK)
    if results_replaced:
        changes.append("results_page_rebuilt")

    TSX.write_text(text, encoding="utf-8")

    css = PRODUCT_CSS.read_text(encoding="utf-8")
    css_before = css
    css = re.sub(r"\n?\.edgeiq-product-race \.edgeiq-command-header \{[\s\S]*?\n\}\n\n\.edgeiq-product-race \.edgeiq-command-header::before \{[\s\S]*?\n\}\n", "\n", css)
    css = re.sub(r"\n?\.edgeiq-workspace-tabs \{[\s\S]*?\n\}\n\n\.edgeiq-workspace-tabs button \{[\s\S]*?\n\}\n", "\n", css)
    css = re.sub(r"\n?@media \(max-width: 980px\) \{\n\s*\.edgeiq-workspace-tabs \{[\s\S]*?\n\s*\}\n\s*\.edgeiq-race-status-pill \{[\s\S]*?\n\s*\}\n\}\n", "\n", css)
    if "/* EDGEiQ Single Product Shell V1 */" not in css:
        css = css.rstrip() + CSS_APPEND + "\n"
    if css != css_before:
        PRODUCT_CSS.write_text(css, encoding="utf-8")
        changes.append("product_css_cleaned")

    after = TSX.read_text(encoding="utf-8")
    race_page_start = after.find('<div className="edgeiq-product-app')
    race_page_end = after.find('{ratingHover ?', race_page_start if race_page_start != -1 else 0)
    race_slice = after[race_page_start:race_page_end if race_page_end != -1 else len(after)] if race_page_start != -1 else ""

    checks = {
        "legacy_ticker_removed": "NO" if re.search(r"EDGEIQ\s+RACING", race_slice, re.I) else "YES",
        "legacy_meeting_selector_removed": "NO" if re.search(r"updateProductView\(\"MEETING\"\)|>Meeting<", race_slice, re.I) else "YES",
        "legacy_race_selector_removed": "NO" if re.search(r"shell-race-|selectedShellMeetingRaces|>Open Race<", race_slice, re.I) else "YES",
        "old_tabs_removed": "NO" if re.search(r"OVERVIEW[\s\S]{0,160}INTELLIGENCE[\s\S]{0,160}MARKET[\s\S]{0,160}TRACKING[\s\S]{0,160}RESULTS", race_slice, re.I) else "YES",
        "only_product_nav_remains": "YES" if all(marker in race_slice for marker in ["edgeiq-product-nav", "setIntelMode(tab.mode)"]) and "edgeiq-workspace-tabs" not in race_slice else "NO",
        "race_tab_rebuilt": "YES" if "edgeiq-race-premium-workspace" in race_slice and "Race Shape Preview" in race_slice and "What To Watch" in race_slice else "NO",
        "field_tab_product_shell_applied": "YES" if "edgeiq-field-workspace edgeiq-product-section" in race_slice and "EVIDENCE" in race_slice else "NO",
        "map_tab_product_shell_applied": "YES" if "edgeiq-map-workspace edgeiq-product-section" in race_slice and "Speed Map" in race_slice else "NO",
        "insights_tab_product_shell_applied": "YES" if "edgeiq-insights-workspace edgeiq-product-section" in race_slice and "<span>INSIGHTS</span>" in race_slice else "NO",
        "market_tab_product_shell_applied": "YES" if "edgeiq-market-workspace edgeiq-product-section" in race_slice and "Market Source State" in race_slice else "NO",
        "results_tab_product_shell_applied": "YES" if "edgeiq-results-workspace edgeiq-product-section" in race_slice and "Official Result" in race_slice else "NO",
    }
    success = all(value == "YES" for value in checks.values())

    rows = [
        {"metric": "status", "value": "SINGLE_PRODUCT_SHELL_V1_APPLIED" if success else "SINGLE_PRODUCT_SHELL_V1_REVIEW_REQUIRED"},
        {"metric": "duplicate_visible_risks_before", "value": before_visible_risks},
        {"metric": "old_meeting_selector_before", "value": before_old_meeting},
        {"metric": "old_tab_strip_before", "value": before_old_tabs},
        {"metric": "tsx_checkpoint", "value": str(TSX_CHECKPOINT.relative_to(ROOT))},
        {"metric": "index_checkpoint", "value": str(INDEX_CHECKPOINT.relative_to(ROOT))},
        {"metric": "css_checkpoint", "value": str(CSS_CHECKPOINT.relative_to(ROOT))},
        {"metric": "checkpoints_created", "value": "YES" if all(checkpoints.values()) else "NO"},
        {"metric": "changes", "value": "|".join(changes)},
    ]
    rows.extend({"metric": key, "value": value} for key, value in checks.items())
    rows.extend([
        {"metric": "ui_changed", "value": "YES"},
        {"metric": "backend_data_changed", "value": "NO"},
        {"metric": "pricing_changed", "value": "NO"},
        {"metric": "probability_changed", "value": "NO"},
        {"metric": "v6_1_changed", "value": "NO"},
        {"metric": "v7_2g2_changed", "value": "NO"},
        {"metric": "csv_schemas_changed", "value": "NO"},
        {"metric": "completed_at", "value": datetime.now(timezone.utc).isoformat()},
    ])
    with SUMMARY.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(rows)

    with REPORT.open("w", encoding="utf-8") as f:
        f.write("EDGEiQ Single Product Shell + Six Tab Rebuild V1\n")
        for row in rows:
            f.write(f"{row['metric']}: {row['value']}\n")
        f.write("\nSafety: UI-only render/style changes. Data loading, pricing, probabilities, V6.1, V7.2G2 and CSV schemas were not changed.\n")

    print(rows[0]["value"])


if __name__ == "__main__":
    main()
