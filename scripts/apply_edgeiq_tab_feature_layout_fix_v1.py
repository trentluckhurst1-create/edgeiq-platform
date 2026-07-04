from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TSX = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
CSS = ROOT / "src" / "styles" / "edgeiqProductTerminalV1.css"


def replace_between(source: str, start: str, end: str, replacement: str) -> str:
    start_idx = source.find(start)
    if start_idx < 0:
        raise RuntimeError(f"start marker not found: {start[:80]}")
    end_idx = source.find(end, start_idx)
    if end_idx < 0:
        raise RuntimeError(f"end marker not found: {end[:80]}")
    return source[:start_idx] + replacement + source[end_idx:]


def main() -> None:
    source = TSX.read_text(encoding="utf-8")

    old = ' const meetingRaceCountLabel = (value: unknown) => { const count = Number(value); return Number.isFinite(count) && count > 0 ? `${count} races` : "Race list pending"; };'
    new = old + '\n const raceFieldCountLabel = (value: unknown) => { const count = Number(value); return Number.isFinite(count) && count > 0 ? `${count}` : "Fields pending"; };'
    if new not in source:
        source = source.replace(old, new)

    source = source.replace('<span>{race.fieldSize}</span>', '<span>{raceFieldCountLabel(race.fieldSize)}</span>')

    old_race_return = ' return <section className="edgeiq-race-premium-workspace edgeiq-product-section edgeiq-race-simple"><div className="edgeiq-tab-heading"><span>RACE</span><strong>Race Intelligence</strong><em>Overview of race shape, standard, strength, confidence.</em></div><div className="edgeiq-race-simple-hero"><span>{header ? `${track(header)} R${raceNo(header)}` : futureMeetingSelectedRace}</span><strong>{header ? `${distance(header)} ${raceClass(header)}` : futureMeetingSelectedMeta || "Race"}</strong><em>{header ? `${trackCondition(header)} / ${raceFieldSize} Runners` : `${futureMeetingFieldCount} Runners`}</em></div><div className="edgeiq-race-simple-grid">{raceCards.map((card) => <article key={`race-simple-${card.label}`} className="edgeiq-race-simple-card"><span>{card.label}</span><strong>{card.value}</strong><em>{card.detail}</em></article>)}</div><section className="edgeiq-race-simple-narrative"><span>Intelligence Narrative</span><p>{narrativeText}</p></section></section>;'
    new_race_return = ''' const raceMapSource = activeRaceRows.map((item) => item.mapEnrichment).find(Boolean) || {};
 const racePacePressure = firstText(raceMapSource, ["race_pressure_band_v3", "race_pressure_band_v2", "race_pressure_band_display"], raceShapeText);
 const raceMapAdvantage = firstText(raceMapSource, ["pace_advantage_display_v3", "pace_advantage_display"], raceShapeText);
 const raceKeyRisk = firstText(raceMapSource, ["race_shape_verdict_v3", "race_shape_verdict_v2"], pressureRisk && pressureRisk !== "-" ? pressureRisk : "No single map risk dominates.");
 const whatMatters = [
 { label: "Pace Pressure", value: racePacePressure },
 { label: "Field Depth", value: raceStrengthText },
 { label: "Map Advantage", value: raceMapAdvantage },
 { label: "Key Risk", value: raceKeyRisk },
 ];
 return <section className="edgeiq-race-premium-workspace edgeiq-product-section edgeiq-race-simple edgeiq-race-useful"><div className="edgeiq-race-simple-hero compact"><span>{header ? `${track(header)} R${raceNo(header)}` : futureMeetingSelectedRace}</span><strong>{header ? `${distance(header)} ${raceClass(header)}` : futureMeetingSelectedMeta || "Race"}</strong><em>{header ? `${trackCondition(header)} / ${raceFieldSize} Runners` : `${futureMeetingFieldCount} Runners`}</em></div><div className="edgeiq-race-simple-grid">{raceCards.map((card) => <article key={`race-simple-${card.label}`} className="edgeiq-race-simple-card"><span>{card.label}</span><strong>{card.value}</strong><em>{card.detail}</em></article>)}</div><section className="edgeiq-race-what-matters"><span>What matters</span>{whatMatters.map((item) => <article key={`race-what-matters-${item.label}`}><strong>{item.label}</strong><em>{item.value}</em></article>)}</section><section className="edgeiq-race-simple-narrative"><span>Intelligence Narrative</span><p>{narrativeText}</p></section></section>;'''
    if old_race_return in source:
        source = source.replace(old_race_return, new_race_return)
    else:
        raise RuntimeError("Race return block not found")

    map_start = ' <div className="edgeiq-tab-heading"><span>MAP</span><strong>Race Map</strong><em>Lane-based speed map with barrier context.</em></div>'
    map_end = ' <section style={{ display: "grid", gridTemplateColumns: "minmax(0,1.35fr) minmax(360px,.65fr)", gap: 12, alignItems: "start" }}>'
    map_replacement = ''' <div className="edgeiq-map-summary-strip">
 {summaryCards.filter((card) => ["Field Size", "Pressure", "Leaders", "Midfield", "Backmarkers", "Map Confidence"].includes(card.label)).map((card) => (
 <article key={`map-summary-strip-${card.label}`}><span>{card.label}</span><strong>{card.value}</strong></article>
 ))}
 </div>

'''
    source = replace_between(source, map_start, map_end, map_replacement)

    runners_start = ' {intelMode === "RUNNERS" ? (() => {'
    runners_end = ' {intelMode === "PERFORMANCE" ? (() => {'
    runners_block = ''' {intelMode === "RUNNERS" ? (() => {
 const fieldRows = activeRaceRows;
 const cleanMarket = (item: EnrichedRunner) => {
 const value = money(livePrice(item.row, item.bet));
 return value && value !== "-" ? value : "Pending";
 };
 const cleanFieldStatus = (item: EnrichedRunner) => {
 if (isScratched(item)) return "Scratched";
 const raw = firstText(item.row, ["runner_status", "scratch_status", "ui_status", "field_status"], "").replace(/_/g, " ").trim().toUpperCase();
 if (raw.includes("SCRATCH")) return "Scratched";
 if (raw.includes("OPEN")) return "Open";
 if (raw.includes("FINAL") || raw.includes("FIELD") || raw.includes("ACTIVE") || raw.includes("READY")) return "Final Field";
 return "Pending";
 };
 const cleanWeight = (row: Row) => firstText(row, ["weight", "allocated_weight", "handicap_weight", "weight_carried", "runner_weight", "weight_kg"], "—");
 const quickValue = (value: unknown) => { const raw = String(value ?? "").trim(); return raw && raw !== "-" ? raw : "—"; };
 return (
 <section className="edgeiq-field-tab edgeiq-product-section edgeiq-field-tab-v2">
 <div className="edgeiq-field-compact-header"><div><span>FIELD</span><strong>{header ? `${track(header)} R${raceNo(header)}` : "Field"}</strong></div><em>{fieldRows.length} runners / Final fields</em></div>
 <div className="edgeiq-field-table edgeiq-product-table" role="table" aria-label="Race field table">
 <div className="edgeiq-field-table-row head" role="row">{['No','Horse','Barrier','Weight','Jockey','Trainer','Market','Status'].map((label) => <span key={`field-head-${label}`}>{label}</span>)}</div>
 {fieldRows.map((item) => {
 const row = item.row;
 const rowKey = runnerRowKey(row);
 const status = cleanFieldStatus(item);
 const isOpen = rowKey === selectedKey;
 const performanceIndex = firstNum(item.ratingsHeatmap, ["runner_rating"]) ?? todayProjectionFigure(item);
 const lastStart = firstText(item.formIntelligence, ["last_start_1_rating", "finishing_position", "performance_intelligence_label"], "");
 const recentForm = firstText(item.formEnrichment, ["form_signal", "form_trend", "form_status"], firstText(item.formIntelligence, ["form_signal", "performance_intelligence_label"], ""));
 const runStyle = firstText(item.mapEnrichment, ["run_style_display_v3", "run_style_display", "run_style"], firstText(row, ["run_style", "speed_map_bucket", "settling_band"], ""));
 return <React.Fragment key={`field-row-wrap-${rowKey}`}><button type="button" className={`edgeiq-field-table-row ${isOpen ? "is-selected" : ""}`} onClick={() => setSelectedKey(rowKey)} role="row" aria-expanded={isOpen}><span>{saddle(row) === 999 ? "-" : saddle(row)}</span><strong>{horse(row)}</strong><span>{barrier(row)}</span><span>{cleanWeight(row)}</span><span>{firstText(row, ["jockey", "jockey_name", "rider"], "-")}</span><span>{firstText(row, ["trainer", "trainer_name"], "-")}</span><span>{cleanMarket(item)}</span><span>{status}</span></button>{isOpen ? <div className="edgeiq-field-quick-profile"><article><span>Recent Form</span><strong>{quickValue(recentForm)}</strong></article><article><span>Last Start</span><strong>{quickValue(lastStart)}</strong></article><article><span>Barrier</span><strong>{barrier(row)}</strong></article><article><span>Jockey</span><strong>{firstText(row, ["jockey", "jockey_name", "rider"], "-")}</strong></article><article><span>Trainer</span><strong>{firstText(row, ["trainer", "trainer_name"], "-")}</strong></article><article><span>Performance Index</span><strong>{performanceIndex === null ? "—" : renderMetricValue(performanceIndex, 1)}</strong></article><article><span>Run Style</span><strong>{quickValue(runStyle)}</strong></article><article><span>Price</span><strong>{money(limitedAdjustedPrice(item) ?? fairPrice(item.row, item.bet))}</strong></article></div> : null}</React.Fragment>;
 })}
 </div>
 </section>
 );
 })() : null}
'''
    source = replace_between(source, runners_start, runners_end, runners_block + runners_end)

    performance_start = ' {intelMode === "PERFORMANCE" ? (() => {'
    performance_end = ' {intelMode === "NEXUS" ? (() => {'
    performance_block = ''' {intelMode === "PERFORMANCE" ? (() => {
 const heatRows = activeRaceRows.map((item) => ({ item, heat: item.ratingsHeatmap || {} }));
 const heatRowsWithRatings = heatRows.filter((entry) => firstNum(entry.heat, ["runner_rating"]) !== null);
 const expectedRaceRating = heatRows.map((entry) => firstNum(entry.heat, ["expected_rating"])).find((value) => value !== null) ?? null;
 const runnerPerformance = heatRows.map((entry) => firstNum(entry.heat, ["runner_rating"])).filter((value): value is number => value !== null).sort((a, b) => a - b);
 const fieldMedian = runnerPerformance.length ? runnerPerformance[Math.floor(runnerPerformance.length / 2)] : null;
 const performanceSpread = runnerPerformance.length ? Math.max(...runnerPerformance) - Math.min(...runnerPerformance) : null;
 const strength = performanceSpread === null ? "-" : performanceSpread >= 12 ? "Deep" : performanceSpread >= 7 ? "Competitive" : "Even";
 const heatCellClass = (value: number | null, type: "score" | "gap" = "score") => {
 if (value === null) return "heat-neutral";
 if (type === "gap") return value >= 5 ? "heat-elite" : value <= -5 ? "heat-risk" : value >= 0 ? "heat-positive" : "heat-neutral";
 return value >= 70 ? "heat-elite" : value >= 55 ? "heat-positive" : value >= 40 ? "heat-neutral" : "heat-risk";
 };
 const heatCellText = (value: number | null, type: "score" | "gap" = "score") => value === null ? "—" : type === "gap" ? signed(value, 1) : renderMetricValue(value, 0);
 if (!heatRowsWithRatings.length) {
 return <section className="edgeiq-ratings-tab edgeiq-performance-tab edgeiq-product-section"><div className="edgeiq-performance-compact-head"><span>PERFORMANCE</span><strong>EDGEiQ Performance Index</strong><em>Performance Index pending for this race.</em></div><div className="edgeiq-product-empty">Performance Index pending for this race.</div></section>;
 }
 return (
 <section className="edgeiq-ratings-tab edgeiq-performance-tab edgeiq-product-section edgeiq-performance-heatmap-v2">
 <div className="edgeiq-performance-compact-head"><span>PERFORMANCE</span><strong>EDGEiQ Performance Index</strong><em>Expected standard {expectedRaceRating === null ? "—" : renderMetricValue(expectedRaceRating, 1)} / median {fieldMedian === null ? "—" : renderMetricValue(fieldMedian, 1)} / {strength}</em></div>
 <div className="edgeiq-heatmap-legend"><span className="heat-elite">Elite</span><span className="heat-positive">Positive</span><span className="heat-neutral">Neutral</span><span className="heat-risk">Risk</span></div>
 <div className="edgeiq-performance-heatmap-table" role="table" aria-label="EDGEiQ Performance heatmap">
 <div className="edgeiq-performance-heatmap-row head" role="row">{['Horse','Performance Index','Gap','Distance','Condition','Class','Pace','Profile','Confidence'].map((label) => <span key={`performance-heat-head-${label}`}>{label}</span>)}</div>
 {heatRows.map(({ item, heat }) => {
 const performanceIndex = firstNum(heat, ["runner_rating"]);
 const gap = firstNum(heat, ["rating_gap"]);
 const distanceScore = firstNum(heat, ["distance_score"]);
 const conditionScore = firstNum(heat, ["condition_score"]);
 const classScore = firstNum(heat, ["class_score"]);
 const paceScore = factorScoreValue(item, "PACE") ?? factorScoreValue(item, "PCE") ?? firstNum(item.mapEnrichment, ["race_pressure_score_v3", "race_pressure_score_v2"]);
 const profileScore = firstNum(heat, ["overall_heat_score", "connections_score", "campaign_score"]);
 const confidenceScore = confidenceScoreValue(item);
 return <div className="edgeiq-performance-heatmap-row" role="row" key={`performance-tab-${runnerRowKey(item.row)}`}><strong>{horse(item.row)}</strong><span className={heatCellClass(performanceIndex)}>{heatCellText(performanceIndex)}</span><span className={heatCellClass(gap, "gap")}>{heatCellText(gap, "gap")}</span><span className={heatCellClass(distanceScore)}>{heatCellText(distanceScore)}</span><span className={heatCellClass(conditionScore)}>{heatCellText(conditionScore)}</span><span className={heatCellClass(classScore)}>{heatCellText(classScore)}</span><span className={heatCellClass(paceScore)}>{heatCellText(paceScore)}</span><span className={heatCellClass(profileScore)}>{heatCellText(profileScore)}</span><span className={heatCellClass(confidenceScore)}>{heatCellText(confidenceScore)}</span></div>;
 })}
 </div>
 </section>
 );
 })() : null}
'''
    source = replace_between(source, performance_start, performance_end, performance_block + performance_end)

    old_form = re.search(r' return <section className="edgeiq-form-showcase edgeiq-product-section edgeiq-form-showcase-v2">[\s\S]*?</section>;\n \}\)\(\) : null\}', source)
    if not old_form:
        raise RuntimeError("Form block return not found")
    new_form_return = ''' return <section className="edgeiq-form-showcase edgeiq-product-section edgeiq-form-showcase-v2 edgeiq-form-clean-v3"><div className="edgeiq-form-clean-header"><div><span>FORM</span><strong>{horse(selected.row)}</strong><em>No {saddle(selected.row) === 999 ? "-" : saddle(selected.row)} / Barrier {firstText(selected.row, ["barrier", "draw"], "-")}</em></div><div className="edgeiq-form-clean-summary">{[["Current", projected], ["Peak", selectedBestRatingLast5Value], ["AVG5", selectedAVGRatingLast5Value], ["Trend", trendText], ["Expected", expected], ["Price", price]].map(([label, value]) => <article key={`form-clean-${label}`}><span>{label}</span><strong>{typeof value === "number" ? renderMetricValue(value, 1) : String(value || "—")}</strong></article>)}</div></div><div className="edgeiq-form-rating-strip slim">{[["Last", selectedLastStartRatingValue], ["Current", projected], ["AVG5", selectedAVGRatingLast5Value], ["Peak", selectedBestRatingLast5Value]].map(([label, value]) => { const performanceValue = typeof value === "number" ? value : null; const width = performanceValue === null ? 0 : Math.max(4, Math.min(100, (performanceValue / sparkMax) * 100)); return <article key={`form-performance-strip-${label}`}><span>{label}</span><div><i style={{ width: `${width}%`, background: performanceValue !== null && expected !== null && performanceValue >= expected ? "#34d399" : performanceValue !== null && expected !== null && performanceValue <= expected - 5 ? "#f87171" : "#e5e7eb" }} /></div><strong>{performanceValue === null ? "-" : renderMetricValue(performanceValue, 1)}</strong></article>; })}</div><section className="edgeiq-form-last-five edgeiq-form-last-five-wide"><div className="edgeiq-form-table-title">Last Five Runs</div><div className="edgeiq-form-table"><div className="edgeiq-form-table-row head">{['Date','Track','Dist','Class','Going','Bar','Jockey','Pos','Margin','SP','Performance Index','Settled'].map((label) => <span key={`form-main-head-${label}`}>{label}</span>)}</div>{!formRows.length ? <div className="edgeiq-form-table-empty">No detailed performance-history lines available.</div> : formRows.map((run) => { const pos = cleanPosition(run.finishingPosition); return <div key={`form-main-row-${run.key}`} className="edgeiq-form-table-row"><span>{cleanRunText(run.date)}</span><span>{cleanRunText(run.track)}</span><span>{cleanRunText(run.distance)}</span><span>{cleanRunText(run.raceClass)}</span><span>{cleanRunText(run.going)}</span><span>{cleanRunText(run.barrier)}</span><span>{cleanRunText(run.jockey)}</span><span className={posClass(pos)}>{pos}</span><span>{cleanRunText(run.beatenMargin)}</span><span>{cleanRunText(run.sp)}</span><span>{run.rating !== null ? renderMetricValue(run.rating, 1) : "-"}</span><span>{cleanRunText(run.settledPosition)}</span></div>; })}</div></section><p className="edgeiq-form-short-read">{formNarrative}</p></section>;
 })() : null}'''
    source = source[:old_form.start()] + new_form_return + source[old_form.end():]

    TSX.write_text(source, encoding="utf-8")

    css = CSS.read_text(encoding="utf-8")
    addition = r'''

/* EDGEiQ Tab Feature + Layout Audit Fix V1 */
.edgeiq-race-useful .edgeiq-race-simple-hero.compact {
  padding: 18px 20px;
  border-radius: 16px;
}
.edgeiq-race-what-matters {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  border: 1px solid rgba(148,163,184,.16);
  border-radius: 16px;
  padding: 14px;
  background: rgba(5,12,22,.55);
}
.edgeiq-race-what-matters > span {
  grid-column: 1 / -1;
  color: #9ca3af;
  font-size: 10px;
  font-weight: 1000;
  letter-spacing: .16em;
  text-transform: uppercase;
}
.edgeiq-race-what-matters article {
  min-width: 0;
  border: 1px solid rgba(148,163,184,.12);
  border-radius: 12px;
  padding: 10px;
  background: rgba(15,23,42,.55);
}
.edgeiq-race-what-matters strong {
  display: block;
  color: #fff;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: .08em;
}
.edgeiq-race-what-matters em {
  display: block;
  margin-top: 6px;
  color: #d1d5db;
  font-style: normal;
  font-size: 12px;
  line-height: 1.35;
}
.edgeiq-field-compact-header,
.edgeiq-performance-compact-head,
.edgeiq-form-clean-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
  border-bottom: 1px solid rgba(148,163,184,.14);
  padding-bottom: 12px;
}
.edgeiq-field-compact-header span,
.edgeiq-performance-compact-head span,
.edgeiq-form-clean-header span {
  display: block;
  color: #9ca3af;
  font-size: 10px;
  font-weight: 1000;
  letter-spacing: .18em;
  text-transform: uppercase;
}
.edgeiq-field-compact-header strong,
.edgeiq-performance-compact-head strong,
.edgeiq-form-clean-header strong {
  display: block;
  color: #fff;
  font-size: 18px;
  line-height: 1.15;
}
.edgeiq-field-compact-header em,
.edgeiq-performance-compact-head em,
.edgeiq-form-clean-header em {
  color: #a8b3c9;
  font-style: normal;
  font-size: 12px;
  font-weight: 800;
}
.edgeiq-field-quick-profile {
  min-width: 1080px;
  display: grid;
  grid-template-columns: repeat(8, minmax(0, 1fr));
  gap: 8px;
  padding: 10px;
  border-bottom: 1px solid rgba(148,163,184,.14);
  background: linear-gradient(90deg, rgba(8,47,73,.30), rgba(15,23,42,.66));
}
.edgeiq-field-quick-profile article {
  min-width: 0;
  border: 1px solid rgba(148,163,184,.14);
  border-radius: 10px;
  padding: 8px;
  background: rgba(3,7,18,.42);
}
.edgeiq-field-quick-profile span {
  display: block;
  color: #9ca3af;
  font-size: 9px;
  font-weight: 1000;
  letter-spacing: .10em;
  text-transform: uppercase;
}
.edgeiq-field-quick-profile strong {
  display: block;
  margin-top: 4px;
  color: #fff;
  font-size: 11px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.edgeiq-performance-heatmap-v2 {
  display: grid;
  gap: 12px;
}
.edgeiq-heatmap-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.edgeiq-heatmap-legend span,
.edgeiq-performance-heatmap-row span:not(:first-child) {
  border-radius: 9px;
}
.edgeiq-heatmap-legend span {
  padding: 6px 10px;
  font-size: 10px;
  font-weight: 1000;
  text-transform: uppercase;
  letter-spacing: .08em;
}
.edgeiq-performance-heatmap-table {
  overflow: auto;
  border: 1px solid rgba(148,163,184,.18);
  border-radius: 16px;
  background: rgba(15,23,42,.58);
}
.edgeiq-performance-heatmap-row {
  min-width: 1040px;
  display: grid;
  grid-template-columns: minmax(210px,1.4fr) repeat(8, minmax(92px, 1fr));
  gap: 0;
  border-bottom: 1px solid rgba(148,163,184,.10);
}
.edgeiq-performance-heatmap-row > span,
.edgeiq-performance-heatmap-row > strong {
  padding: 10px 11px;
  color: #d1d5db;
  font-size: 12px;
  border-right: 1px solid rgba(148,163,184,.08);
}
.edgeiq-performance-heatmap-row > strong {
  color: #fff;
}
.edgeiq-performance-heatmap-row.head {
  background: rgba(3,7,18,.55);
}
.edgeiq-performance-heatmap-row.head span {
  color: #9ca3af;
  font-size: 10px;
  font-weight: 1000;
  letter-spacing: .10em;
  text-transform: uppercase;
}
.heat-elite { background: linear-gradient(135deg, rgba(52,211,153,.30), rgba(5,12,22,.40)); color: #dcfce7 !important; }
.heat-positive { background: linear-gradient(135deg, rgba(52,211,153,.16), rgba(5,12,22,.42)); color: #e5e7eb !important; }
.heat-neutral { background: rgba(148,163,184,.10); color: #e5e7eb !important; }
.heat-risk { background: linear-gradient(135deg, rgba(248,113,113,.22), rgba(5,12,22,.42)); color: #fee2e2 !important; }
.edgeiq-form-clean-v3 .edgeiq-tab-heading,
.edgeiq-form-clean-v3 .edgeiq-form-showcase-hero {
  display: none;
}
.edgeiq-form-clean-summary {
  display: grid;
  grid-template-columns: repeat(6, minmax(82px, 1fr));
  gap: 8px;
  min-width: min(680px, 100%);
}
.edgeiq-form-clean-summary article {
  border: 1px solid rgba(148,163,184,.14);
  border-radius: 10px;
  padding: 8px;
  background: rgba(15,23,42,.45);
}
.edgeiq-form-clean-summary strong {
  font-size: 13px;
}
.edgeiq-form-rating-strip.slim article {
  padding: 9px;
  border-radius: 12px;
}
.edgeiq-map-summary-strip {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}
.edgeiq-map-summary-strip article {
  min-width: 0;
  border: 1px solid rgba(148,163,184,.14);
  border-radius: 12px;
  padding: 9px 10px;
  background: rgba(5,12,22,.58);
}
.edgeiq-map-summary-strip span {
  display: block;
  color: #9ca3af;
  font-size: 9px;
  font-weight: 1000;
  letter-spacing: .10em;
  text-transform: uppercase;
}
.edgeiq-map-summary-strip strong {
  display: block;
  margin-top: 4px;
  color: #fff;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
@media (max-width: 1000px) {
  .edgeiq-race-what-matters,
  .edgeiq-map-summary-strip,
  .edgeiq-form-clean-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .edgeiq-field-quick-profile {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
'''
    if "EDGEiQ Tab Feature + Layout Audit Fix V1" not in css:
        CSS.write_text(css + addition, encoding="utf-8")


if __name__ == "__main__":
    main()
