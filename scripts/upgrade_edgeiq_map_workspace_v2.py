from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
TSX=ROOT/'src'/'components'/'RaceIntelligenceScreen.tsx'
CHECKPOINT=ROOT/'src'/'components'/'RaceIntelligenceScreen_CHECKPOINT_MAP_WORKSPACE_V2_20260629.tsx'
REPORT=ROOT/'public'/'data'/'edgeiq_map_workspace_v2_upgrade_report.txt'
if not CHECKPOINT.exists(): shutil.copyfile(TSX,CHECKPOINT)
text=TSX.read_text(encoding='utf-8')
text=text.replace('mapEnrichment: "/data/edgeiq_map_enrichment_feed_v1.csv"','mapEnrichment: "/data/edgeiq_map_enrichment_feed_v2.csv"')
start=text.index('{intelMode === "MAP" ? (')
end=text.index('{intelMode === "FORM"', start)
new_block=r'''{intelMode === "MAP" ? (() => {
        const mapSourceRow = (item: EnrichedRunner): Row => ({ ...(item.row || {}), ...(item.mapEnrichment || {}) });
        const mapClean = (value: unknown, fallback = "—") => {
          const raw = String(value ?? "").trim();
          if (!raw || /^(UNKNOWN|NOT LOADED|SOURCE_MISSING|SOURCE GAP|NULL|NAN|UNDEFINED|0\.0)$/i.test(raw)) return fallback;
          return raw;
        };
        const mapNum = (item: EnrichedRunner, keys: string[]) => firstNum(mapSourceRow(item), keys);
        const mapText = (item: EnrichedRunner, keys: string[], fallback = "—") => mapClean(firstText(mapSourceRow(item), keys, ""), fallback);
        const mapTone = (value: string) => {
          const raw = value.toUpperCase();
          if (raw.includes("LEADER") || raw.includes("SUITED") || raw === "LOW" || raw.includes("HIGH CONF")) return "#34d399";
          if (raw.includes("ON PACE") || raw.includes("NEUTRAL") || raw === "MEDIUM") return "#7dd3fc";
          if (raw.includes("MIDFIELD") || raw.includes("TACTICAL") || raw.includes("MODERATE")) return "#f5c451";
          if (raw.includes("BACK") || raw.includes("RISK") || raw === "HIGH") return "#f87171";
          return "#94a3b8";
        };
        const mapRowsV2 = [...activeRaceRows].map((item) => {
          const src = mapSourceRow(item);
          const x = firstNum(src, ["map_x_pct_display", "map_x_pct"]);
          const y = firstNum(src, ["map_y_px_display", "map_y_px"]);
          return {
            item,
            key: runnerRowKey(item.row),
            horseName: horse(item.row),
            shortName: shortHorseName(horse(item.row), 13),
            saddle: mapClean(firstText(src, ["saddlecloth", "horse_no", "runner_no"], saddle(item.row) === 999 ? "" : String(saddle(item.row)))) ,
            barrier: mapClean(firstText(src, ["barrier"], barrier(item.row))),
            runStyle: mapClean(firstText(src, ["run_style_display", "run_style", "speed_map_bucket"], "")),
            earlySpeed: mapClean(firstText(src, ["early_speed_rating_display", "projected_speed_display", "early_speed", "projected_speed"], "")),
            paceFit: mapClean(firstText(src, ["pace_fit_display", "pace_fit_band", "pace_fit"], "")),
            settling: mapClean(firstText(src, ["settling_band_display", "settling_band", "settling_position"], "")),
            wideRisk: mapClean(firstText(src, ["wide_risk_display", "wide_risk"], "")),
            coverRisk: mapClean(firstText(src, ["cover_risk_display", "cover_risk"], "")),
            pressureRole: mapClean(firstText(src, ["pressure_role_display", "pressure_role"], "")),
            lateSpeed: mapClean(firstText(src, ["late_speed_display", "late_speed"], "")),
            confidence: mapClean(firstText(src, ["map_confidence_display", "map_confidence"], "")),
            evidence: mapClean(firstText(src, ["map_evidence_display", "map_evidence"], "")),
            lane: mapClean(firstText(src, ["map_lane_display", "map_lane"], "")),
            zone: mapClean(firstText(src, ["map_zone_display", "map_zone"], "")),
            x: x !== null ? clamp(x, 4, 96) : 74,
            y: y !== null ? clamp(y, 8, 94) : 50,
            selected: !!selected && runnerRowKey(item.row) === runnerRowKey(selected.row),
          };
        }).sort((a, b) => a.x - b.x || Number(a.barrier || 99) - Number(b.barrier || 99));
        const mapRaceSource = mapRowsV2[0]?.item ? mapSourceRow(mapRowsV2[0].item) : {};
        const raceFieldSizeV2 = firstText(mapRaceSource, ["race_field_size_map_v2"], String(activeRaceRows.length));
        const raceLeadersV2 = firstText(mapRaceSource, ["race_leader_count_v2"], String(mapRowsV2.filter((r) => r.runStyle === "LEADER").length));
        const raceOnPaceV2 = firstText(mapRaceSource, ["race_on_pace_count_v2"], String(mapRowsV2.filter((r) => r.runStyle === "ON PACE").length));
        const raceMidfieldV2 = firstText(mapRaceSource, ["race_midfield_count_v2"], String(mapRowsV2.filter((r) => r.runStyle === "MIDFIELD").length));
        const raceBackmarkersV2 = firstText(mapRaceSource, ["race_backmarker_count_v2"], String(mapRowsV2.filter((r) => r.runStyle === "BACKMARKER").length));
        const racePressureV2 = mapClean(firstText(mapRaceSource, ["race_pressure_band_v2", "race_pressure_band_display"], ""));
        const racePressureScoreV2 = mapClean(firstText(mapRaceSource, ["race_pressure_score_v2", "race_pressure_score_display"], ""));
        const raceShapeSummaryV2 = mapClean(firstText(mapRaceSource, ["race_shape_summary_v2"], ""));
        const raceShapeVerdictV2 = mapClean(firstText(mapRaceSource, ["race_shape_verdict_v2"], ""));
        const paceAdvantageV2 = mapClean(firstText(mapRaceSource, ["pace_advantage_display"], ""));
        const mapConfidenceV2 = mapClean(firstText(mapRaceSource, ["map_confidence_display"], ""));
        const selectedMapV2 = selected ? mapRowsV2.find((row) => row.key === runnerRowKey(selected.row)) : null;
        const selectedMapVerdict = selectedMapV2
          ? `${selectedMapV2.horseName} maps as ${selectedMapV2.runStyle.toLowerCase()} from barrier ${selectedMapV2.barrier}. Pace fit is ${selectedMapV2.paceFit.toLowerCase()} with ${selectedMapV2.wideRisk.toLowerCase()} wide risk and ${selectedMapV2.coverRisk.toLowerCase()} cover risk.`
          : "Select a runner to inspect the map read.";
        const summaryCards = [
          { label: "Field Size", value: raceFieldSizeV2, tone: "#f8fafc" },
          { label: "Leaders", value: raceLeadersV2, tone: "#34d399" },
          { label: "On Pace", value: raceOnPaceV2, tone: "#7dd3fc" },
          { label: "Midfield", value: raceMidfieldV2, tone: "#f5c451" },
          { label: "Backmarkers", value: raceBackmarkersV2, tone: "#f87171" },
          { label: "Pressure", value: `${racePressureV2} ${racePressureScoreV2 !== "—" ? `(${racePressureScoreV2})` : ""}`, tone: mapTone(racePressureV2) },
          { label: "Pace Advantage", value: paceAdvantageV2, tone: mapTone(paceAdvantageV2) },
          { label: "Map Confidence", value: mapConfidenceV2, tone: mapTone(mapConfidenceV2) },
        ];
        return (
          <section style={workspaceSectionStyle}>
            <div style={titleStyle}>
              <span>MAP WORKSPACE</span>
              <em>{raceShapeSummaryV2}</em>
            </div>

            <section style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(130px, 1fr))", gap: 8, marginBottom: 12 }}>
              {summaryCards.map((card) => (
                <div key={`map-v2-summary-${card.label}`} style={{ border: "1px solid rgba(80,120,180,.26)", borderRadius: 8, padding: 9, background: "rgba(5,12,22,.78)" }}>
                  <span style={{ color: "#94a3b8", fontSize: 10, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".08em" }}>{card.label}</span>
                  <strong style={{ display: "block", color: card.tone, fontSize: 13, fontWeight: 1000, marginTop: 4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{card.value}</strong>
                </div>
              ))}
            </section>

            <section style={{ display: "grid", gridTemplateColumns: "minmax(0,1.35fr) minmax(360px,.65fr)", gap: 12, alignItems: "start" }}>
              <div style={{ border: "1px solid rgba(125,211,252,.22)", borderRadius: 10, padding: 12, background: "linear-gradient(135deg, rgba(5,12,22,.96), rgba(8,20,34,.86))" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center", marginBottom: 10 }}>
                  <strong style={{ color: "#f8fafc", fontSize: 13, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".08em" }}>Speed Map Visual</strong>
                  <span style={{ color: "#94a3b8", fontSize: 10.5, fontWeight: 900 }}>Barrier 1 bottom | leaders left</span>
                </div>
                <div style={{ position: "relative", height: 430, border: "1px solid rgba(80,120,180,.24)", borderRadius: 10, overflow: "hidden", background: "linear-gradient(90deg, rgba(6,78,59,.12), rgba(30,41,59,.22), rgba(76,29,149,.08))" }}>
                  {[{ label: "LEADERS", left: 5, width: 22, color: "#34d399" }, { label: "ON PACE", left: 27, width: 23, color: "#7dd3fc" }, { label: "MIDFIELD", left: 50, width: 25, color: "#f5c451" }, { label: "BACKMARKERS", left: 75, width: 20, color: "#f87171" }].map((band) => (
                    <div key={`map-v2-band-${band.label}`} style={{ position: "absolute", left: `${band.left}%`, top: 0, bottom: 0, width: `${band.width}%`, borderLeft: "1px solid rgba(148,163,184,.14)", color: band.color, fontSize: 10, fontWeight: 1000, letterSpacing: ".08em", textTransform: "uppercase", padding: 8, pointerEvents: "none" }}>{band.label}</div>
                  ))}
                  {[20,40,60,80].map((line) => <div key={`map-v2-grid-${line}`} style={{ position: "absolute", left: 0, right: 0, top: `${line}%`, height: 1, background: "rgba(148,163,184,.10)" }} />)}
                  {mapRowsV2.map((row) => (
                    <button
                      key={`map-v2-point-${row.key}`}
                      type="button"
                      onClick={() => { setSelectedKey(row.key); setDrawerOpen(true); }}
                      title={`${row.horseName} | ${row.runStyle} | Barrier ${row.barrier} | Pace ${row.paceFit}`}
                      style={{ position: "absolute", left: `${row.x}%`, top: `${row.y}%`, transform: "translate(-50%, -50%)", border: `1px solid ${row.selected ? "rgba(224,242,254,.92)" : `${mapTone(row.runStyle)}88`}`, borderRadius: 999, padding: "5px 8px", background: row.selected ? "rgba(8,47,73,.98)" : "rgba(5,12,22,.92)", color: row.selected ? "#e0f2fe" : "#f8fafc", boxShadow: row.selected ? "0 0 0 3px rgba(56,189,248,.20), 0 0 18px rgba(56,189,248,.18)" : "0 8px 18px rgba(2,6,23,.25)", display: "flex", gap: 5, alignItems: "center", cursor: "pointer", maxWidth: 150 }}>
                        <span style={{ minWidth: 20, height: 20, borderRadius: 999, display: "grid", placeItems: "center", background: mapTone(row.runStyle), color: "#020617", fontSize: 10, fontWeight: 1000 }}>{row.saddle}</span>
                        <strong style={{ fontSize: 10.5, fontWeight: 1000, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{row.shortName}</strong>
                      </button>
                    ))}
                </div>
              </div>

              <div style={{ display: "grid", gap: 10 }}>
                <section style={{ border: "1px solid rgba(80,120,180,.26)", borderRadius: 10, padding: 11, background: "rgba(8,15,28,.80)" }}>
                  <strong style={{ color: "#f8fafc", fontSize: 12.5, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".08em" }}>Selected Runner Map Card</strong>
                  {selectedMapV2 ? (
                    <div style={{ display: "grid", gap: 8, marginTop: 10 }}>
                      <strong style={{ color: "#e0f2fe", fontSize: 18, fontWeight: 1000 }}>{selectedMapV2.horseName}</strong>
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0,1fr))", gap: 7 }}>
                        {[['Barrier', selectedMapV2.barrier], ['Run Style', selectedMapV2.runStyle], ['Early Speed', selectedMapV2.earlySpeed], ['Expected Position', selectedMapV2.zone], ['Pace Fit', selectedMapV2.paceFit], ['Wide Risk', selectedMapV2.wideRisk], ['Cover Risk', selectedMapV2.coverRisk], ['Pressure Role', selectedMapV2.pressureRole], ['Late Speed', selectedMapV2.lateSpeed], ['Evidence', selectedMapV2.evidence]].map(([label, value]) => (
                          <div key={`selected-map-v2-${label}`} style={{ border: "1px solid rgba(80,120,180,.20)", borderRadius: 8, padding: 7, background: "rgba(5,12,22,.68)" }}>
                            <span style={{ color: "#94a3b8", fontSize: 9.5, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".07em" }}>{label}</span>
                            <strong style={{ display: "block", color: mapTone(String(value)), fontSize: 11.5, fontWeight: 1000, marginTop: 3 }}>{value}</strong>
                          </div>
                        ))}
                      </div>
                      <p style={{ margin: 0, color: "#dbe7fb", fontSize: 12, lineHeight: 1.55, fontWeight: 850 }}>{selectedMapVerdict}</p>
                    </div>
                  ) : <p style={{ color: "#94a3b8", fontSize: 12 }}>Select a runner to inspect the map read.</p>}
                </section>

                <section style={{ border: "1px solid rgba(80,120,180,.26)", borderRadius: 10, padding: 11, background: "rgba(8,15,28,.80)" }}>
                  <strong style={{ color: "#f8fafc", fontSize: 12.5, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".08em" }}>Race Shape Verdict</strong>
                  <p style={{ margin: "8px 0 0", color: "#dbe7fb", fontSize: 12, lineHeight: 1.55, fontWeight: 850 }}>{raceShapeVerdictV2}</p>
                </section>
              </div>
            </section>

            <section style={{ marginTop: 12, border: "1px solid rgba(80,120,180,.26)", borderRadius: 10, overflow: "hidden", background: "rgba(8,15,28,.78)" }}>
              <div style={{ display: "grid", gridTemplateColumns: "42px minmax(160px,1.4fr) 70px 110px 92px 88px 92px 104px", gap: 0, padding: "8px 10px", background: "rgba(15,23,42,.92)", color: "#94a3b8", fontSize: 10, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".07em" }}>
                {['#','Horse','Barrier','Run Style','Early Speed','Pace Fit','Settling','Wide Risk'].map((label) => <span key={`map-v2-table-head-${label}`}>{label}</span>)}
              </div>
              {mapRowsV2.map((row) => (
                <button key={`map-v2-table-${row.key}`} type="button" onClick={() => { setSelectedKey(row.key); setDrawerOpen(true); }} style={{ appearance: "none", display: "grid", gridTemplateColumns: "42px minmax(160px,1.4fr) 70px 110px 92px 88px 92px 104px", gap: 0, width: "100%", padding: "8px 10px", border: 0, borderTop: "1px solid rgba(51,65,85,.55)", background: row.selected ? "rgba(8,47,73,.58)" : "rgba(5,12,22,.68)", color: "#dbe7fb", textAlign: "left", cursor: "pointer", alignItems: "center" }}>
                  <strong style={{ color: row.selected ? "#7dd3fc" : "#f8fafc", fontSize: 11 }}>{row.saddle}</strong>
                  <strong style={{ color: "#f8fafc", fontSize: 11.5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{row.horseName}</strong>
                  <span style={{ color: "#cbd5e1", fontSize: 11, fontWeight: 900 }}>{row.barrier}</span>
                  <span style={{ color: mapTone(row.runStyle), fontSize: 10.5, fontWeight: 1000 }}>{row.runStyle}</span>
                  <span style={{ color: "#7dd3fc", fontSize: 10.5, fontWeight: 900 }}>{row.earlySpeed}</span>
                  <span style={{ color: mapTone(row.paceFit), fontSize: 10.5, fontWeight: 1000 }}>{row.paceFit}</span>
                  <span style={{ color: mapTone(row.settling), fontSize: 10.5, fontWeight: 900 }}>{row.settling}</span>
                  <span style={{ color: mapTone(row.wideRisk), fontSize: 10.5, fontWeight: 1000 }}>{row.wideRisk}</span>
                </button>
              ))}
            </section>
          </section>
        );
      })() : null}
'''
text=text[:start]+new_block+text[end:]
TSX.write_text(text,encoding='utf-8')
REPORT.write_text('EDGEiQ MAP workspace V2 applied\ncheckpoint='+str(CHECKPOINT)+'\nstatus=MAP_WORKSPACE_V2_APPLIED\n',encoding='utf-8')
print(REPORT.read_text(encoding='utf-8'))
