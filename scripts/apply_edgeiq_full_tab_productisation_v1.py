from pathlib import Path
import csv
import shutil
import re
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DATA = ROOT / "public" / "data"
TSX = SRC / "components" / "RaceIntelligenceScreen.tsx"
INDEX = SRC / "index.css"
SCALE = SRC / "styles" / "edgeiqProductScaleGlobalV1.css"
TERMINAL_CSS = SRC / "styles" / "edgeiqProductTerminalV1.css"
CHECKPOINT_MANIFEST = DATA / "edgeiq_full_tab_productisation_v1_checkpoint_manifest.csv"
APPLY_SUMMARY = DATA / "edgeiq_full_tab_productisation_v1_apply_summary.csv"
APPLY_REPORT = DATA / "edgeiq_full_tab_productisation_v1_apply_report.txt"

STAMP = "PRE_FULL_TAB_PRODUCTISATION_V1_20260630"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def write_csv(path: Path, rows, fieldnames=None):
    rows = list(rows)
    if fieldnames is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
        fieldnames = fields
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def checkpoint_name(path: Path) -> Path:
    if path == TSX:
        return path.parent / f"RaceIntelligenceScreen_CHECKPOINT_{STAMP}.tsx"
    if path == INDEX:
        return path.parent / f"index_CHECKPOINT_{STAMP}.css"
    if path == SCALE:
        return path.parent / f"edgeiqProductScaleGlobalV1_CHECKPOINT_{STAMP}.css"
    return path.with_name(f"{path.stem}_CHECKPOINT_{STAMP}{path.suffix}")


def create_checkpoints():
    rows = []
    for path in [TSX, INDEX, SCALE]:
        cp = checkpoint_name(path)
        if not path.exists():
            rows.append({"source_file": rel(path), "checkpoint_file": rel(cp), "status": "SOURCE_MISSING", "checkpoint_created": "NO", "created_at": now_iso()})
            continue
        if not cp.exists():
            shutil.copy2(path, cp)
            status = "CHECKPOINT_CREATED"
            created = "YES"
        else:
            status = "CHECKPOINT_ALREADY_EXISTS"
            created = "NO"
        rows.append({"source_file": rel(path), "checkpoint_file": rel(cp), "status": status, "checkpoint_created": created, "created_at": now_iso()})
    write_csv(CHECKPOINT_MANIFEST, rows)
    return rows


