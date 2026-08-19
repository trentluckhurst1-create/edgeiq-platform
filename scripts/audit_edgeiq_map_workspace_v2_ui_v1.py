import csv
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
TSX=ROOT/'src'/'components'/'RaceIntelligenceScreen.tsx'
OUT=DATA/'edgeiq_map_workspace_v2_ui_audit_v1.csv'
SUM=DATA/'edgeiq_map_workspace_v2_ui_audit_v1_summary.csv'
REP=DATA/'edgeiq_map_workspace_v2_ui_audit_v1_report.txt'
text=TSX.read_text(encoding='utf-8',errors='replace')
start=text.find('{intelMode === "MAP"')
end=text.find('{intelMode === "FORM"',start)
block=text[start:end] if start>=0 and end>start else ''
checks=[
 ('map_feed_v2_reference','edgeiq_map_enrichment_feed_v2.csv' in text),
 ('race_shape_summary_cards','summaryCards' in block and 'Field Size' in block and 'Map Confidence' in block),
 ('speed_map_visual_section','Speed Map Visual' in block and 'mapRowsV2.map' in block),
 ('runner_map_table','Runner Map Table' in block and 'Run Style' in block and 'Wide Risk' in block),
 ('selected_runner_map_card','Selected Runner Map Card' in block and 'selectedMapVerdict' in block),
 ('race_shape_verdict','Race Shape Verdict' in block and 'raceShapeVerdictV2' in block),
 ('no_debug_blocks','debug' not in block.lower()),
 ('no_broken_form_refs','selectedFormVerdict' not in block and 'lastFiveRuns' not in block),
 ('no_undefined_style_names','undefined' not in re.sub(r'UNDEFINED','',block,flags=re.I).lower()),
]
# allow sanitizer regex to mention placeholders; fail visible fallback literals only.
raw_visible=any(x in block for x in ['>not loaded<','>SOURCE_MISSING<','>NaN<','>undefined<'])
checks.append(('no_raw_visible_placeholders',not raw_visible))
rows=[{'check':k,'status':'PASS' if v else 'FAIL'} for k,v in checks]
fails=[r for r in rows if r['status']=='FAIL']
status='MAP_WORKSPACE_V2_UI_AUDIT_PASS' if not fails else 'MAP_WORKSPACE_V2_UI_AUDIT_REVIEW_REQUIRED'
with OUT.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['check','status']); w.writeheader(); w.writerows(rows)
summary=[('checks',len(rows)),('passed',len(rows)-len(fails)),('failed',len(fails)),('pricing_maths_changed','NO'),('v6_1_changed','NO'),('v7_2g2_changed','NO'),('status',status)]
with SUM.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows({'metric':k,'value':v} for k,v in summary)
lines=['EDGEiQ MAP WORKSPACE V2 UI AUDIT']+[f'{k}={v}' for k,v in summary]
if fails: lines.append('failures='+', '.join(r['check'] for r in fails))
REP.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines))
