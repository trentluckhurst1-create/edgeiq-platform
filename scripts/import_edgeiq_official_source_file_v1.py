from edgeiq_external_data_common_v1 import ROOT,DOC,now,write_csv,write_json,file_sha,read_csv
import argparse,json,shutil
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--source',required=True); parser.add_argument('--file',required=True); parser.add_argument('--date',required=True); parser.add_argument('--data-type',required=True)
parser.add_argument('--dry-run',action='store_true'); parser.add_argument('--no-publish',action='store_true'); parser.add_argument('--evidence-root',default=str(ROOT/'data'/'evidence'/'external-data-integration-v1'/'manual-import')); parser.add_argument('--verbose',action='store_true')
args=parser.parse_args(); src=Path(args.file).resolve()
if not src.exists(): raise SystemExit(f'Input file not found: {src}')
if src.suffix.lower() not in {'.csv','.json','.xml','.xlsx','.pdf','.html','.htm'}: raise SystemExit(f'Unsupported format: {src.suffix}')
digest=file_sha(src); evidence_dir=Path(args.evidence_root)/args.date/digest[:16]; evidence_dir.mkdir(parents=True,exist_ok=True); raw_copy=evidence_dir/src.name
if not args.dry_run: shutil.copy2(src,raw_copy)
rows=read_csv(src) if src.suffix.lower()=='.csv' else []; schema=list(rows[0].keys()) if rows else []; identity='PASS' if {'race_date','track','race_no'}.issubset({x.lower() for x in schema}) else 'REVIEW_REQUIRED'
out={'source':args.source,'input_file':str(src),'source_publication_date':args.date,'data_type':args.data_type,'file_sha256':digest,'original_filename':src.name,'raw_evidence_copy':'DRY_RUN_NOT_COPIED' if args.dry_run else str(raw_copy.relative_to(ROOT)),'format':src.suffix.lower(),'rows':len(rows),'schema':schema,'identity_validation':identity,'dry_run':args.dry_run,'no_publish':args.no_publish,'checked_at':now(),'canonical_promotion':'NO'}
write_json(DOC/'EDGEIQ_MANUAL_OFFICIAL_FILE_IMPORT_LAST_RUN_V1.json',out)
write_csv(DOC/'EDGEIQ_MANUAL_OFFICIAL_FILE_IMPORT_LAST_RUN_V1.csv',[{k:json.dumps(v) if isinstance(v,list) else v for k,v in out.items()}],list(out.keys()))
print(json.dumps(out,indent=2,sort_keys=True)); raise SystemExit(0 if args.dry_run or identity=='PASS' else 2)
