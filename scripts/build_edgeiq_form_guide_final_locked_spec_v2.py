from __future__ import annotations
from pathlib import Path
import json
import csv
import shutil
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / 'docs' / 'product-specification'
IMPL_DIR = ROOT / 'docs' / 'full-product-implementation'
SHOT_DIR = IMPL_DIR / 'screenshots' / 'form-guide-final-locked'
SRC_APPROVED = IMPL_DIR / 'screenshots' / 'form-guide-exact' / '05_FORM_GUIDE_APPROVED.png'
TOKENS = ROOT / 'src' / 'edgeiq-os' / 'styles' / 'formGuideFinalLocked.tokens.css'
BINDING = IMPL_DIR / 'FORM_GUIDE_FINAL_DATA_BINDING_MATRIX.csv'
TRACE = IMPL_DIR / 'FORM_GUIDE_FINAL_LIVE_COMPONENT_TRACE.md'

SUMMARY_COLUMNS = [
    ('NO','runner.no','Race saddlecloth number from governed field/display normaliser'),
    ('SILK','runner.silkUrl','Silks image URL or deterministic fallback marker'),
    ('LAST 5','runner.lastFive','Most recent five official finish-position tokens'),
    ('HORSE','runner.horse','Runner display name'),
    ('TRAINER','runner.trainer','Trainer display name'),
    ('JOCKEY','runner.jockey','Jockey display name'),
    ('WT','runner.weight','Allocated/declared weight from field/form data'),
    ('BAR','runner.barrier','Declared barrier'),
    ('DAYS','runner.daysSinceLastRun','Days since latest official start'),
    ('EPI','runner.epi','EDGEiQ Performance Index display field'),
    ('EARLY SPEED','runner.earlySpeed','Current early-speed projection'),
    ('LATE SPEED','runner.late','Late-speed/finish projection'),
    ('SUITABILITY','runner.suitabilityScore + runner.suitabilityLabel','Governed suitability score and label'),
    ('FORM MOMENTUM','runner.formMomentum','Recent-form trend indicator'),
    ('MARKET','runner.marketPrice','Current market price where available'),
    ('EDGEiQ PRICE','runner.edgeiqPrice','Approved EDGEiQ price display field; model maths unchanged'),
]
RECENT_COLUMNS = [
    ('DATE','run.date'),('TRACK','run.track'),('DIST','run.distance'),('CLASS','run.raceClass'),('GOING','run.condition'),
    ('JOCKEY','run.jockey'),('BARRIER','run.barrier'),('WEIGHT','run.weight'),('EPI','run.epi'),('ERI','run.eri'),
    ('POS','run.position'),('POSITION IN RUNNING','run.positionInRunning'),('MARGIN','run.margin'),('SP','run.sp'),
    ('8-6','run.esi800600'),('6-4','run.esi600400'),('4-2','run.esi400200'),('2-F','run.esi200F'),
]
MATRIX_COLUMNS = ['CATEGORY','CAREER','TODAY DISTANCE','TODAY TRACK','FIRM','TODAY GOING','SOFT','HEAVY','TRACK/DIST','TODAY CLASS','TODAY JOCKEY','1ST UP','2ND UP','3RD UP']
MATRIX_ROWS = ['STARTS','WINS','PLACES','WIN %','PLACE %','AVG EPI','AVG ERI']
MATCH_ROWS = ['Track','Distance','Going','Rail','Tempo','Pace Setup']

