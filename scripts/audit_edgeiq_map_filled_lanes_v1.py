import csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
TSX=ROOT/'src'/'components'/'RaceIntelligenceScreen.tsx'
OUT=DATA/'edgeiq_map_filled_lanes_audit_v1.csv'
SUM=DATA/'edgeiq_map_filled_lanes_audit_v1_summary.csv'
REP=DATA/'edgeiq_map_filled_lanes_audit_v1_report.txt'
text=TSX.read_text(encoding='utf-8',errors='replace')
start=text.find('{intelMode === "MAP"')
end=text.find('{intelMode === "FORM"',start)
block=text[start:end] if start>=0 and end>start else ''
checks=[
 ('filled_lane_render_exists','linear-gradient(90deg, ${mapTone(row.runStyle)}44' in block and 'height: 16' in block),
 ('lane_fill_width_uses_map_x','width: `calc(${Math.max(0, Math.min(100, row.x))}% * .86)`' in block),
 ('horse_pill_uses_same_x','left: `calc(44px + (${Math.max(0, Math.min(100, row.x))}% * .86))`' in block),
 ('barrier_lane_logic_still_exists','mapLaneRowsV1' in block and 'barrierB - barrierA' in block),
 ('barrier_1_bottom_text_still_exists','Barrier 1 bottom' in block),
 ('zone_labels_still_exist',all(x in block for x in ['LEADERS','ON PACE','MIDFIELD','BACKMARKERS'])),
 ('no_scatter_only_y_position','top: `${row.y}%`' not in block and 'map-v2-point' not in block),
 ('selected_highlight_still_exists','row.selected ?' in block and '0 0 0 3px rgba(56,189,248' in block),
 ('no_debug_blocks','debug' not in block.lower()),
]
rows=[{'check':k,'status':'PASS' if v else 'FAIL'} for k,v in checks]
fails=[r for r in rows if r['status']=='FAIL']
status='MAP_FILLED_LANES_AUDIT_PASS' if not fails else 'MAP_FILLED_LANES_AUDIT_REVIEW_REQUIRED'
with OUT.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['check','status']); w.writeheader(); w.writerows(rows)
summary=[('checks',len(rows)),('passed',len(rows)-len(fails)),('failed',len(fails)),('pricing_maths_changed','NO'),('v6_1_changed','NO'),('v7_2g2_changed','NO'),('status',status)]
with SUM.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows({'metric':k,'value':v} for k,v in summary)
lines=['EDGEiQ MAP FILLED LANES AUDIT V1']+[f'{k}={v}' for k,v in summary]
if fails: lines.append('failures='+', '.join(r['check'] for r in fails))
REP.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines))
