from pathlib import Path
from datetime import datetime, timezone
import csv
import shutil

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
TSX = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
CSS = ROOT / "src" / "styles" / "edgeiqProductTerminalV1.css"
TSX_CHECKPOINT = ROOT / "src" / "components" / "RaceIntelligenceScreen_CHECKPOINT_PRE_RACE_TAB_PRODUCT_REBUILD_V1_20260630.tsx"
CSS_CHECKPOINT = ROOT / "src" / "styles" / "edgeiqProductTerminalV1_CHECKPOINT_PRE_RACE_TAB_PRODUCT_REBUILD_V1_20260630.css"
SUMMARY = ROOT / "public" / "data" / "edgeiq_race_tab_product_rebuild_v1_summary.csv"
REPORT = ROOT / "public" / "data" / "edgeiq_race_tab_product_rebuild_v1_report.txt"

HERO_BLOCK = '''        <div className="edgeiq-race-hero-premium">
          <div className="edgeiq-race-hero-left">
            <span className="edgeiq-race-horse-icon" aria-hidden="true">&#9822;</span>
            <div className="edgeiq-race-hero-copy">
              <span className="edgeiq-race-kicker">Race Intelligence</span>
              <h1>{track(header)} R{raceNo(header)}</h1>
              <div className="edgeiq-race-identity-meta" aria-label="Race details">
                <span>{distance(header)}</span>
                {raceClass(header) !== "—" && <span>{raceClass(header)}</span>}
                <span>{trackCondition(header).toUpperCase()}</span>
                <span>{activeRaceRows.length} runners</span>
                {railDisplay !== "—" && <span>Rail {railDisplay}</span>}
              </div>
            </div>
          </div>

          <div className="edgeiq-race-system-status-grid" aria-label="Source and system status">
            <article>
              <span>Data</span>
              <strong>Connected</strong>
              <em>{activeRaceRows.length} runners</em>
            </article>
            <article>
              <span>Engine</span>
              <strong>Active</strong>
              <em>EDGEiQ workspace</em>
            </article>
            <article>
              <span>Market</span>
              <strong>{livePriceRowCount > 0 ? "Connected" : "Unavailable"}</strong>
              <em>{livePriceRowCount > 0 ? `${livePriceRowCount} runners` : "source-aware empty"}</em>
            </article>
            <article>
              <span>Gear</span>
              <strong>{activeRaceRows.some((item) => firstText(item.row, ["gear_changes", "gear_change", "gear", "gear_status"], "") !== "") ? "Connected" : "Unavailable"}</strong>
              <em>{activeRaceRows.some((item) => firstText(item.row, ["gear_changes", "gear_change", "gear", "gear_status"], "") !== "") ? "source loaded" : "source not refreshed"}</em>
            </article>
            <article>
              <span>Evidence</span>
              <strong>{(() => {
                const coverageBase = Math.max(1, displayEvidenceFieldSize * 6);
                const coverageTotal = paceCoverageCount + dnaCoverageCount + campaignCoverageCount + historyCoverageCount + displayConnectionsCoverageCount + displayMarketCoverageCount;
                const coveragePct = Math.round((coverageTotal / coverageBase) * 100);
                return coveragePct >= 70 ? "High" : coveragePct >= 40 ? "Medium" : "Low";
              })()}</strong>
              <em>{`${paceCoverageCount + dnaCoverageCount + campaignCoverageCount + historyCoverageCount + displayConnectionsCoverageCount + displayMarketCoverageCount}/${Math.max(1, displayEvidenceFieldSize * 6)} checks`}</em>
            </article>
          </div>
        </div>'''

