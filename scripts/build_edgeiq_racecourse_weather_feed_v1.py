from __future__ import annotations
import json, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'public'/'data';SUMMARY=DATA/'edgeiq_meetings_summary_feed_v1.json';OUTPUT=DATA/'edgeiq_racecourse_weather_feed_v1.json'
ALIASES={'CAULFIELD HEATH':'Caulfield East, Victoria, Australia','CAULFIELD':'Caulfield East, Victoria, Australia','FLEMINGTON':'Flemington, Victoria, Australia','THE VALLEY':'Moonee Ponds, Victoria, Australia','MOONEE VALLEY':'Moonee Ponds, Victoria, Australia','SANDOWN':'Springvale, Victoria, Australia','SANDOWN HILLSIDE':'Springvale, Victoria, Australia','SANDOWN LAKESIDE':'Springvale, Victoria, Australia','MORNINGTON':'Mornington, Victoria, Australia'}
def get_json(url:str):
 req=urllib.request.Request(url,headers={'User-Agent':'EDGEiQ-Racing/1.0'});return json.loads(urllib.request.urlopen(req,timeout=20).read().decode('utf-8'))
def locate(name:str):
 q=ALIASES.get(name.upper(),f'{name}, Victoria, Australia');u='https://geocoding-api.open-meteo.com/v1/search?'+urllib.parse.urlencode({'name':q.split(',')[0],'count':5,'language':'en','format':'json','countryCode':'AU'});rows=get_json(u).get('results') or []
 if not rows:return None
 r=rows[0];return {'query':q,'name':r.get('name'),'latitude':r.get('latitude'),'longitude':r.get('longitude'),'timezone':r.get('timezone')}
def weather(loc:dict):
 p={'latitude':loc['latitude'],'longitude':loc['longitude'],'current':'temperature_2m,apparent_temperature,precipitation,rain,weather_code,cloud_cover,wind_speed_10m,wind_direction_10m','daily':'weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max','timezone':'Australia/Melbourne','forecast_days':3};return get_json('https://api.open-meteo.com/v1/forecast?'+urllib.parse.urlencode(p))
def main():
 if not SUMMARY.exists():return 0
 src=json.loads(SUMMARY.read_text(encoding='utf-8'));seen={};rows=[]
 for day in src.get('days',[]):
  for m in day.get('meetings',[]):
   name=str(m.get('meeting') or m.get('venue') or '').strip()
   if not name:continue
   key=name.upper()
   if key not in seen:
    try:seen[key]=locate(name)
    except Exception:seen[key]=None
   loc=seen[key]
   if not loc:continue
   try:w=weather(loc)
   except Exception:continue
   rows.append({'meetingKey':m.get('meetingKey'),'meeting':name,'date':day.get('date'),'location':loc,'current':w.get('current',{}),'currentUnits':w.get('current_units',{}),'daily':w.get('daily',{}),'dailyUnits':w.get('daily_units',{}),'source':'Open-Meteo','fetchedAt':datetime.now(timezone.utc).isoformat()})
 OUTPUT.write_text(json.dumps({'schemaVersion':'edgeiq_racecourse_weather_feed_v1','generatedAt':datetime.now(timezone.utc).isoformat(),'rows':rows},separators=(',',':'))+'\n',encoding='utf-8');print(f'EDGEIQ_RACECOURSE_WEATHER_FEED_V1 PASS ROWS={len(rows)}');return 0
if __name__=='__main__':raise SystemExit(main())
