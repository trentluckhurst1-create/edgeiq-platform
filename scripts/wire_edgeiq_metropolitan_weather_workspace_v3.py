from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

types_path = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "services"
    / "weather"
    / "WeatherTypes.ts"
)

component_path = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "race"
    / "components"
    / "MeetingWeatherWorkspace.tsx"
)

css_path = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "styles"
    / "edgeiqOsV2.css"
)

weather_types = r'''export type EdgeiqWeatherRecord = {
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
'''

weather_component = r'''import { useCallback, useEffect, useMemo, useState } from "react";
import {
  getMeetingWeather,
  type EdgeiqWeatherRecord,
} from "../../services/weather";

type MeetingWeatherWorkspaceProps = {
  raceBook: any;
  clean: (value: any) => string;
};

type WeatherDatumProps = {
  label: string;
  value: string | null;
  wide?: boolean;
};

function usableText(value: unknown): string | null {
  if (value === undefined || value === null) return null;

  const text = String(value).trim();

  if (
    !text ||
    text === "-" ||
    text === "—" ||
    ["n/a", "na", "none", "null", "undefined"].includes(
      text.toLowerCase(),
    )
  ) {
    return null;
  }

  return text;
}

function firstText(...values: unknown[]): string | null {
  for (const value of values) {
    const text = usableText(value);
    if (text) return text;
  }

  return null;
}

function metric(
  value: number | null | undefined,
  unit: string,
  precision = 1,
): string | null {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(value)
  ) {
    return null;
  }

  const rounded = Number(value.toFixed(precision));
  return `${rounded}${unit}`;
}

function joinValues(...values: Array<string | null>): string | null {
  const usable = values.filter(
    (value): value is string => Boolean(value),
  );

  return usable.length ? usable.join(" ") : null;
}

function WeatherDatum({
  label,
  value,
  wide = false,
}: WeatherDatumProps) {
  if (!value) return null;

  return (
    <div
      className={[
        "eiq-metro-weather-datum",
        wide ? "is-wide" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function SourceStatus({
  status,
}: {
  status: string | null;
}) {
  const normalised = String(status ?? "").toUpperCase();
  const isLive = normalised === "LIVE";

  return (
    <span
      className={[
        "eiq-metro-weather-status",
        isLive ? "is-live" : "is-unavailable",
      ].join(" ")}
    >
      {isLive ? "LIVE" : "UNAVAILABLE"}
    </span>
  );
}

export function MeetingWeatherWorkspace({
  raceBook,
  clean,
}: MeetingWeatherWorkspaceProps) {
  const official = raceBook?.official ?? {};
  const localTrack =
    raceBook?.track ??
    raceBook?.trackIntel ??
    raceBook?.trackIntelligence ??
    {};

  const meeting =
    firstText(
      clean(official.meeting),
      clean(official.venue),
      clean(official.track),
    ) ?? "Current Meeting";

  const raceDate = firstText(
    clean(official.date),
    clean(official.raceDate),
    clean(official.meetingDate),
  );

  const [weather, setWeather] =
    useState<EdgeiqWeatherRecord | null>(null);

  const [loadState, setLoadState] = useState<
    "LOADING" | "READY" | "UNAVAILABLE"
  >("LOADING");

  const loadWeather = useCallback(
    async (force = false) => {
      try {
        const record = await getMeetingWeather(meeting, force);

        setWeather(record);
        setLoadState(record ? "READY" : "UNAVAILABLE");
      } catch {
        setLoadState("UNAVAILABLE");
      }
    },
    [meeting],
  );

  useEffect(() => {
    void loadWeather(false);

    const refreshTimer = window.setInterval(() => {
      void loadWeather(true);
    }, 5 * 60 * 1000);

    return () => {
      window.clearInterval(refreshTimer);
    };
  }, [loadWeather]);

  const values = useMemo(() => {
    const officialTrackRating = firstText(
      weather?.official_track_rating,
      clean(official.trackCondition),
      clean(localTrack.trackCondition),
      clean(localTrack.condition),
    );

    const rail = firstText(
      weather?.official_rail,
      clean(official.rail),
      clean(localTrack.rail),
      clean(localTrack.railPosition),
    );

    const temperature = metric(
      weather?.temperature_c,
      "°C",
      1,
    );

    const temperatureRange =
      weather?.temperature_min_c !== null &&
      weather?.temperature_min_c !== undefined &&
      weather?.temperature_max_c !== null &&
      weather?.temperature_max_c !== undefined
        ? `${metric(weather.temperature_min_c, "°C")} – ${metric(
            weather.temperature_max_c,
            "°C",
          )}`
        : null;

    const wind = joinValues(
      firstText(weather?.wind_direction),
      metric(weather?.wind_speed_kmh, " km/h", 1),
    );

    const windGust = weather?.wind_gust_kmh
      ? joinValues(
          metric(weather.wind_gust_kmh, " km/h", 1),
          weather.wind_gust_event
            ? `at ${weather.wind_gust_event}`
            : null,
        )
      : null;

    return {
      officialTrackRating,
      rail,
      goingStick: firstText(weather?.going_stick),
      irrigation: firstText(weather?.irrigation),

      temperature,
      temperatureRange,
      humidity: metric(weather?.humidity_pct, "%", 1),

      rainfallToday: metric(
        weather?.rainfall_today_mm,
        " mm",
        1,
      ),
      rainfall24h: metric(
        weather?.rainfall_24h_mm,
        " mm",
        1,
      ),
      rainfallSince: metric(
        weather?.rainfall_since_9am_mm,
        " mm",
        1,
      ),
      rainfall7day: metric(
        weather?.rainfall_7day_mm,
        " mm",
        1,
      ),
      rainfallCurrent: metric(
        weather?.rainfall_current_mm,
        " mm",
        1,
      ),

      wind,
      windGust,

      moistureLoss: metric(
        weather?.moisture_loss_mm,
        " mm",
        2,
      ),
      moistureLoss7day: metric(
        weather?.moisture_loss_7day_mm,
        " mm",
        2,
      ),

      weatherComment: firstText(weather?.weather_comment),
      additionalComment: firstText(
        weather?.additional_comment,
      ),

      provider: firstText(weather?.source_name),
      observedDate: firstText(
        weather?.source_observed_date,
      ),
      observedTime: firstText(
        weather?.source_observed_time,
      ),
      stationStatus: firstText(weather?.station_status),
      meetingTitle: firstText(weather?.meeting_title),
      meetingDate: firstText(weather?.meeting_date),
      ratingUpdated: firstText(
        weather?.official_track_rating_updated,
      ),
    };
  }, [weather, official, localTrack, clean]);

  const meetingContext = [
    raceDate ?? values.meetingDate,
    values.officialTrackRating,
    values.rail ? `Rail ${values.rail}` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  const hasTrackData = Boolean(
    values.officialTrackRating ||
      values.rail ||
      values.goingStick ||
      values.irrigation,
  );

  const hasWeatherData = Boolean(
    values.temperature ||
      values.humidity ||
      values.rainfallToday ||
      values.rainfall24h ||
      values.rainfall7day ||
      values.wind ||
      values.windGust ||
      values.moistureLoss,
  );

  const hasComments = Boolean(
    values.weatherComment ||
      values.additionalComment,
  );

  return (
    <section className="eiq-metro-weather">
      <header className="eiq-metro-weather__header">
        <div>
          <span>Meeting Weather</span>
          <strong>{values.meetingTitle ?? meeting}</strong>
          {meetingContext ? <p>{meetingContext}</p> : null}
        </div>

        <div className="eiq-metro-weather__source-summary">
          <SourceStatus status={weather?.source_status ?? null} />

          {values.provider ? (
            <strong>{values.provider}</strong>
          ) : null}

          {values.observedTime ? (
            <small>
              Updated {values.observedTime}
              {values.observedDate
                ? ` · ${values.observedDate}`
                : ""}
            </small>
          ) : null}
        </div>
      </header>

      {loadState === "LOADING" && !weather ? (
        <section className="eiq-metro-weather__empty">
          <span>Official Source</span>
          <strong>Loading meeting conditions.</strong>
        </section>
      ) : null}

      {loadState === "UNAVAILABLE" && !weather ? (
        <section className="eiq-metro-weather__empty">
          <span>Official Source</span>
          <strong>
            Official weather data is not available for this meeting.
          </strong>
          <p>
            EDGEIQ does not fill missing source fields with assumptions.
          </p>
        </section>
      ) : null}

      {hasTrackData ? (
        <section className="eiq-metro-weather__panel">
          <header>
            <span>Official Track</span>
            {values.ratingUpdated ? (
              <small>{values.ratingUpdated}</small>
            ) : null}
          </header>

          <div className="eiq-metro-weather__grid">
            <WeatherDatum
              label="Official Track Rating"
              value={values.officialTrackRating}
            />

            <WeatherDatum
              label="Official Rail Position"
              value={values.rail}
              wide
            />

            <WeatherDatum
              label="GoingStick"
              value={values.goingStick}
              wide
            />

            <WeatherDatum
              label="Irrigation"
              value={values.irrigation}
              wide
            />
          </div>
        </section>
      ) : null}

      {hasWeatherData ? (
        <section className="eiq-metro-weather__panel">
          <header>
            <span>Live Station Conditions</span>
            {values.stationStatus ? (
              <small>
                Station {values.stationStatus.toLowerCase()}
              </small>
            ) : null}
          </header>

          <div className="eiq-metro-weather__grid">
            <WeatherDatum
              label="Temperature"
              value={values.temperature}
            />

            <WeatherDatum
              label="Temperature Range"
              value={values.temperatureRange}
            />

            <WeatherDatum
              label="Humidity"
              value={values.humidity}
            />

            <WeatherDatum
              label="Wind"
              value={values.wind}
            />

            <WeatherDatum
              label="Wind Gust"
              value={values.windGust}
            />

            <WeatherDatum
              label="Rainfall Today"
              value={values.rainfallToday}
            />

            <WeatherDatum
              label="Rainfall — 24 Hours"
              value={values.rainfall24h}
            />

            <WeatherDatum
              label="Rainfall Since Reading Period"
              value={values.rainfallSince}
            />

            <WeatherDatum
              label="Current Rainfall"
              value={values.rainfallCurrent}
            />

            <WeatherDatum
              label="Rainfall — 7 Days"
              value={values.rainfall7day}
            />

            <WeatherDatum
              label="Moisture Loss — 24 Hours"
              value={values.moistureLoss}
            />

            <WeatherDatum
              label="Moisture Loss — 7 Days"
              value={values.moistureLoss7day}
            />
          </div>
        </section>
      ) : null}

      {hasComments ? (
        <section className="eiq-metro-weather__panel">
          <header>
            <span>Official Reports</span>
          </header>

          <div className="eiq-metro-weather__reports">
            {values.weatherComment ? (
              <article>
                <span>Official Weather Forecast</span>
                <p>{values.weatherComment}</p>
              </article>
            ) : null}

            {values.additionalComment ? (
              <article>
                <span>Track Manager Notes</span>
                <p>{values.additionalComment}</p>
              </article>
            ) : null}
          </div>
        </section>
      ) : null}

      {weather ? (
        <section className="eiq-metro-weather__provenance">
          <div>
            <span>Provider</span>
            <strong>{values.provider ?? weather.provider}</strong>
          </div>

          <div>
            <span>Feed Status</span>
            <strong>{weather.source_status}</strong>
          </div>

          <div>
            <span>Observation</span>
            <strong>
              {joinValues(
                values.observedDate,
                values.observedTime,
              ) ?? "Source timestamp unavailable"}
            </strong>
          </div>

          <div>
            <span>Refresh</span>
            <strong>Every 5 minutes</strong>
          </div>
        </section>
      ) : null}

      <footer className="eiq-metro-weather__governance">
        <span>EDGEIQ Weather Standard</span>
        <p>
          Official observations and clearly labelled source forecasts
          are displayed. EDGEIQ does not project future official track
          ratings or steward decisions.
        </p>
      </footer>
    </section>
  );
}
'''

