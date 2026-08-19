
from __future__ import annotations
import argparse, json, os
from edgeiq_racing_com_public_common_v1 import *
OPS={
 'MEETING':'query getRacesForMeet($meetId: ID!){ getRacesForMeet(meetId:$meetId){ id raceNumber distance name hasSectionals hasResults }}',
 'RACE':'query getRaceForm($raceId: ID!){ getRaceForm(raceId:$raceId){ id name distance hasSectionals }}',
 'SECTIONAL_AVAILABILITY':'query checkChampionDataForSectionals($raceId: ID!){ checkChampionDataForSectionals(raceId:$raceId) }',
 'RUNNER_SECTIONALS':'query getRaceForm($raceId: ID!){ getRaceForm(raceId:$raceId){ id sectionaltimes_callback }}'
}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mode',default='ALL',choices=['MEETING','RACE','SECTIONAL_AVAILABILITY','RUNNER_SECTIONALS','ALL']); ap.add_argument('--meeting-id',default=''); ap.add_argument('--race-id',default=''); ap.add_argument('--delay',type=float,default=0.75); args=ap.parse_args()
    ensure(); modes=list(OPS) if args.mode=='ALL' else [args.mode]
    reg=[]; matrix=[]
    key=os.environ.get('RACINGCOM_PUBLIC_WIDGET_API_KEY','').strip()
    for m in modes:
        doc=OPS[m]; op_path=GRAPHQL/'operation_documents'/(m.lower()+'.graphql'); write_text(op_path,doc+'\n')
        access='CREDENTIAL_REQUIRED'; status='SKIPPED_CREDENTIAL_ABSENT'; detail='No credential or browser context supplied; direct replay not attempted.'
        if m=='MEETING':
            r=request_public(APPV2_MEETS.format(year=2026,month=7)); status=r['status']; access='PUBLIC_ANONYMOUS_CONFIRMED' if r['ok'] else ('ACCESS_FORBIDDEN' if r['status'] in (401,403) else 'UNKNOWN')
            write_text(GRAPHQL/'response_samples_redacted'/'meeting_catalogue_appv2.json',redact_text(r['body'].decode('utf-8','ignore')))
            detail='Public appv2 meeting catalogue probe.'
        reg.append({'operation_name':m,'document_path':str(op_path.relative_to(ROOT)),'source':'repository_frontend_forensics_and_governed_local_evidence','document_sha256':sha_file(op_path),'direct_graphql_replay_status':status,'access_classification':access})
        matrix.append({'operation_name':m,'endpoint':GRAPHQL_ENDPOINT,'mode':args.mode,'http_status':status,'access_classification':access,'detail':detail})
    write_csv(GRAPHQL/'operation_registry.csv',reg); write_json(GRAPHQL/'operation_registry.json',reg)
    write_csv(GRAPHQL/'graphql_access_matrix.csv',matrix); write_json(GRAPHQL/'graphql_access_matrix.json',matrix)
    write_text(GRAPHQL/'graphql_forensics_report.md','# Racing.com GraphQL Public Replay V1\n\nDirect GraphQL replay does not import cookies, tokens or browser credentials. Runner-level sectionals are classified credential-required unless a logged-out public request succeeds.\n')
if __name__=='__main__': main()
