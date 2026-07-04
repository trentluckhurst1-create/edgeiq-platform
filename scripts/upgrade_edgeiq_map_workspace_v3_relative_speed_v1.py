from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
TSX=ROOT/'src'/'components'/'RaceIntelligenceScreen.tsx'
CHECKPOINT=ROOT/'src'/'components'/'RaceIntelligenceScreen_CHECKPOINT_MAP_V3_RELATIVE_SPEED_20260629.tsx'
REPORT=ROOT/'public'/'data'/'edgeiq_map_workspace_v3_relative_speed_upgrade_report.txt'
if not CHECKPOINT.exists(): shutil.copyfile(TSX,CHECKPOINT)
s=TSX.read_text(encoding='utf-8')
s=s.replace('mapEnrichment: "/data/edgeiq_map_enrichment_feed_v2.csv"','mapEnrichment: "/data/edgeiq_map_enrichment_feed_v3.csv"')
repls={
'["map_x_pct_display", "map_x_pct"]':'["map_x_pct_display_v3", "map_x_pct_display", "map_x_pct"]',
'["map_y_px_display", "map_y_px"]':'["map_y_px_display_v3", "map_y_px_display", "map_y_px"]',
'["run_style_display", "run_style", "speed_map_bucket"]':'["run_style_display_v3", "run_style_display", "run_style", "speed_map_bucket"]',
'["early_speed_rating_display", "projected_speed_display", "early_speed", "projected_speed"]':'["early_speed_rating_display", "projected_speed_display", "early_speed", "projected_speed"]',
'["pace_fit_display", "pace_fit_band", "pace_fit"]':'["pace_fit_display", "pace_fit_band", "pace_fit"]',
'["settling_band_display", "settling_band", "settling_position"]':'["settling_band_display_v3", "settling_band_display", "settling_band", "settling_position"]',
'["wide_risk_display", "wide_risk"]':'["wide_risk_display", "wide_risk"]',
'["race_leader_count_v2"]':'["race_leader_count_v3", "race_leader_count_v2"]',
'["race_on_pace_count_v2"]':'["race_on_pace_count_v3", "race_on_pace_count_v2"]',
'["race_midfield_count_v2"]':'["race_midfield_count_v3", "race_midfield_count_v2"]',
'["race_backmarker_count_v2"]':'["race_backmarker_count_v3", "race_backmarker_count_v2"]',
'["race_pressure_band_v2", "race_pressure_band_display"]':'["race_pressure_band_v3", "race_pressure_band_v2", "race_pressure_band_display"]',
'["race_pressure_score_v2", "race_pressure_score_display"]':'["race_pressure_score_v3", "race_pressure_score_v2", "race_pressure_score_display"]',
'["race_shape_summary_v2"]':'["race_shape_summary_v3", "race_shape_summary_v2"]',
'["race_shape_verdict_v2"]':'["race_shape_verdict_v3", "race_shape_verdict_v2"]',
'["pace_advantage_display"]':'["pace_advantage_display_v3", "pace_advantage_display"]',
'["map_confidence_display"]':'["map_confidence_display_v3", "map_confidence_display"]'
}
for a,b in repls.items(): s=s.replace(a,b)
# Add rank/gap fields into mapRowsV2 object after confidence.
s=s.replace('''            confidence: mapClean(firstText(src, ["map_confidence_display_v3", "map_confidence_display", "map_confidence"], "")),
            evidence:''','''            confidence: mapClean(firstText(src, ["map_confidence_display_v3", "map_confidence_display", "map_confidence"], "")),
            speedRank: mapClean(firstText(src, ["speed_rank_v3"], "")),
            speedGap: mapClean(firstText(src, ["speed_gap_to_leader_v3"], "")),
            relativeBand: mapClean(firstText(src, ["relative_speed_band_v3"], "")),
            evidence:''')
# Selected card include rank/gap.
s=s.replace("[['Barrier', selectedMapV2.barrier], ['Run Style', selectedMapV2.runStyle], ['Early Speed', selectedMapV2.earlySpeed]", "[['Barrier', selectedMapV2.barrier], ['Speed Rank', selectedMapV2.speedRank], ['Speed Gap', selectedMapV2.speedGap], ['Run Style', selectedMapV2.runStyle], ['Early Speed', selectedMapV2.earlySpeed]")
s=s.replace('''              <div style={{ display: "grid", gridTemplateColumns: "42px minmax(160px,1.4fr) 70px 110px 92px 88px 92px 104px", gap: 0, padding: "8px 10px", background: "rgba(15,23,42,.92)", color: "#94a3b8", fontSize: 10, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".07em" }}>
                {['#','Horse','Barrier','Run Style','Early Speed','Pace Fit','Settling','Wide Risk'].map((label) => <span key={`map-v2-table-head-${label}`}>{label}</span>)}
              </div>''','''              <div style={{ display: "grid", gridTemplateColumns: "42px minmax(150px,1.3fr) 70px 76px 76px 96px 88px 96px 104px", gap: 0, padding: "8px 10px", background: "rgba(15,23,42,.92)", color: "#94a3b8", fontSize: 10, fontWeight: 1000, textTransform: "uppercase", letterSpacing: ".07em" }}>
                {['#','Horse','Barrier','Speed Rank','Speed Gap','Style','Pace Fit','Wide Risk','Confidence'].map((label) => <span key={`map-v3-table-head-${label}`}>{label}</span>)}
              </div>''')