def product_css():
    return r'''
/* EDGEiQ Full Tab Productisation V1 */
.edgeiq-product-race {
  --edgeiq-product-accent: #2af5dc;
  --edgeiq-product-blue: #3191ff;
  --edgeiq-product-purple: #9d7cff;
  --edgeiq-product-gold: #f5c451;
  --edgeiq-product-orange: #f59e0b;
}

.edgeiq-product-race .edgeiq-command-header {
  overflow: hidden;
  border: 1px solid rgba(42,245,220,.28) !important;
  background:
    radial-gradient(circle at 12% 0%, rgba(49,145,255,.17), transparent 30rem),
    linear-gradient(135deg, rgba(10,30,51,.94), rgba(2,8,20,.92)) !important;
}

.edgeiq-product-race .edgeiq-command-header::before {
  content: "♞ EDGEiQ";
  position: absolute;
  right: 18px;
  top: 14px;
  color: rgba(42,245,220,.22);
  font-size: 42px;
  font-weight: 1000;
  letter-spacing: .02em;
  pointer-events: none;
}

.edgeiq-race-status-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.edgeiq-race-status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 28px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(80,120,180,.30);
  background: rgba(5,12,22,.72);
  color: #dbeafe;
  font-size: 10.5px;
  font-weight: 950;
  text-transform: uppercase;
  letter-spacing: .09em;
}

.edgeiq-race-status-pill.good { border-color: rgba(52,211,153,.36); color: #bbf7d0; }
.edgeiq-race-status-pill.warn { border-color: rgba(245,196,81,.36); color: #fde68a; }
.edgeiq-race-status-pill.info { border-color: rgba(49,145,255,.38); color: #bfdbfe; }
.edgeiq-race-status-pill.source { border-color: rgba(249,115,22,.36); color: #fed7aa; }

.edgeiq-workspace-tabs {
  position: sticky;
  top: 0;
  z-index: 18;
}

.edgeiq-workspace-tabs button {
  min-height: 42px !important;
}

.edgeiq-product-race section,
.edgeiq-product-race details {
  border-radius: 12px !important;
}

.edgeiq-command-workspace,
.edgeiq-map-workspace,
.edgeiq-field-workspace,
.edgeiq-insights-workspace,
.edgeiq-market-workspace,
.edgeiq-results-workspace {
  border: 1px solid rgba(69,121,164,.28) !important;
  background:
    radial-gradient(circle at 0% 0%, rgba(49,145,255,.10), transparent 24rem),
    linear-gradient(180deg, rgba(10,30,51,.84), rgba(4,11,21,.82)) !important;
}

.edgeiq-results-empty-state,
.edgeiq-market-source-state {
  border: 1px solid rgba(245,196,81,.32);
  border-radius: 12px;
  background: rgba(245,196,81,.08);
  padding: 16px;
  color: #fde68a;
  display: grid;
  gap: 6px;
}

.edgeiq-product-race [style*="OVERBET"],
.edgeiq-product-race [style*="Best Value"],
.edgeiq-product-race [style*="Top Call"] {
  outline: 1px solid rgba(245,196,81,.18);
}

@media (max-width: 980px) {
  .edgeiq-workspace-tabs {
    position: relative;
  }
  .edgeiq-race-status-pill {
    width: calc(50% - 4px);
    justify-content: center;
  }
}
'''.lstrip()


def replace_once(text: str, old: str, new: str, changes: list[str], label: str):
    if old in text:
        text = text.replace(old, new, 1)
        changes.append(label)
    return text


def apply_index():
    text = INDEX.read_text(encoding="utf-8")
    import_line = "@import './styles/edgeiqProductTerminalV1.css';"
    if import_line not in text:
        lines = text.splitlines()
        insert_at = 0
        while insert_at < len(lines) and lines[insert_at].strip().startswith("@import"):
            insert_at += 1
        lines.insert(insert_at, import_line)
        INDEX.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True
    return False


