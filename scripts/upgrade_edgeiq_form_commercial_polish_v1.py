from pathlib import Path

path = Path('src/components/RaceIntelligenceScreen.tsx')
checkpoint = Path('src/components/RaceIntelligenceScreen_CHECKPOINT_FORM_COMMERCIAL_POLISH_V1_20260628.tsx')
text = path.read_text(encoding='utf-8')
checkpoint.write_text(text, encoding='utf-8')
start = text.index('      {intelMode === "FORM" ? (')
end = text.index('      {intelMode === "RUNNERS" ? (', start)
block = text[start:end]

# Add customer-facing helper functions after selected trend tone.
needle = '        const selectedTrendTone = selectedTrendRead.includes("IMPROV") || selectedTrendRead.includes("PEAK") ? "#34d399" : selectedTrendRead.includes("REGRESS") ? "#f87171" : selectedTrendRead.includes("CONTEXT") ? "#94a3b8" : selectedTrendRead.includes("PARTIAL") ? "#7dd3fc" : selectedTrendRead.includes("LIMITED") ? "#f5c451" : "#7dd3fc";\n'
insert = '''        const selectedFormScoreBand = selectedFormScore === null ? "LIMITED" : selectedFormScore >= 85 ? "ELITE" : selectedFormScore >= 75 ? "STRONG" : selectedFormScore >= 60 ? "AVERAGE" : selectedFormScore >= 45 ? "RISK" : "POOR";
        const customerSourceLabel = (value: string) => {
          const raw = String(value || "").toUpperCase();
          if (!raw) return "Not Enough Evidence";
          const labels = new Set<string>();
          raw.split(/[;|]/).map((part) => part.trim()).filter(Boolean).forEach((part) => {
            if (part.includes("OTHER_RATING_SOURCE") || part.includes("RATING_DATE_MATCH")) labels.add("Recovered Rating");
            else if (part.includes("RESULTS_WAREHOUSE")) labels.add("Results Warehouse");
            else if (part.includes("RUNNER_BOARD_SNAPSHOT")) labels.add("Board Snapshot");
            else if (part.includes("REPLAY_ARCHIVE")) labels.add("Replay Archive");
            else if (part.includes("V6_1_RESEARCH_ARCHIVE")) labels.add("V6.1 Archive");
            else if (part.includes("INTELLIGENCE_SNAPSHOT")) labels.add("Intelligence Snapshot");
            else if (part.includes("HISTORY_MASTER") || part.includes("HISTORICAL_RATING_WAREHOUSE")) labels.add("History Master");
            else if (part.includes("HISTORICAL_FORM_TABLE")) labels.add("Historical Form");
            else if (part.includes("V6_1_RESEARCH_HISTORY")) labels.add("V6.1 Rated History");
            else if (part.includes("PARTIAL")) labels.add("Partial Evidence");
            else if (part.includes("CONTEXT")) labels.add("Context Only");
            else if (part.includes("RATED_HISTORY")) labels.add("Historical Rating");
            else if (part.includes("RESULT_HISTORY")) labels.add("Results History");
          });
          return Array.from(labels).slice(0, 2).join(" + ") || "Historical Evidence";
        };
        const marginDisplay = (finish: string, margin: string) => {
          if (!margin) return "--";
          const clean = margin.endsWith("L") ? margin : `${margin}L`;
          return String(finish || "").replace(/[^0-9]/g, "") === "1" ? `Won by ${clean}` : `Beaten ${clean}`;
        };
        const setupProfileText = (label: string, value: string, score: number | null, fallbackDetail: string) => {
          const base = value && value !== "--" ? value : fallbackDetail;
          const scoreText = score !== null ? `score ${renderMetricValue(score, 0)}` : "Not Enough Evidence";
          const band = score === null ? "Partial Evidence" : score >= 75 ? "Strong" : score >= 60 ? "Neutral" : score >= 45 ? "Watch" : "Risk";
          return `${base} | ${scoreText} | ${band}`;
        };
'''
if insert not in block:
    block = block.replace(needle, needle + insert)

# Improve verdict copy.
old = '''        const selectedFormVerdict = !selected
          ? "Select a runner to inspect form."
          : selectedIsContextOnly
            ? "Context only; no detailed rated-history lines available."
            : selectedFormStatus.includes("PARTIAL")
              ? `Partial historical profile; use with caution. ${selectedTrendRead.includes("REGRESS") ? "Recent ratings are regressing." : selectedTrendRead.includes("IMPROV") ? "Recent ratings are improving." : "Evidence is useful but incomplete."}`
              : selectedFormScore !== null && selectedFormScore >= 80
                ? `Rated history loaded; profile can be assessed from recent figures. ${selectedTrendRead.includes("REGRESS") ? "Trend is regressing." : selectedTrendRead.includes("IMPROV") ? "Trend is improving." : "Trend is holding."}`
                : "Rated history loaded; profile can be assessed from recent figures.";'''
