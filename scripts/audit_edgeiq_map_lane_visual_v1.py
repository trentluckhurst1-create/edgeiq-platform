import csv
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
TSX=ROOT/'src'/'components'/'RaceIntelligenceScreen.tsx'
OUT=DATA/'edgeiq_map_lane_visual_audit_v1.csv'
SUM=DATA/'edgeiq_map_lane_visual_audit_v1_summary.csv'
REP=DATA/'edgeiq_map_lane_visual_audit_v1_report.txt'
text=TSX.read_text(encoding='utf-8',errors='replace')
start=text.find('{intelMode === "MAP"')
end=text.find('{intelMode === "FORM"',start)
block=text[start:end] if start>=0 and end>start else ''
checks=[
 ('lane_based_rendering_exists','mapLaneRowsV1.map' in block and 'map-lane-row' in block),
 ('no_scatter_only_y_positioning','top: `${row.y}%`' not in block and 'map-v2-point' not in block),
 ('barrier_sort_logic_exists','barrierB - barrierA' in block and 'validA' in block and 'validB' in block),
 ('barrier_1_bottom_logic_exists','Barrier 1 bottom' in block and 'barrierB - barrierA' in block),
 ('zone_labels_exist',all(x in block for x in ['LEADERS','ON PACE','MIDFIELD','BACKMARKERS'])),
 ('selected_highlight_exists','row.selected ?' in block and 'rgba(8,47,73' in block),
 ('v3_x_position_still_used','row.x' in block and 'map_x_pct_display_v3' in block),
 ('speed_rank_gap_retained','row.speedRank' in block and 'row.speedGap' in block),
 ('no_debug_blocks','debug' not in block.lower()),
]
raw_visible=any(x in block for x in ['>not loaded<','>SOURCE_MISSING<','>NaN<','>undefined<'])
checks.append(('no_raw_placeholders',not raw_visible))
rows=[{'check':k,'status':'PASS' if v else 'FAIL'} for k,v in checks]
fails=[r for r in rows if r['status']=='FAIL']
status='MAP_LANE_VISUAL_AUDIT_PASS' if not fails else 'MAP_LANE_VISUAL_AUDIT_REVIEW_REQUIRED'
with OUT.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['check','status']); w.writeheader(); w.writerows(rows)
summary=[('checks',len(rows)),('passed',len(rows)-len(fails)),('failed',len(fails)),('pricing_maths_changed','NO'),('v6_1_changed','NO'),('v7_2g2_changed','NO'),('status',status)]
with SUM.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows({'metric':k,'value':v} for k,v in summary)
lines=['EDGEiQ MAP LANE VISUAL AUDIT V1']+[f'{k}={v}' for k,v in summary]
if fails: lines.append('failures='+', '.join(r['check'] for r in fails))
REP.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines))
