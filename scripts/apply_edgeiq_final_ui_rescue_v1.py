from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
APP = ROOT / "src" / "App.tsx"
RACE = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
CSS = ROOT / "src" / "styles" / "edgeiqProductTerminalV1.css"
OUT_SUMMARY = ROOT / "public" / "data" / "edgeiq_final_ui_rescue_apply_v1_summary.csv"
OUT_REPORT = ROOT / "public" / "data" / "edgeiq_final_ui_rescue_apply_v1_report.txt"

changes = []

def write_if_changed(path: Path, text: str, label: str) -> None:
    old = path.read_text(encoding="utf-8")
    if old != text:
        path.write_text(text, encoding="utf-8")
        changes.append(label)

app = APP.read_text(encoding="utf-8")
app2 = app
app2 = app2.replace('const [tab, setTab] = useState<TabKey>(storedTab);', 'const [tab, setTab] = useState<TabKey>("INTELLIGENCE");')
app2 = app2.replace('const showOuterTerminalChrome = tab !== "INTELLIGENCE" || intelligenceProductView === "RACE";', 'const showOuterTerminalChrome = false;')
write_if_changed(APP, app2, "src/App.tsx")

race = RACE.read_text(encoding="utf-8")
race2 = race

# FILES registration.
if 'ratingsHeatmap: "/data/edgeiq_ratings_intelligence_heatmap_v1.csv"' not in race2:
    race2 = race2.replace('  commandEnrichment: "/data/edgeiq_command_enrichment_feed_v3.csv",\n};', '  commandEnrichment: "/data/edgeiq_command_enrichment_feed_v3.csv",\n  ratingsHeatmap: "/data/edgeiq_ratings_intelligence_heatmap_v1.csv",\n};')

# Type support.
if 'ratingsHeatmap?: Row;' not in race2:
    race2 = race2.replace('  formEnrichment?: Row;\n};', '  formEnrichment?: Row;\n  ratingsHeatmap?: Row;\n};')

# State support.
if 'ratingsHeatmapRows' not in race2:
    race2 = race2.replace('  const [formEnrichmentRows, setFormEnrichmentRows] = useState<Row[]>([]);\n', '  const [formEnrichmentRows, setFormEnrichmentRows] = useState<Row[]>([]);\n  const [ratingsHeatmapRows, setRatingsHeatmapRows] = useState<Row[]>([]);\n')

# CSV loading support.
race2 = race2.replace('commandEnrichment, formEnrichment] = await Promise.all([', 'commandEnrichment, formEnrichment, ratingsHeatmap] = await Promise.all([')
if 'loadCsv(FILES.ratingsHeatmap)' not in race2:
    race2 = race2.replace('        loadCsv(FILES.formEnrichment),\n      ]);', '        loadCsv(FILES.formEnrichment),\n        loadCsv(FILES.ratingsHeatmap),\n      ]);')
if 'setRatingsHeatmapRows(ratingsHeatmap);' not in race2:
    race2 = race2.replace('      setFormEnrichmentRows(formEnrichment);\n      setIntelligenceScoreRows(intelligenceScore);', '      setFormEnrichmentRows(formEnrichment);\n      setRatingsHeatmapRows(ratingsHeatmap);\n      setIntelligenceScoreRows(intelligenceScore);')

# Enriched runner join support.
if 'const ratingsHeatmap = findSidecarByRaceHorse(ratingsHeatmapRows, row);' not in race2:
    race2 = race2.replace('      const mapEnrichment = findSidecarByRaceHorse(mapEnrichmentRows, row);\n', '      const mapEnrichment = findSidecarByRaceHorse(mapEnrichmentRows, row);\n      const ratingsHeatmap = findSidecarByRaceHorse(ratingsHeatmapRows, row);\n')
race2 = race2.replace('mapEnrichment, formEnrichment, factorRows };', 'mapEnrichment, formEnrichment, ratingsHeatmap, factorRows };')
race2 = race2.replace('mapEnrichmentRows, formEnrichmentRows, formEnrichmentByRunnerKey]);', 'mapEnrichmentRows, formEnrichmentRows, ratingsHeatmapRows, formEnrichmentByRunnerKey]);')