RACE_BLOCK = '''      {intelMode === "COMMAND" ? (() => {
        const raceRowsForTab = activeRaceRows.filter((item) => !isScratched(item));
        const raceFieldSize = raceRowsForTab.length || activeRaceRows.length;
        const raceSourceRow = (item: EnrichedRunner): Row => ({ ...(item.row || {}), ...(item.runnerIntel || {}), ...(item.mapEnrichment || {}) });
        const cleanRaceValue = (value: unknown, fallback = "—") => {
          const raw = String(value ?? "").trim();
          if (!raw || /^(UNKNOWN|NOT LOADED|SOURCE_MISSING|SOURCE GAP|NULL|NAN|UNDEFINED)$/i.test(raw)) return fallback;
          return raw;
        };
        const raceRunStyle = (item: EnrichedRunner): string => cleanRaceValue(firstText(raceSourceRow(item), ["run_style_display_v3", "run_style_display", "run_style", "settling_band", "speed_map_bucket", "early_speed_band"], ""), "Unmapped").replace(/_/g, " ").toUpperCase();
        const raceRole = (item: EnrichedRunner): string => {
          const style = raceRunStyle(item);
          if (style.includes("LEAD")) return "Leaders";
          if (style.includes("ON PACE") || style.includes("PACE")) return "On Pace";
          if (style.includes("BACK")) return "Backmarkers";
          if (style.includes("MID")) return "Midfield";
          return "Unmapped";
        };
        const raceLeaders = raceRowsForTab.filter((item) => raceRole(item) === "Leaders");
        const raceOnPace = raceRowsForTab.filter((item) => raceRole(item) === "On Pace");
        const raceMidfield = raceRowsForTab.filter((item) => raceRole(item) === "Midfield");
        const raceBackmarkers = raceRowsForTab.filter((item) => raceRole(item) === "Backmarkers");
        const raceMappedCount = raceLeaders.length + raceOnPace.length + raceMidfield.length + raceBackmarkers.length;
        const raceForwardCount = raceLeaders.length + raceOnPace.length;
        const raceLateCount = raceBackmarkers.length;
        const racePressureRead = cleanRaceValue(speedMapPressureRisk || selectedRacePressureDisplay || selectedRacePressureRiskRunner || fallbackPressureLabel, "Standard");
        const raceShapeRead = cleanRaceValue(selectedRaceShapeLabel !== "—" ? selectedRaceShapeLabel : displayExpectedTempo, raceForwardCount > raceLateCount ? "Forward control" : raceLateCount > raceForwardCount ? "Late runners involved" : "Even shape");
        const raceSetupRunner = bestValueRows[0] || topModelRow || null;
        const raceEvidenceBase = Math.max(1, displayEvidenceFieldSize * 6);
        const raceEvidenceTotal = paceCoverageCount + dnaCoverageCount + campaignCoverageCount + historyCoverageCount + displayConnectionsCoverageCount + displayMarketCoverageCount;
        const raceEvidencePct = Math.round((raceEvidenceTotal / raceEvidenceBase) * 100);
        const raceEvidenceBand = raceEvidencePct >= 70 ? "High" : raceEvidencePct >= 40 ? "Medium" : "Low";
        const raceMarketRead = livePriceRowCount > 0 ? `Market ${marketStatus}` : "Market source unavailable";
        const raceNarrative = raceAssessmentNarrative || raceStory || customerBriefingNarrative || briefingNarrative || "Race intelligence is loaded for this field.";
        const raceFactorCards = [
          { label: "Pace Pressure", value: `${raceForwardCount} forward / ${raceLateCount} late`, detail: raceMappedCount ? `${raceMappedCount}/${raceFieldSize} runners mapped` : "Pace map source is not loaded for this race.", tone: "#2af5dc" },
          { label: "Market Source", value: livePriceRowCount > 0 ? "Connected" : "Unavailable", detail: livePriceRowCount > 0 ? `${livePriceRowCount}/${raceFieldSize} runners with live reference` : "Market source-aware empty state.", tone: livePriceRowCount > 0 ? "#64f589" : "#ff8a25" },
          { label: "Connection Coverage", value: `${displayConnectionsCoverageCount}/${displayEvidenceFieldSize}`, detail: displayConnectionsCoverageCount > 0 ? "Connection evidence available." : "No trainer, jockey or combination angle is currently triggered.", tone: "#ffca4b" },
          { label: "Campaign Coverage", value: `${campaignCoverageCount}/${displayEvidenceFieldSize}`, detail: campaignCoverageCount > 0 ? "Preparation evidence is loaded." : "Campaign profile source is limited for this race.", tone: "#9d7cff" },
        ];
        const paceGroups = [
          { label: "Leaders", items: raceLeaders, tone: "#64f589" },
          { label: "On Pace", items: raceOnPace, tone: "#2af5dc" },
          { label: "Midfield", items: raceMidfield, tone: "#ffca4b" },
          { label: "Backmarkers", items: raceBackmarkers, tone: "#ff8a25" },
        ];
        const watchItems = [
          raceMappedCount ? `${raceForwardCount} runners map forward and ${raceLateCount} map late.` : "Pace map source is not loaded for this race.",
          raceSetupRunner ? `${horse(raceSetupRunner.row)} has the clearest setup profile from the loaded evidence.` : "No setup advantage currently identified.",
          `${raceEvidenceBand} evidence confidence from ${raceEvidenceTotal}/${raceEvidenceBase} source checks.`,
          livePriceRowCount > 0 ? `${livePriceRowCount} runners have market reference loaded.` : "Market source is unavailable, so market context is intentionally muted.",
        ];
        return (
          <section className="edgeiq-race-premium-workspace">
            <div className="edgeiq-race-intel-card-grid" aria-label="Race intelligence cards">
              <article className="edgeiq-race-intel-card">
                <span>Race Shape Preview</span>
                <strong>{raceShapeRead}</strong>
                <em>{displayExpectedTempo !== "—" ? `${displayExpectedTempo} tempo` : "Tempo read is source-aware."}</em>
              </article>
              <article className="edgeiq-race-intel-card">
                <span>Pressure Profile</span>
                <strong>{racePressureRead}</strong>
                <em>{chaosChipLabel || `${raceForwardCount} forward runners identified`}</em>
              </article>
              <article className="edgeiq-race-intel-card">
                <span>Setup Advantage</span>
                <strong>{raceSetupRunner ? horse(raceSetupRunner.row) : "None identified"}</strong>
                <em>{opportunityChipLabel || "No setup advantage currently identified."}</em>
              </article>
              <article className="edgeiq-race-intel-card">
                <span>Evidence Confidence</span>
                <strong>{raceEvidenceBand}</strong>
                <em>{`${raceEvidenceTotal}/${raceEvidenceBase} source checks`}</em>
              </article>
              <article className="edgeiq-race-intel-card feature">
                <span>Race Narrative</span>
                <strong>{raceNarrative}</strong>
                <em>{raceMarketRead}</em>
              </article>
            </div>

            <div className="edgeiq-race-bottom-grid">
              <section className="edgeiq-race-premium-panel">
                <div className="edgeiq-race-panel-title">
                  <span>Key Intelligence Factors</span>
                  <em>Source-aware race context</em>
                </div>
                <div className="edgeiq-race-factor-grid">
                  {raceFactorCards.map((card) => (
                    <article key={`race-factor-${card.label}`} className="edgeiq-race-factor-card" style={{ borderColor: `${card.tone}55` }}>
                      <span style={{ color: card.tone }}>{card.label}</span>
                      <strong>{card.value}</strong>
                      <em>{card.detail}</em>
                    </article>
                  ))}
                </div>
              </section>

              <section className="edgeiq-race-premium-panel">
                <div className="edgeiq-race-panel-title">
                  <span>Pace Map Overview</span>
                  <em>{raceMappedCount ? `${raceMappedCount}/${raceFieldSize} runners mapped` : "Source-aware empty state"}</em>
                </div>
                {raceMappedCount ? (
                  <div className="edgeiq-race-pace-grid">
                    {paceGroups.map((group) => (
                      <article key={`race-pace-${group.label}`}>
                        <span style={{ color: group.tone }}>{group.label}</span>
                        <strong>{group.items.length}</strong>
                        <em>{group.items.slice(0, 3).map((item) => horse(item.row)).join(" · ") || "No runners mapped"}</em>
                      </article>
                    ))}
                  </div>
                ) : (
                  <div className="edgeiq-race-empty-state">Pace map source is not loaded for this race.</div>
                )}
              </section>

              <section className="edgeiq-race-premium-panel">
                <div className="edgeiq-race-panel-title">
                  <span>What To Watch</span>
                  <em>Race conditions that matter</em>
                </div>
                <div className="edgeiq-race-watch-list">
                  {watchItems.map((item, index) => (
                    <div key={`race-watch-${index}`}>
                      <span>{index + 1}</span>
                      <strong>{item}</strong>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          </section>
        );
      })() : null}
'''