new = '''        const selectedFormVerdict = !selected
          ? "Select a runner to inspect form."
          : selectedIsContextOnly
            ? "Context only. EDGEiQ has runner context, but no detailed rated-history lines are available. Do not overstate the form profile."
            : selectedFormStatus.includes("PARTIAL")
              ? `Partial rated-history profile. There is enough evidence to assess recent form, but some historical fields are missing. Treat the profile with moderate caution. ${selectedTrendRead.includes("REGRESS") ? "Recent ratings are regressing." : selectedTrendRead.includes("IMPROV") ? "Recent ratings are improving." : "The recent pattern is holding."}`
              : `Rated form history loaded. Recent figures are strong enough to assess the profile with confidence. The peak rating gives a clear reference point against today's setup. ${selectedTrendRead.includes("REGRESS") ? "Recent ratings are regressing." : selectedTrendRead.includes("IMPROV") ? "Recent ratings are improving." : "The recent pattern is holding."}`;'''
block = block.replace(old, new)

# Source label and raw run source transformation.
block = block.replace('const source = firstText(selectedRunnerForm, [`${prefix}source`, `${prefix}reason`, `${prefix}performance_label`], "");', 'const rawSource = firstText(selectedRunnerForm, [`${prefix}source`, `${prefix}reason`, `${prefix}performance_label`], "");\n          const source = customerSourceLabel(rawSource);')

# Populate lower setup profile cards from fields/scores.
block = block.replace('const distanceProfile = profileValue(selected?.row || {}, ["distance_profile", "distance_read", "distance_truth_status", "distance_profile_status"]);\n        const conditionProfile = profileValue(selected?.row || {}, ["condition_profile", "condition_read", "condition_truth_status", "condition_profile_status"]);\n        const classProfile = profileValue(selected?.row || {}, ["class_profile", "class_read", "class_truth_status", "class_profile_status"]);', 'const distanceProfileRaw = profileValue(selected?.row || {}, ["distance_profile", "distance_read", "distance_truth_status", "distance_profile_status"]);\n        const conditionProfileRaw = profileValue(selected?.row || {}, ["condition_profile", "condition_read", "condition_truth_status", "condition_profile_status"]);\n        const classProfileRaw = profileValue(selected?.row || {}, ["class_profile", "class_read", "class_truth_status", "class_profile_status"]);\n        const distanceProfile = setupProfileText("Distance", distanceProfileRaw || firstText(selected.row, ["distance", "race_distance", "distance_m", "race_distance_m"], ""), firstNum(selected.row, ["distance_fit_score", "score_distance", "edgeiq_score_distance_v3", "distance_score"]), "Current trip");\n        const conditionProfile = setupProfileText("Condition", conditionProfileRaw || firstText(selected.row, ["condition", "track_condition", "official_condition", "edgeiq_condition"], ""), firstNum(selected.row, ["condition_fit_score", "score_condition", "edgeiq_score_condition_v3", "condition_score"]), "Current going");\n        const classProfile = setupProfileText("Class", classProfileRaw || firstText(selected.row, ["race_class", "class", "class_name"], ""), firstNum(selected.row, ["class_fit_score", "score_class", "edgeiq_score_class_v3", "class_score"]), "Current class");')

# Left runner table header and row layout.
block = block.replace('gridTemplateColumns: "38px minmax(0,1fr) 64px 108px"', 'gridTemplateColumns: "34px minmax(0,1fr) 58px"')
block = block.replace('<span>#</span><span>Horse</span><span style={{ textAlign: "right" }}>Form</span><span style={{ textAlign: "right" }}>Trend</span>', '<span>#</span><span>Horse</span><span style={{ textAlign: "right" }}>Score</span>')
block = block.replace('gridTemplateColumns: "38px minmax(0,1fr) 64px 108px"', 'gridTemplateColumns: "34px minmax(0,1fr) 58px"')
old_row = '''                          <span style={{ minWidth: 0, display: "grid", gap: 2 }}>
                            <strong style={{ color: "#f8fafc", fontSize: 11.5, fontWeight: 1000, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{horse(item.row)}</strong>
                            <span style={{ color: "#64748b", fontSize: 9.5, fontWeight: 850, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{itemQuality || "DATA QUALITY NOT LOADED"}</span>
                          </span>
                          <strong style={{ color: formRatingTone(itemScore), fontSize: 12, textAlign: "right" }}>{itemScore !== null ? renderMetricValue(itemScore, 0) : "--"}</strong>
                          <span style={{ color: itemTrend.includes("IMPROV") || itemTrend.includes("PEAK") ? "#34d399" : itemTrend.includes("REGRESS") ? "#f87171" : itemTrend.includes("CONTEXT") ? "#94a3b8" : "#f5c451", fontSize: 9.5, fontWeight: 950, textAlign: "right", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{itemTrend}</span>'''