s=s.replace('''                <button key={`map-v2-table-${row.key}`} type="button" onClick={() => { setSelectedKey(row.key); setDrawerOpen(true); }} style={{ appearance: "none", display: "grid", gridTemplateColumns: "42px minmax(160px,1.4fr) 70px 110px 92px 88px 92px 104px", gap: 0, width: "100%", padding: "8px 10px", border: 0, borderTop: "1px solid rgba(51,65,85,.55)", background: row.selected ? "rgba(8,47,73,.58)" : "rgba(5,12,22,.68)", color: "#dbe7fb", textAlign: "left", cursor: "pointer", alignItems: "center" }}>
                  <strong style={{ color: row.selected ? "#7dd3fc" : "#f8fafc", fontSize: 11 }}>{row.saddle}</strong>
                  <strong style={{ color: "#f8fafc", fontSize: 11.5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{row.horseName}</strong>
                  <span style={{ color: "#cbd5e1", fontSize: 11, fontWeight: 900 }}>{row.barrier}</span>
                  <span style={{ color: mapTone(row.runStyle), fontSize: 10.5, fontWeight: 1000 }}>{row.runStyle}</span>
                  <span style={{ color: "#7dd3fc", fontSize: 10.5, fontWeight: 900 }}>{row.earlySpeed}</span>
                  <span style={{ color: mapTone(row.paceFit), fontSize: 10.5, fontWeight: 1000 }}>{row.paceFit}</span>
                  <span style={{ color: mapTone(row.settling), fontSize: 10.5, fontWeight: 900 }}>{row.settling}</span>
                  <span style={{ color: mapTone(row.wideRisk), fontSize: 10.5, fontWeight: 1000 }}>{row.wideRisk}</span>''','''                <button key={`map-v3-table-${row.key}`} type="button" onClick={() => { setSelectedKey(row.key); setDrawerOpen(true); }} style={{ appearance: "none", display: "grid", gridTemplateColumns: "42px minmax(150px,1.3fr) 70px 76px 76px 96px 88px 96px 104px", gap: 0, width: "100%", padding: "8px 10px", border: 0, borderTop: "1px solid rgba(51,65,85,.55)", background: row.selected ? "rgba(8,47,73,.58)" : "rgba(5,12,22,.68)", color: "#dbe7fb", textAlign: "left", cursor: "pointer", alignItems: "center" }}>
                  <strong style={{ color: row.selected ? "#7dd3fc" : "#f8fafc", fontSize: 11 }}>{row.saddle}</strong>
                  <strong style={{ color: "#f8fafc", fontSize: 11.5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{row.horseName}</strong>
                  <span style={{ color: "#cbd5e1", fontSize: 11, fontWeight: 900 }}>{row.barrier}</span>
                  <span style={{ color: "#7dd3fc", fontSize: 10.5, fontWeight: 1000 }}>{row.speedRank}</span>
                  <span style={{ color: "#f5c451", fontSize: 10.5, fontWeight: 1000 }}>{row.speedGap}</span>
                  <span style={{ color: mapTone(row.runStyle), fontSize: 10.5, fontWeight: 1000 }}>{row.runStyle}</span>
                  <span style={{ color: mapTone(row.paceFit), fontSize: 10.5, fontWeight: 1000 }}>{row.paceFit}</span>
                  <span style={{ color: mapTone(row.wideRisk), fontSize: 10.5, fontWeight: 1000 }}>{row.wideRisk}</span>
                  <span style={{ color: mapTone(row.confidence), fontSize: 10.5, fontWeight: 1000 }}>{row.confidence}</span>''')
TSX.write_text(s,encoding='utf-8')
REPORT.write_text('EDGEiQ MAP workspace V3 relative speed applied\ncheckpoint='+str(CHECKPOINT)+'\nstatus=MAP_WORKSPACE_V3_RELATIVE_SPEED_APPLIED\n',encoding='utf-8')
print(REPORT.read_text())