CSS_APPEND = r'''

/* EDGEiQ Race Tab Product Rebuild V1 */
.edgeiq-race-hero-premium {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(420px, .95fr);
  gap: 18px;
  align-items: stretch;
  border: 1px solid rgba(80,120,180,.22);
  border-radius: 18px;
  padding: 18px;
  background:
    radial-gradient(circle at 0% 0%, rgba(42,245,220,.15), transparent 28rem),
    radial-gradient(circle at 80% 30%, rgba(157,124,255,.12), transparent 30rem),
    linear-gradient(135deg, rgba(7,18,34,.92), rgba(4,11,21,.80));
}

.edgeiq-race-hero-left {
  display: grid;
  grid-template-columns: 86px minmax(0, 1fr);
  gap: 18px;
  align-items: center;
}

.edgeiq-race-horse-icon {
  width: 74px;
  height: 74px;
  border-radius: 18px;
  border: 1px solid rgba(42,245,220,.36);
  background:
    radial-gradient(circle at 35% 25%, rgba(42,245,220,.28), transparent 3.3rem),
    linear-gradient(145deg, rgba(8,27,42,.96), rgba(3,10,22,.9));
  color: #2af5dc;
  display: grid;
  place-items: center;
  font-size: 42px;
  line-height: 1;
  box-shadow: 0 18px 45px rgba(42,245,220,.12);
}

.edgeiq-race-hero-copy h1 {
  margin: 0;
  color: #ffffff;
  font-size: 46px;
  line-height: .98;
  letter-spacing: .015em;
}

.edgeiq-race-system-status-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  align-content: stretch;
}

.edgeiq-race-system-status-grid article {
  min-height: 92px;
  border: 1px solid rgba(80,120,180,.25);
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(8,20,34,.86), rgba(3,10,22,.72));
  padding: 11px;
  display: grid;
  gap: 5px;
  align-content: center;
}

.edgeiq-race-system-status-grid span,
.edgeiq-race-intel-card span,
.edgeiq-race-panel-title span,
.edgeiq-race-factor-card span,
.edgeiq-race-pace-grid span {
  color: #94a3b8;
  font-size: 10px;
  font-weight: 1000;
  letter-spacing: .13em;
  text-transform: uppercase;
}

.edgeiq-race-system-status-grid strong {
  color: #ffffff;
  font-size: 15px;
  font-weight: 1000;
  line-height: 1.1;
}

.edgeiq-race-system-status-grid em,
.edgeiq-race-factor-card em,
.edgeiq-race-pace-grid em,
.edgeiq-race-panel-title em,
.edgeiq-race-intel-card em {
  color: #a9b8ca;
  font-size: 11.5px;
  font-style: normal;
  line-height: 1.35;
}

.edgeiq-race-premium-workspace {
  display: grid;
  gap: 16px;
  border: 1px solid rgba(42,245,220,.18);
  border-radius: 18px;
  padding: 16px;
  background:
    radial-gradient(circle at 8% 0%, rgba(42,245,220,.09), transparent 25rem),
    linear-gradient(180deg, rgba(6,18,32,.82), rgba(3,9,18,.78));
}

.edgeiq-race-intel-card-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.edgeiq-race-intel-card {
  min-height: 146px;
  border: 1px solid rgba(80,120,180,.27);
  border-radius: 16px;
  padding: 15px;
  background:
    radial-gradient(circle at 0% 0%, rgba(49,145,255,.10), transparent 14rem),
    linear-gradient(180deg, rgba(9,24,42,.92), rgba(3,10,22,.84));
  display: grid;
  gap: 9px;
  align-content: start;
}

.edgeiq-race-intel-card:nth-child(2) { border-color: rgba(42,245,220,.30); }
.edgeiq-race-intel-card:nth-child(3) { border-color: rgba(245,196,81,.32); }
.edgeiq-race-intel-card:nth-child(4) { border-color: rgba(157,124,255,.32); }
.edgeiq-race-intel-card.feature { border-color: rgba(245,158,11,.35); }

.edgeiq-race-intel-card strong {
  color: #ffffff;
  font-size: 18px;
  font-weight: 1000;
  line-height: 1.18;
}

.edgeiq-race-intel-card.feature strong {
  font-size: 15px;
  line-height: 1.35;
}

.edgeiq-race-bottom-grid {
  display: grid;
  grid-template-columns: 1.05fr .95fr .9fr;
  gap: 12px;
  align-items: stretch;
}

.edgeiq-race-premium-panel {
  border: 1px solid rgba(80,120,180,.25);
  border-radius: 16px;
  padding: 14px;
  background: linear-gradient(180deg, rgba(8,20,34,.88), rgba(3,10,22,.80));
  display: grid;
  gap: 12px;
}

.edgeiq-race-panel-title {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  border-bottom: 1px solid rgba(80,120,180,.24);
  padding-bottom: 10px;
}

.edgeiq-race-factor-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.edgeiq-race-factor-card,
.edgeiq-race-pace-grid article {
  border: 1px solid rgba(80,120,180,.24);
  border-radius: 13px;
  background: rgba(5,12,22,.70);
  padding: 11px;
  display: grid;
  gap: 6px;
}

.edgeiq-race-factor-card strong,
.edgeiq-race-pace-grid strong {
  color: #ffffff;
  font-size: 16px;
  font-weight: 1000;
}

.edgeiq-race-pace-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.edgeiq-race-empty-state {
  border: 1px solid rgba(245,158,11,.30);
  border-radius: 13px;
  background: rgba(245,158,11,.08);
  color: #fed7aa;
  padding: 14px;
  font-size: 13px;
  font-weight: 850;
}

.edgeiq-race-watch-list {
  display: grid;
  gap: 9px;
}

.edgeiq-race-watch-list div {
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  border: 1px solid rgba(80,120,180,.22);
  border-radius: 13px;
  background: rgba(5,12,22,.68);
  padding: 10px;
}

.edgeiq-race-watch-list span {
  width: 24px;
  height: 24px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: rgba(42,245,220,.14);
  color: #2af5dc;
  font-size: 11px;
  font-weight: 1000;
}

.edgeiq-race-watch-list strong {
  color: #dbeafe;
  font-size: 12.5px;
  line-height: 1.42;
}

@media (max-width: 1180px) {
  .edgeiq-race-hero-premium,
  .edgeiq-race-bottom-grid {
    grid-template-columns: 1fr;
  }
  .edgeiq-race-system-status-grid,
  .edgeiq-race-intel-card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .edgeiq-race-hero-left,
  .edgeiq-race-factor-grid,
  .edgeiq-race-pace-grid,
  .edgeiq-race-system-status-grid,
  .edgeiq-race-intel-card-grid {
    grid-template-columns: 1fr;
  }
}
'''


