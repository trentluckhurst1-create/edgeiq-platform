import { useEffect, useMemo, useState } from "react";
import type { ThreeDayMeeting } from "../services/threeDayCatalog";
import {
  buildMeetingWeatherViewModel,
  loadWeatherTerminalFeeds,
  type MeetingWeatherViewModel,
  type WeatherTerminalFeeds,
  type WeatherValue,
} from "../services/weatherFeed";

type MeetingWeatherWorkspaceProps = {
  meeting: ThreeDayMeeting;
};

function valueOrUnavailable(value: string | null | undefined): string {
  return value && value.trim() ? value : "Unavailable";
}

function statusText(status: MeetingWeatherViewModel["status"]): string {
  if (status === "current") return "Current";
  if (status === "stale") return "Stale";
  if (status === "error") return "Unavailable";
  return "Unavailable";
}

function SummaryGrid({ items }: { items: WeatherValue[] }) {
  return (
    <dl className="eiq-weather-v1-summary-grid">
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd>{valueOrUnavailable(item.value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function WorkspaceHeader({ model }: { model: MeetingWeatherViewModel }) {
  const authority = valueOrUnavailable(model.source.authority);
  const observedAt = valueOrUnavailable(model.source.observedAt);
  return (
    <header className="eiq-weather-v1-header">
      <div>
        <span>WEATHER</span>
        <h2>Meeting weather and race-day conditions</h2>
        <p>{model.meetingName}</p>
      </div>
      <dl className="eiq-weather-v1-status-strip" aria-label="Weather data state">
        <div>
          <dt>STATE</dt>
          <dd>{statusText(model.status)}</dd>
        </div>
        <div>
          <dt>AUTHORITY</dt>
          <dd>{authority}</dd>
        </div>
        <div>
          <dt>OBSERVED</dt>
          <dd>{observedAt}</dd>
        </div>
      </dl>
    </header>
  );
}

function WeatherSummary({ model }: { model: MeetingWeatherViewModel }) {
  return (
    <section className="eiq-weather-v1-panel">
      <header>
        <span>Current Observations</span>
      </header>
      <SummaryGrid items={model.summary} />
    </section>
  );
}

function RaceDayImpact({ model }: { model: MeetingWeatherViewModel }) {
  return (
    <section className="eiq-weather-v1-panel">
      <header>
        <span>Race-Day Weather Context</span>
      </header>
      <dl className="eiq-weather-v1-impact-grid">
        {model.impactRows.map((row) => (
          <div key={row.label}>
            <dt>{row.label}</dt>
            <dd>{valueOrUnavailable(row.value)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function WeatherNotes({ model }: { model: MeetingWeatherViewModel }) {
  if (!model.notes.length) return null;
  return (
    <section className="eiq-weather-v1-panel eiq-weather-v1-notes">
      <header>
        <span>Meeting Weather Notes</span>
      </header>
      <ul>
        {model.notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>
    </section>
  );
}

export function MeetingWeatherWorkspace({ meeting }: MeetingWeatherWorkspaceProps) {
  const [feeds, setFeeds] = useState<WeatherTerminalFeeds | null>(null);
  const [loading, setLoading] = useState(true);
  const [sourceError, setSourceError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    loadWeatherTerminalFeeds()
      .then((nextFeeds) => {
        if (cancelled) return;
        setFeeds(nextFeeds);
        setSourceError(nextFeeds.sourceError ?? null);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        const message = error instanceof Error ? error.message : String(error);
        setSourceError(message);
        setFeeds({
          metropolitan: [],
          raceWeather: [],
          onTrack: [],
          victorianTrack: [],
          generatedAt: null,
          sourceError: message,
        });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const model = useMemo(
    () =>
      feeds
        ? buildMeetingWeatherViewModel(meeting, feeds, {
            sourceError,
          })
        : null,
    [feeds, meeting, sourceError],
  );

  if (loading || !model) {
    return (
      <section className="eiq-weather-v1">
        <div className="eiq-weather-v1-loading">
          <span>WEATHER</span>
          <strong>Loading official weather data...</strong>
        </div>
      </section>
    );
  }

  return (
    <section className="eiq-weather-v1" aria-label="Weather workspace">
      <WorkspaceHeader model={model} />
      {model.status === "unavailable" || model.status === "error" ? (
        <section className="eiq-weather-v1-unavailable">
          <strong>Official weather data is not currently available for this meeting.</strong>
        </section>
      ) : null}
      {model.status === "stale" ? (
        <section className="eiq-weather-v1-unavailable">
          <strong>Latest available weather observations are stale.</strong>
          <p>EDGEiQ displays the governed observation state and does not treat stale observations as current.</p>
        </section>
      ) : null}
      <div className="eiq-weather-v1-layout">
        <main className="eiq-weather-v1-stack">
          <WeatherSummary model={model} />
          <RaceDayImpact model={model} />
          <WeatherNotes model={model} />
        </main>
      </div>
    </section>
  );
}
