from __future__ import annotations
from pathlib import Path
import json, csv
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
TSX = ROOT / 'src' / 'edgeiq-os' / 'race' / 'components' / 'RaceFormGuideWorkspace.tsx'
CSS = ROOT / 'src' / 'edgeiq-os' / 'styles' / 'edgeiqOsV2.css'
SHOT_DIR = ROOT / 'docs' / 'full-product-implementation' / 'screenshots' / 'form-guide-final-locked'
RUNTIME = SHOT_DIR / '05_FORM_GUIDE_RUNTIME.json'
DOM = SHOT_DIR / '05_FORM_GUIDE_DOM_GEOMETRY.json'
CONSOLE = SHOT_DIR / '05_FORM_GUIDE_CONSOLE.json'
NETWORK = SHOT_DIR / '05_FORM_GUIDE_NETWORK.json'
AUDIT_CSV = ROOT / 'docs' / 'full-product-implementation' / 'FORM_GUIDE_FINAL_LOCKED_V2_AUDIT.csv'
SUMMARY = ROOT / 'docs' / 'full-product-implementation' / 'FORM_GUIDE_FINAL_LOCKED_V2_AUDIT_SUMMARY.json'
REPORT = ROOT / 'docs' / 'full-product-implementation' / 'FORM_GUIDE_FINAL_LOCKED_V2_AUDIT_REPORT.md'

REQ_FILES = [
    '05_FORM_GUIDE_APPROVED.png','05_FORM_GUIDE_LIVE_1536x1024.png','05_FORM_GUIDE_OVERLAY_50.png','05_FORM_GUIDE_DIFF.png','05_FORM_GUIDE_EDGE_DIFF.png','05_FORM_GUIDE_REGION_DIFF.csv','05_FORM_GUIDE_DOM_GEOMETRY.json','05_FORM_GUIDE_RUNTIME.json','05_FORM_GUIDE_CONSOLE.json','05_FORM_GUIDE_NETWORK.json'
]
SUMMARY_COLUMNS = ['NO','SILK','LAST 5','HORSE','TRAINER','JOCKEY','WT','BAR','DAYS','EPI','EARLY SPEED','LATE SPEED','SUITABILITY','FORM MOMENTUM','MARKET','EDGEiQ PRICE']
RECENT_COLUMNS = ['DATE','TRACK','DIST','CLASS','GOING','JOCKEY','BARRIER','WEIGHT','EPI','ERI','POS','POSITION IN RUNNING','MARGIN','SP','8-6','6-4','4-2','2-F']
FORBIDDEN_SOURCE = ['â','Â','™','œ','Metric Guide','form-guide-approved-exact"']
FORBIDDEN_VISIBLE = ['UNKNOWN','NOT LOADED','SOURCE GAP','null','undefined','NaN','Metric Guide']

def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default

def add(rows, check, passed, detail):
    rows.append({'check':check,'passed':'YES' if passed else 'NO','detail':detail})

def main():
    rows = []
    tsx = TSX.read_text(encoding='utf-8') if TSX.exists() else ''
    css = CSS.read_text(encoding='utf-8') if CSS.exists() else ''
    runtime = load_json(RUNTIME, {})
    console = load_json(CONSOLE, [])
    network = load_json(NETWORK, [])
    dom = load_json(DOM, [])

    add(rows,'component_exists',TSX.exists(),str(TSX.relative_to(ROOT)))
    add(rows,'final_marker_in_source','data-edgeiq-workspace="form-guide-final-locked"' in tsx,'root marker')
    add(rows,'final_marker_runtime',runtime.get('markerCount',0) >= 1,f"markerCount={runtime.get('markerCount')}")
    add(rows,'legacy_marker_not_runtime',runtime.get('oldMarkerCount',0) == 0,f"oldMarkerCount={runtime.get('oldMarkerCount')}")
    add(rows,'viewport_1536x1024',runtime.get('viewport',{}).get('width') == 1536 and runtime.get('viewport',{}).get('height') == 1024,str(runtime.get('viewport')))
    add(rows,'device_scale_factor_1',runtime.get('viewport',{}).get('devicePixelRatio') == 1,str(runtime.get('viewport')))
    cols = runtime.get('columns','').split('|') if runtime.get('columns') else []
    add(rows,'summary_columns_exact',cols == SUMMARY_COLUMNS,'|'.join(cols))
    recent = runtime.get('recentColumns','').split('|') if runtime.get('recentColumns') else []
    add(rows,'recent_columns_exact',recent == RECENT_COLUMNS,'|'.join(recent))
    add(rows,'profile_matrix_cells_present',runtime.get('matrixCells',0) >= 80,f"matrixCells={runtime.get('matrixCells')}")
    add(rows,'recent_form_region_present',any(d.get('region') == 'recent_form' and d.get('visible') for d in dom), 'recent_form visible')
    add(rows,'runner_profile_expanded',any(d.get('region') == 'true' and d.get('visible') for d in dom) or runtime.get('expandedRunner') is not None, f"expandedRunner={runtime.get('expandedRunner')}")
    add(rows,'capture_artifacts_present',all((SHOT_DIR / name).exists() for name in REQ_FILES), ','.join(name for name in REQ_FILES if not (SHOT_DIR/name).exists()))
    source_hits = [term for term in FORBIDDEN_SOURCE if term in tsx]
    add(rows,'source_encoding_clean',not source_hits, ','.join(source_hits))
    visible_hits = runtime.get('forbiddenVisibleHits', [])
    add(rows,'visible_forbidden_copy_absent',not visible_hits, ','.join(visible_hits))
    console_errors = [e for e in console if e.get('type') in {'error','pageerror'}]
    add(rows,'console_no_errors',not console_errors, json.dumps(console_errors[:5]))
    bad_network = [e for e in network if ((e.get('type') == 'requestfailed' and e.get('failure') != 'net::ERR_ABORTED') or int(e.get('status',0) or 0) >= 500)]
    add(rows,'network_no_failures',not bad_network, json.dumps(bad_network[:5]))
    add(rows,'final_css_present','EDGEIQ FORM GUIDE FINAL LOCKED V2 START' in css,'css marker')
    add(rows,'no_visible_metric_guide_button','Metric Guide' not in runtime.get('bodySample',''),'body sample')

    AUDIT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_CSV.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=['check','passed','detail'])
        writer.writeheader(); writer.writerows(rows)
    failed = [r for r in rows if r['passed'] != 'YES']
    status = 'FORM_GUIDE_FINAL_LOCKED_V2_PASS' if not failed else 'FORM_GUIDE_FINAL_LOCKED_V2_REVIEW_REQUIRED'
    summary = {'status':status,'timestamp':datetime.now().isoformat(timespec='seconds'),'checks':len(rows),'failed':len(failed),'failed_checks':[r['check'] for r in failed]}
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    REPORT.write_text('# FORM GUIDE FINAL LOCKED V2 AUDIT\n\n' + f"Status: `{status}`\n\n" + '\n'.join(f"- {r['check']}: {r['passed']} ({r['detail']})" for r in rows) + '\n', encoding='utf-8')
    print(status)
    if failed:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