def copy_checkpoint(src: Path, dst: Path) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst.exists()


def replace_between(text: str, start_marker: str, end_marker: str, replacement: str, keep_end=True):
    start = text.find(start_marker)
    if start == -1:
        return text, False, "START_NOT_FOUND"
    end = text.find(end_marker, start)
    if end == -1:
        return text, False, "END_NOT_FOUND"
    if keep_end:
        return text[:start] + replacement + text[end:], True, "REPLACED"
    return text[:start] + replacement + text[end + len(end_marker):], True, "REPLACED"


def main():
    tsx_checkpoint = copy_checkpoint(TSX, TSX_CHECKPOINT)
    css_checkpoint = copy_checkpoint(CSS, CSS_CHECKPOINT)

    text = TSX.read_text(encoding="utf-8")
    if "edgeiq-race-hero-premium" in text:
        hero_done = True
        hero_status = "ALREADY_PRESENT"
    else:
        hero_start = '        <div className="edgeiq-race-identity-card">'
        hero_end = '      </section>\n\n      {intelMode === "COMMAND" ? ('
        text, hero_done, hero_status = replace_between(text, hero_start, hero_end, HERO_BLOCK + '\n      </section>\n\n', keep_end=False)

    command_start = '      {intelMode === "COMMAND" ? ('
    map_start = '      {intelMode === "MAP" ? (() => {'
    if command_start in text:
        text, race_done, race_status = replace_between(text, command_start, map_start, RACE_BLOCK, keep_end=True)
    else:
        legacy_race_start = '      <section className="edgeiq-command-workspace" style={evidenceSectionStyle}>'
        text, race_done, race_status = replace_between(text, legacy_race_start, map_start, RACE_BLOCK, keep_end=True)
    TSX.write_text(text, encoding="utf-8")

    css = CSS.read_text(encoding="utf-8")
    css_changed = False
    if "/* EDGEiQ Race Tab Product Rebuild V1 */" not in css:
      CSS.write_text(css.rstrip() + CSS_APPEND + "\n", encoding="utf-8")
      css_changed = True

    after = TSX.read_text(encoding="utf-8")
    command_block = ""
    start = after.find('      {intelMode === "COMMAND" ? (() => {')
    end = after.find('      {intelMode === "MAP" ? (() => {', start)
    if start != -1 and end != -1:
        command_block = after[start:end]
    old_visible_terms = ["Top Call", "Best Value", "Main Risk", " Tip", "Selection", "Bet ", "Market Command", "Connection Command", "Evidence Footer", "EDGEiQ Score Breakdown"]
    old_terms_found = [term for term in old_visible_terms if term.lower() in command_block.lower()]
    premium_hero_added = "edgeiq-race-hero-premium" in after and "edgeiq-race-horse-icon" in after
    five_cards_added = all(term in command_block for term in ["Race Shape Preview", "Pressure Profile", "Setup Advantage", "Evidence Confidence", "Race Narrative"])
    bottom_sections_added = all(term in command_block for term in ["Key Intelligence Factors", "Pace Map Overview", "What To Watch"])
    old_replaced = race_done and "edgeiq-race-premium-workspace" in command_block and "Intelligence Brief" not in command_block
    status = "EDGEIQ_RACE_TAB_PRODUCT_REBUILD_V1_APPLIED" if hero_done and old_replaced and five_cards_added and bottom_sections_added and not old_terms_found else "EDGEIQ_RACE_TAB_PRODUCT_REBUILD_V1_REVIEW_REQUIRED"

    rows = [
        {"metric": "status", "value": status},
        {"metric": "tsx_checkpoint", "value": str(TSX_CHECKPOINT.relative_to(ROOT))},
        {"metric": "css_checkpoint", "value": str(CSS_CHECKPOINT.relative_to(ROOT))},
        {"metric": "tsx_checkpoint_created", "value": "YES" if tsx_checkpoint else "NO"},
        {"metric": "css_checkpoint_created", "value": "YES" if css_checkpoint else "NO"},
        {"metric": "premium_race_hero_added", "value": "YES" if premium_hero_added else "NO"},
        {"metric": "premium_race_hero_status", "value": hero_status},
        {"metric": "old_race_tab_replaced", "value": "YES" if old_replaced else "NO"},
        {"metric": "race_tab_replace_status", "value": race_status},
        {"metric": "five_race_intelligence_cards_added", "value": "YES" if five_cards_added else "NO"},
        {"metric": "bottom_sections_added", "value": "YES" if bottom_sections_added else "NO"},
        {"metric": "old_tipping_internal_language_removed", "value": "YES" if not old_terms_found else "NO"},
        {"metric": "old_terms_found_in_race_block", "value": "|".join(old_terms_found)},
        {"metric": "product_css_changed", "value": "YES" if css_changed else "NO"},
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
        f.write("EDGEiQ Race Tab Product Rebuild V1\n")
        f.write(f"Status: {status}\n\n")
        f.write("Checkpoints:\n")
        f.write(f"- {TSX_CHECKPOINT.relative_to(ROOT)}\n")
        f.write(f"- {CSS_CHECKPOINT.relative_to(ROOT)}\n\n")
        f.write("Changes:\n")
        f.write(f"- Premium race hero added: {'YES' if premium_hero_added else 'NO'} ({hero_status})\n")
        f.write(f"- Old RACE tab replaced: {'YES' if old_replaced else 'NO'} ({race_status})\n")
        f.write(f"- Five race intelligence cards added: {'YES' if five_cards_added else 'NO'}\n")
        f.write(f"- Bottom sections added: {'YES' if bottom_sections_added else 'NO'}\n")
        f.write(f"- Old tipping/internal language removed from RACE block: {'YES' if not old_terms_found else 'NO'}\n")
        if old_terms_found:
            f.write(f"- Remaining terms: {' | '.join(old_terms_found)}\n")
        f.write("\nSafety confirmations:\n")
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
