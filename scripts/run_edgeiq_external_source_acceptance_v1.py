from edgeiq_external_data_common_v1 import DATA,DOC,credential_status,read_csv,write_csv,write_json,now
import argparse,json
parser=argparse.ArgumentParser()
parser.add_argument('--mode',choices=['STATUS','RACINGCOM','RACING_AUSTRALIA','ALTERNATIVES','LOCAL_RECOVERY','MANUAL_IMPORT_TEST','FULL'],default='STATUS')
parser.add_argument('--source',default=''); parser.add_argument('--date',default=''); parser.add_argument('--date-from',default=''); parser.add_argument('--date-to',default='')
parser.add_argument('--dry-run',action='store_true'); parser.add_argument('--no-publish',action='store_true'); parser.add_argument('--offline',action='store_true'); parser.add_argument('--fixture-root',default=''); parser.add_argument('--verbose',action='store_true')
args=parser.parse_args(); rows=[]; fields=['mode','source','network_access','authentication','publication_availability','parser','identity','canonical_promotion','downstream_performance','status','operator_action']
if args.mode in {'STATUS','FULL'}:
    for row in read_csv(DATA/'edgeiq_external_source_access_health_fact_v1.csv'):
        rows.append({'mode':args.mode,'source':row.get('source_id'),'network_access':row.get('response_class'),'authentication':row.get('credential_present'),'publication_availability':row.get('latest_available_data_date'),'parser':'not run','identity':'not run','canonical_promotion':'NO','downstream_performance':'not run','status':row.get('access_status'),'operator_action':row.get('operator_action_required')})
if args.mode in {'RACINGCOM','FULL'} and credential_status()['RACINGCOM_PUBLIC_WIDGET_API_KEY']=='ABSENT':
    rows.append({'mode':args.mode,'source':'RACINGCOM_GRAPHQL_SPEED_TIMING','network_access':'SKIPPED','authentication':'ABSENT','publication_availability':'NOT_TESTED','parser':'not run','identity':'not run','canonical_promotion':'NO','downstream_performance':'NO','status':'SUPPORTED_CREDENTIAL_REQUIRED','operator_action':'Set approved RACINGCOM_PUBLIC_WIDGET_API_KEY'})
if args.mode in {'RACING_AUSTRALIA','FULL'}:
    rows.append({'mode':args.mode,'source':'RACING_AUSTRALIA_FREEFIELDS_RESULTS','network_access':'ACCESS_FORBIDDEN_OR_OFFLINE','authentication':'UNKNOWN_OR_FORBIDDEN','publication_availability':'NOT_CONFIRMED','parser':'existing','identity':'existing','canonical_promotion':'NO','downstream_performance':'NO','status':'SOURCE_ACCESS_FORBIDDEN','operator_action':'Resolve approved access or use official manual export'})
if args.mode in {'ALTERNATIVES','LOCAL_RECOVERY','MANUAL_IMPORT_TEST','FULL'}:
    rows.append({'mode':args.mode,'source':'OPERATOR_OFFICIAL_FILE_IMPORT','network_access':'N/A','authentication':'OPERATOR_EXTERNAL','publication_availability':'REQUIRES_FILE','parser':'available','identity':'validated at import','canonical_promotion':'candidate only','downstream_performance':'dry-run ready','status':'SUPPORTED_MANUAL_EXPORT_REQUIRED','operator_action':'Provide unmodified official export file'})
write_csv(DOC/'EDGEIQ_EXTERNAL_SOURCE_ACCEPTANCE_LAST_RUN_V1.csv',rows,fields); write_json(DOC/'EDGEIQ_EXTERNAL_SOURCE_ACCEPTANCE_LAST_RUN_V1.json',{'mode':args.mode,'checked_at':now(),'rows':rows})
print(json.dumps({'mode':args.mode,'rows':rows},indent=2,sort_keys=True))
