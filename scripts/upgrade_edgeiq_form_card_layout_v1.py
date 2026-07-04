from pathlib import Path
import re

path = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard\src\components\RaceIntelligenceScreen.tsx")
backup = path.with_name("RaceIntelligenceScreen_CHECKPOINT_FORM_CARD_LAYOUT_V1_20260628.tsx")
backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

text = path.read_text(encoding="utf-8")

form_block = r'''
      {intelMode === "FORM" ? (
        <section style={workspaceSectionStyle}>
          <div style={titleStyle}>
            <span>FORM COMMAND</span>
            <em>horse card, recent ratings, setup profile and last-five evidence</em>
          </div>

          {selected ? (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "320px minmax(0,1fr)", gap: 12 }}>
                <div style={{ ...workspaceSectionStyle, margin: 0 }}>
                  <div style={titleStyle}>
                    <span>RUNNERS</span>
                    <em>select horse</em>
                  </div>
                  <div style={{ display: "grid", gap: 6 }}>
                    {rankedEnriched.map((item) => {
                      const itemForm = item.formEnrichment || item.formIntelligence || item.runnerForm;
                      const isSelected = runnerRowKey(item.row) === runnerRowKey(selected.row);
                      const formScore = firstNum(itemForm, ["form_peak_rating_last5", "form_avg_rating_last5", "form_last_start_rating"]);
                      const formTrend = firstText(itemForm, ["form_signal", "form_trend"], "--").replace(/_/g, " ").toUpperCase();
                      return (
                        <button
                          key={`form-runner-${runnerRowKey(item.row)}`}
                          type="button"
                          onClick={() => setSelectedKey(runnerRowKey(item.row))}
                          style={{
                            appearance: "none",
                            border: isSelected ? "1px solid rgba(52,211,153,.72)" : "1px solid rgba(51,65,85,.72)",
                            background: isSelected ? "rgba(6,45,34,.82)" : "rgba(8,15,28,.82)",
                            color: "#f8fafc",
                            borderRadius: 10,
                            padding: "9px 10px",
                            display: "grid",
                            gridTemplateColumns: "26px minmax(0,1fr) 54px 74px",
                            gap: 8,
                            alignItems: "center",
                            textAlign: "left",
                            cursor: "pointer",
                          }}
                        >
                          <strong style={{ color: "#94a3b8" }}>{saddle(item.row) || "--"}</strong>
                          <span style={{ fontWeight: 1000, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{horse(item.row)}</span>
                          <span style={{ color: formScore !== null ? scoreToneValue(formScore) : "#64748b", fontWeight: 1000 }}>{renderMetricValue(formScore, 0)}</span>
                          <span style={{ color: formTrend.includes("PEAK") || formTrend.includes("IMPROV") ? "#34d399" : formTrend.includes("REGRESS") || formTrend.includes("DECLIN") ? "#f87171" : "#f5c451", fontSize: 10, fontWeight: 1000 }}>{formTrend}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div style={{ display: "grid", gap: 12 }}>
                  <section style={{ ...workspaceSectionStyle, margin: 0 }}>
                    <div style={titleStyle}>
                      <span>{horse(selected.row)}</span>
                      <em>{firstText(selectedRunnerForm, ["form_source"], "FORM SOURCE").replace(/_/g, " ")}</em>
                    </div>

                    <div style={selectedGridStyle(8)}>
                      {[
                        { label: "Form Status", value: firstText(selectedRunnerForm, ["form_truth_status"], "--").replace(/_/g, " ").toUpperCase(), tone: firstText(selectedRunnerForm, ["form_truth_status"], "").includes("OK") ? "#34d399" : "#f5c451" },
                        { label: "Signal", value: firstText(selectedRunnerForm, ["form_signal"], "--").replace(/_/g, " ").toUpperCase(), tone: "#7dd3fc" },
                        { label: "Trend", value: firstText(selectedRunnerForm, ["form_trend"], "--").replace(/_/g, " ").toUpperCase(), tone: "#f5c451" },
                        { label: "Starts", value: firstText(selectedRunnerForm, ["form_history_starts"], "--"), tone: "#cbd5e1" },
                        { label: "Last Rating", value: renderMetricValue(firstNum(selectedRunnerForm, ["form_last_start_rating"]), 1), tone: "#f5c451" },
                        { label: "Avg L5", value: renderMetricValue(firstNum(selectedRunnerForm, ["form_avg_rating_last5"]), 1), tone: "#7dd3fc" },
                        { label: "Peak L5", value: renderMetricValue(firstNum(selectedRunnerForm, ["form_peak_rating_last5"]), 1), tone: "#34d399" },
                        { label: "Projected", value: renderMetricValue(projectionRatingValue(selected), 1), tone: "#c084fc" },
                      ].map((metric) => (
                        <div key={`form-card-${metric.label}`} style={valueTileStyle}>
                          <span style={miniLabelStyle}>{metric.label}</span>
                          <strong style={{ ...miniValueStyle, color: metric.tone }}>{metric.value || "--"}</strong>
                        </div>
                      ))}
                    </div>
                  </section>

                  <section style={{ ...workspaceSectionStyle, margin: 0 }}>
                    <div style={titleStyle}>
                      <span>LAST FIVE RUNS</span>
                      <em>date, track, distance, class, condition, finish, margin and rating</em>
                    </div>

                    <div style={{ display: "grid", gap: 6 }}>
                      <div style={{ display: "grid", gridTemplateColumns: "80px 120px 64px 118px 78px 64px 72px 72px", gap: 8, color: "#94a3b8", fontSize: 10, textTransform: "uppercase", letterSpacing: ".08em", fontWeight: 900 }}>
                        <span>Date</span><span>Track</span><span>Dist</span><span>Class</span><span>Cond</span><span>Fin</span><span>Margin</span><span>Rating</span>
                      </div>

                      {[1,2,3,4,5].map((n) => {
                        const prefix = `last_start_${n}_`;
                        const date = firstText(selectedRunnerForm, [`${prefix}date`], "");
                        const trk = firstText(selectedRunnerForm, [`${prefix}track`], "");
                        const dist = firstText(selectedRunnerForm, [`${prefix}distance`], "");
                        const cls = firstText(selectedRunnerForm, [`${prefix}class`], "");
                        const cond = firstText(selectedRunnerForm, [`${prefix}condition`], "");
                        const finish = firstText(selectedRunnerForm, [`${prefix}finish`, `${prefix}finishing_position`], "");
                        const margin = firstText(selectedRunnerForm, [`${prefix}margin`, `${prefix}beaten_margin`], "");
                        const rating = firstNum(selectedRunnerForm, [`${prefix}rating`]);
                        const hasRun = date || trk || cls || finish || rating !== null;
                        return (
                          <div key={`form-run-${n}`} style={{ display: "grid", gridTemplateColumns: "80px 120px 64px 118px 78px 64px 72px 72px", gap: 8, alignItems: "center", padding: "8px 10px", border: "1px solid rgba(51,65,85,.7)", borderRadius: 10, background: hasRun ? "rgba(8,15,28,.82)" : "rgba(8,15,28,.38)" }}>
                            <span style={{ color: "#cbd5e1", fontWeight: 900 }}>{date || "--"}</span>
                            <span style={{ color: "#f8fafc", fontWeight: 900 }}>{trk || "No run detail"}</span>
                            <span style={{ color: "#cbd5e1" }}>{dist ? `${dist}`.replace(".0","") + "m" : "--"}</span>
                            <span style={{ color: "#cbd5e1", fontWeight: 800 }}>{cls || "--"}</span>
                            <span style={{ color: "#cbd5e1" }}>{cond || "--"}</span>
                            <span style={{ color: finish === "1.0" || finish === "1" ? "#34d399" : "#cbd5e1", fontWeight: 1000 }}>{finish || "--"}</span>
                            <span style={{ color: "#cbd5e1" }}>{margin || "--"}</span>
                            <span style={{ color: rating !== null ? scoreToneValue(rating) : "#64748b", fontWeight: 1000 }}>{renderMetricValue(rating, 1)}</span>
                          </div>
                        );
                      })}
                    </div>

                    {firstText(selectedRunnerForm, ["form_truth_status"], "") === "BACKFILLED_CONTEXT_ONLY" ? (
                      <p style={{ ...narrativeInsetStyle, marginTop: 10 }}>
                        EDGEiQ has context for this runner, but no detailed rated-history lines in the current source. We show context only rather than inventing form.
                      </p>
                    ) : null}
                  </section>
                </div>
              </div>
            </>
          ) : (
            <p style={narrativeInsetStyle}>Select a runner to inspect form.</p>
          )}
        </section>
      ) : null}

'''

pattern = re.compile(r'\s*\{intelMode === "FORM" \? \([\s\S]*?\n\s*\{intelMode === "RUNNERS" \? \(', re.M)
match = pattern.search(text)
if not match:
    raise SystemExit("[FORM_CARD_LAYOUT] Could not find FORM block boundary")

text = text[:match.start()] + "\n" + form_block + "\n      {intelMode === \"RUNNERS\" ? (" + text[match.end():]
path.write_text(text, encoding="utf-8")

print("[FORM_CARD_LAYOUT_V1] COMPLETE")
print(backup)
