export type EdgeiqWeatherRecord = {
  meeting_key: string;
  meeting: string;
  course: string;

  provider: string;
  source_name: string;
  source_url: string;
  source_endpoint?: string | null;

  fetched_at_utc: string;
  source_observed_date?: string | null;
  source_observed_time?: string | null;
  source_observed_datetime?: string | null;

  station_status?: string | null;
  source_status: string;

  official_track_rating: string | null;
  official_track_rating_updated?: string | null;
  official_rail: string | null;
  going_stick: string | null;

  temperature_c: number | null;
  temperature_min_c?: number | null;
  temperature_max_c?: number | null;

  rainfall_24h_mm: number | null;
  rainfall_since_9am_mm: number | null;
  rainfall_today_mm: number | null;
  rainfall_current_mm?: number | null;
  rainfall_7day_mm?: number | null;
  forecast_rainfall: string | null;

  humidity_pct: number | null;
  humidity_min_pct?: number | null;
  humidity_max_pct?: number | null;

  moisture_loss_mm: number | null;
  moisture_loss_7day_mm?: number | null;
  soil_moisture: string | number | null;

  irrigation: string | null;
  weather_comment: string | null;
  additional_comment: string | null;

  wind_direction: string | null;
  wind_direction_degrees?: number | null;
  wind_speed_kmh: number | null;
  wind_average_kmh?: number | null;
  wind_gust_kmh?: number | null;
  wind_gust_max_kmh?: number | null;
  wind_gust_event?: string | null;
  wind_station: string | null;
  wind_station_count: number;

  meeting_date?: string | null;
  meeting_title?: string | null;

  station_id?: string | number | null;
  station_type?: string | null;
  venue_id?: string | number | null;
  report_id?: string | null;

  going_waypoint_map?: string | null;
  going_zone_map?: string | null;

  provider_description?: string | null;
  provider_signature?: string | null;

  turf_http_status: number | null;
  wind_http_status: number | null;
  api_status?: number | null;

  errors: string[];
};

export type EdgeiqWeatherFeed = {
  schema_version: string;
  generated_at_utc: string;
  provider_registry?: Record<string, string>;
  records: EdgeiqWeatherRecord[];
};