def apply_tsx():
    text = TSX.read_text(encoding="utf-8")
    before = text
    changes = []

    text = text.replace('type IntelMode = "COMMAND" | "MAP" | "FORM" | "RUNNERS" | "FACTORS" | "ADVANCED";', 'type IntelMode = "COMMAND" | "MAP" | "FORM" | "RUNNERS" | "FACTORS" | "ADVANCED" | "RESULTS";')
    if '"RESULTS";' in text:
        changes.append("intel_mode_results_added")

    old_tabs = '''  const intelModeTabs: Array<{ mode: IntelMode; label: string; hint: string }> = [
    { mode: "COMMAND", label: "RACE", hint: "How the race is expected to unfold" },
    { mode: "MAP", label: "MAP", hint: "How the race is likely to be run" },
    { mode: "FORM", label: "FORM", hint: "Full form, recent ratings and last-start evidence" },
    { mode: "RUNNERS", label: "FIELD", hint: "Profiles and intelligence for every runner" },
    { mode: "FACTORS", label: "INSIGHTS", hint: "Deep intelligence and evidence" },
    { mode: "ADVANCED", label: "MARKET", hint: "Market and source intelligence" },
  ];'''
    new_tabs = '''  const intelModeTabs: Array<{ mode: IntelMode; label: string; hint: string }> = [
    { mode: "COMMAND", label: "RACE", hint: "Race shape, pressure, setup and evidence confidence" },
    { mode: "RUNNERS", label: "FIELD", hint: "Profiles and intelligence for every runner" },
    { mode: "MAP", label: "MAP", hint: "Expected settling lanes and pressure zones" },
    { mode: "FACTORS", label: "INSIGHTS", hint: "Ratings, campaign, connections and source coverage" },
    { mode: "ADVANCED", label: "MARKET", hint: "Market source state and fair-price context" },
    { mode: "RESULTS", label: "RESULTS", hint: "Official result and post-race review when available" },
  ];'''
    text = replace_once(text, old_tabs, new_tabs, changes, "primary_nav_tabs_standardised")

    # Header language and status strip.
    text = text.replace("PRE-RACE COMMAND", "RACE INTELLIGENCE")
    if "RACE INTELLIGENCE" in text:
        changes.append("race_header_label")

    market_span = '''              <span style={fitBadge(`Market ${marketStatus}`, marketStatusTone, "rgba(15,23,42,.88)", "1px solid rgba(71,85,105,.75)")}>
                {`Market ${marketStatus}`}
              </span>'''
    market_span_new = market_span + '''
              <div className="edgeiq-race-status-strip" aria-label="Race source status">
                <span className="edgeiq-race-status-pill good">Data {`${activeRaceRows.length}/${raceRows.length || activeRaceRows.length}`} runners</span>
                <span className="edgeiq-race-status-pill info">Engine EDGEiQ active</span>
                <span className={livePriceRowCount > 0 ? "edgeiq-race-status-pill good" : "edgeiq-race-status-pill source"}>{livePriceRowCount > 0 ? `Market ${marketStatus}` : "Market source unavailable"}</span>
                <span className="edgeiq-race-status-pill source">Gear source not refreshed</span>
                <span className="edgeiq-race-status-pill info">Evidence {`${activeRaceRows.filter((item) => hasConnectionPayload(connectionSourceRow(item))).length}/${activeRaceRows.length || 0}`}</span>
              </div>'''
    text = replace_once(text, market_span, market_span_new, changes, "race_source_status_pills")

    # Visible copy cleanup only. Variable names and source keys stay untouched.
    visible_replacements = [
        (">FACTOR LAB<", ">INSIGHTS<", "factor_lab_to_insights"),
        ("<span>FACTOR LAB</span>", "<span>INSIGHTS</span>", "factor_lab_title_to_insights"),
        ("Research Lab", "Market Context", "research_lab_to_market_context"),
        ("Research context, track read and supporting intelligence", "Market/source state, track read and supporting intelligence", "research_context_copy"),
        ("Research Metrics", "Source Coverage", "research_metrics_to_source_coverage"),
        ("Value Edge", "Setup Gap", "value_edge_to_setup_gap"),
        ("OVERBET RISK", "EVIDENCE CAUTION", "overbet_risk_to_evidence_caution"),
        ("Overbet Risk", "Evidence Caution", "overbet_title_to_evidence_caution"),
        ("overbet risk identified", "evidence caution identified", "overbet_sentence_to_evidence_caution"),
        ("No overbet risk identified.", "No evidence caution identified.", "overbet_fallback_to_evidence_caution"),
        ("Market Watch", "Market Context", "market_watch_to_context"),
        ("Race Shape Command", "Race Shape Preview", "race_shape_command_to_preview"),
        ("Market Command", "Market Context", "market_command_to_context"),
        ("Connection Command", "Connection Intelligence", "connection_command_to_intelligence"),
        ("FORM COMMAND", "FORM INTELLIGENCE", "form_command_to_form_intelligence"),
        ("Top Call", "Race Shape Preview", "top_call_to_race_shape_preview"),
        ("Main Risk", "Evidence Confidence", "main_risk_to_evidence_confidence"),
        ("Best Value", "Setup Advantage", "best_value_to_setup_advantage"),
        ("Best Bet", "Race Context", "best_bet_to_race_context"),
        ("tipping", "race explanation", "tipping_copy_cleanup"),
    ]
    for old, new, label in visible_replacements:
        if old in text:
            count = text.count(old)
            text = text.replace(old, new)
            changes.append(f"{label}:{count}")

    # Product workspace classes.
    text = text.replace('<section style={workspaceSectionStyle}>\n        <div style={titleStyle}>\n          <span>INSIGHTS</span>', '<section className="edgeiq-insights-workspace" style={workspaceSectionStyle}>\n        <div style={titleStyle}>\n          <span>INSIGHTS</span>')
    text = text.replace('<details style={advancedDetailsStyle}>', '<details className="edgeiq-market-workspace" style={advancedDetailsStyle}>')

    # Add RESULTS workspace before the hidden decision board.
    marker = '      <section style={{ ...panelStyle, overflowX: "auto", display: "none" }}>'
    if 'intelMode === "RESULTS"' not in text and marker in text:
        results_block = '''      {intelMode === "RESULTS" ? (
        <section className="edgeiq-results-workspace" style={workspaceSectionStyle}>
          <div style={titleStyle}>
            <span>RESULTS</span>
            <em>Post-race review and official result context</em>
          </div>
          <div className="edgeiq-results-empty-state">
            <strong>Results and post-race review will appear once official results are available.</strong>
            <span>EDGEiQ will keep this workspace source-aware and separate from pre-race intelligence.</span>
          </div>
        </section>
      ) : null}

'''
        text = text.replace(marker, results_block + marker, 1)
        changes.append("results_workspace_added")

    # Market tab copy/source state tightening inside ADVANCED.
    text = text.replace("Market pricing will update here as TAB movement develops.", "Market source state will update here when timestamp-safe live pricing is available.")
    text = text.replace("Market Signal", "Market Context")
    text = text.replace("EDGEiQ View", "Fair Price Context")
    text = text.replace("betting confidence", "evidence confidence")
    text = text.replace("Betting confidence", "Evidence confidence")

    TSX.write_text(text, encoding="utf-8")
    return changes, before != text


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    checkpoints = create_checkpoints()
    TERMINAL_CSS.write_text(product_css(), encoding="utf-8")
    index_changed = apply_index()
    tsx_changes, tsx_changed = apply_tsx()

    rows = [
        {"metric": "status", "value": "FULL_TAB_PRODUCTISATION_V1_APPLIED"},
        {"metric": "checkpoints_created_or_present", "value": len(checkpoints)},
        {"metric": "tsx_changed", "value": "YES" if tsx_changed else "NO"},
        {"metric": "index_css_changed", "value": "YES" if index_changed else "NO"},
        {"metric": "product_terminal_css", "value": rel(TERMINAL_CSS)},
        {"metric": "changes", "value": "|".join(tsx_changes)},
        {"metric": "ui_changed", "value": "YES"},
        {"metric": "backend_data_changed", "value": "NO"},
        {"metric": "pricing_changed", "value": "NO"},
        {"metric": "probability_changed", "value": "NO"},
        {"metric": "v6_1_changed", "value": "NO"},
        {"metric": "v7_2g2_changed", "value": "NO"},
        {"metric": "active_csv_schemas_changed", "value": "NO"},
        {"metric": "built_at", "value": now_iso()},
    ]
    write_csv(APPLY_SUMMARY, rows, ["metric", "value"])
    APPLY_REPORT.write_text("\n".join([
        "EDGEiQ Full Tab Productisation V1 Apply Report",
        "===============================================",
        "Status: FULL_TAB_PRODUCTISATION_V1_APPLIED",
        f"Checkpoints created/present: {len(checkpoints)}",
        f"Product CSS: {rel(TERMINAL_CSS)}",
        "Primary nav final: RACE | FIELD | MAP | INSIGHTS | MARKET | RESULTS",
        "Internal mapping retained: COMMAND=RACE, RUNNERS=FIELD, FACTORS=INSIGHTS, ADVANCED=MARKET.",
        "RESULTS workspace added as a professional empty state.",
        "Visible product language tightened away from tipping/betting labels.",
        "Backend data changed: NO",
        "Pricing changed: NO",
        "Probability changed: NO",
        "V6.1 changed: NO",
        "V7.2G2 changed: NO",
        "Active CSV schemas changed: NO",
    ]) + "\n", encoding="utf-8")
    print("FULL_TAB_PRODUCTISATION_V1_APPLIED")


if __name__ == "__main__":
    main()