new_row = '''                          <span style={{ minWidth: 0, display: "grid", gap: 3 }}>
                            <strong style={{ color: "#f8fafc", fontSize: 11.5, fontWeight: 1000, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{horse(item.row)}</strong>
                            <span style={{ display: "flex", gap: 6, alignItems: "center", minWidth: 0 }}>
                              <em style={{ color: "#94a3b8", fontSize: 9.5, fontStyle: "normal", fontWeight: 850, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{itemQuality || "Partial Evidence"}</em>
                              <em style={{ color: itemTrend.includes("IMPROV") || itemTrend.includes("PEAK") ? "#34d399" : itemTrend.includes("REGRESS") ? "#f87171" : itemTrend.includes("CONTEXT") ? "#94a3b8" : "#f5c451", fontSize: 9.5, fontStyle: "normal", fontWeight: 950, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{itemTrend}</em>
                            </span>
                          </span>
                          <span style={{ justifySelf: "end", border: `1px solid ${formRatingTone(itemScore)}66`, borderRadius: 999, padding: "3px 7px", minWidth: 38, textAlign: "center", color: formRatingTone(itemScore), background: `${formRatingTone(itemScore)}18`, fontSize: 11, fontWeight: 1000 }}>{itemScore !== null ? renderMetricValue(itemScore, 0) : "--"}</span>'''
block = block.replace(old_row, new_row)

# Header hierarchy: replace raw grid info line with single readable detail line.
old_header = '''                        <div style={{ display: "grid", gridTemplateColumns: "repeat(6, minmax(90px,1fr))", gap: 8, color: "#cbd5e1", fontSize: 11, fontWeight: 850 }}>
                          <span>No {saddle(selected.row) === 999 ? "--" : saddle(selected.row)}</span>
                          <span>Barrier {firstText(selected.row, ["barrier", "barrier_no", "draw"], "--")}</span>
                          <span>{firstText(selected.row, ["trainer", "trainer_name"], "Trainer not loaded")}</span>
                          <span>{firstText(selected.row, ["jockey", "jockey_name"], "Jockey not loaded")}</span>
                          <span>{firstText(selected.row, ["weight", "weight_carried", "allocated_weight"], "Weight --")}</span>
                          <span>{firstText(selected.row, ["age_sex", "age", "sex"], "Age/sex --")}</span>
                        </div>'''
new_header = '''                        <div style={{ color: "#cbd5e1", fontSize: 12, fontWeight: 850, lineHeight: 1.45 }}>
                          No {saddle(selected.row) === 999 ? "--" : saddle(selected.row)} | Barrier {firstText(selected.row, ["barrier", "barrier_no", "draw"], "--")} | Trainer {firstText(selected.row, ["trainer", "trainer_name"], "not loaded")} | Jockey {firstText(selected.row, ["jockey", "jockey_name"], "not loaded")} | {firstText(selected.row, ["weight", "weight_carried", "allocated_weight"], "weight --")} | {firstText(selected.row, ["age_sex", "age", "sex"], "age/sex --")}
                        </div>'''
block = block.replace(old_header, new_header)

# Score card label/band.
block = block.replace('<span style={{ color: "#94a3b8", fontSize: 10, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".08em" }}>Form</span>', '<span style={{ color: "#94a3b8", fontSize: 10, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".08em" }}>FORM SCORE</span>')
block = block.replace('<em style={{ color: selectedTrendTone, fontSize: 10.5, fontStyle: "normal", fontWeight: 950 }}>{selectedTrendRead}</em>', '<em style={{ color: selectedTrendTone, fontSize: 10.5, fontStyle: "normal", fontWeight: 950 }}>{selectedFormScoreBand}</em>')

# Last five columns/comment label and margin/source display.
block = block.replace("'SOURCE / COMMENT'", "'COMMENT'")
block = block.replace('>{run.margin || "--"}</span>', '>{marginDisplay(run.pos, run.margin)}</span>')
block = block.replace('>{run.source || "not loaded"}</span>', '>{run.source || "Not Enough Evidence"}</span>')

# Lower profile card copy.
block = block.replace('entry.value || "profile source not loaded"', 'entry.value || "Not Enough Evidence"')

# Verdict missing copy.
block = block.replace('` Missing source detail: ${missingDetail}.`', '` Some setup fields are not loaded from source: ${missingDetail}.`')

text = text[:start] + block + text[end:]
path.write_text(text, encoding='utf-8')
print('FORM commercial polish V1 applied')
print(f'checkpoint={checkpoint}')
