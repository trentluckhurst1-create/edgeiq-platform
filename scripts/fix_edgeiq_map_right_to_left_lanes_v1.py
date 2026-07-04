from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
TSX=ROOT/'src'/'components'/'RaceIntelligenceScreen.tsx'
CHECKPOINT=ROOT/'src'/'components'/'RaceIntelligenceScreen_CHECKPOINT_MAP_RIGHT_TO_LEFT_LANES_V1_20260629.tsx'
REPORT=ROOT/'public'/'data'/'edgeiq_map_right_to_left_lanes_fix_v1_report.txt'
if not CHECKPOINT.exists(): shutil.copyfile(TSX,CHECKPOINT)
s=TSX.read_text(encoding='utf-8')
old='''                        <span style={{ position: "absolute", left: 8, top: "50%", transform: "translateY(-50%)", width: 30, color: "#94a3b8", fontSize: 10, fontWeight: 1000, textAlign: "center" }}>B{row.barrier}</span>
                        <span style={{ position: "absolute", left: 44, right: 8, top: "50%", height: 1, background: "linear-gradient(90deg, rgba(125,211,252,.22), rgba(148,163,184,.10))" }} />
                        <span style={{ position: "absolute", left: 44, top: "50%", transform: "translateY(-50%)", width: `calc(${Math.max(0, Math.min(100, row.x))}% * .86)`, height: 16, borderRadius: 999, background: `linear-gradient(90deg, ${mapTone(row.runStyle)}44, ${mapTone(row.runStyle)}88)`, boxShadow: row.selected ? `0 0 16px ${mapTone(row.runStyle)}33` : "none", opacity: row.selected ? .95 : .68, pointerEvents: "none" }} />
                        {[27,50,75].map((line) => <span key={`map-lane-divider-${row.key}-${line}`} style={{ position: "absolute", left: `${line}%`, top: 0, bottom: 0, width: 1, background: "rgba(148,163,184,.10)" }} />)}
                        <span style={{ position: "absolute", left: `calc(44px + (${Math.max(0, Math.min(100, row.x))}% * .86))`, top: "50%", transform: "translate(-50%, -50%)", border: `1px solid ${row.selected ? "rgba(224,242,254,.92)" : `${mapTone(row.runStyle)}88`}`, borderRadius: 999, padding: "4px 8px", background: row.selected ? "rgba(8,47,73,.98)" : "rgba(5,12,22,.95)", color: row.selected ? "#e0f2fe" : "#f8fafc", boxShadow: row.selected ? "0 0 0 3px rgba(56,189,248,.20), 0 0 18px rgba(56,189,248,.18)" : "0 6px 14px rgba(2,6,23,.22)", display: "inline-flex", gap: 5, alignItems: "center", maxWidth: 168 }}>'''
new='''                        <span style={{ position: "absolute", right: 8, top: "50%", transform: "translateY(-50%)", width: 34, color: "#94a3b8", fontSize: 10, fontWeight: 1000, textAlign: "center" }}>B{row.barrier}</span>
                        <span style={{ position: "absolute", left: 8, right: 44, top: "50%", height: 1, background: "linear-gradient(90deg, rgba(148,163,184,.10), rgba(125,211,252,.22))" }} />
                        {[27,50,75].map((line) => <span key={`map-lane-divider-${row.key}-${line}`} style={{ position: "absolute", left: `${line}%`, top: 0, bottom: 0, width: 1, background: "rgba(148,163,184,.10)" }} />)}
                        <span style={{ position: "absolute", left: `calc(8px + (${Math.max(0, Math.min(100, row.x))}% * .86))`, right: 44, top: "50%", transform: "translateY(-50%)", height: 16, borderRadius: 999, background: `linear-gradient(90deg, ${mapTone(row.runStyle)}88, ${mapTone(row.runStyle)}44)`, boxShadow: row.selected ? `0 0 16px ${mapTone(row.runStyle)}33` : "none", opacity: row.selected ? .95 : .68, pointerEvents: "none" }} />
                        <span style={{ position: "absolute", left: `calc(8px + (${Math.max(0, Math.min(100, row.x))}% * .86))`, top: "50%", transform: "translate(-50%, -50%)", border: `1px solid ${row.selected ? "rgba(224,242,254,.92)" : `${mapTone(row.runStyle)}88`}`, borderRadius: 999, padding: "4px 8px", background: row.selected ? "rgba(8,47,73,.98)" : "rgba(5,12,22,.95)", color: row.selected ? "#e0f2fe" : "#f8fafc", boxShadow: row.selected ? "0 0 0 3px rgba(56,189,248,.20), 0 0 18px rgba(56,189,248,.18)" : "0 6px 14px rgba(2,6,23,.22)", display: "inline-flex", gap: 5, alignItems: "center", maxWidth: 168 }}>'''
if old not in s: raise SystemExit('right-to-left lane anchor not found')
s=s.replace(old,new,1)
# Update the visual help text without touching data logic.
s=s.replace('Barrier 1 bottom | leaders left','Rail / barriers right | barrier 1 bottom | leaders left')
TSX.write_text(s,encoding='utf-8')
REPORT.write_text('EDGEiQ MAP right-to-left lanes applied\ncheckpoint='+str(CHECKPOINT)+'\nstatus=MAP_RIGHT_TO_LEFT_LANES_V1_APPLIED\n',encoding='utf-8')
print(REPORT.read_text())