# Customer-facing label polish.
race2 = race2.replace('>Factor Lab</span>', '>Evidence Lab</span>')

heatmap_jsx = r'''

        <section className="edgeiq-product-heatmap edgeiq-product-card" aria-label="Ratings Intelligence Heat Map">
          <div className="edgeiq-product-heatmap-head">
            <div>
              <span>RATINGS INTELLIGENCE HEAT MAP</span>
              <strong>Compares each runner against the expected standard of this race.</strong>
            </div>
            <em>{activeRaceRows.filter((item) => item.ratingsHeatmap).length}/{activeRaceRows.length || 0} runners mapped</em>
          </div>

          {activeRaceRows.some((item) => item.ratingsHeatmap) ? (() => {
            const heatRows = activeRaceRows.flatMap((item) =>
              item.ratingsHeatmap ? [{ item, heat: item.ratingsHeatmap }] : []
            );
            const expectedRatings = heatRows.map((entry) => firstNum(entry.heat, ["expected_rating"])).filter((value): value is number => value !== null);
            const runnerRatings = heatRows.map((entry) => firstNum(entry.heat, ["runner_rating"])).filter((value): value is number => value !== null);
            const heatScores = heatRows.map((entry) => firstNum(entry.heat, ["overall_heat_score"])).filter((value): value is number => value !== null);
            const expectedRaceRating = expectedRatings.length ? expectedRatings[0] : null;
            const ratingSpread = runnerRatings.length ? Math.max(...runnerRatings) - Math.min(...runnerRatings) : null;
            const avgHeatScore = heatScores.length ? heatScores.reduce((sum, value) => sum + value, 0) / heatScores.length : null;
            const evidencePct = heatRows.length && activeRaceRows.length ? Math.round((heatRows.length / activeRaceRows.length) * 100) : 0;
            const cleanCell = (value: unknown) => {
              const label = text(value);
              return label && !["UNKNOWN", "NOT LOADED", "SOURCE GAP", "NULL", "NAN", "UNDEFINED"].includes(label.toUpperCase()) ? label : "—";
            };
            const metricLabel = (value: number | null, suffix = "") => value === null ? "—" : `${value.toFixed(1)}${suffix}`;
            return (
              <>
                <div className="edgeiq-product-heatmap-grid">
                  <article>
                    <span>Expected Race Rating</span>
                    <strong>{metricLabel(expectedRaceRating)}</strong>
                  </article>
                  <article>
                    <span>Rating Spread</span>
                    <strong>{metricLabel(ratingSpread)}</strong>
                  </article>
                  <article>
                    <span>Field Depth</span>
                    <strong>{metricLabel(avgHeatScore)}</strong>
                  </article>
                  <article>
                    <span>Evidence Coverage</span>
                    <strong>{evidencePct}%</strong>
                  </article>
                </div>

                <div className="edgeiq-product-table edgeiq-product-heatmap-table" role="table" aria-label="Ratings intelligence heat map table">
                  <div className="edgeiq-product-table-row edgeiq-product-table-head" role="row">
                    {["Runner", "Expected", "Rating", "Gap", "Distance", "Condition", "Class", "Campaign", "Connections", "Overall"].map((label) => (
                      <span key={`heat-head-${label}`} role="columnheader">{label}</span>
                    ))}
                  </div>
                  {heatRows.map(({ item, heat }) => {
                    const band = cleanCell(firstText(heat, ["heat_band"], "NO_EVIDENCE"));
                    const bandClass = `heat-band-${band.toLowerCase().replace(/_/g, "-")}`;
                    const ratingGap = firstNum(heat, ["rating_gap"]);
                    return (
                      <div className={`edgeiq-product-table-row ${bandClass}`} role="row" key={`ratings-heat-${runnerRowKey(item.row)}`}>
                        <strong role="cell">{horse(item.row)}</strong>
                        <span role="cell">{cleanCell(firstText(heat, ["expected_rating"], ""))}</span>
                        <span role="cell">{cleanCell(firstText(heat, ["runner_rating"], ""))}</span>
                        <span role="cell">{ratingGap === null ? "—" : signed(ratingGap, 1)}</span>
                        <span role="cell">{cleanCell(firstText(heat, ["distance_heat"], ""))}</span>
                        <span role="cell">{cleanCell(firstText(heat, ["condition_heat"], ""))}</span>
                        <span role="cell">{cleanCell(firstText(heat, ["class_heat"], ""))}</span>
                        <span role="cell">{cleanCell(firstText(heat, ["campaign_heat"], ""))}</span>
                        <span role="cell">{cleanCell(firstText(heat, ["connections_heat"], ""))}</span>
                        <span role="cell"><em>{band}</em></span>
                      </div>
                    );
                  })}
                </div>
              </>
            );
          })() : (
            <div className="edgeiq-product-empty">Ratings heatmap source unavailable for this race.</div>
          )}
        </section>
'''

