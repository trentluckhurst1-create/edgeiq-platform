from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'src'/'edgeiq-os'/'race'/'services'/'weatherFeed.ts'
checkpoint=ROOT/'src'/'edgeiq-os'/'race'/'services'/'weatherFeed_CHECKPOINT_PRE_VICTORIAN_TRACK_WEATHER_V1.ts'
if path.exists() and not checkpoint.exists(): checkpoint.write_text(path.read_text(encoding='utf-8'),encoding='utf-8')
text=path.read_text(encoding='utf-8')
if 'const VICTORIAN_TRACK_WEATHER_URL = "/data/edgeiq_victorian_track_weather_v1.json";' not in text:
 text=text.replace('const ON_TRACK_WEATHER_URL = "/data/edgeiq_on_track_weather_governed_v1_2.json";\n','const ON_TRACK_WEATHER_URL = "/data/edgeiq_on_track_weather_governed_v1_2.json";\nconst VICTORIAN_TRACK_WEATHER_URL = "/data/edgeiq_victorian_track_weather_v1.json";\n')
if 'victorianTrack: MetropolitanWeatherRecord[];' not in text:
 text=text.replace('  onTrack: MetropolitanWeatherRecord[];\n','  onTrack: MetropolitanWeatherRecord[];\n  victorianTrack: MetropolitanWeatherRecord[];\n')
helper='''function victorianTrackToMetropolitan(record: Record<string, unknown>): MetropolitanWeatherRecord {
  const provider = firstText(record.weather_provider, "Bureau of Meteorology");
  return {
    meeting_key: record.canonical_venue_name,
    meeting: record.canonical_venue_name,
    course: record.canonical_venue_name,
    provider,
    source_name: provider,
    source_url: null,
    source_endpoint: null,
    fetched_at_utc: record.generated_timestamp,
    source_observed_datetime: record.observation_timestamp,
    source_observed_time: record.observation_timestamp,
    station_status: record.availability_status,
    source_status: record.availability_status,
    governed_source_state: record.availability_status,
    freshness_status: record.freshness_status,
    official_track_rating: null,
    official_rail: null,
    going_stick: null,
    temperature_c: record.temperature_c,
    rainfall_24h_mm: null,
    rainfall_since_9am_mm: record.rain_since_9am_mm,
    rainfall_today_mm: record.rain_since_9am_mm,
    rainfall_7day_mm: null,
    forecast_rainfall: null,
    humidity_pct: record.humidity_pct,
    moisture_loss_mm: null,
    soil_moisture: null,
    irrigation: null,
    weather_comment: record.user_disclosure,
    additional_comment: record.station_relationship,
    wind_direction: record.wind_direction,
    wind_speed_kmh: record.wind_speed_kmh,
    wind_average_kmh: record.wind_speed_kmh,
    wind_gust_kmh: record.wind_gust_kmh,
    wind_gust_max_kmh: record.wind_gust_kmh,
    wind_station: null,
    wind_station_count: 1,
    turf_http_status: null,
    wind_http_status: null,
    errors: [],
  };
}

'''
if 'function victorianTrackToMetropolitan' not in text:
 idx=text.find('function onTrackToMetropolitan(record: Record<string, unknown>): MetropolitanWeatherRecord {')
 if idx>=0: text=text[:idx]+helper+text[idx:]
old='''  pendingFeeds = Promise.all([
    loadJson(METROPOLITAN_URL),
    loadJson(RACE_WEATHER_URL),
    loadJson(ON_TRACK_WEATHER_URL).catch(() => ({ records: [] })),
  ])
    .then(([metropolitanPayload, racePayload, onTrackPayload]) => {'''
new='''  pendingFeeds = Promise.all([
    loadJson(METROPOLITAN_URL),
    loadJson(RACE_WEATHER_URL),
    loadJson(ON_TRACK_WEATHER_URL).catch(() => ({ records: [] })),
    loadJson(VICTORIAN_TRACK_WEATHER_URL).catch(() => ({ records: [] })),
  ])
    .then(([metropolitanPayload, racePayload, onTrackPayload, victorianTrackPayload]) => {'''
if old in text: text=text.replace(old,new)
needle='''      const onTrack = Array.isArray((onTrackPayload as any)?.records)
        ? (onTrackPayload as any).records.map((record: Record<string, unknown>) => onTrackToMetropolitan(record))
        : [];
'''
rep=needle+'''      const victorianTrack = Array.isArray((victorianTrackPayload as any)?.records)
        ? (victorianTrackPayload as any).records.map((record: Record<string, unknown>) => victorianTrackToMetropolitan(record))
        : [];
'''
if 'const victorianTrack = Array.isArray((victorianTrackPayload as any)?.records)' not in text:
 text=text.replace(needle,rep)
text=text.replace('if (metropolitan.length > 10000 || raceWeather.length > 10000 || onTrack.length > 10000)','if (metropolitan.length > 10000 || raceWeather.length > 10000 || onTrack.length > 10000 || victorianTrack.length > 10000)')
text=text.replace('"EDGEiQ rejected oversized weather feed", metropolitan.length, raceWeather.length, onTrack.length','"EDGEiQ rejected oversized weather feed", metropolitan.length, raceWeather.length, onTrack.length, victorianTrack.length')
if 'victorianTrack: [],' not in text: text=text.replace('          onTrack: [],\n','          onTrack: [],\n          victorianTrack: [],\n')
text=text.replace('metropolitan: [...onTrack, ...metropolitan],','metropolitan: [...victorianTrack, ...onTrack, ...metropolitan],')
if 'victorianTrack,' not in text: text=text.replace('        onTrack,\n','        onTrack,\n        victorianTrack,\n')
path.write_text(text,encoding='utf-8')
print('PATCH_EDGEIQ_WEATHER_WORKSPACE_LIVE_CONDITIONS_V1 PASS')
