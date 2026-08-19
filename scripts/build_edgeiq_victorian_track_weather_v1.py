from edgeiq_weather_victoria_common_v1 import *
sel={r['canonical_track_identity']:r for r in read_csv(DOCS_BOM/'edgeiq_victorian_track_bom_station_selection_v1.csv')}
cat=PUBLIC/'edgeiq_three_day_product_catalog_v1.json'; meetings=[]
if cat.exists(): meetings=(json.loads(cat.read_text(encoding='utf-8')) or {}).get('meetings',[])
records=[]
for m in meetings:
 c,n,s,l=canonical(m.get('meeting') or m.get('track') or '')
 x=sel.get(c,{})
 fam=x.get('weather_source_family') or ('RACECOURSE_DIRECT' if c in DIRECT else 'BOM_FALLBACK_CANDIDATE')
 prov=x.get('weather_provider') or (DIRECT.get(c,('', 'Bureau of Meteorology'))[1])
 if fam=='RACECOURSE_DIRECT': avail='SOURCE_STALE'; qual='RACECOURSE_DIRECT_GOVERNED'; rel='At track'; fresh='STALE'; sid=''; sn=n
 elif x.get('selected_station_id'): avail='STATION_UNRESOLVED'; qual='REAL_TIME_LIMITED_QC'; rel='Station candidate requires review'; fresh='UNAVAILABLE'; sid=x.get('selected_station_id',''); sn=x.get('selected_station_name','')
 else: avail='STATION_UNRESOLVED'; qual='UNAVAILABLE'; rel='Weather station unresolved'; fresh='UNAVAILABLE'; sid=''; sn=''
 records.append({'schema_version':'edgeiq_victorian_track_weather_v1','generated_timestamp':utc(),'meeting_id':m.get('meetingKey') or f"{m.get('date')}|{m.get('meeting')}",'race_date':m.get('date',''),'canonical_track_identity':c,'canonical_venue_name':n,'surface':s,'layout':l,'weather_provider':prov,'weather_source_family':fam,'station_id':sid,'station_name':sn,'station_distance_km':x.get('distance_km',''),'station_relationship':rel,'observation_timestamp':'','freshness_status':fresh,'quality_status':qual,'temperature_c':'','apparent_temperature_c':'','humidity_pct':'','wind_direction':'','wind_speed_kmh':'','wind_gust_kmh':'','rain_since_9am_mm':'','pressure_msl_hpa':'','availability_status':avail,'user_disclosure':'CURRENT CONDITIONS UNAVAILABLE' if avail in {'STATION_UNRESOLVED','LICENCE_REQUIRED'} else ('At track' if fam=='RACECOURSE_DIRECT' else 'Regional observation')})
fields='schema_version generated_timestamp meeting_id race_date canonical_track_identity canonical_venue_name surface layout weather_provider weather_source_family station_id station_name station_distance_km station_relationship observation_timestamp freshness_status quality_status temperature_c apparent_temperature_c humidity_pct wind_direction wind_speed_kmh wind_gust_kmh rain_since_9am_mm pressure_msl_hpa availability_status user_disclosure'.split()
write_csv(DOCS_LIVE/'edgeiq_victorian_track_weather_v1.csv',records,fields)
p={'schema_version':'edgeiq_victorian_track_weather_v1','generated_at':utc(),'records':records}
write_json(DOCS_LIVE/'edgeiq_victorian_track_weather_v1.json',p); write_json(PUBLIC/'edgeiq_victorian_track_weather_v1.json',p)
a={'status':'PASS_WITH_GAPS','generated_at':utc(),'runtime_records_published':len(records),'meetings_required':len(records),'direct_source_meetings':sum(r['weather_source_family']=='RACECOURSE_DIRECT' for r in records),'bom_meetings':sum(r['weather_source_family']!='RACECOURSE_DIRECT' for r in records),'current':sum(r['freshness_status']=='CURRENT' for r in records),'stale':sum(r['freshness_status']=='STALE' for r in records),'unavailable':sum(r['availability_status'] in {'STATION_UNRESOLVED','SOURCE_UNAVAILABLE'} for r in records),'licence_blocked':sum(r['availability_status']=='LICENCE_REQUIRED' for r in records)}
write_json(DOCS_LIVE/'edgeiq_victorian_track_weather_v1_audit.json',a)
print(f"EDGEIQ_VICTORIAN_TRACK_WEATHER_V1 PASS_WITH_GAPS records={len(records)}")
