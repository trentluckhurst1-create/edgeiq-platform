from edgeiq_weather_victoria_common_v1 import *
def files_matching(patterns):
 rows=[]
 for base in [ROOT/'scripts',ROOT/'public'/'data',ROOT/'data'/'weather',ROOT/'docs'/'operations-readiness',ROOT/'src'/'edgeiq-os'/'race']:
  if not base.exists(): continue
  for p in base.rglob('*'):
   if p.is_file() and any(x in p.name.lower() for x in patterns): rows.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size})
 return sorted(rows,key=lambda r:r['path'])
b={'schema_version':'edgeiq_victorian_weather_baseline_v1','generated_at':utc(),'weather_files':files_matching(['weather','bom','track_intelligence','metropolitan']),'existing_direct_integrations':[{'track':'Flemington','provider':'VRC','source':'edgeiq_on_track_weather_governed_v1_2.json'},{'track':'Caulfield','provider':'MRC/TurfTrax','source':'edgeiq_on_track_weather_governed_v1_2.json'},{'track':'Caulfield Heath','provider':'MRC/TurfTrax','source':'edgeiq_on_track_weather_governed_v1_2.json'},{'track':'Sandown Hillside','provider':'MRC/TurfTrax','source':'edgeiq_on_track_weather_governed_v1_2.json'},{'track':'Sandown Lakeside','provider':'MRC/TurfTrax','source':'edgeiq_on_track_weather_governed_v1_2.json'},{'track':'Mornington','provider':'MRC/TurfTrax','source':'edgeiq_on_track_weather_governed_v1_2.json'}],'known_prior_bom_work':['build_edgeiq_vic_bom_observations_v1.py','build_edgeiq_bom_track_location_registry_v1.py','build_edgeiq_weather_source_registry_v1.py'],'important_caveat':'Forecast locations and observation stations are separate; no BOM station is approved without governed racecourse/station evidence.'}
write_json(DOCS_BOM/'edgeiq_victorian_weather_baseline_v1.json',b)
md=['# EDGEiQ Victorian Weather Baseline V1','',f"Generated: {b['generated_at']}",'','## Existing Direct Integrations']+[f"- {x['track']}: {x['provider']} via `{x['source']}`" for x in b['existing_direct_integrations']]+['','## Repository Weather Assets',f"Weather-related files found: {len(b['weather_files'])}",'','## Governance Note',b['important_caveat']]
(DOCS_BOM/'edgeiq_victorian_weather_baseline_v1.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
print(f"EDGEIQ_VICTORIAN_WEATHER_BASELINE_V1 PASS files={len(b['weather_files'])}")
