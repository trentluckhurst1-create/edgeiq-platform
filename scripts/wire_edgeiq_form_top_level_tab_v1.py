from pathlib import Path

path = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard\src\components\RaceIntelligenceScreen.tsx")
backup = path.with_name("RaceIntelligenceScreen_CHECKPOINT_FORM_TOP_LEVEL_TAB_20260628.tsx")
backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

text = path.read_text(encoding="utf-8")

replacements = {
    'runnerForm: "/data/edgeiq_runner_form_engine_current.csv",':
    'runnerForm: "/data/edgeiq_runner_form_engine_current.csv",\n  formEnrichment: "/data/edgeiq_form_enrichment_feed_v2.csv",',

    'commandEnrichment?: Row;\n  mapEnrichment?: Row;':
    'commandEnrichment?: Row;\n  mapEnrichment?: Row;\n  formEnrichment?: Row;',

    'type IntelMode = "COMMAND" | "MAP" | "RUNNERS" | "FACTORS" | "ADVANCED";':
    'type IntelMode = "COMMAND" | "MAP" | "FORM" | "RUNNERS" | "FACTORS" | "ADVANCED";',

    'const [commandEnrichmentRows, setCommandEnrichmentRows] = useState<Row[]>([]);':
    'const [commandEnrichmentRows, setCommandEnrichmentRows] = useState<Row[]>([]);\n  const [formEnrichmentRows, setFormEnrichmentRows] = useState<Row[]>([]);',

    'chaosIndex, opportunityScore, commandEnrichment] = await Promise.all([':
    'chaosIndex, opportunityScore, commandEnrichment, formEnrichment] = await Promise.all([',

    'loadCsv(FILES.commandEnrichment),\n      ]);':
    'loadCsv(FILES.commandEnrichment),\n        loadCsv(FILES.formEnrichment),\n      ]);',

    'setCommandEnrichmentRows(commandEnrichment);':
    'setCommandEnrichmentRows(commandEnrichment);\n      setFormEnrichmentRows(formEnrichment);',

    'const mapEnrichment = findSidecarByRaceHorse(mapEnrichmentRows, row);':
    'const mapEnrichment = findSidecarByRaceHorse(mapEnrichmentRows, row);\n      const formEnrichment = findSidecarByRaceHorse(formEnrichmentRows, row);',

    'hiddenGem, commandEnrichment, mapEnrichment, factorRows };':
    'hiddenGem, commandEnrichment, mapEnrichment, formEnrichment, factorRows };',

    'hiddenGemRows, commandEnrichmentRows, mapEnrichmentRows]);':
    'hiddenGemRows, commandEnrichmentRows, mapEnrichmentRows, formEnrichmentRows]);',

    'const selectedRunnerForm = selected?.formIntelligence || selected?.runnerForm;':
    'const selectedRunnerForm = selected?.formEnrichment || selected?.formIntelligence || selected?.runnerForm;',

    '{ mode: "MAP", label: "MAP", hint: "How the race is likely to be run" },\n    { mode: "RUNNERS", label: "RUNNERS", hint: "Compare ratings and drill into one runner" },':
    '{ mode: "MAP", label: "MAP", hint: "How the race is likely to be run" },\n    { mode: "FORM", label: "FORM", hint: "Full form, recent ratings and last-start evidence" },\n    { mode: "RUNNERS", label: "RUNNERS", hint: "Compare ratings and drill into one runner" },',
}

for old, new in replacements.items():
    if old not in text:
        print(f"[WARN] pattern not found: {old[:80]}")
    text = text.replace(old, new)

