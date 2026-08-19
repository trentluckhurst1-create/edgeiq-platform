from edgeiq_weather_victoria_common_v1 import *
FIELDS='source_track_name normalised_source_track_name canonical_venue_name canonical_track_identity display_name state surface layout sponsor_removed sponsor_token_removed alias_rule weather_source_family weather_provider bom_assignment_required active notes'.split()
def row(src,c,n,s,l,rule='CANONICAL_IDENTITY',tok='',note=''):
 direct=c in DIRECT; prov=DIRECT[c][1] if direct else 'BOM'
 return {'source_track_name':src,'normalised_source_track_name':norm(src),'canonical_venue_name':n,'canonical_track_identity':c,'display_name':n,'state':'VIC','surface':s,'layout':l,'sponsor_removed':'YES' if tok else 'NO','sponsor_token_removed':tok,'alias_rule':rule,'weather_source_family':'RACECOURSE_DIRECT' if direct else 'BOM_FALLBACK_CANDIDATE','weather_provider':prov,'bom_assignment_required':'false' if direct else 'true','active':'true','notes':note}
rows=[]
for c,n,s,l in IN_SCOPE: rows.append(row(n,c,n,s,l))
for c,(n,p) in DIRECT.items(): rows.append(row(n,c,n,'TURF','TURF',note=f'Existing direct {p} racecourse weather source preserved.'))
for src,(c,n,s,l) in SPECIAL.items(): rows.append(row(src.title(),c,n,s,l,'SPECIAL_CANONICAL_CONVERSION','Southside' if src.startswith('SOUTHSIDE') else '', 'Governed special alias conversion.'))
for c,n,s,l in IN_SCOPE:
 for sponsor in SPONSORS:
  if sponsor=='Southside' and c not in {'CRANBOURNE','TYNONG','TYNONG_SYNTHETIC'}: continue
  rows.append(row(f'{sponsor} {n}',c,n,s,l,'KNOWN_SPONSOR_PREFIX_REMOVAL',sponsor,'Evidence-based sponsor prefix alias.'))
for path in PUBLIC.glob('*.csv'):
 if not any(x in path.name.lower() for x in ['meeting','race_list','catalog','track']): continue
 for r in read_csv(path)[:20000]:
  for col in ['track','meeting','track_name','venue','course']:
   v=r.get(col,'').strip()
   if not v: continue
   c,n,s,l=canonical(v)
   if c in {x[0] for x in IN_SCOPE} or c in DIRECT:
    tok=next((sp for sp in SPONSORS if norm(v).startswith(norm(sp)+' ')),'')
    rows.append(row(v,c,n,s,l,'OBSERVED_SPONSOR_PREFIX_REMOVAL' if tok else 'OBSERVED_ALIAS_TO_CANONICAL',tok,'Observed in repository feed.'))
uniq={}
for r in rows:
 if r['normalised_source_track_name'] in {'','VIC'}: continue
 uniq[(r['normalised_source_track_name'],r['canonical_track_identity'])]=r
rows=list(uniq.values())
write_csv(DOCS_BOM/'edgeiq_victorian_track_alias_registry_v1.csv',rows,FIELDS)
write_json(DOCS_BOM/'edgeiq_victorian_track_alias_registry_v1.json',{'schema_version':'edgeiq_victorian_track_alias_registry_v1','generated_at':utc(),'record_count':len(rows),'records':rows})
expected={c for c,_,_,_ in IN_SCOPE}|set(DIRECT); represented={r['canonical_track_identity'] for r in rows}; missing=sorted(expected-represented)
direct_ok=all(any(r['canonical_track_identity']==c and r['weather_source_family']=='RACECOURSE_DIRECT' and r['bom_assignment_required']=='false' for r in rows) for c in DIRECT)
a={'status':'PASS' if not missing and direct_ok else 'FAIL','generated_at':utc(),'rows':len(rows),'expected_identities':len(expected),'represented_identities':len(represented),'missing_identities':missing,'direct_sources_preserved':direct_ok,'blank_vic_record_created':any(r['normalised_source_track_name']=='VIC' for r in rows),'tynong_normalisation_complete':any(r['source_track_name'].upper().startswith('PAKENHAM') and r['canonical_venue_name'].startswith('Tynong') for r in rows),'cranbourne_normalisation_complete':any(r['source_track_name'].upper()=='SOUTHSIDE CRANBOURNE' and r['canonical_venue_name']=='Cranbourne' for r in rows)}
write_json(DOCS_BOM/'edgeiq_victorian_track_alias_audit_v1.json',a)
print(f"EDGEIQ_VICTORIAN_TRACK_ALIAS_REGISTRY_V1 {a['status']} rows={len(rows)}")
