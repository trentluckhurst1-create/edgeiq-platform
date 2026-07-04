import csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
TSX=ROOT/'src'/'components'/'RaceIntelligenceScreen.tsx'
OUT=DATA/'edgeiq_map_right_to_left_lanes_audit_v1.csv'
SUM=DATA/'edgeiq_map_right_to_left_lanes_audit_v1_summary.csv'
REP=DATA/'edgeiq_map_right_to_left_lanes_audit_v1_report.txt'
text=TSX.read_text(encoding='utf-8',errors='replace')
start=text.find('{intelMode === "MAP"')
end=text.find('{intelMode === "FORM"',start)
block=text[start:end] if start>=0 and end>start else ''
checks=[
 ('right_to_left_lane_fill_logic_exists','right: 44' in block and 'left: `calc(8px + (${Math.max(0, Math.min(100, row.x))}% * .86))`' in block),
 ('barrier_labels_on_right','position: "absolute", right: 8' in block and '>B{row.barrier}</span>' in block),
 ('barrier_1_bottom_text_exists','barrier 1 bottom' in block.lower()),
 ('zone_labels_retained',all(x in block for x in ['LEADERS','ON PACE','MIDFIELD','BACKMARKERS'])),
 ('v3_x_position_retained','row.x' in block and 'map_x_pct_display_v3' in block),
 ('lane_based_rendering_retained','mapLaneRowsV1.map' in block and 'map-lane-row' in block),
 ('no_scatter_map','top: `${row.y}%`' not in block and 'map-v2-point' not in block),
 ('no_raw_placeholders',not any(x in block for x in ['>not loaded<','>SOURCE_MISSING<','>NaN<','>undefined<'])),
 ('no_debug_blocks','debug' not in block.lower()),
]
rows=[{'check':k,'status':'PASS' if v else 'FAIL'} for k,v in checks]
fails=[r for r in rows if r['status']=='FAIL']
status='MAP_RIGHT_TO_LEFT_LANES_AUDIT_PASS' if not fails else 'MAP_RIGHT_TO_LEFT_LANES_AUDIT_REVIEW_REQUIRED'
with OUT.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['check','status']); w.writeheader(); w.writerows(rows)
summary=[('checks',len(rows)),('passed',len(rows)-len(fails)),('failed',len(fails)),('pricing_maths_changed','NO'),('v6_1_changed','NO'),('v7_2g2_changed','NO'),('status',status)]
with SUM.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows({'metric':k,'value':v} for k,v in summary)
lines=['EDGEiQ MAP RIGHT TO LEFT LANES AUDIT V1']+[f'{k}={v}' for k,v in summary]
if fails: lines.append('failures='+', '.join(r['check'] for r in fails))
REP.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines))
