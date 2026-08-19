from edgeiq_weather_victoria_common_v1 import *
loc_fields='canonical_track_identity canonical_venue_name surface layout racecourse_latitude racecourse_longitude racecourse_elevation_m_if_known location_source location_source_url location_verified_at coordinate_confidence'.split()
loc=[]
for c,n,s,l in IN_SCOPE: loc.append({'canonical_track_identity':c,'canonical_venue_name':n,'surface':s,'layout':l,'racecourse_latitude':'','racecourse_longitude':'','racecourse_elevation_m_if_known':'','location_source':'NOT_YET_GOVERNED','location_source_url':'','location_verified_at':'','coordinate_confidence':'UNRESOLVED'})
for c,(n,p) in DIRECT.items(): loc.append({'canonical_track_identity':c,'canonical_venue_name':n,'surface':'TURF','layout':'TURF','racecourse_latitude':'','racecourse_longitude':'','racecourse_elevation_m_if_known':'','location_source':f'Existing {p} direct weather integration; BOM coordinate not required for live observation assignment.','location_source_url':'','location_verified_at':utc(),'coordinate_confidence':'DIRECT_SOURCE_LOCATION_NOT_REQUIRED'})
write_csv(DOCS_BOM/'edgeiq_victorian_racecourse_location_registry_v1.csv',loc,loc_fields)
write_json(DOCS_BOM/'edgeiq_victorian_racecourse_location_registry_v1.json',{'schema_version':'edgeiq_victorian_racecourse_location_registry_v1','generated_at':utc(),'records':loc})
cands=read_csv(DOCS_BOM/'edgeiq_victorian_track_bom_station_candidates_v1.csv'); by={}
for c in cands: by.setdefault(c.get('canonical_track_identity',''),[]).append(c)
fields='canonical_track_identity canonical_venue_name weather_source_family weather_provider bom_assignment_required selected_station_id selected_station_name fixed_or_portable distance_km elevation_difference_m station_relationship evidence_score approval_status selection_reason effective_from effective_to mapping_version reviewed_at'.split()
sel=[]
for c,n,s,l in IN_SCOPE:
 cs=by.get(c,[])
 if cs:
  x=cs[0]; status='REVIEW_REQUIRED_CONFLICT'; reason='Candidate station exists, but authoritative racecourse coordinates/elevation are not governed; final approval blocked.'; sid=x.get('bom_station_id',''); sn=x.get('bom_station_name',''); fixed=x.get('fixed_or_portable','UNKNOWN')
 else:
  status='UNRESOLVED'; reason='No governed fixed BOM observation station selected; do not force a proxy.'; sid=''; sn=''; fixed=''
 sel.append({'canonical_track_identity':c,'canonical_venue_name':n,'weather_source_family':'BOM_FALLBACK_CANDIDATE','weather_provider':'Bureau of Meteorology','bom_assignment_required':'true','selected_station_id':sid,'selected_station_name':sn,'fixed_or_portable':fixed,'distance_km':'','elevation_difference_m':'','station_relationship':'UNRESOLVED','evidence_score':'','approval_status':status,'selection_reason':reason,'effective_from':'','effective_to':'','mapping_version':'v1','reviewed_at':''})
for c,(n,p) in DIRECT.items(): sel.append({'canonical_track_identity':c,'canonical_venue_name':n,'weather_source_family':'RACECOURSE_DIRECT','weather_provider':p,'bom_assignment_required':'false','selected_station_id':'','selected_station_name':'','fixed_or_portable':'','distance_km':'','elevation_difference_m':'','station_relationship':'AT_TRACK_DIRECT_SOURCE','evidence_score':'','approval_status':'AUTO_APPROVED_DIRECT_LOCAL','selection_reason':f'Existing governed {p} racecourse-direct source preserved; BOM fallback not assigned.','effective_from':'2026-07-26','effective_to':'','mapping_version':'v1','reviewed_at':utc()})
write_csv(DOCS_BOM/'edgeiq_victorian_track_bom_station_selection_v1.csv',sel,fields)
write_json(DOCS_BOM/'edgeiq_victorian_track_bom_station_selection_v1.json',{'schema_version':'edgeiq_victorian_track_bom_station_selection_v1','generated_at':utc(),'records':sel})
manual=[r for r in sel if r['approval_status'] not in {'AUTO_APPROVED_DIRECT_LOCAL','AUTO_APPROVED_NEARBY_REPRESENTATIVE'}]
write_csv(DOCS_BOM/'edgeiq_victorian_track_bom_manual_review_v1.csv',manual,fields)
(DOCS_BOM/'edgeiq_victorian_track_bom_station_selection_report_v1.md').write_text(f'# EDGEiQ Victorian BOM Station Selection V1\n\nGenerated: {utc()}\n\nDirect VRC/MRC courses are approved. BOM fallback candidates remain review-required or unresolved until racecourse coordinates, distance/elevation and licence terms are governed.\n\nManual-review rows: {len(manual)}\n',encoding='utf-8')
(DOCS_BOM/'edgeiq_victorian_track_bom_manual_review_v1.md').write_text(f'# EDGEiQ Victorian Track BOM Manual Review V1\n\nRows requiring manual review: {len(manual)}\n',encoding='utf-8')
print(f'EDGEIQ_TRACK_BOM_STATION_SELECTION_V1 PARTIAL manual_review={len(manual)}')
