from pathlib import Path
import re
import shutil
ROOT = Path(__file__).resolve().parents[1]
TSX = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
CHECKPOINT = ROOT / "src" / "components" / "RaceIntelligenceScreen_CHECKPOINT_FORM_COMMERCIAL_V3_FEATURES_20260629.tsx"
REPORT = ROOT / "public" / "data" / "edgeiq_form_commercial_v3_features_upgrade_v1_report.txt"
if not CHECKPOINT.exists(): shutil.copyfile(TSX, CHECKPOINT)
text = TSX.read_text(encoding="utf-8")
original = text
form_start = text.index('{intelMode === "FORM"')
form_end = text.index('{intelMode === "RUNNERS"', form_start)
before, block, after = text[:form_start], text[form_start:form_end], text[form_end:]
block = re.sub(r'const selectedFormScoreBand = .*?;', 'const selectedFormScoreBand = selectedFormScore === null ? "LIMITED" : selectedFormScore >= 85 ? "ELITE" : selectedFormScore >= 80 ? "STRONG" : selectedFormScore >= 70 ? "AVERAGE" : selectedFormScore >= 55 ? "WATCH" : "RISK";', block, count=1, flags=re.S)
insert_after_lastfive = '''        const cleanFormToken = (value: string) => {
          const raw = String(value || "").trim();
          if (!raw || raw === "—" || /^(UNKNOWN|NOT LOADED|SOURCE GAP|NULL|NAN|UNDEFINED)$/i.test(raw)) return "—";
          return raw;
        };
        const formFigures = selectedIsContextOnly
          ? "Context only"
          : lastFiveRuns.length
            ? lastFiveRuns.map((run) => cleanFormToken(run.pos) === "—" ? "--" : cleanFormToken(run.pos)).join("-")
            : "--";
        const reliableRatingRuns = lastFiveRuns.filter((run) => run.rating !== null && Number.isFinite(run.rating));
        const ratingTrendText = reliableRatingRuns.length >= 2
          ? reliableRatingRuns.map((run) => renderMetricValue(run.rating, 1)).join(" → ")
          : "Insufficient rated trend";
        const ratingTrendSentence = reliableRatingRuns.length >= 2 ? `Rated trend: ${ratingTrendText}.` : "Rated trend is insufficient from reliable figures.";
        const outlierWarning = lastFiveRuns.some((run) => String(run.source || "").toUpperCase().includes("RATING NOT RELIABLE")) ? "One or more historical ratings were hidden because the source rating was not reliable." : "";
        const careerSnapshotItems = [
          { label: "Career", value: (() => {
            const starts = firstText(selectedRunnerForm, ["form_history_starts"], "");
            const wins = firstText(selectedRunnerForm, ["form_history_wins"], "");
            const places = firstText(selectedRunnerForm, ["form_history_places"], "");
            return starts ? `${starts}-${wins || "0"}-${places || "0"}` : "";
          })() },
          { label: "Track", value: firstText(selectedRunnerForm, ["track_profile_display", "track_profile", "track_read"], "") },
          { label: "Distance", value: firstText(selectedRunnerForm, ["distance_profile_display_v2", "distance_profile_display"], "") },
          { label: "Condition", value: firstText(selectedRunnerForm, ["condition_profile_display_v2", "condition_profile_display"], "") },
          { label: "Class", value: firstText(selectedRunnerForm, ["class_profile_display_v2", "class_profile_display"], "") },
        ].filter((item) => cleanFormToken(item.value) !== "—" && !String(item.value || "").toUpperCase().includes("NOT ENOUGH EVIDENCE"));
'''
if 'const cleanFormToken = (value: string)' not in block:
    block = block.replace('        }).filter((run) => run.hasRun);\n', '        }).filter((run) => run.hasRun);\n' + insert_after_lastfive, 1)
profile_add = '''
        const richProfileText = (profile: "distance" | "condition" | "class", fallback: string) => {
          const title = profile.charAt(0).toUpperCase() + profile.slice(1);
          const starts = firstText(selectedRunnerForm, [`${profile}_starts`, `${profile}_profile_starts`, `${profile}_history_starts`], "");
          const wins = firstText(selectedRunnerForm, [`${profile}_wins`, `${profile}_profile_wins`, `${profile}_history_wins`], "");
          const places = firstText(selectedRunnerForm, [`${profile}_places`, `${profile}_profile_places`, `${profile}_history_places`], "");
          const peak = firstText(selectedRunnerForm, [`${profile}_peak_rating`, `${profile}_profile_peak_rating`, `${profile}_best_rating`], "");
          const band = firstText(selectedRunnerForm, [`${profile}_profile_band`, `${profile}_band`, `${profile}_truth_status`], "").replace(/_/g, " ");
          const parts = [];
          if (starts) parts.push(`${starts} starts${wins ? `, ${wins} wins` : ""}${places ? `, ${places} places` : ""}`);
          if (peak) parts.push(`peak ${peak}`);
          if (band) parts.push(band);
          if (parts.length) return `${title}: ${parts.join(" | ")}`;
          return cleanFormToken(fallback) !== "—" ? fallback : "Not Enough Evidence";
        };
        const richDistanceProfile = richProfileText("distance", distanceProfile);
        const richConditionProfile = richProfileText("condition", conditionProfile);
        const richClassProfile = richProfileText("class", classProfile);
        const setupProfileSentence = [richDistanceProfile, richConditionProfile, richClassProfile].filter((value) => value && !String(value).toUpperCase().includes("NOT ENOUGH EVIDENCE")).length ? "Setup profile evidence is available for today's distance, condition or class." : "Setup profile evidence remains limited.";
        const selectedFormVerdictEnhanced = [selectedFormVerdict, ratingTrendSentence, setupProfileSentence, outlierWarning].filter(Boolean).join(" ");
'''
if 'const richProfileText = ' not in block:
    block = re.sub(r'(        const classProfile = .*?;\n)', r'\1' + profile_add, block, count=1)