insert_marker = '      {intelMode === "RUNNERS" ? ('
form_block = r'''
      {intelMode === "FORM" ? (
        <section style={workspaceSectionStyle}>
          <div style={titleStyle}>
            <span>FORM COMMAND</span>
            <em>Last-start evidence, rating movement and recent form for the selected runner</em>
          </div>

          {selected ? (
            <>
              <div style={summaryGridStyle}>
                {[
                  { label: "Runner", value: horse(selected.row), tone: "#f8fafc" },
                  { label: "Form Status", value: firstText(selectedRunnerForm, ["form_truth_status"], "--").replace(/_/g, " ").toUpperCase(), tone: firstText(selectedRunnerForm, ["form_truth_status"], "").includes("OK") ? "#34d399" : "#f5c451" },
                  { label: "Signal", value: firstText(selectedRunnerForm, ["form_signal"], "--").replace(/_/g, " ").toUpperCase(), tone: "#7dd3fc" },
                  { label: "Trend", value: firstText(selectedRunnerForm, ["form_trend"], "--").replace(/_/g, " ").toUpperCase(), tone: cellTone(firstText(selectedRunnerForm, ["form_trend"], "--")) },
                  { label: "Starts", value: firstText(selectedRunnerForm, ["form_history_starts"], "--"), tone: "#cbd5e1" },
                  { label: "Last Rating", value: renderMetricValue(firstNum(selectedRunnerForm, ["form_last_start_rating"]), 1), tone: "#f5c451" },
                  { label: "Avg L5", value: renderMetricValue(firstNum(selectedRunnerForm, ["form_avg_rating_last5"]), 1), tone: "#7dd3fc" },
                  { label: "Peak L5", value: renderMetricValue(firstNum(selectedRunnerForm, ["form_peak_rating_last5"]), 1), tone: "#34d399" },
                ].map((metric) => (
                  <div key={`form-summary-${metric.label}`} style={valueTileStyle}>
                    <span style={miniLabelStyle}>{metric.label}</span>
                    <strong style={{ ...miniValueStyle, color: metric.tone }}>{metric.value || "--"}</strong>
                  </div>
                ))}
              </div>

              <section style={{ ...workspaceSectionStyle, marginTop: 12 }}>
                <div style={titleStyle}>
                  <span>LAST FIVE RUNS</span>
                  <em>{firstText(selectedRunnerForm, ["form_source"], "FORM_SOURCE").replace(/_/g, " ")}</em>
                </div>

                <div style={{ display: "grid", gap: 6 }}>
                  <div style={{ display: "grid", gridTemplateColumns: "76px 1fr 70px 70px 70px 70px", gap: 8, color: "#94a3b8", fontSize: 10, textTransform: "uppercase", letterSpacing: ".08em", fontWeight: 900 }}>
                    <span>Date</span><span>Track / Class</span><span>Dist</span><span>Finish</span><span>Margin</span><span>Rating</span>
                  </div>
                  {[1,2,3,4,5].map((n) => {
                    const prefix = `last_start_${n}_`;
                    const date = firstText(selectedRunnerForm, [`${prefix}date`], "");
                    const trk = firstText(selectedRunnerForm, [`${prefix}track`], "");
                    const cls = firstText(selectedRunnerForm, [`${prefix}class`], "");
                    const dist = firstText(selectedRunnerForm, [`${prefix}distance`], "");
                    const finish = firstText(selectedRunnerForm, [`${prefix}finish`, `${prefix}finishing_position`], "");
                    const margin = firstText(selectedRunnerForm, [`${prefix}margin`, `${prefix}beaten_margin`], "");
                    const rating = firstNum(selectedRunnerForm, [`${prefix}rating`]);
                    const hasRun = date || trk || finish || rating !== null;
                    return (
                      <div key={`form-run-${n}`} style={{ display: "grid", gridTemplateColumns: "76px 1fr 70px 70px 70px 70px", gap: 8, alignItems: "center", padding: "8px 10px", border: "1px solid rgba(51,65,85,.7)", borderRadius: 10, background: hasRun ? "rgba(8,15,28,.82)" : "rgba(8,15,28,.38)" }}>
                        <span style={{ color: "#cbd5e1", fontWeight: 900 }}>{date || "--"}</span>
                        <span style={{ color: "#f8fafc", fontWeight: 900 }}>{[trk, cls].filter(Boolean).join(" / ") || "No run detail"}</span>
                        <span style={{ color: "#cbd5e1" }}>{dist ? `${dist}`.replace(".0","") + "m" : "--"}</span>
                        <span style={{ color: finish === "1.0" || finish === "1" ? "#34d399" : "#cbd5e1", fontWeight: 900 }}>{finish || "--"}</span>
                        <span style={{ color: "#cbd5e1" }}>{margin || "--"}</span>
                        <span style={{ color: rating !== null ? scoreToneValue(rating) : "#64748b", fontWeight: 1000 }}>{renderMetricValue(rating, 1)}</span>
                      </div>
                    );
                  })}
                </div>

                {firstText(selectedRunnerForm, ["form_truth_status"], "") === "BACKFILLED_CONTEXT_ONLY" ? (
                  <p style={{ ...narrativeInsetStyle, marginTop: 10 }}>
                    Form context exists for this runner, but detailed last-start history is not available in the current rated-history source. EDGEiQ is showing context only rather than inventing form lines.
                  </p>
                ) : null}
              </section>
            </>
          ) : (
            <p style={narrativeInsetStyle}>Select a runner to inspect form.</p>
          )}
        </section>
      ) : null}

'''

if insert_marker not in text:
    print("[WARN] FORM insertion marker not found")
else:
    text = text.replace(insert_marker, form_block + "\n" + insert_marker)

path.write_text(text, encoding="utf-8")
print("[FORM_TOP_LEVEL_TAB_WIRE] COMPLETE")
print(backup)