SPEC_MD = '''# FORM GUIDE FINAL LOCKED SPEC V2

This spec supersedes the rejected runtime of the prior Form Guide rebuild. The approved screenshot remains the visual target, but V2 requires the live workspace to render a rich selected runner, a populated profile matrix, and governed recent-form evidence instead of sparse placeholder panels.

## Live Component Contract

- Component: `src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx`
- Required root marker: `data-edgeiq-workspace="form-guide-final-locked"`
- Default capture viewport: `1536x1024`, deviceScaleFactor `1`, browser zoom `100%`
- No race selector chip row inside FORM GUIDE
- No visible Metric Guide panel/button
- No empty stat cards masquerading as intelligence

## Layout Regions

1. Race header with race identity and compact metadata.
2. Toolbar row with Ratings View, info, customise, and export controls.
3. All-runner summary table, 16 default visible columns.
4. Expanded selected-runner sheet directly beneath selected row.
5. Runner hero with silk, identity, and current metric strip.
6. Three-column analysis band: Today Match, Horse Profile matrix, short match read.
7. Recent Form table with last eight starts and sectional cells.
8. Sectional legend immediately below the recent form table.

## Data Rules

- Missing visible values render as `—`.
- Do not render raw placeholders such as UNKNOWN, NOT LOADED, SOURCE GAP, null, undefined, NaN, or 0.0% for missing data.
- Use governed enriched FORM data where available.
- Pricing/probability/rating model math is not changed.
'''

TOKENS_CSS = '''/* EDGEiQ FORM GUIDE FINAL LOCKED V2 TOKENS */
:root {
  --eiq-fg-bg: #f3efe4;
  --eiq-fg-panel: #f8f4ea;
  --eiq-fg-ink: #172033;
  --eiq-fg-muted: #6f7480;
  --eiq-fg-rule: rgba(23, 32, 51, 0.16);
  --eiq-fg-green: #38a169;
  --eiq-fg-red: #c2413a;
  --eiq-fg-blue: #2f80ed;
  --eiq-fg-amber: #b7791f;
  --eiq-fg-table-min: 1308px;
  --eiq-fg-row-h: 42px;
}
'''

INTERACTIONS = '''# FORM GUIDE FINAL LOCKED INTERACTIONS V2

- Clicking a runner row expands or collapses that runner's profile sheet.
- Expanding a runner scrolls the runner profile into view without changing race selection or app navigation.
- Header tooltips may appear on metric columns; they are transient and must not occupy permanent layout space.
- Race navigation remains controlled by the surrounding race workspace, not by a FORM GUIDE chip row.
- Empty data states must be quiet (`—`) and must not create oversized blank panels.
'''

GEOMETRY_ROWS = [
    ['region','x','y','width','height','notes'],
    ['workspace','0','0','1536','auto','Live component fills race content width'],
    ['race_header','24','16','1488','86','Header and metadata'],
    ['toolbar','24','112','1488','42','Compact controls'],
    ['summary_table','24','164','1488','variable','16 column all-runner table'],
    ['runner_sheet','24','below_selected_row','1488','variable','Expanded runner evidence sheet'],
    ['runner_header','16','16','calc(100%-32)','104','Silk, identity, metric strip'],
    ['today_match','16','136','220','220','Six row match summary'],
    ['profile_matrix','252','136','calc(100%-508)','220','Statistical matrix'],
    ['match_read','calc(100%-240)','136','220','220','Short insight panel'],
    ['recent_form','16','372','calc(100%-32)','auto','Last eight starts table'],
]
TEXT_ROWS = [
    ['text','status'],
    ['FORM GUIDE','required'],
    ['Ratings View','required'],
    ['HORSE PROFILE','required'],
    ["TODAY'S MATCH",'required'],
    ['HORSE PROFILE (CAREER)','required'],
    ['RECENT FORM','required'],
    ['LAST 8 STARTS','required'],
    ['Sectionals (Lengths):','required'],
]
TYPO_ROWS = [
    ['region','font_size','weight','case','notes'],
    ['table_header','11px','800','uppercase','Dense TopRate-style headings'],
    ['table_body','12px','600','mixed','Compact but readable'],
    ['runner_name','18px','900','uppercase','Selected runner hero'],
    ['metric_label','10px','800','uppercase','Hero metrics'],
    ['matrix_cell','11px','700','mixed','Profile matrix'],
]
COLOUR_ROWS = [
    ['token','value','usage'],
    ['--eiq-fg-bg','#f3efe4','Form guide surface'],
    ['--eiq-fg-panel','#f8f4ea','Panels'],
    ['--eiq-fg-ink','#172033','Primary text'],
    ['--eiq-fg-muted','#6f7480','Secondary text'],
    ['--eiq-fg-green','#38a169','Positive/improving cells'],
    ['--eiq-fg-red','#c2413a','Negative/regression cells'],
]

