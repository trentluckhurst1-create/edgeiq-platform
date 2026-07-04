from pathlib import Path
p=Path('src/components/RaceIntelligenceScreen.tsx')
s=p.read_text(encoding='utf-8')
s=s.replace('formEnrichment: "/data/edgeiq_form_enrichment_feed_v2.csv"','formEnrichment: "/data/edgeiq_form_enrichment_feed_v3.csv"')
s=s.replace('const formScore = firstNum(itemForm, ["form_peak_rating_last5", "form_avg_rating_last5", "form_last_start_rating"]);', 'const formScore = firstNum(itemForm, ["form_peak_rating_last5", "form_avg_rating_last5", "form_last_start_rating"]) ?? projectionRatingValue(item) ?? firstNum(item.row, ["projected_rating_v5_2", "total_rating_points", "rating_ladder_score"]);')
s=s.replace('const formTrend = firstText(itemForm, ["form_signal", "form_trend"], "--").replace(/_/g, " ").toUpperCase();', 'const formTrend = firstText(itemForm, ["form_signal", "form_trend", "rating_trend", "form_truth_status"], "FORM LOADED").replace(/_/g, " ").toUpperCase();')
s=s.replace('<span style={{ color: formScore !== null ? scoreToneValue(formScore) : "#64748b", fontWeight: 1000 }}>{renderMetricValue(formScore, 0)}</span>', '<span style={{ color: formScore !== null ? scoreToneValue(formScore) : "#64748b", fontWeight: 1000 }}>{formScore !== null ? renderMetricValue(formScore, 0) : "NOT LOADED"}</span>')
s=s.replace('{ label: "Trend", value: firstText(selectedRunnerForm, ["form_trend"], "--").replace(/_/g, " ").toUpperCase(), tone: "#f5c451" },', '{ label: "Trend", value: firstText(selectedRunnerForm, ["form_trend", "rating_trend", "form_cycle"], "--").replace(/_/g, " ").toUpperCase(), tone: "#f5c451" },')
s=s.replace('{ label: "Starts", value: firstText(selectedRunnerForm, ["form_history_starts"], "--"), tone: "#cbd5e1" },', '{ label: "Starts", value: firstText(selectedRunnerForm, ["form_history_starts"], "--"), tone: "#cbd5e1" },\n                        { label: "Wins / Places", value: `${firstText(selectedRunnerForm, ["form_history_wins"], "0")} / ${firstText(selectedRunnerForm, ["form_history_places"], "0")}`, tone: "#cbd5e1" },')
old='''                    <div style={{ display: "grid", gap: 6 }}>
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
                    ) : null}'''
new='''                    {firstText(selectedRunnerForm, ["form_truth_status"], "") === "BACKFILLED_CONTEXT_ONLY" ? (
                      <p style={{ ...narrativeInsetStyle, marginTop: 10 }}>
                        Context only - no detailed rated-history lines available.
                      </p>
                    ) : (
                      <div style={{ display: "grid", gap: 6 }}>
                        <div style={{ display: "grid", gridTemplateColumns: "80px 120px 64px 118px 78px 64px 72px 72px 68px minmax(160px,1fr)", gap: 8, color: "#94a3b8", fontSize: 10, textTransform: "uppercase", letterSpacing: ".08em", fontWeight: 900 }}>
                          <span>Date</span><span>Track</span><span>Dist</span><span>Class</span><span>Cond</span><span>Fin</span><span>Margin</span><span>Rating</span><span>SP</span><span>Reason</span>
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
                          const sp = firstText(selectedRunnerForm, [`${prefix}sp`, `${prefix}SP`], "");
                          const reason = firstText(selectedRunnerForm, [`${prefix}reason`, `${prefix}performance_label`], "");
                          const hasRun = date || trk || cls || finish || rating !== null;
                          return hasRun ? (
                            <div key={`form-run-${n}`} style={{ display: "grid", gridTemplateColumns: "80px 120px 64px 118px 78px 64px 72px 72px 68px minmax(160px,1fr)", gap: 8, alignItems: "center", padding: "8px 10px", border: "1px solid rgba(51,65,85,.7)", borderRadius: 10, background: "rgba(8,15,28,.82)" }}>
                              <span style={{ color: "#cbd5e1", fontWeight: 900 }}>{date || "--"}</span>
                              <span style={{ color: "#f8fafc", fontWeight: 900, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{trk || "No run detail"}</span>
                              <span style={{ color: "#cbd5e1" }}>{dist ? `${dist}`.replace(".0","") + "m" : "--"}</span>
                              <span style={{ color: "#cbd5e1", fontWeight: 800, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{cls || "--"}</span>
                              <span style={{ color: "#cbd5e1" }}>{cond || "--"}</span>
                              <span style={{ color: finish === "1.0" || finish === "1" ? "#34d399" : "#cbd5e1", fontWeight: 1000 }}>{finish || "--"}</span>
                              <span style={{ color: "#cbd5e1" }}>{margin || "--"}</span>
                              <span style={{ color: rating !== null ? scoreToneValue(rating) : "#64748b", fontWeight: 1000 }}>{rating !== null ? renderMetricValue(rating, 1) : "--"}</span>
                              <span style={{ color: "#cbd5e1" }}>{sp || "--"}</span>
                              <span style={{ color: "#94a3b8", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{reason || "--"}</span>
                            </div>
                          ) : null;
                        })}
                      </div>
                    )}'''
if old not in s:
    raise SystemExit('FORM table block not found')
s=s.replace(old,new)
p.write_text(s,encoding='utf-8')
print('RaceIntelligenceScreen.tsx FORM V3 UI update applied')
