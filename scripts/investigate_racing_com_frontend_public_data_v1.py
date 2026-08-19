
from __future__ import annotations
import json, re
from pathlib import Path
from edgeiq_racing_com_public_common_v1 import *

def main():
    ensure(); rows=read_csv(PUB/'edgeiq_racingcom_runner_speed_fact_v1.csv')
    page=first(rows[0],['source_page_url'],'https://www.racing.com/form') if rows else 'https://www.racing.com/form'
    inv=[]; matches=[]; ops=[]; res=[]
    r=request_public(page)
    html=r['body'].decode('utf-8','ignore') if r['body'] else ''
    html_path=FRONTEND/'public_speed_page_redacted.html'; write_text(html_path,redact_text(html))
    inv.append({'resource_type':'html','url':page,'http_status':r['status'],'bytes':len(r['body']),'sha256':r['hash'],'stored_path':str(html_path.relative_to(ROOT)),'access_classification':'PUBLIC_ANONYMOUS_CONFIRMED' if r['ok'] else ('ACCESS_FORBIDDEN' if r['status'] in (401,403) else 'UNKNOWN')})
    scripts=[]
    for src in re.findall(r'<script[^>]+src=["\']([^"\']+)',html,re.I):
        u=src if src.startswith('http') else ('https://www.racing.com'+src if src.startswith('/') else src)
        if 'racing.com' in u or 'racing' in u: scripts.append(u)
    for u in sorted(set(scripts))[:40]:
        rr=request_public(u); body=rr['body']; name=sha_bytes(u.encode())[:12]+'.js'; sp=FRONTEND/'bundles'/name; sp.parent.mkdir(parents=True,exist_ok=True); write_text(sp,redact_text(body.decode('utf-8','ignore')))
        text=body.decode('utf-8','ignore')
        inv.append({'resource_type':'javascript','url':u,'http_status':rr['status'],'bytes':len(body),'sha256':rr['hash'],'stored_path':str(sp.relative_to(ROOT)),'access_classification':'PUBLIC_ANONYMOUS_CONFIRMED' if rr['ok'] else ('ACCESS_FORBIDDEN' if rr['status'] in (401,403) else 'UNKNOWN')})
        for sym in SYMBOLS:
            for m in re.finditer(re.escape(sym),text,re.I):
                matches.append({'bundle_url':u,'symbol':sym,'offset':m.start(),'context':redact_text(text[max(0,m.start()-80):m.end()+120]).replace('\n',' ')})
        if 'getRaceForm' in text: ops.append({'operation_name':'getRaceForm','evidence_bundle_url':u,'evidence':'symbol_match','access':'frontend_public_bundle'})
        if 'cloudfront' in text.lower() or 'downloadCsv' in text: res.append({'candidate_type':'sectional_resource','evidence_bundle_url':u,'evidence':'cloudfront/download symbol match'})
    if not ops:
        ops.append({'operation_name':'getRaceForm','evidence_bundle_url':'local governed retained payloads','evidence':'outputs/sectionals/raw/VIC/racingcom_full_payloads/getRaceForm_*.json','access':'LOCAL_GOVERNED_EVIDENCE_DIRECT_PUBLIC_NOT_CONFIRMED'})
    if not res:
        res.append({'candidate_type':'runner_sectionals_payload','evidence_bundle_url':'local governed retained payloads','evidence':'data.sectionaltimes_callback.Horses[].SectionalTimes/SplitTimes'})
    write_csv(FRONTEND/'bundle_inventory.csv',inv); write_json(FRONTEND/'bundle_inventory.json',inv)
    write_csv(FRONTEND/'symbol_matches.csv',matches); write_json(FRONTEND/'symbol_matches.json',matches)
    write_json(FRONTEND/'graphql_operation_candidates.json',ops); write_json(FRONTEND/'sectional_resource_candidates.json',res)
    report=['# Racing.com Frontend Public Data Forensics V1','',f'Seed page: {page}',f'HTML status: {r["status"]}',f'Public JS bundles found: {len(scripts)}',f'Symbol matches: {len(matches)}','', 'Runner sectional source evidence is retained local getRaceForm payloads unless live public replay proves anonymous access.']
    write_text(FRONTEND/'frontend_forensics_report.md','\n'.join(report)+'\n')
if __name__=='__main__': main()
