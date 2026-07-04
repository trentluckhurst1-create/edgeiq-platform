from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
TSX=ROOT/'src'/'components'/'RaceIntelligenceScreen.tsx'
CHECKPOINT=ROOT/'src'/'components'/'RaceIntelligenceScreen_CHECKPOINT_MAP_LANE_VISUAL_V1_20260629.tsx'
REPORT=ROOT/'public'/'data'/'edgeiq_map_lane_visual_fix_v1_report.txt'
if not CHECKPOINT.exists(): shutil.copyfile(TSX,CHECKPOINT)
s=TSX.read_text(encoding='utf-8')
old='''        const selectedMapV2 = selected ? mapRowsV2.find((row) => row.key === runnerRowKey(selected.row)) : null;
        const selectedMapVerdict = selectedMapV2'''
new='''        const mapLaneRowsV1 = [...mapRowsV2].sort((a, b) => {
          const barrierA = Number(a.barrier);
          const barrierB = Number(b.barrier);
          const validA = Number.isFinite(barrierA) && barrierA > 0;
          const validB = Number.isFinite(barrierB) && barrierB > 0;
          if (validA && validB) return barrierB - barrierA;
          if (validA) return -1;
          if (validB) return 1;
          return a.x - b.x;
        });
        const selectedMapV2 = selected ? mapRowsV2.find((row) => row.key === runnerRowKey(selected.row)) : null;
        const selectedMapVerdict = selectedMapV2'''
if old not in s: raise SystemExit('mapLaneRows insertion anchor not found')
s=s.replace(old,new,1)
old_visual='''                <div style={{ position: "relative", height: 430, border: "1px solid rgba(80,120,180,.24)", borderRadius: 10, overflow: "hidden", background: "linear-gradient(90deg, rgba(6,78,59,.12), rgba(30,41,59,.22), rgba(76,29,149,.08))" }}>
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
                </div>'''
new_visual='''                <div style={{ position: "relative", border: "1px solid rgba(80,120,180,.24)", borderRadius: 10, overflow: "hidden", background: "linear-gradient(90deg, rgba(6,78,59,.12), rgba(30,41,59,.22), rgba(76,29,149,.08))" }}>
                  <div style={{ position: "relative", height: 28, borderBottom: "1px solid rgba(80,120,180,.20)", background: "rgba(15,23,42,.72)" }}>
                    {[{ label: "LEADERS", left: 5, width: 22, color: "#34d399" }, { label: "ON PACE", left: 27, width: 23, color: "#7dd3fc" }, { label: "MIDFIELD", left: 50, width: 25, color: "#f5c451" }, { label: "BACKMARKERS", left: 75, width: 20, color: "#f87171" }].map((band) => (
                      <span key={`map-lane-zone-${band.label}`} style={{ position: "absolute", left: `${band.left}%`, width: `${band.width}%`, top: 7, color: band.color, fontSize: 10, fontWeight: 1000, letterSpacing: ".08em", textTransform: "uppercase", textAlign: "center" }}>{band.label}</span>
                    ))}
                  </div>
                  <div style={{ display: "grid" }}>
                    {mapLaneRowsV1.map((row, laneIndex) => (
                      <button
                        key={`map-lane-row-${row.key}`}
                        type="button"
                        onClick={() => { setSelectedKey(row.key); setDrawerOpen(true); }}
                        title={`${row.horseName} | Barrier ${row.barrier} | Rank ${row.speedRank} | Gap ${row.speedGap} | ${row.runStyle}`}
                        style={{ position: "relative", minHeight: 34, border: 0, borderTop: laneIndex === 0 ? 0 : "1px solid rgba(51,65,85,.55)", background: row.selected ? "rgba(8,47,73,.52)" : laneIndex % 2 === 0 ? "rgba(5,12,22,.72)" : "rgba(15,23,42,.50)", cursor: "pointer", textAlign: "left", overflow: "hidden" }}
                      >
                        <span style={{ position: "absolute", left: 8, top: "50%", transform: "translateY(-50%)", width: 30, color: "#94a3b8", fontSize: 10, fontWeight: 1000, textAlign: "center" }}>B{row.barrier}</span>
                        <span style={{ position: "absolute", left: 44, right: 8, top: "50%", height: 1, background: "linear-gradient(90deg, rgba(125,211,252,.22), rgba(148,163,184,.10))" }} />
                        {[27,50,75].map((line) => <span key={`map-lane-divider-${row.key}-${line}`} style={{ position: "absolute", left: `${line}%`, top: 0, bottom: 0, width: 1, background: "rgba(148,163,184,.10)" }} />)}
                        <span style={{ position: "absolute", left: `calc(44px + (${row.x}% * .86))`, top: "50%", transform: "translate(-50%, -50%)", border: `1px solid ${row.selected ? "rgba(224,242,254,.92)" : `${mapTone(row.runStyle)}88`}`, borderRadius: 999, padding: "4px 8px", background: row.selected ? "rgba(8,47,73,.98)" : "rgba(5,12,22,.95)", color: row.selected ? "#e0f2fe" : "#f8fafc", boxShadow: row.selected ? "0 0 0 3px rgba(56,189,248,.20), 0 0 18px rgba(56,189,248,.18)" : "0 6px 14px rgba(2,6,23,.22)", display: "inline-flex", gap: 5, alignItems: "center", maxWidth: 168 }}>
                          <span style={{ minWidth: 20, height: 20, borderRadius: 999, display: "grid", placeItems: "center", background: mapTone(row.runStyle), color: "#020617", fontSize: 10, fontWeight: 1000 }}>{row.saddle}</span>
                          <strong style={{ fontSize: 10.5, fontWeight: 1000, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{row.shortName}</strong>
                        </span>
                      </button>
                    ))}
                  </div>
                </div>'''
if old_visual not in s: raise SystemExit('visual block not found')
s=s.replace(old_visual,new_visual,1)
TSX.write_text(s,encoding='utf-8')
REPORT.write_text('EDGEiQ MAP lane visual restored\ncheckpoint='+str(CHECKPOINT)+'\nstatus=MAP_LANE_VISUAL_V1_APPLIED\n',encoding='utf-8')
print(REPORT.read_text())
