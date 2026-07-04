from pathlib import Path

path = Path('src/components/RaceIntelligenceScreen.tsx')
checkpoint = Path('src/components/RaceIntelligenceScreen_CHECKPOINT_FORM_TOPRATE_STRUCTURE_V1_20260628.tsx')
text = path.read_text(encoding='utf-8')
checkpoint.write_text(text, encoding='utf-8')
start = text.index('      {intelMode === "FORM" ? (')
end = text.index('      {intelMode === "RUNNERS" ? (', start)
new_block = r'''      {intelMode === "FORM" ? (() => {
        const selectedFormStatus = firstText(selectedRunnerForm, ["form_truth_status", "form_v4_truth_status"], "NOT LOADED").replace(/_/g, " ").toUpperCase();
        const selectedFormSource = firstText(selectedRunnerForm, ["form_source"], "FORM SOURCE").replace(/_/g, " ").toUpperCase();
        const selectedFormDataQuality = firstText(selectedRunnerForm, ["form_data_quality", "form_truth_status"], selectedFormStatus).replace(/_/g, " ").toUpperCase();
        const selectedIsContextOnly = selectedFormStatus.includes("CONTEXT");
        const selectedFormScore = selected ? (firstNum(selectedRunnerForm, ["form_peak_rating_last5", "form_avg_rating_last5", "form_last_start_rating"]) ?? projectionRatingValue(selected)) : null;
        const formRatingTone = (value: number | null) => value === null ? "#64748b" : value >= 90 ? "#34d399" : value >= 80 ? "#22d3ee" : value >= 70 ? "#f5c451" : value >= 60 ? "#fb923c" : "#f87171";
        const selectedFormScoreTone = formRatingTone(selectedFormScore);
        const selectedTrendRaw = firstText(selectedRunnerForm, ["form_signal", "form_trend", "rating_trend", "form_cycle", "form_data_quality"], selectedIsContextOnly ? "CONTEXT ONLY" : "LIMITED FORM").replace(/_/g, " ").toUpperCase();
        const selectedTrendRead = selectedTrendRaw.includes("IMPROV") || selectedTrendRaw.includes("PEAK") ? "IMPROVING" : selectedTrendRaw.includes("DECLIN") || selectedTrendRaw.includes("REGRESS") ? "REGRESSING" : selectedTrendRaw.includes("CONTEXT") ? "CONTEXT ONLY" : selectedTrendRaw.includes("PARTIAL") ? "PARTIAL HISTORY" : selectedTrendRaw.includes("LIMITED") ? "LIMITED FORM" : selectedTrendRaw.includes("HOLD") || selectedTrendRaw.includes("STABLE") ? "HOLDING" : selectedTrendRaw;
        const selectedTrendTone = selectedTrendRead.includes("IMPROV") || selectedTrendRead.includes("PEAK") ? "#34d399" : selectedTrendRead.includes("REGRESS") ? "#f87171" : selectedTrendRead.includes("CONTEXT") ? "#94a3b8" : selectedTrendRead.includes("PARTIAL") ? "#7dd3fc" : selectedTrendRead.includes("LIMITED") ? "#f5c451" : "#7dd3fc";
        const selectedRaceDateValue = raceDate(selected?.row || {});
        const dayDiff = (fromDate: string) => {
          if (!fromDate || !selectedRaceDateValue) return null;
          const from = new Date(`${fromDate}T00:00:00`).getTime();
          const to = new Date(`${selectedRaceDateValue}T00:00:00`).getTime();
          if (!Number.isFinite(from) || !Number.isFinite(to)) return null;
          return Math.max(0, Math.round((to - from) / 86400000));
        };
        const finishTone = (value: string) => {
          const finishValue = Number(String(value || "").replace(/[^0-9.]/g, ""));
          if (!Number.isFinite(finishValue) || !finishValue) return "#94a3b8";
          if (finishValue === 1) return "#34d399";
          if (finishValue <= 3) return "#7dd3fc";
          if (finishValue <= 6) return "#f5c451";
          return "#f87171";
        };
        const conditionTone = (value: string) => {
          const v = value.toUpperCase();
          if (v.includes("GOOD") || v.includes("FIRM")) return { color: "#052e16", bg: "#86efac", border: "rgba(134,239,172,.65)" };
          if (v.includes("SOFT")) return { color: "#082f49", bg: "#7dd3fc", border: "rgba(125,211,252,.65)" };
          if (v.includes("HEAVY")) return { color: "#450a0a", bg: "#f87171", border: "rgba(248,113,113,.65)" };
          if (v.includes("FAST")) return { color: "#020617", bg: "#f8fafc", border: "rgba(248,250,252,.7)" };
          return { color: "#94a3b8", bg: "rgba(15,23,42,.72)", border: "rgba(100,116,139,.38)" };
        };
        const formPill = (label: string, tone: string, muted = false) => ({
          border: `1px solid ${muted ? "rgba(100,116,139,.38)" : `${tone}66`}`,
          borderRadius: 999,
          padding: "4px 8px",
          background: muted ? "rgba(15,23,42,.56)" : `${tone}18`,
          color: muted ? "#94a3b8" : tone,
          fontSize: 10,
          fontWeight: 1000,
          textTransform: "uppercase" as const,
          letterSpacing: ".07em",
          whiteSpace: "nowrap" as const,
        });
        const mutedCell = { color: "#64748b", fontSize: 10.5, fontWeight: 800 };
        const formPanelStyle = { border: "1px solid rgba(80,120,180,.28)", borderRadius: 8, padding: 10, background: "linear-gradient(135deg, rgba(8,15,28,.94), rgba(5,12,22,.82))" };
        const selectedFormVerdict = !selected
          ? "Select a runner to inspect form."
          : selectedIsContextOnly
            ? "Context only; no detailed rated-history lines available."
            : selectedFormStatus.includes("PARTIAL")
              ? `Partial historical profile; use with caution. ${selectedTrendRead.includes("REGRESS") ? "Recent ratings are regressing." : selectedTrendRead.includes("IMPROV") ? "Recent ratings are improving." : "Evidence is useful but incomplete."}`
              : selectedFormScore !== null && selectedFormScore >= 80
                ? `Rated history loaded; profile can be assessed from recent figures. ${selectedTrendRead.includes("REGRESS") ? "Trend is regressing." : selectedTrendRead.includes("IMPROV") ? "Trend is improving." : "Trend is holding."}`
                : "Rated history loaded; profile can be assessed from recent figures.";
        const missingDetail = [
          firstText(selectedRunnerForm, ["last_start_1_distance"], "") ? "" : "distance",
          firstText(selectedRunnerForm, ["last_start_1_class"], "") ? "" : "class",
          firstText(selectedRunnerForm, ["last_start_1_condition"], "") ? "" : "condition",
        ].filter(Boolean).join(", ");
        const lastFiveRuns = [1,2,3,4,5].map((n) => {
          const prefix = `last_start_${n}_`;
          const date = firstText(selectedRunnerForm, [`${prefix}date`], "");
          const trk = firstText(selectedRunnerForm, [`${prefix}track`], "");
          const going = firstText(selectedRunnerForm, [`${prefix}condition`], "");
          const dist = firstText(selectedRunnerForm, [`${prefix}distance`], "");
          const cls = firstText(selectedRunnerForm, [`${prefix}class`], "");
          const pos = firstText(selectedRunnerForm, [`${prefix}finish`, `${prefix}finishing_position`], "");
          const margin = firstText(selectedRunnerForm, [`${prefix}margin`, `${prefix}beaten_margin`], "");
          const sp = firstText(selectedRunnerForm, [`${prefix}sp`, `${prefix}SP`], "");
          const rating = firstNum(selectedRunnerForm, [`${prefix}rating`]);
          const source = firstText(selectedRunnerForm, [`${prefix}source`, `${prefix}reason`, `${prefix}performance_label`], "");
          const dlr = dayDiff(date);
          const hasRun = !!(date || trk || cls || pos || rating !== null);
          return { n, date, dlr, trk, going, dist, cls, pos, margin, sp, rating, source, hasRun };
        }).filter((run) => run.hasRun);
        const profileValue = (row: Row, keys: string[]) => firstText(row, keys, "");
        const distanceProfile = profileValue(selected?.row || {}, ["distance_profile", "distance_read", "distance_truth_status", "distance_profile_status"]);
        const conditionProfile = profileValue(selected?.row || {}, ["condition_profile", "condition_read", "condition_truth_status", "condition_profile_status"]);
        const classProfile = profileValue(selected?.row || {}, ["class_profile", "class_read", "class_truth_status", "class_profile_status"]);
        const winPct = (() => {
          const starts = firstNum(selectedRunnerForm, ["form_history_starts"]);
          const wins = firstNum(selectedRunnerForm, ["form_history_wins"]);
          return starts && wins !== null ? `${renderMetricValue((wins / starts) * 100, 0)}%` : "--";
        })();
        const placePct = (() => {
          const starts = firstNum(selectedRunnerForm, ["form_history_starts"]);
          const places = firstNum(selectedRunnerForm, ["form_history_places"]);
          return starts && places !== null ? `${renderMetricValue((places / starts) * 100, 0)}%` : "--";
        })();
        return (
          <section style={workspaceSectionStyle}>
            <div style={titleStyle}>
              <span>FORM COMMAND</span>
              <em>dense professional form-analysis card from recovered historical ratings</em>
            </div>

            {selected ? (
              <div style={{ display: "grid", gridTemplateColumns: "390px minmax(0,1fr)", gap: 12, alignItems: "start" }}>
                <aside style={{ ...formPanelStyle, padding: 0, overflow: "hidden" }}>
                  <div style={{ display: "grid", gridTemplateColumns: "38px minmax(0,1fr) 64px 108px", gap: 0, padding: "8px 10px", background: "rgba(15,23,42,.92)", borderBottom: "1px solid rgba(80,120,180,.35)", color: "#94a3b8", fontSize: 10, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".08em" }}>
                    <span>#</span><span>Horse</span><span style={{ textAlign: "right" }}>Form</span><span style={{ textAlign: "right" }}>Trend</span>
                  </div>
                  <div style={{ display: "grid", maxHeight: 650, overflowY: "auto" }}>
                    {rankedEnriched.map((item) => {
                      const itemForm = item.formEnrichment || item.row || {};
                      const isSelected = runnerRowKey(item.row) === runnerRowKey(selected.row);
                      const itemQuality = firstText(itemForm, ["form_data_quality", "form_truth_status"], "").replace(/_/g, " ").toUpperCase();
                      const itemScore = firstNum(itemForm, ["form_peak_rating_last5", "form_avg_rating_last5", "form_last_start_rating"]) ?? projectionRatingValue(item);
                      const itemTrend = firstText(itemForm, ["form_signal", "form_trend", "rating_trend", "form_data_quality"], itemQuality || "FORM").replace(/_/g, " ").toUpperCase();
                      return (
                        <button
                          key={`form-table-runner-${runnerRowKey(item.row)}`}
                          type="button"
                          onClick={() => setSelectedKey(runnerRowKey(item.row))}
                          style={{
                            appearance: "none",
                            display: "grid",
                            gridTemplateColumns: "38px minmax(0,1fr) 64px 108px",
                            gap: 0,
                            alignItems: "center",
                            padding: "7px 10px",
                            border: 0,
                            borderBottom: "1px solid rgba(51,65,85,.55)",
                            background: isSelected ? "linear-gradient(90deg, rgba(52,211,153,.18), rgba(8,15,28,.92))" : "rgba(5,12,22,.78)",
                            boxShadow: isSelected ? "inset 3px 0 0 #34d399" : "none",
                            cursor: "pointer",
                            textAlign: "left",
                          }}
                        >
                          <strong style={{ color: isSelected ? "#34d399" : "#94a3b8", fontSize: 11 }}>{saddle(item.row) === 999 ? "--" : saddle(item.row)}</strong>
                          <span style={{ minWidth: 0, display: "grid", gap: 2 }}>
                            <strong style={{ color: "#f8fafc", fontSize: 11.5, fontWeight: 1000, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{horse(item.row)}</strong>
                            <span style={{ color: "#64748b", fontSize: 9.5, fontWeight: 850, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{itemQuality || "DATA QUALITY NOT LOADED"}</span>
                          </span>
                          <strong style={{ color: formRatingTone(itemScore), fontSize: 12, textAlign: "right" }}>{itemScore !== null ? renderMetricValue(itemScore, 0) : "--"}</strong>
                          <span style={{ color: itemTrend.includes("IMPROV") || itemTrend.includes("PEAK") ? "#34d399" : itemTrend.includes("REGRESS") ? "#f87171" : itemTrend.includes("CONTEXT") ? "#94a3b8" : "#f5c451", fontSize: 9.5, fontWeight: 950, textAlign: "right", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{itemTrend}</span>
                        </button>
                      );
                    })}
                  </div>
                </aside>

                <div style={{ display: "grid", gap: 10, minWidth: 0 }}>
                  <section style={{ ...formPanelStyle, padding: 0, overflow: "hidden", border: `1px solid ${selectedFormScoreTone}55` }}>
                    <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) auto", gap: 12, padding: "11px 12px", background: "linear-gradient(90deg, rgba(15,23,42,.98), rgba(8,15,28,.86))", borderBottom: "1px solid rgba(80,120,180,.32)" }}>
                      <div style={{ display: "grid", gap: 7 }}>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
                          <span style={formPill(selectedFormSource, "#7dd3fc")}>SOURCE</span>
                          <span style={formPill(selectedFormDataQuality, selectedFormDataQuality.includes("FULL") ? "#34d399" : selectedFormDataQuality.includes("PARTIAL") ? "#7dd3fc" : selectedFormDataQuality.includes("CONTEXT") ? "#f5c451" : "#f87171")}>DATA QUALITY</span>
                          <span style={formPill(selectedFormStatus, selectedFormStatus.includes("OK") ? "#34d399" : selectedFormStatus.includes("PARTIAL") ? "#7dd3fc" : "#f5c451")}>FORM STATUS</span>
                        </div>
                        <strong style={{ color: "#f8fafc", fontSize: 24, fontWeight: 1000, letterSpacing: ".01em", lineHeight: 1 }}>{horse(selected.row)}</strong>
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(6, minmax(90px,1fr))", gap: 8, color: "#cbd5e1", fontSize: 11, fontWeight: 850 }}>
                          <span>No {saddle(selected.row) === 999 ? "--" : saddle(selected.row)}</span>
                          <span>Barrier {firstText(selected.row, ["barrier", "barrier_no", "draw"], "--")}</span>
                          <span>{firstText(selected.row, ["trainer", "trainer_name"], "Trainer not loaded")}</span>
                          <span>{firstText(selected.row, ["jockey", "jockey_name"], "Jockey not loaded")}</span>
                          <span>{firstText(selected.row, ["weight", "weight_carried", "allocated_weight"], "Weight --")}</span>
                          <span>{firstText(selected.row, ["age_sex", "age", "sex"], "Age/sex --")}</span>
                        </div>
                      </div>
                      <div style={{ minWidth: 96, borderLeft: "1px solid rgba(80,120,180,.28)", paddingLeft: 12, textAlign: "right" }}>
                        <span style={{ color: "#94a3b8", fontSize: 10, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".08em" }}>Form</span>
                        <strong style={{ display: "block", color: selectedFormScoreTone, fontSize: 30, fontWeight: 1000, lineHeight: 1 }}>{selectedFormScore !== null ? renderMetricValue(selectedFormScore, 0) : "--"}</strong>
                        <em style={{ color: selectedTrendTone, fontSize: 10.5, fontStyle: "normal", fontWeight: 950 }}>{selectedTrendRead}</em>
                      </div>
                    </div>
                  </section>

                  <section style={{ display: "grid", gridTemplateColumns: "1.05fr .95fr 1.05fr .95fr", gap: 8 }}>
                    {[
                      { title: "Rating Profile", rows: [["Last", selectedLastStartRating], ["Peak", selectedBestRatingLast5], ["Avg L5", selectedAvgRatingLast5], ["Projected", selectedTodayProjectionFigure !== null ? renderMetricValue(selectedTodayProjectionFigure, 1) : "--"]] },
                      { title: "Run Stats", rows: [["Starts", firstText(selectedRunnerForm, ["form_history_starts"], "--")], ["Wins", firstText(selectedRunnerForm, ["form_history_wins"], "--")], ["Places", firstText(selectedRunnerForm, ["form_history_places"], "--")], ["Win / Place", `${winPct} / ${placePct}`]] },
                      { title: "Today Setup", rows: [["Distance", firstText(selected.row, ["distance", "race_distance", "distance_m", "race_distance_m"], "not loaded")], ["Class", firstText(selected.row, ["race_class", "class", "class_name"], "not loaded")], ["Condition", firstText(selected.row, ["condition", "track_condition", "official_condition", "edgeiq_condition"], "not loaded")], ["Barrier / Style", `${firstText(selected.row, ["barrier", "draw"], "--")} / ${firstText(selected.mapEnrichment || selected.row, ["run_style", "pace_style", "projected_run_style"], "--")}`]] },
                      { title: "Form Status", rows: [["Status", selectedFormStatus], ["Signal", firstText(selectedRunnerForm, ["form_signal"], "--")], ["Trend", selectedTrendRead], ["Quality", selectedFormDataQuality]] },
                    ].map((block) => (
                      <div key={`form-toprate-block-${block.title}`} style={formPanelStyle}>
                        <strong style={{ display: "block", color: "#7dd3fc", fontSize: 11, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 7 }}>{block.title}</strong>
                        <div style={{ display: "grid", gap: 4 }}>
                          {block.rows.map(([label, value]) => (
                            <div key={`${block.title}-${label}`} style={{ display: "grid", gridTemplateColumns: "78px minmax(0,1fr)", gap: 8, alignItems: "center" }}>
                              <span style={{ color: "#94a3b8", fontSize: 10.5, fontWeight: 850 }}>{label}</span>
                              <strong style={{ color: value && value !== "--" && value !== "not loaded" ? "#f8fafc" : "#64748b", fontSize: 11.5, fontWeight: 950, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{value}</strong>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </section>

                  <section style={{ ...formPanelStyle, padding: 0, overflow: "hidden" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center", padding: "9px 10px", background: "rgba(15,23,42,.92)", borderBottom: "1px solid rgba(80,120,180,.35)" }}>
                      <strong style={{ color: "#f8fafc", fontSize: 13, textTransform: "uppercase", letterSpacing: ".08em" }}>Last Five Runs</strong>
                      <span style={{ color: "#94a3b8", fontSize: 11, fontWeight: 900 }}>central evidence table</span>
                    </div>
                    {selectedIsContextOnly ? (
                      <div style={{ margin: 10, border: "1px solid rgba(245,196,81,.32)", borderRadius: 8, padding: 12, background: "rgba(245,196,81,.08)", color: "#f5c451", fontSize: 12, fontWeight: 900 }}>
                        Context only; no detailed rated-history lines available.
                      </div>
                    ) : (
                      <div style={{ overflowX: "auto" }}>
                        <div style={{ minWidth: 1120 }}>
                          <div style={{ display: "grid", gridTemplateColumns: "76px 52px 116px 86px 66px 126px 52px 70px 62px 70px minmax(170px,1fr)", gap: 0, background: "rgba(15,23,42,.86)", color: "#94a3b8", fontSize: 10, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".07em", borderBottom: "1px solid rgba(80,120,180,.35)" }}>
                            {['DATE','DLR','TRACK','GOING','DIST','CLASS','POS','MARGIN','SP','RATING','SOURCE / COMMENT'].map((label) => <span key={`form-head-${label}`} style={{ padding: "7px 8px", borderRight: "1px solid rgba(51,65,85,.5)" }}>{label}</span>)}
                          </div>
                          {lastFiveRuns.map((run, index) => {
                            const goingTone = conditionTone(run.going);
                            return (
                              <div key={`form-toprate-run-${run.n}`} style={{ display: "grid", gridTemplateColumns: "76px 52px 116px 86px 66px 126px 52px 70px 62px 70px minmax(170px,1fr)", gap: 0, background: index % 2 === 0 ? "rgba(8,15,28,.9)" : "rgba(15,23,42,.58)", borderBottom: "1px solid rgba(51,65,85,.48)", color: "#cbd5e1", fontSize: 11 }}>
                                <span style={{ padding: "7px 8px", fontWeight: 900 }}>{run.date || "--"}</span>
                                <span style={{ padding: "7px 8px", color: run.dlr !== null ? "#f5c451" : "#64748b", fontWeight: 900 }}>{run.dlr !== null ? run.dlr : "--"}</span>
                                <span style={{ padding: "7px 8px", color: run.trk ? "#f8fafc" : "#64748b", fontWeight: 900, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{run.trk || "--"}</span>
                                <span style={{ padding: "5px 7px" }}><span style={{ display: "inline-block", minWidth: 54, textAlign: "center", border: `1px solid ${goingTone.border}`, borderRadius: 4, padding: "2px 5px", background: goingTone.bg, color: goingTone.color, fontWeight: 950 }}>{run.going || "--"}</span></span>
                                <span style={{ padding: "7px 8px", ...(run.dist ? {} : mutedCell) }}>{run.dist ? `${run.dist}`.replace(".0", "") + "m" : "--"}</span>
                                <span style={{ padding: "7px 8px", color: run.cls ? "#cbd5e1" : "#64748b", fontWeight: 850, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{run.cls || "not loaded"}</span>
                                <span style={{ padding: "7px 8px", color: finishTone(run.pos), fontWeight: 1000 }}>{run.pos || "--"}</span>
                                <span style={{ padding: "7px 8px", color: run.margin ? "#cbd5e1" : "#64748b" }}>{run.margin || "--"}</span>
                                <span style={{ padding: "7px 8px", color: run.sp ? "#cbd5e1" : "#64748b" }}>{run.sp || "--"}</span>
                                <span style={{ padding: "7px 8px", color: formRatingTone(run.rating), fontWeight: 1000 }}>{run.rating !== null ? renderMetricValue(run.rating, 1) : "--"}</span>
                                <span style={{ padding: "7px 8px", color: run.source ? "#94a3b8" : "#64748b", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{run.source || "not loaded"}</span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </section>

                  <section style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0,1fr)) 1.2fr", gap: 8 }}>
                    {[
                      { title: "Distance Profile", value: distanceProfile },
                      { title: "Condition Profile", value: conditionProfile },
                      { title: "Class Profile", value: classProfile },
                    ].map((entry) => (
                      <div key={`form-profile-matrix-${entry.title}`} style={formPanelStyle}>
                        <strong style={{ color: "#7dd3fc", fontSize: 11, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".08em" }}>{entry.title}</strong>
                        <p style={{ color: entry.value ? "#dbe7fb" : "#64748b", fontSize: 11.5, lineHeight: 1.45, margin: "8px 0 0", fontWeight: 850 }}>{entry.value || "profile source not loaded"}</p>
                      </div>
                    ))}
                    <div style={{ ...formPanelStyle, border: `1px solid ${selectedTrendTone}44` }}>
                      <strong style={{ color: "#f8fafc", fontSize: 11, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".08em" }}>EDGEiQ Verdict</strong>
                      <p style={{ color: "#dbe7fb", fontSize: 12, lineHeight: 1.5, margin: "8px 0 0", fontWeight: 850 }}>{selectedFormVerdict}{missingDetail ? ` Missing source detail: ${missingDetail}.` : ""}</p>
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
print('FORM TopRate structure V1 applied')
print(f'checkpoint={checkpoint}')
