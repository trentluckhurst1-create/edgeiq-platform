from pathlib import Path

path = Path('src/components/RaceIntelligenceScreen.tsx')
checkpoint = Path('src/components/RaceIntelligenceScreen_CHECKPOINT_FORM_PREMIUM_UI_V1_20260628.tsx')
text = path.read_text(encoding='utf-8')
checkpoint.write_text(text, encoding='utf-8')
start = text.index('      {intelMode === "FORM" ? (')
end = text.index('      {intelMode === "RUNNERS" ? (', start)
new_block = r'''      {intelMode === "FORM" ? (() => {
        const selectedFormStatus = firstText(selectedRunnerForm, ["form_truth_status", "form_v3_truth_status"], "NOT LOADED").replace(/_/g, " ").toUpperCase();
        const selectedFormSource = firstText(selectedRunnerForm, ["form_source"], "FORM SOURCE").replace(/_/g, " ").toUpperCase();
        const selectedIsContextOnly = selectedFormStatus.includes("CONTEXT");
        const selectedFormScore = selected ? (firstNum(selectedRunnerForm, ["form_peak_rating_last5", "form_avg_rating_last5", "form_last_start_rating"]) ?? projectionRatingValue(selected)) : null;
        const selectedFormScoreTone = selectedFormScore === null ? "#64748b" : selectedFormScore >= 90 ? "#34d399" : selectedFormScore >= 80 ? "#22d3ee" : selectedFormScore >= 70 ? "#f5c451" : selectedFormScore >= 60 ? "#fb923c" : "#f87171";
        const selectedTrendRaw = firstText(selectedRunnerForm, ["form_signal", "form_trend", "rating_trend", "form_cycle"], selectedIsContextOnly ? "CONTEXT ONLY" : "LIMITED FORM").replace(/_/g, " ").toUpperCase();
        const selectedTrendRead = selectedTrendRaw.includes("IMPROV") || selectedTrendRaw.includes("PEAK") ? "IMPROVING" : selectedTrendRaw.includes("DECLIN") || selectedTrendRaw.includes("REGRESS") ? "REGRESSING" : selectedTrendRaw.includes("CONTEXT") ? "CONTEXT ONLY" : selectedTrendRaw.includes("LIMITED") ? "LIMITED FORM" : selectedTrendRaw.includes("STABLE") ? "HOLDING" : selectedTrendRaw;
        const selectedTrendTone = selectedTrendRead.includes("IMPROV") || selectedTrendRead.includes("PEAK") ? "#34d399" : selectedTrendRead.includes("REGRESS") ? "#f87171" : selectedTrendRead.includes("CONTEXT") ? "#94a3b8" : selectedTrendRead.includes("LIMITED") ? "#f5c451" : "#7dd3fc";
        const selectedTrendIcon = selectedTrendRead.includes("IMPROV") || selectedTrendRead.includes("PEAK") ? "UP" : selectedTrendRead.includes("REGRESS") ? "DOWN" : selectedTrendRead.includes("CONTEXT") ? "CTX" : selectedTrendRead.includes("LIMITED") ? "LTD" : "HOLD";
        const lastStartDateText = firstText(selectedRunnerForm, ["last_start_1_date"], "");
        const daysSinceRun = lastStartDateText ? Math.max(0, Math.round((Date.now() - new Date(`${lastStartDateText}T00:00:00`).getTime()) / 86400000)) : null;
        const selectedFormVerdict = !selected
          ? "Select a runner to inspect form."
          : selectedIsContextOnly
            ? "Context only: EDGEiQ has profile context but no detailed rated-history lines."
            : selectedBestRatingLast5Value !== null && selectedTodayProjectionFigure !== null && selectedBestRatingLast5Value > selectedTodayProjectionFigure
              ? "Recent rated history loaded. Peak figure is above today's projected rating."
              : selectedRecentRatings.length <= 1
                ? "Limited rated-history profile. Treat with caution."
                : "Recent rated-history profile loaded for this runner.";
        const selectedMissingProfileBits = [
          firstText(selectedRunnerForm, ["last_start_1_distance"], "") ? "" : "distance",
          firstText(selectedRunnerForm, ["last_start_1_class"], "") ? "" : "class",
          firstText(selectedRunnerForm, ["last_start_1_condition"], "") ? "" : "condition",
        ].filter(Boolean).join(", ");
        const formPanelStyle = { border: "1px solid rgba(80,120,180,.28)", borderRadius: 12, padding: 12, background: "linear-gradient(135deg, rgba(8,15,28,.92), rgba(5,12,22,.78))" };
        const formMutedText = { color: "#64748b", fontSize: 11, fontWeight: 850 };
        const formPill = (label: string, tone: string, muted = false) => ({
          border: `1px solid ${muted ? "rgba(100,116,139,.38)" : `${tone}66`}`,
          borderRadius: 999,
          padding: "5px 8px",
          background: muted ? "rgba(15,23,42,.56)" : `${tone}18`,
          color: muted ? "#94a3b8" : tone,
          fontSize: 10.5,
          fontWeight: 1000,
          textTransform: "uppercase" as const,
          letterSpacing: ".07em",
          whiteSpace: "nowrap" as const,
        });
        const formRatingTone = (value: number | null) => value === null ? "#64748b" : value >= 90 ? "#34d399" : value >= 80 ? "#22d3ee" : value >= 70 ? "#f5c451" : value >= 60 ? "#fb923c" : "#f87171";
        const finishTone = (value: string) => {
          const finishValue = Number(String(value || "").replace(/[^0-9.]/g, ""));
          if (!Number.isFinite(finishValue) || !finishValue) return "#94a3b8";
          if (finishValue === 1) return "#34d399";
          if (finishValue <= 3) return "#7dd3fc";
          if (finishValue <= 6) return "#f5c451";
          return "#f87171";
        };
        const displayField = (value: string, fallback = "not loaded") => value && value !== "--" ? value : fallback;
        const lastFiveRuns = [1,2,3,4,5].map((n) => {
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
          const hasRun = !!(date || trk || cls || finish || rating !== null);
          return { n, date, trk, dist, cls, cond, finish, margin, rating, sp, reason, hasRun };
        }).filter((run) => run.hasRun);
        const profileSnapshot = [
          { label: "Career Starts", value: firstText(selectedRunnerForm, ["form_history_starts"], "") || firstText(selected?.row || {}, ["career_starts", "starts"], "") },
          { label: "Wins", value: firstText(selectedRunnerForm, ["form_history_wins"], "") || firstText(selected?.row || {}, ["wins", "career_wins"], "") },
          { label: "Places", value: firstText(selectedRunnerForm, ["form_history_places"], "") || firstText(selected?.row || {}, ["places", "career_places"], "") },
          { label: "Distance Profile", value: firstText(selected?.row || {}, ["distance_profile", "distance_read", "distance_truth_status"], "") },
          { label: "Condition Profile", value: firstText(selected?.row || {}, ["condition_profile", "condition_read", "condition_truth_status"], "") },
          { label: "Class Profile", value: firstText(selected?.row || {}, ["class_profile", "class_read", "class_truth_status"], "") },
          { label: "Campaign", value: firstText(selected?.row || {}, ["campaign_signal", "campaign_truth_status", "campaign_status"], "") },
          { label: "Trajectory", value: firstText(selected?.runnerTrajectory || selected?.row || {}, ["trajectory_direction", "trajectory_truth_status", "form_trend"], "") },
        ];
        return (
          <section style={workspaceSectionStyle}>
            <div style={titleStyle}>
              <span>FORM COMMAND</span>
              <em>premium horse-card intelligence, ratings profile and last-five evidence</em>
            </div>

            {selected ? (
              <div style={{ display: "grid", gridTemplateColumns: "330px minmax(0,1fr)", gap: 12, alignItems: "start" }}>
                <aside style={{ ...formPanelStyle, position: "sticky", top: 8 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center", marginBottom: 10 }}>
                    <strong style={{ color: "#f8fafc", fontSize: 13, textTransform: "uppercase", letterSpacing: ".09em" }}>Runner Selector</strong>
                    <span style={{ color: "#94a3b8", fontSize: 10.5, fontWeight: 900 }}>{rankedEnriched.length} loaded</span>
                  </div>
                  <div style={{ display: "grid", gap: 7 }}>
                    {rankedEnriched.map((item) => {
                      const itemForm = item.formEnrichment || item.row || {};
                      const isSelected = runnerRowKey(item.row) === runnerRowKey(selected.row);
                      const itemContextOnly = firstText(itemForm, ["form_truth_status", "form_v3_truth_status"], "").toUpperCase().includes("CONTEXT");
                      const formScore = firstNum(itemForm, ["form_peak_rating_last5", "form_avg_rating_last5", "form_last_start_rating"]) ?? projectionRatingValue(item) ?? firstNum(item.row, ["projected_rating_v5_2", "total_rating_points", "rating_ladder_score"]);
                      const formTrend = firstText(itemForm, ["form_signal", "form_trend", "rating_trend", "form_truth_status"], itemContextOnly ? "CONTEXT ONLY" : "FORM LOADED").replace(/_/g, " ").toUpperCase();
                      const itemTone = formRatingTone(formScore);
                      return (
                        <button
                          key={`form-premium-runner-${runnerRowKey(item.row)}`}
                          type="button"
                          onClick={() => setSelectedKey(runnerRowKey(item.row))}
                          style={{
                            appearance: "none",
                            border: isSelected ? "1px solid rgba(52,211,153,.78)" : "1px solid rgba(51,65,85,.72)",
                            background: isSelected ? "linear-gradient(135deg, rgba(6,45,34,.92), rgba(8,15,28,.82))" : "rgba(8,15,28,.82)",
                            color: "#f8fafc",
                            borderRadius: 10,
                            padding: 9,
                            display: "grid",
                            gridTemplateColumns: "28px minmax(0,1fr) 58px",
                            gap: 8,
                            alignItems: "center",
                            textAlign: "left",
                            cursor: "pointer",
                            boxShadow: isSelected ? "0 0 0 1px rgba(52,211,153,.12), 0 10px 24px rgba(0,0,0,.22)" : "none",
                          }}
                        >
                          <strong style={{ color: "#94a3b8", textAlign: "center" }}>{saddle(item.row) === 999 ? "--" : saddle(item.row)}</strong>
                          <span style={{ display: "grid", gap: 3, minWidth: 0 }}>
                            <strong style={{ fontWeight: 1000, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{horse(item.row)}</strong>
                            <span style={{ color: itemContextOnly ? "#94a3b8" : formTrend.includes("IMPROV") || formTrend.includes("PEAK") ? "#34d399" : formTrend.includes("REGRESS") || formTrend.includes("DECLIN") ? "#f87171" : "#f5c451", fontSize: 9.5, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".04em", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                              {itemContextOnly ? "CONTEXT ONLY" : formTrend}
                            </span>
                          </span>
                          <span style={{ display: "grid", justifyItems: "end", gap: 2 }}>
                            <strong style={{ color: itemTone, fontWeight: 1000 }}>{formScore !== null ? renderMetricValue(formScore, 0) : "NL"}</strong>
                            {itemContextOnly ? <em style={{ color: "#94a3b8", fontSize: 9, fontStyle: "normal", fontWeight: 900 }}>CTX</em> : null}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </aside>

                <div style={{ display: "grid", gap: 12 }}>
                  <section style={{ ...formPanelStyle, border: `1px solid ${selectedFormScoreTone}55`, boxShadow: `0 0 22px ${selectedFormScoreTone}10` }}>
                    <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) auto", gap: 14, alignItems: "start" }}>
                      <div style={{ display: "grid", gap: 8 }}>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 7, alignItems: "center" }}>
                          <span style={formPill(selectedFormSource, "#7dd3fc")}>SOURCE</span>
                          <span style={formPill(selectedFormStatus, selectedIsContextOnly ? "#f5c451" : "#34d399", false)}>STATUS</span>
                          {selectedIsContextOnly ? <span style={formPill("CONTEXT ONLY", "#f5c451")}>WARNING</span> : null}
                        </div>
                        <strong style={{ color: "#f8fafc", fontSize: 28, fontWeight: 1000, letterSpacing: ".01em", lineHeight: 1 }}>{horse(selected.row)}</strong>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, color: "#cbd5e1", fontSize: 12, fontWeight: 850 }}>
                          <span>No {saddle(selected.row) === 999 ? "--" : saddle(selected.row)}</span>
                          <span>Barrier {firstText(selected.row, ["barrier", "barrier_no", "draw"], "--")}</span>
                          <span>{firstText(selected.row, ["trainer", "trainer_name"], "Trainer not loaded")}</span>
                          <span>{firstText(selected.row, ["jockey", "jockey_name"], "Jockey not loaded")}</span>
                          <span>{displayField(firstText(selected.row, ["distance", "race_distance", "distance_m", "race_distance_m"], ""), "distance not loaded")}</span>
                          <span>{displayField(firstText(selected.row, ["condition", "track_condition", "official_condition", "edgeiq_condition"], ""), "condition not loaded")}</span>
                        </div>
                      </div>
                      <div style={{ minWidth: 128, border: `1px solid ${selectedFormScoreTone}66`, borderRadius: 12, padding: 12, background: `${selectedFormScoreTone}12`, textAlign: "center" }}>
                        <span style={{ color: "#94a3b8", fontSize: 10, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".09em" }}>Form Score</span>
                        <strong style={{ display: "block", color: selectedFormScoreTone, fontSize: 34, fontWeight: 1000, lineHeight: 1.05 }}>{selectedFormScore !== null ? renderMetricValue(selectedFormScore, 0) : "NL"}</strong>
                        <em style={{ color: "#cbd5e1", fontSize: 10.5, fontStyle: "normal", fontWeight: 850 }}>{selectedTrendRead}</em>
                      </div>
                    </div>
                  </section>

                  <section style={formPanelStyle}>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(130px, 1fr))", gap: 8 }}>
                      {[
                        { label: "Last Start", value: selectedLastStartRatingValue, display: selectedLastStartRating },
                        { label: "Avg L5", value: selectedAvgRatingLast5Value, display: selectedAvgRatingLast5 },
                        { label: "Peak L5", value: selectedBestRatingLast5Value, display: selectedBestRatingLast5 },
                        { label: "Projected", value: selectedTodayProjectionFigure, display: selectedTodayProjectionFigure !== null ? renderMetricValue(selectedTodayProjectionFigure, 1) : "--" },
                        { label: "Starts", value: firstNum(selectedRunnerForm, ["form_history_starts"]), display: firstText(selectedRunnerForm, ["form_history_starts"], "--") },
                        { label: "Wins / Places", value: null, display: `${firstText(selectedRunnerForm, ["form_history_wins"], "0")} / ${firstText(selectedRunnerForm, ["form_history_places"], "0")}` },
                        { label: "Days Since Run", value: daysSinceRun, display: daysSinceRun !== null ? `${daysSinceRun}` : "--" },
                        { label: "Evidence", value: null, display: selectedFormStatus },
                      ].map((metric) => {
                        const tone = metric.value === null ? "#7dd3fc" : formRatingTone(metric.value);
                        return (
                          <div key={`premium-form-rating-${metric.label}`} style={{ border: "1px solid rgba(80,120,180,.24)", borderRadius: 10, padding: 10, background: "rgba(5,12,22,.72)", display: "grid", gap: 5 }}>
                            <span style={{ color: "#94a3b8", fontSize: 10, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".08em" }}>{metric.label}</span>
                            <strong style={{ color: metric.display === "--" ? "#64748b" : tone, fontSize: 18, fontWeight: 1000 }}>{metric.display}</strong>
                          </div>
                        );
                      })}
                    </div>
                  </section>

                  <section style={formPanelStyle}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center", marginBottom: 10 }}>
                      <strong style={{ color: "#f8fafc", fontSize: 13, textTransform: "uppercase", letterSpacing: ".08em" }}>Form Trend</strong>
                      <span style={formPill(selectedTrendIcon, selectedTrendTone)}>{selectedTrendRead}</span>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "140px minmax(0,1fr)", gap: 12, alignItems: "center" }}>
                      <div style={{ border: `1px solid ${selectedTrendTone}66`, background: `${selectedTrendTone}12`, borderRadius: 12, padding: 12, textAlign: "center" }}>
                        <strong style={{ color: selectedTrendTone, fontSize: 20, fontWeight: 1000 }}>{selectedTrendIcon}</strong>
                        <span style={{ display: "block", color: "#94a3b8", fontSize: 10, fontWeight: 900, marginTop: 4 }}>TREND READ</span>
                      </div>
                      <div style={{ color: "#cbd5e1", fontSize: 12.5, lineHeight: 1.55, fontWeight: 820 }}>
                        {selectedFormVerdict}
                        {selectedMissingProfileBits ? ` Source note: ${selectedMissingProfileBits} detail is partially missing from the last-start source.` : ""}
                      </div>
                    </div>
                  </section>

                  <section style={formPanelStyle}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center", marginBottom: 10 }}>
                      <strong style={{ color: "#f8fafc", fontSize: 13, textTransform: "uppercase", letterSpacing: ".08em" }}>Last Five Runs</strong>
                      <span style={{ color: "#94a3b8", fontSize: 11, fontWeight: 900 }}>class, distance, condition, finish, margin, rating</span>
                    </div>
                    {selectedIsContextOnly ? (
                      <div style={{ border: "1px solid rgba(245,196,81,.32)", borderRadius: 10, padding: 12, background: "rgba(245,196,81,.08)", color: "#f5c451", fontSize: 12, fontWeight: 900 }}>
                        Context only - no detailed rated-history lines available.
                      </div>
                    ) : (
                      <div style={{ display: "grid", gap: 6, overflowX: "auto" }}>
                        <div style={{ minWidth: 980, display: "grid", gridTemplateColumns: "82px 138px 68px 126px 78px 58px 74px 72px 68px minmax(180px,1fr)", gap: 8, color: "#94a3b8", fontSize: 10, textTransform: "uppercase", letterSpacing: ".08em", fontWeight: 1000 }}>
                          <span>Date</span><span>Track</span><span>Dist</span><span>Class</span><span>Cond</span><span>Fin</span><span>Margin</span><span>Rating</span><span>SP</span><span>Comment</span>
                        </div>
                        {lastFiveRuns.map((run) => (
                          <div key={`premium-form-run-${run.n}`} style={{ minWidth: 980, display: "grid", gridTemplateColumns: "82px 138px 68px 126px 78px 58px 74px 72px 68px minmax(180px,1fr)", gap: 8, alignItems: "center", padding: "9px 10px", border: "1px solid rgba(51,65,85,.72)", borderRadius: 10, background: "rgba(8,15,28,.84)" }}>
                            <span style={{ color: "#cbd5e1", fontWeight: 950 }}>{run.date || "--"}</span>
                            <span style={{ color: "#f8fafc", fontWeight: 950, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{run.trk || "not loaded"}</span>
                            <span style={{ ...(run.dist ? {} : formMutedText), color: run.dist ? "#cbd5e1" : "#64748b" }}>{run.dist ? `${run.dist}`.replace(".0", "") + "m" : "not loaded"}</span>
                            <span style={{ ...(run.cls ? {} : formMutedText), color: run.cls ? "#cbd5e1" : "#64748b", fontWeight: 850, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{run.cls || "unknown"}</span>
                            <span style={{ ...(run.cond ? {} : formMutedText), color: run.cond ? "#cbd5e1" : "#64748b" }}>{run.cond || "unknown"}</span>
                            <span style={{ color: finishTone(run.finish), fontWeight: 1000 }}>{run.finish || "--"}</span>
                            <span style={{ color: "#cbd5e1" }}>{run.margin || "--"}</span>
                            <span style={{ color: formRatingTone(run.rating), fontWeight: 1000 }}>{run.rating !== null ? renderMetricValue(run.rating, 1) : "--"}</span>
                            <span style={{ color: "#cbd5e1" }}>{run.sp || "--"}</span>
                            <span style={{ color: run.reason ? "#94a3b8" : "#64748b", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{run.reason || "not loaded"}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </section>

                  <section style={{ display: "grid", gridTemplateColumns: "minmax(0,1.1fr) minmax(0,.9fr)", gap: 12 }}>
                    <div style={formPanelStyle}>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center", marginBottom: 10 }}>
                        <strong style={{ color: "#f8fafc", fontSize: 13, textTransform: "uppercase", letterSpacing: ".08em" }}>Career / Profile Snapshot</strong>
                        <span style={{ color: "#94a3b8", fontSize: 11, fontWeight: 900 }}>available evidence only</span>
                      </div>
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(130px,1fr))", gap: 8 }}>
                        {profileSnapshot.map((entry) => (
                          <div key={`form-profile-${entry.label}`} style={{ border: "1px solid rgba(80,120,180,.22)", borderRadius: 10, padding: 9, background: "rgba(5,12,22,.68)", display: "grid", gap: 4 }}>
                            <span style={{ color: "#94a3b8", fontSize: 10, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".07em" }}>{entry.label}</span>
                            <strong style={{ color: entry.value ? "#f8fafc" : "#64748b", fontSize: 12, fontWeight: 950, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{entry.value || "NOT LOADED"}</strong>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div style={formPanelStyle}>
                      <strong style={{ color: "#f8fafc", fontSize: 13, textTransform: "uppercase", letterSpacing: ".08em" }}>EDGEiQ Form Verdict</strong>
                      <p style={{ color: "#dbe7fb", fontSize: 12.5, lineHeight: 1.58, margin: "10px 0 0", fontWeight: 820 }}>{selectedFormVerdict}</p>
                      {selectedMissingProfileBits ? <p style={{ color: "#f5c451", fontSize: 11.5, lineHeight: 1.5, margin: "8px 0 0", fontWeight: 850 }}>Partial source detail: {selectedMissingProfileBits} not fully loaded for this runner.</p> : null}
                    </div>
                  </section>

                  <section style={formPanelStyle}>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(5, minmax(130px, 1fr))", gap: 8 }}>
                      {["Performance Timeline", "Setup Match", "Performance Matrix", "Form Fingerprint", "Comparison Tool"].map((label) => (
                        <div key={`form-future-${label}`} style={{ border: "1px dashed rgba(125,211,252,.25)", borderRadius: 10, padding: 10, background: "rgba(5,12,22,.48)", minHeight: 64 }}>
                          <strong style={{ color: "#7dd3fc", fontSize: 11, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".07em" }}>{label}</strong>
                          <p style={{ color: "#64748b", fontSize: 10.5, lineHeight: 1.35, margin: "6px 0 0", fontWeight: 820 }}>Coming next: rating timeline from historical run feed.</p>
                        </div>
                      ))}
                    </div>
                  </section>
                </div>
              </div>
            ) : (
              <p style={narrativeInsetStyle}>Select a runner to inspect form.</p>
            )}
          </section>
        );
      })() : null}


'''
text = text[:start] + new_block + text[end:]
path.write_text(text, encoding='utf-8')
print('FORM premium UI V1 block applied')
print(f'checkpoint={checkpoint}')
