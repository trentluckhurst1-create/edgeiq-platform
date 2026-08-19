from edgeiq_weather_victoria_common_v1 import *
lic=json.loads((DOCS_BOM/'edgeiq_bom_data_access_and_licensing_assessment_v1.json').read_text(encoding='utf-8')) if (DOCS_BOM/'edgeiq_bom_data_access_and_licensing_assessment_v1.json').exists() else {}
sel=read_csv(DOCS_BOM/'edgeiq_victorian_track_bom_station_selection_v1.csv')
rows=[]
for r in sel:
 if r.get('weather_source_family')!='BOM_FALLBACK_CANDIDATE': continue
 if r.get('approval_status')!='AUTO_APPROVED_NEARBY_REPRESENTATIVE': continue
 rows.append({'station_id':r.get('selected_station_id'),'station_name':r.get('selected_station_name'),'observation_timestamp':'','timezone':'Australia/Melbourne','temperature_c':'','apparent_temperature_c':'','dew_point_c':'','relative_humidity_pct':'','delta_t_c':'','wind_direction':'','wind_speed_kmh':'','wind_gust_kmh':'','pressure_msl_hpa':'','rain_since_9am_mm':'','low_temperature_c':'','high_temperature_c':'','source_product_id':'','source_retrieved_at':'','source_url_or_product':'','freshness_status':'UNAVAILABLE','quality_status':'REAL_TIME_LIMITED_QC','collection_status':'LICENCE_REQUIRED'})
fields='station_id station_name observation_timestamp timezone temperature_c apparent_temperature_c dew_point_c relative_humidity_pct delta_t_c wind_direction wind_speed_kmh wind_gust_kmh pressure_msl_hpa rain_since_9am_mm low_temperature_c high_temperature_c source_product_id source_retrieved_at source_url_or_product freshness_status quality_status collection_status'.split()
write_csv(DOCS_OBS/'edgeiq_bom_victorian_latest_observations_v1.csv',rows,fields)
write_json(DOCS_OBS/'edgeiq_bom_victorian_latest_observations_v1.json',{'schema_version':'edgeiq_bom_victorian_latest_observations_v1','generated_at':utc(),'collection_status':lic.get('production_collection_status','LICENCE_REQUIRED'),'record_count':len(rows),'records':rows})
write_json(DOCS_OBS/'edgeiq_bom_observation_ingestion_audit_v1.json',{'status':'LICENCE_REQUIRED','generated_at':utc(),'approved_bom_station_rows':len(rows),'current_observations':0,'stale_observations':0,'unavailable_observations':len(rows),'notes':['No automated BOM production collection executed because data access is licence-gated.','No fabricated observations were published.']})
print('EDGEIQ_BOM_LATEST_OBSERVATIONS_V1 LICENCE_REQUIRED')
