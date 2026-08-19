
from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path
from racingcom_speed_data_parser_v2 import RacingComSpeedDataParseError, parse_speed_csv

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
OUTDIR = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
AUDIT = OUTDIR / "edgeiq_racingcom_parser_v2_tests.csv"
SUMMARY = OUTDIR / "edgeiq_racingcom_parser_v2_tests_summary.json"

def write_csv(path, rows):
    with path.open('w', encoding='utf-8', newline='') as f:
        w=csv.DictWriter(f, fieldnames=['test','status','detail']); w.writeheader(); w.writerows(rows)

def run():
    rows=[]
    acq=list(csv.DictReader(open(OUTDIR/'edgeiq_racingcom_csv_acquisition_v2.csv', encoding='utf-8')))
    valid_path=ROOT/acq[0]['cache_path'] if acq else None
    def record(name, passed, detail): rows.append({'test':name,'status':'PASS' if passed else 'FAIL','detail':detail})
    try:
        parsed,_=parse_speed_csv(valid_path, acq[0]['csv_url'], acq[0]['race_id'])
        record('valid_racingcom_csv_parses', len(parsed)>0, f'rows={len(parsed)}')
    except Exception as e: record('valid_racingcom_csv_parses', False, str(e))
    with tempfile.TemporaryDirectory() as td:
        d=Path(td)
        cases={
            'empty_csv_rejected':'',
            'html_body_rejected':'<!doctype html><html></html>',
            'malformed_rows_controlled':'1/05/2026 12:00:00 AM;Ladbrokes Geelong-Professional-2026-05-01;Race;00:01:00.000;GEEL_1000m_TRACK\nHorse Only\n',
            'missing_metadata_rejected':'Horse;1;200;17;00:00:11.000\n',
            'duplicate_runner_controlled':'1/05/2026 12:00:00 AM;Ladbrokes Geelong-Professional-2026-05-01;Race;00:01:00.000;GEEL_1000m_TRACK\nHorse;1;200;17;00:00:11.000\nHorse;2;200;18;00:00:10.000\n',
        }
        for name, body in cases.items():
            p=d/f'{name}.csv'; p.write_text(body, encoding='utf-8')
            try:
                parsed,rejects=parse_speed_csv(p, 'fixture', '2026-05-01_GEELONG_R1')
                if name in {'malformed_rows_controlled','duplicate_runner_controlled'}:
                    record(name, len(rejects)>0, f'parsed={len(parsed)} rejects={len(rejects)}')
                else:
                    record(name, False, f'unexpected parse rows={len(parsed)} rejects={len(rejects)}')
            except RacingComSpeedDataParseError as e:
                record(name, True, str(e))
            except Exception as e:
                record(name, False, type(e).__name__ + ':' + str(e))
    passed=sum(1 for r in rows if r['status']=='PASS')
    summary={'status':'RACINGCOM_PARSER_V2_TESTS_PASS' if passed==len(rows) else 'RACINGCOM_PARSER_V2_TESTS_FAIL','tests':len(rows),'passed':passed,'failed':len(rows)-passed}
    write_csv(AUDIT, rows)
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))
    return 0 if summary['status'].endswith('PASS') else 1

if __name__ == '__main__':
    raise SystemExit(run())