header_old = '''                          {firstText(selected.row, ["age_sex", "age", "sex"], "") ? <span>Age/Sex: {firstText(selected.row, ["age_sex", "age", "sex"], "")}</span> : null}
                        </div>'''
header_new = '''                          {firstText(selected.row, ["age_sex", "age", "sex"], "") ? <span>Age/Sex: {firstText(selected.row, ["age_sex", "age", "sex"], "")}</span> : null}
                        </div>
                        <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) minmax(0,1.45fr)", gap: 8, marginTop: 2 }}>
                          <div style={{ border: "1px solid rgba(80,120,180,.28)", borderRadius: 8, padding: "7px 8px", background: "rgba(5,12,22,.64)" }}>
                            <span style={{ color: "#94a3b8", fontSize: 9.5, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".08em" }}>Form Figures</span>
                            <strong style={{ display: "block", color: selectedIsContextOnly ? "#94a3b8" : "#f8fafc", fontSize: 13, fontWeight: 1000, marginTop: 3 }}>{formFigures}</strong>
                          </div>
                          <div style={{ border: "1px solid rgba(80,120,180,.28)", borderRadius: 8, padding: "7px 8px", background: "rgba(5,12,22,.64)" }}>
                            <span style={{ color: "#94a3b8", fontSize: 9.5, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".08em" }}>Rating Trend</span>
                            <strong style={{ display: "block", color: reliableRatingRuns.length >= 2 ? "#7dd3fc" : "#64748b", fontSize: 12, fontWeight: 950, marginTop: 3, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{ratingTrendText}</strong>
                          </div>
                        </div>'''
if 'Form Figures</span>' not in block:
    if header_old not in block: raise SystemExit('header anchor not found')
    block = block.replace(header_old, header_new, 1)
section_old = '''                  </section>

                  <section style={{ display: "grid", gridTemplateColumns: "1.05fr .95fr 1.05fr .95fr", gap: 8 }}>'''
section_new = '''                  </section>

                  {careerSnapshotItems.length ? (
                    <section style={{ ...formPanelStyle, display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
                      <strong style={{ color: "#7dd3fc", fontSize: 10.5, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".08em", marginRight: 2 }}>Career Snapshot</strong>
                      {careerSnapshotItems.map((item) => (
                        <span key={`form-career-snapshot-${item.label}`} style={{ border: "1px solid rgba(80,120,180,.32)", borderRadius: 999, padding: "5px 8px", background: "rgba(15,23,42,.68)", color: "#dbe7fb", fontSize: 11, fontWeight: 900 }}>
                          <em style={{ color: "#94a3b8", fontStyle: "normal", marginRight: 5 }}>{item.label}</em>{item.value}
                        </span>
                      ))}
                    </section>
                  ) : null}

                  <section style={{ display: "grid", gridTemplateColumns: "1.05fr .95fr 1.05fr .95fr", gap: 8 }}>'''
if 'Career Snapshot</strong>' not in block:
    if section_old not in block: raise SystemExit('section anchor not found')
    block = block.replace(section_old, section_new, 1)
block = block.replace('''                      { title: "Distance Profile", value: distanceProfile },
                      { title: "Condition Profile", value: conditionProfile },
                      { title: "Class Profile", value: classProfile },''','''                      { title: "Distance Profile", value: richDistanceProfile },
                      { title: "Condition Profile", value: richConditionProfile },
                      { title: "Class Profile", value: richClassProfile },''')
block = block.replace('''{selectedFormVerdict.split(". ").join(".\n\n")}{missingDetail ? `\n\nSome setup fields are unavailable from source: ${missingDetail}.` : ""}''','''{selectedFormVerdictEnhanced.split(". ").join(".\n\n")}{missingDetail ? `\n\nSome setup fields are unavailable from source: ${missingDetail}.` : ""}''')
text = before + block + after
if text == original: raise SystemExit('No changes applied')
TSX.write_text(text, encoding='utf-8')
REPORT.write_text(f"EDGEiQ FORM commercial V3 features applied\ncheckpoint={CHECKPOINT}\nstatus=FORM_COMMERCIAL_V3_FEATURES_APPLIED\n", encoding='utf-8')
print(REPORT.read_text(encoding='utf-8'))