weather_css = r'''

/* =========================================================
   EDGEIQ METROPOLITAN WEATHER WORKSPACE V3
   VRC + TurfTrax provider registry
   ========================================================= */

.eiq-metro-weather {
  display: grid;
  gap: 12px;
}

.eiq-metro-weather__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 15px 16px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 12px;
  background: rgba(7, 12, 22, 0.82);
}

.eiq-metro-weather__header > div:first-child > span,
.eiq-metro-weather__panel > header > span,
.eiq-metro-weather__reports article > span,
.eiq-metro-weather__empty > span,
.eiq-metro-weather__governance > span {
  display: block;
  color: rgba(148, 163, 184, 0.9);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.11em;
  text-transform: uppercase;
}

.eiq-metro-weather__header > div:first-child > strong {
  display: block;
  margin-top: 5px;
  color: #f8fafc;
  font-size: 16px;
  font-weight: 700;
  line-height: 1.25;
}

.eiq-metro-weather__header p {
  margin: 5px 0 0;
  color: rgba(203, 213, 225, 0.76);
  font-size: 11px;
}

.eiq-metro-weather__source-summary {
  display: grid;
  justify-items: end;
  gap: 4px;
  min-width: 160px;
  text-align: right;
}

.eiq-metro-weather__source-summary > strong {
  color: rgba(241, 245, 249, 0.94);
  font-size: 11px;
  font-weight: 700;
}

.eiq-metro-weather__source-summary > small {
  color: rgba(148, 163, 184, 0.78);
  font-size: 10px;
}

.eiq-metro-weather-status {
  display: inline-flex;
  align-items: center;
  min-height: 19px;
  padding: 2px 7px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 999px;
  font-size: 8px;
  font-weight: 800;
  letter-spacing: 0.1em;
}

.eiq-metro-weather-status.is-live {
  color: rgba(187, 247, 208, 0.96);
  border-color: rgba(74, 222, 128, 0.28);
  background: rgba(22, 101, 52, 0.17);
}

.eiq-metro-weather-status.is-unavailable {
  color: rgba(203, 213, 225, 0.82);
}

.eiq-metro-weather__panel,
.eiq-metro-weather__empty,
.eiq-metro-weather__governance {
  padding: 13px;
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 12px;
  background: rgba(10, 16, 28, 0.72);
}

.eiq-metro-weather__panel > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.eiq-metro-weather__panel > header > small {
  color: rgba(148, 163, 184, 0.72);
  font-size: 10px;
}

.eiq-metro-weather__grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(130px, 1fr));
  gap: 7px;
}

.eiq-metro-weather-datum {
  min-height: 60px;
  padding: 10px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 9px;
  background: rgba(2, 7, 16, 0.43);
}

.eiq-metro-weather-datum.is-wide {
  grid-column: span 2;
}

.eiq-metro-weather-datum > span {
  display: block;
  color: rgba(148, 163, 184, 0.82);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}

.eiq-metro-weather-datum > strong {
  display: block;
  margin-top: 7px;
  color: #f1f5f9;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.45;
  white-space: pre-line;
}

.eiq-metro-weather__reports {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.eiq-metro-weather__reports article {
  padding: 11px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 9px;
  background: rgba(2, 7, 16, 0.43);
}

.eiq-metro-weather__reports p {
  margin: 7px 0 0;
  color: rgba(226, 232, 240, 0.9);
  font-size: 11px;
  line-height: 1.55;
  white-space: pre-line;
}

.eiq-metro-weather__provenance {
  display: grid;
  grid-template-columns: repeat(4, minmax(120px, 1fr));
  gap: 1px;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 10px;
  background: rgba(148, 163, 184, 0.12);
}

.eiq-metro-weather__provenance > div {
  padding: 9px 10px;
  background: rgba(7, 12, 22, 0.94);
}

.eiq-metro-weather__provenance span {
  display: block;
  color: rgba(148, 163, 184, 0.76);
  font-size: 8px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eiq-metro-weather__provenance strong {
  display: block;
  margin-top: 4px;
  color: rgba(226, 232, 240, 0.9);
  font-size: 10px;
  font-weight: 700;
}

.eiq-metro-weather__empty strong {
  display: block;
  margin-top: 6px;
  color: rgba(241, 245, 249, 0.94);
  font-size: 12px;
}

.eiq-metro-weather__empty p,
.eiq-metro-weather__governance p {
  margin: 6px 0 0;
  color: rgba(148, 163, 184, 0.78);
  font-size: 10px;
  line-height: 1.45;
}

@media (max-width: 1100px) {
  .eiq-metro-weather__grid {
    grid-template-columns: repeat(2, minmax(130px, 1fr));
  }

  .eiq-metro-weather__provenance {
    grid-template-columns: repeat(2, minmax(120px, 1fr));
  }
}

@media (max-width: 720px) {
  .eiq-metro-weather__header {
    display: grid;
  }

  .eiq-metro-weather__source-summary {
    justify-items: start;
    text-align: left;
  }

  .eiq-metro-weather__grid,
  .eiq-metro-weather__reports,
  .eiq-metro-weather__provenance {
    grid-template-columns: 1fr;
  }

  .eiq-metro-weather-datum.is-wide {
    grid-column: auto;
  }
}
'''

types_path.write_text(
    weather_types,
    encoding="utf-8",
)

component_path.write_text(
    weather_component,
    encoding="utf-8",
)

css = css_path.read_text(
    encoding="utf-8",
)

marker = "EDGEIQ METROPOLITAN WEATHER WORKSPACE V3"

if marker not in css:
    css = css.rstrip() + "\n" + weather_css + "\n"

css_path.write_text(
    css,
    encoding="utf-8",
)

print("[EDGEIQ] Metropolitan Weather Workspace V3 wired")
print("[EDGEIQ] VRC and TurfTrax canonical fields rendered")
print("[EDGEIQ] Form and Map files were not modified")