if 'Ratings Intelligence Heat Map' not in race2:
    marker = '\n\n\n        {selected ? ('
    if marker in race2:
        race2 = race2.replace(marker, heatmap_jsx + marker, 1)
    else:
        raise SystemExit('INSIGHTS insertion marker not found')

write_if_changed(RACE, race2, "src/components/RaceIntelligenceScreen.tsx")

css = CSS.read_text(encoding="utf-8")
css_add = r'''

/* EDGEiQ Final UI Rescue V1 - Ratings heatmap */
.edgeiq-product-race .edgeiq-product-heatmap {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 14px;
  padding: 16px;
  margin: 0 0 16px;
  border: 1px solid rgba(42,245,220,.22);
  border-radius: 18px;
  background:
    radial-gradient(circle at 0% 0%, rgba(42,245,220,.13), transparent 18rem),
    radial-gradient(circle at 82% 20%, rgba(157,124,255,.10), transparent 24rem),
    linear-gradient(145deg, rgba(6,18,32,.94), rgba(3,9,20,.88));
  box-shadow: 0 18px 44px rgba(0,0,0,.26), inset 0 1px 0 rgba(255,255,255,.05);
  overflow: hidden;
}

.edgeiq-product-race .edgeiq-product-heatmap::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 2px;
  background: linear-gradient(180deg, rgba(42,245,220,.82), rgba(157,124,255,.20));
  pointer-events: none;
}

.edgeiq-product-race .edgeiq-product-heatmap-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  position: relative;
  z-index: 1;
}

.edgeiq-product-race .edgeiq-product-heatmap-head div {
  display: grid;
  gap: 5px;
}

.edgeiq-product-race .edgeiq-product-heatmap-head span {
  color: #2af5dc;
  font-size: 10px;
  font-weight: 1000;
  letter-spacing: .22em;
  text-transform: uppercase;
}

.edgeiq-product-race .edgeiq-product-heatmap-head strong {
  color: #f8fafc;
  font-size: 17px;
  line-height: 1.2;
}

.edgeiq-product-race .edgeiq-product-heatmap-head em {
  font-style: normal;
  color: #a9b8ca;
  font-size: 11px;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: .08em;
}

.edgeiq-product-race .edgeiq-product-heatmap-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  position: relative;
  z-index: 1;
}

.edgeiq-product-race .edgeiq-product-heatmap-grid article {
  display: grid;
  gap: 6px;
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(80,120,180,.25);
  background: rgba(5,12,22,.58);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.04);
}

.edgeiq-product-race .edgeiq-product-heatmap-grid span {
  color: #8ea4bd;
  font-size: 9.5px;
  font-weight: 1000;
  letter-spacing: .12em;
  text-transform: uppercase;
}

.edgeiq-product-race .edgeiq-product-heatmap-grid strong {
  color: #fff;
  font-size: 20px;
  line-height: 1;
}

.edgeiq-product-race .edgeiq-product-heatmap-table {
  position: relative;
  z-index: 1;
  overflow-x: auto;
  border-radius: 14px;
  border: 1px solid rgba(80,120,180,.22);
}

.edgeiq-product-race .edgeiq-product-heatmap-table .edgeiq-product-table-row {
  display: grid;
  grid-template-columns: minmax(150px, 1.35fr) repeat(9, minmax(82px, .75fr));
  min-width: 1040px;
  align-items: center;
  gap: 0;
  border-bottom: 1px solid rgba(80,120,180,.14);
}

.edgeiq-product-race .edgeiq-product-heatmap-table .edgeiq-product-table-row > span,
.edgeiq-product-race .edgeiq-product-heatmap-table .edgeiq-product-table-row > strong {
  min-height: 38px;
  display: flex;
  align-items: center;
  padding: 8px 9px;
  border-right: 1px solid rgba(80,120,180,.10);
  color: #cbd5e1;
  font-size: 11px;
  line-height: 1.2;
}

.edgeiq-product-race .edgeiq-product-heatmap-table .edgeiq-product-table-head > span {
  min-height: 34px;
  color: #8ea4bd;
  background: rgba(8,18,32,.78);
  font-size: 9.5px;
  font-weight: 1000;
  text-transform: uppercase;
  letter-spacing: .10em;
}

.edgeiq-product-race .edgeiq-product-heatmap-table strong {
  color: #f8fafc !important;
  font-weight: 1000;
}

.edgeiq-product-race .edgeiq-product-heatmap-table em {
  font-style: normal;
  padding: 5px 8px;
  border-radius: 999px;
  border: 1px solid rgba(148,163,184,.22);
  background: rgba(148,163,184,.08);
  color: #cbd5e1;
  font-size: 9px;
  font-weight: 1000;
  letter-spacing: .08em;
  white-space: nowrap;
}

.edgeiq-product-race .edgeiq-product-heatmap-table .heat-band-elite-edge { background: linear-gradient(90deg, rgba(45,212,191,.18), rgba(5,12,22,.62)); }
.edgeiq-product-race .edgeiq-product-heatmap-table .heat-band-above-expected { background: linear-gradient(90deg, rgba(59,130,246,.16), rgba(5,12,22,.62)); }
.edgeiq-product-race .edgeiq-product-heatmap-table .heat-band-par { background: rgba(5,12,22,.62); }
.edgeiq-product-race .edgeiq-product-heatmap-table .heat-band-below-expected { background: linear-gradient(90deg, rgba(245,196,81,.14), rgba(5,12,22,.62)); }
.edgeiq-product-race .edgeiq-product-heatmap-table .heat-band-risk { background: linear-gradient(90deg, rgba(248,113,113,.14), rgba(5,12,22,.62)); }
.edgeiq-product-race .edgeiq-product-heatmap-table .heat-band-no-evidence { background: rgba(15,23,42,.52); }

@media (max-width: 920px) {
  .edgeiq-product-race .edgeiq-product-heatmap-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 620px) {
  .edgeiq-product-race .edgeiq-product-heatmap-head {
    display: grid;
  }
  .edgeiq-product-race .edgeiq-product-heatmap-grid {
    grid-template-columns: 1fr;
  }
}
'''
if 'EDGEiQ Final UI Rescue V1 - Ratings heatmap' not in css:
    css = css.rstrip() + css_add + "\n"
write_if_changed(CSS, css, "src/styles/edgeiqProductTerminalV1.css")

OUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
OUT_SUMMARY.write_text("metric,value\nfiles_changed,%s\nlegacy_shell_gate,DISABLED\nratings_heatmap_wired,YES\n" % (";".join(changes) if changes else "NONE"), encoding="utf-8")
OUT_REPORT.write_text("EDGEIQ_FINAL_UI_RESCUE_APPLY_V1\n\nFiles changed:\n- " + ("\n- ".join(changes) if changes else "None") + "\n\nLegacy outer chrome is hard-disabled through showOuterTerminalChrome=false. Ratings heatmap feed is registered, joined to enriched runners, and rendered in INSIGHTS.\n", encoding="utf-8")
print("EDGEIQ_FINAL_UI_RESCUE_APPLY_V1 complete")
print("files_changed=" + (";".join(changes) if changes else "NONE"))

