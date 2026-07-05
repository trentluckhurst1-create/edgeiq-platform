type Row = Record<string, any>;

type RaceLabWorkspaceProps = {
  selected: any;
  selectedConnectionSource: Row | null | undefined;
  firstText: any;
  text: any;
  num: any;
  pct: any;
  money: any;
  renderMetricValue: any;
  header: Row;
  track: any;
  distance: any;
  raceClass: any;
  selectedConnectionNarrative: string;
  labModule: string;
  setLabModule: any;
  labPriceEngineRows: Row[];
  selectedTrack: string;
  selectedRaceNo: any;
  selectedRaceDate: any;
  cleanTrack: any;
  cleanHorse: any;
  integer: any;
  firstNum: any;
  priceEngineAdjustments: Record<string, number>;
  setPriceEngineAdjustments: any;
};

export function RaceLabWorkspace({
  selected,
  selectedConnectionSource,
  firstText,
  text,
  num,
  pct,
  money,
  renderMetricValue,
  header,
  track,
  distance,
  raceClass,
  selectedConnectionNarrative,
  labModule,
  setLabModule,
  labPriceEngineRows,
  selectedTrack,
  selectedRaceNo,
  selectedRaceDate,
  cleanTrack,
  cleanHorse,
  integer,
  firstNum,
  priceEngineAdjustments,
  setPriceEngineAdjustments,
}: RaceLabWorkspaceProps) {
const source: Row = selected?.nexusContextual || selectedConnectionSource || {};
 const trainerName = firstText(source, ["trainer"], selected ? firstText(selected.row, ["trainer", "trainer_name"], "-") : "-");
 const jockeyName = firstText(source, ["jockey"], selected ? firstText(selected.row, ["jockey", "jockey_name", "rider"], "-") : "-");
 const cleanNexusValue = (value: unknown) => { const raw = text(value).trim(); return raw && raw !== "-" ? raw : "ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â"; };
 const cleanNexusPct = (value: unknown) => {
 const raw = text(value);
 const valueNum = num(raw);
 if (valueNum === null) return cleanNexusValue(raw);
 return pct(valueNum);
 };
 const cleanNexusScore = (value: unknown, digits = 1) => {
 const valueNum = num(value);
 return valueNum === null ? cleanNexusValue(value) : valueNum.toFixed(digits);
 };
 const calibratedScore = cleanNexusScore(firstText(source, ["nexus_context_score_calibrated"], ""));
 const calibratedBand = cleanNexusValue(firstText(source, ["nexus_context_band_calibrated"], ""));
 const percentile = cleanNexusPct(firstText(source, ["nexus_context_percentile"], ""));
 const raceRank = cleanNexusValue(firstText(source, ["nexus_context_rank_in_race"], ""));
 const fieldRank = cleanNexusValue(firstText(source, ["nexus_context_field_rank"], ""));
 const rawContext = cleanNexusValue(firstText(source, ["raw_nexus_context_score", "nexus_context_score"], ""));
 const rawBand = cleanNexusValue(firstText(source, ["raw_nexus_context_band", "nexus_context_band"], ""));
 const nexusPanels = [
 { title: "Trainer", name: trainerName, metrics: [["25 win", cleanNexusPct(source.trainer_recent_25_win_pct)], ["50 win", cleanNexusPct(source.trainer_recent_50_win_pct)], ["100 win", cleanNexusPct(source.trainer_recent_100_win_pct)], ["Best context", cleanNexusValue(source.trainer_best_context)]] },
 { title: "Jockey", name: jockeyName, metrics: [["25 win", cleanNexusPct(source.jockey_recent_25_win_pct)], ["50 win", cleanNexusPct(source.jockey_recent_50_win_pct)], ["100 win", cleanNexusPct(source.jockey_recent_100_win_pct)], ["Best context", cleanNexusValue(source.jockey_best_context)]] },
 { title: "Partnership", name: cleanNexusValue(source.partnership_band), metrics: [["Score", cleanNexusScore(source.partnership_score)], ["Starts", cleanNexusValue(source.partnership_starts)], ["Wins", cleanNexusValue(source.partnership_wins)], ["ROI / A/E", `${cleanNexusValue(source.partnership_roi)} / ${cleanNexusValue(source.partnership_ae)}`]] },
 { title: "Style Fit", name: cleanNexusValue(source.style_alignment_band), metrics: [["Score", cleanNexusScore(source.style_alignment_score)], ["Horse style", cleanNexusValue(source.horse_run_style)], ["Trainer style", cleanNexusValue(source.trainer_best_style)], ["Jockey style", cleanNexusValue(source.jockey_best_style)]] },
 ];
 const positives = ["top_positive_1", "top_positive_2", "top_positive_3"].map((key) => cleanNexusValue(source[key])).filter((value) => value !== "ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â");
 const risks = ["top_risk_1", "top_risk_2", "top_risk_3"].map((key) => cleanNexusValue(source[key])).filter((value) => value !== "ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â");
 const narrative = cleanNexusValue(firstText(source, ["nexus_summary", "connection_narrative"], selectedConnectionNarrative || "")).replace(/\bNexus\b/gi, "EDGEiQ Insight");
 const labModules = ["TRAINERS", "JOCKEYS", "PARTNERSHIPS", "TRACKS", "DISTANCES", "BARRIERS", "RUN STYLES", "FIRST UP", "SECOND UP", "CLASS", "PRICE ENGINE"];
 const activeLabPanel = nexusPanels.find((panel) => panel.title.toUpperCase() === labModule.replace(/S$/, "")) || nexusPanels[0];
 const labHeroSubject = labModule === "PRICE ENGINE" ? "Price Engine Research" : labModule === "JOCKEYS" ? jockeyName : labModule === "PARTNERSHIPS" ? cleanNexusValue(source.partnership_band) : labModule === "RUN STYLES" ? cleanNexusValue(source.horse_run_style) : labModule === "TRACKS" ? track(header) : labModule === "DISTANCES" ? distance(header) : labModule === "CLASS" ? raceClass(header) : trainerName;
 const labRaceNoToken = text(integer(selectedRaceNo) ?? selectedRaceNo);
 const labSelectedDate = text(selectedRaceDate);
 const labPriceMatches = labPriceEngineRows.filter((row) => cleanTrack(row.track) === selectedTrack && text(integer(row.race_no) ?? row.race_no) === labRaceNoToken && (!labSelectedDate || text(row.race_date) === labSelectedDate));
 const fallbackPriceRaceKey = labPriceEngineRows[0] ? `${text(labPriceEngineRows[0].race_date)}|${cleanTrack(labPriceEngineRows[0].track)}|${text(integer(labPriceEngineRows[0].race_no) ?? labPriceEngineRows[0].race_no)}` : "";
 const fallbackPriceRows = fallbackPriceRaceKey ? labPriceEngineRows.filter((row) => `${text(row.race_date)}|${cleanTrack(row.track)}|${text(integer(row.race_no) ?? row.race_no)}` === fallbackPriceRaceKey) : [];
 const labPriceRows = (labPriceMatches.length ? labPriceMatches : fallbackPriceRows).slice(0, 16);
 const labPriceKey = (row: Row) => `${text(row.race_date)}|${cleanTrack(row.track)}|${text(integer(row.race_no) ?? row.race_no)}|${cleanHorse(row.runner)}`;
 const labPriceRawRows = labPriceRows.map((row) => {
 const key = labPriceKey(row);
 const adjustment = priceEngineAdjustments[key] ?? 0;
 const baseRating = firstNum(row, ["base_rating", "editable_rating"]);
 const baseProbability = firstNum(row, ["base_probability"]) ?? 0;
 const pointToLengths = firstNum(row, ["rating_point_to_lengths"]) ?? 0.1382;
 const rawProbability = Math.max(0.0001, baseProbability * Math.exp((adjustment * pointToLengths) / 2));
 return { row, key, adjustment, baseRating, adjustedRating: baseRating === null ? null : baseRating + adjustment, baseProbability, rawProbability };
 });
 const labPriceTotal = labPriceRawRows.reduce((sum, entry) => sum + entry.rawProbability, 0);
 const labPriceDisplayRows = labPriceRawRows.map((entry) => {
 const adjustedProbability = labPriceTotal > 0 ? entry.rawProbability / labPriceTotal : 0;
 return { ...entry, adjustedProbability, adjustedPrice: adjustedProbability > 0 ? 1 / adjustedProbability : null };
 });
 const labPriceAverageConfidence = labPriceDisplayRows.length ? labPriceDisplayRows.reduce((sum, entry) => sum + (firstNum(entry.row, ["data_confidence"]) ?? 0), 0) / labPriceDisplayRows.length : null;
 return <section className="edgeiq-connections-tab edgeiq-lab-tab edgeiq-product-section edgeiq-product-v4-panel edgeiq-lab-v1-lock"><div className="edgeiq-tab-heading edgeiq-product-v4-section-title"><span>LAB</span><strong>Racing Research Laboratory</strong><em>Research, profile, compare and discover.</em></div><div className="edgeiq-lab-v1-layout"><aside className="edgeiq-lab-v1-modules"><strong>Research Modules</strong>{labModules.map((module) => <button type="button" className={labModule === module ? "is-active" : ""} key={`lab-module-${module}`} onClick={() => setLabModule(module)}>{module}</button>)}</aside><section className="edgeiq-lab-v1-main"><div className="edgeiq-lab-v1-subject edgeiq-lab-v1-hero"><span>{labModule}</span><strong>{labHeroSubject}</strong><em>{track(header)} / {distance(header)} / {raceClass(header)}</em></div>{labModule === "PRICE ENGINE" ? <><div className="edgeiq-lab-price-research-banner"><span>Research only</span><strong>Editable rating points do not alter production prices.</strong><em>{labPriceMatches.length ? "Current race feed" : "Fallback research race feed"} / Confidence {labPriceAverageConfidence === null ? "ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â" : pct(labPriceAverageConfidence * 100)}</em></div><div className="edgeiq-lab-price-table edgeiq-product-v4-table" role="table" aria-label="Price Engine research table"><div className="edgeiq-lab-price-row head" role="row">{['Runner','Base','Adj Pts','Adj Rating','Base Prob','Adj Prob','Base Price','Adj Price','Status'].map((label) => <span key={`lab-price-head-${label}`}>{label}</span>)}</div>{labPriceDisplayRows.length ? labPriceDisplayRows.map((entry) => <div className="edgeiq-lab-price-row" role="row" key={`lab-price-row-${entry.key}`}><strong>{firstText(entry.row, ["runner"], "ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â")}</strong><span>{entry.baseRating === null ? "ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â" : renderMetricValue(entry.baseRating, 2)}</span><input aria-label={`Adjust rating points for ${firstText(entry.row, ["runner"], "runner")}`} type="number" step="0.5" value={entry.adjustment} onChange={(event) => { const next = Number(event.currentTarget.value); setPriceEngineAdjustments((current) => ({ ...current, [entry.key]: Number.isFinite(next) ? next : 0 })); }} /><span>{entry.adjustedRating === null ? "ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â" : renderMetricValue(entry.adjustedRating, 2)}</span><span>{pct(entry.baseProbability * 100)}</span><span>{pct(entry.adjustedProbability * 100)}</span><span>{money(firstNum(entry.row, ["base_price"]))}</span><span>{money(entry.adjustedPrice)}</span><span>{firstText(entry.row, ["pricing_status"], "RESEARCH_ONLY")}</span></div>) : <div className="edgeiq-lab-price-empty">Price Engine research feed is not loaded for this race.</div>}</div></> : <><div className="edgeiq-lab-v1-metrics">{(activeLabPanel ? [activeLabPanel, ...nexusPanels.filter((panel) => panel.title !== activeLabPanel.title)] : nexusPanels).slice(0, 4).map((panel) => <article key={`lab-metric-${panel.title}`}><span>{panel.title}</span><strong>{panel.metrics[0]?.[1] || "ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â"}</strong><em>{cleanNexusValue(panel.name)}</em></article>)}</div><div className="edgeiq-lab-v1-table edgeiq-product-v4-table" role="table" aria-label="Lab research leaderboard"><div className="edgeiq-lab-v1-row head" role="row">{['Research Area','Subject','Metric 1','Metric 2','Metric 3','Context'].map((label) => <span key={`lab-research-head-${label}`}>{label}</span>)}</div>{nexusPanels.map((panel) => <div className="edgeiq-lab-v1-row" role="row" key={`lab-research-${panel.title}`}><strong>{panel.title}</strong><span>{cleanNexusValue(panel.name)}</span>{panel.metrics.slice(0, 3).map(([label, value]) => <span key={`lab-research-${panel.title}-${label}`}>{label}: {cleanNexusValue(value)}</span>)}<span>{panel.metrics[3] ? `${panel.metrics[3][0]}: ${cleanNexusValue(panel.metrics[3][1])}` : "ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â"}</span></div>)}</div></>}</section><aside className="edgeiq-lab-v1-insight"><span>EDGEiQ Insight</span><p>{labModule === "PRICE ENGINE" ? "Price Engine research lets rating-point assumptions be tested against adjusted probability and research price without writing to production pricing feeds." : narrative}</p><strong>{labModule === "PRICE ENGINE" ? "Research Guardrail" : "Saved Studies"}</strong><em>{labModule === "PRICE ENGINE" ? "Local adjustments reset with the browser session and remain research-only." : positives[0] || risks[0] || "Research context pending."}</em></aside></div></section>;
}