def write_csv(path: Path, rows):
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)

def main():
    SPEC_DIR.mkdir(parents=True, exist_ok=True)
    IMPL_DIR.mkdir(parents=True, exist_ok=True)
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    if SRC_APPROVED.exists():
        shutil.copy2(SRC_APPROVED, SHOT_DIR / '05_FORM_GUIDE_APPROVED.png')

    (SPEC_DIR / 'FORM_GUIDE_FINAL_LOCKED_SPEC_V2.md').write_text(SPEC_MD, encoding='utf-8')
    (SPEC_DIR / 'FORM_GUIDE_FINAL_LOCKED_SPEC_V2.json').write_text(json.dumps({
        'version':'FORM_GUIDE_FINAL_LOCKED_SPEC_V2',
        'viewport': {'width':1536,'height':1024,'deviceScaleFactor':1,'zoom':'100%'},
        'component':'src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx',
        'marker':'form-guide-final-locked',
        'summaryColumns':[c[0] for c in SUMMARY_COLUMNS],
        'recentFormColumns':[c[0] for c in RECENT_COLUMNS],
        'profileMatrixColumns':MATRIX_COLUMNS,
        'profileMatrixRows':MATRIX_ROWS,
        'todayMatchRows':MATCH_ROWS,
        'forbiddenVisibleText':['UNKNOWN','NOT LOADED','SOURCE GAP','null','undefined','NaN','Metric Guide'],
        'modelMathChanged': False,
    }, indent=2), encoding='utf-8')
    write_csv(SPEC_DIR / 'FORM_GUIDE_FINAL_GEOMETRY_V2.csv', GEOMETRY_ROWS)
    write_csv(SPEC_DIR / 'FORM_GUIDE_FINAL_TEXT_V2.csv', TEXT_ROWS)
    write_csv(SPEC_DIR / 'FORM_GUIDE_FINAL_TYPOGRAPHY_V2.csv', TYPO_ROWS)
    write_csv(SPEC_DIR / 'FORM_GUIDE_FINAL_COLOURS_V2.csv', COLOUR_ROWS)
    write_csv(SPEC_DIR / 'FORM_GUIDE_FINAL_TABLE_COLUMNS_V2.csv', [['table','ordinal','column','binding']] + [['summary',i+1,c,b] for i,(c,b,_) in enumerate(SUMMARY_COLUMNS)] + [['recent_form',i+1,c,b] for i,(c,b) in enumerate(RECENT_COLUMNS)])
    (SPEC_DIR / 'FORM_GUIDE_FINAL_INTERACTIONS_V2.md').write_text(INTERACTIONS, encoding='utf-8')
    TOKENS.write_text(TOKENS_CSS, encoding='utf-8')
    write_csv(BINDING, [['region','field','binding','source_contract']] + [['summary_table',c,b,n] for c,b,n in SUMMARY_COLUMNS] + [['recent_form',c,b,'runner.recentRuns from enriched FORM feed'] for c,b in RECENT_COLUMNS] + [['profile_matrix',c,'profileRows / computed matrix','career/distance/track/condition/class/jockey/race-day profiles'] for c in MATRIX_COLUMNS] + [['today_match',r,'TodayMatch computed row','selected runner + race metadata'] for r in MATCH_ROWS])
    TRACE.write_text(f'''# FORM GUIDE FINAL LIVE COMPONENT TRACE

Generated: {datetime.now().isoformat(timespec='seconds')}

## Proven Live Component Path

`src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx`

## Required Marker

`data-edgeiq-workspace="form-guide-final-locked"`

## Runtime Mount Path

Race workspace renders the FORM GUIDE tab through the EDGEiQ OS race component tree. The final locked marker is located on the root `<section>` returned by `RaceFormGuideWorkspace`.

## Guardrails

- Production model maths unchanged.
- EPI/ERI/pricing/probability/V6.1/V7.2G2 unchanged.
- FORM GUIDE visual/data presentation only.
''', encoding='utf-8')
    print(json.dumps({'status':'FORM_GUIDE_FINAL_LOCKED_SPEC_V2_BUILT','files':10}, indent=2))

if __name__ == '__main__':
    main()
