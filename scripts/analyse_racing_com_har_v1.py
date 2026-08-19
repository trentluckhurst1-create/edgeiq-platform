
from __future__ import annotations
import argparse, json
from edgeiq_racing_com_public_common_v1 import *
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--har',default=''); args=ap.parse_args(); ensure()
    reqs=[]; gql=[]; cf=[]; sec=[]
    if args.har and Path(args.har).exists():
        obj=json.loads(Path(args.har).read_text(encoding='utf-8'))
        for e in obj.get('log',{}).get('entries',[]):
            rq=e.get('request',{}); url=rq.get('url',''); row={'method':rq.get('method',''),'url_hash':sha_bytes(url.encode()),'host':url.split('/')[2] if '://' in url else '', 'status':e.get('response',{}).get('status',''), 'contains_sensitive_headers':'NO'}
            reqs.append(row)
            if 'graphql' in url.lower(): gql.append(row)
            if 'cloudfront' in url.lower(): cf.append(row)
            if any(x in url.lower() for x in ['sectional','split','speed-data','csv','pdf']): sec.append(row)
    write_csv(HAR/'request_inventory.csv',reqs); write_csv(HAR/'graphql_requests.csv',gql); write_csv(HAR/'cloudfront_requests.csv',cf); write_csv(HAR/'sectional_candidates.csv',sec)
    write_json(HAR/'sanitised_capture_summary.json',{'har_supplied':bool(args.har),'requests':len(reqs),'graphql':len(gql),'cloudfront':len(cf),'sectional_candidates':len(sec)})
    write_text(HAR/'har_analysis_report.md','# Racing.com HAR Analysis V1\n\nNo HAR is required. If supplied, request URLs are hashed/sanitised and no cookies or auth headers are persisted.\n')
if __name__=='__main__': main()
