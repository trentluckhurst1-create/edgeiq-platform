import { useEffect, useMemo, useState } from "react";
import type { ThreeDayMeeting } from "../services/threeDayCatalog";
import { resolveTrackMapPath } from "../services/trackMapAssets";
import {
  buildMeetingTrackViewModel,
  loadTrackTerminalFeeds,
  type MeetingTrackViewModel,
  type TrackTerminalFeeds,
  type TrackValue,
} from "../services/trackFeed";

type MeetingTrackWorkspaceProps = {
  meeting: ThreeDayMeeting;
};

function valueOrUnavailable(value: string | null | undefined): string {
  return value && value.trim() ? value : "Unavailable";
}

function FieldGrid({ items }: { items: TrackValue[] }) {
  return (
    <dl className="eiq-track-v1-field-grid">
      {items.map((item) => (
        <div key={item.label} className={item.tone ? `is-${item.tone}` : ""}>
          <dt>{item.label}</dt>
          <dd>{valueOrUnavailable(item.value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function WorkspaceHeader({ model }: { model: MeetingTrackViewModel }) {
  return (
    <header className="eiq-track-v1-header">
      <div>
        <span>TRACK</span>
        <h2>Current track, rail and profile context</h2>
        <p>{model.trackName}</p>
      </div>
    </header>
  );
}

const SPECIAL_INSTRUMENT_TRACKS = new Set([
  "FLEMINGTON",
  "CAULFIELD",
  "CAULFIELD HEATH",
  "MOONEE VALLEY",
  "SANDOWN HILLSIDE",
  "SANDOWN LAKESIDE",
  "MORNINGTON",
]);

function normaliseTrackDisplayName(value: string): string {
  return value
    .trim()
    .toUpperCase()
    .replace(/[-_/]+/g, " ")
    .replace(/\s+/g, " ");
}

function normaliseConditionLabel(value: string): string {
  return value
    .trim()
    .toUpperCase()
    .replace(/[-_/]+/g, " ")
    .replace(/\s+/g, " ");
}

function formatMillimetres(value: string | null | undefined): string | null | undefined {
  if (!value) return value;
  const trimmed = value.trim();
  if (!trimmed) return value;
  const upper = trimmed.toUpperCase();
  if (upper === "UNAVAILABLE" || upper === "NOT SUPPLIED" || upper === "N/A" || upper === "NA") return value;
  if (/\bMM\b/i.test(trimmed)) return trimmed;
  if (/^-?\d+(?:\.\d+)?$/.test(trimmed)) return `${trimmed} mm`;
  return trimmed;
}

function buildTrackConditionFields(model: MeetingTrackViewModel): TrackValue[] {
  const trackName = normaliseTrackDisplayName(model.trackName);
  const showInstrumentFields = SPECIAL_INSTRUMENT_TRACKS.has(trackName);

  return model.officialFields
    .filter((item) => {
      const label = normaliseConditionLabel(item.label);
      if (["INSPECTION TIME", "TRACK MANAGER"].includes(label)) return false;
      if (!showInstrumentFields && ["GOING STICK", "MOISTURE"].includes(label)) return false;
      return true;
    })
    .map((item) => {
      const label = normaliseConditionLabel(item.label);
      let displayLabel = item.label;
      let displayValue = item.value;

      if (label === "PENETROMETER AVERAGE") displayLabel = "PENETROMETER";
      if (label === "RAIN 7D" || label === "RAIN 7 D") displayLabel = "RAIN 7 DAYS";
      if (label === "IRRIGATION 7D" || label === "IRRIGATION 7 D") displayLabel = "IRRIGATION 7 DAYS";
      if (
        label === "RAIN 24H" ||
        label === "RAIN 24 H" ||
        label === "RAIN 7D" ||
        label === "RAIN 7 D" ||
        label === "RAIN 7 DAYS" ||
        label === "IRRIGATION 24H" ||
        label === "IRRIGATION 24 H" ||
        label === "IRRIGATION 7D" ||
        label === "IRRIGATION 7 D" ||
        label === "IRRIGATION 7 DAYS"
      ) {
        displayValue = formatMillimetres(item.value);
      }

      return { ...item, label: displayLabel, value: displayValue };
    });
}

function TrackCondition({ model }: { model: MeetingTrackViewModel }) {
  const conditionFields = buildTrackConditionFields(model);

  return (
    <section className="eiq-track-v1-panel">
      <header>
        <span>Track Condition</span>
        <strong>Current official context</strong>
      </header>
      <FieldGrid items={conditionFields} />
    </section>
  );
}

function TrackMapPanel({ model }: { model: MeetingTrackViewModel }) {
  const installedMap = resolveTrackMapPath(model.trackName, model.map.courseType);

  return (
    <section className="eiq-track-v1-panel eiq-track-v1-map-panel">
      <header>
        <span>Rail Position and Track Map</span>
        <strong>{valueOrUnavailable(model.railPosition)}</strong>
      </header>
      {installedMap ? (
        <figure className="eiq-track-v1-map">
          <img src={installedMap} alt={`${model.trackName} track map`} />
        </figure>
      ) : (
        <div className="eiq-track-v1-unavailable">
          <strong>Track map unavailable.</strong>
          <p>No installed curated track map matches this meeting.</p>
        </div>
      )}
    </section>
  );
}

function TrackDetails({ model }: { model: MeetingTrackViewModel }) {
  return (
    <section className="eiq-track-v1-panel">
      <header>
        <span>Track Details</span>
        <strong>Current operational profile</strong>
      </header>
      <FieldGrid items={model.details} />
    </section>
  );
}

function PatternAnalysis({ model }: { model: MeetingTrackViewModel }) {
  return (
    <section className="eiq-track-v1-panel">
      <header>
        <span>Track Pattern Analysis</span>
        <strong>Lane and settling-position evidence</strong>
      </header>
      {model.patternRows.length ? (
        <div className="eiq-track-v1-table-scroll">
          <table className="eiq-track-v1-table">
            <thead>
              <tr>
                <th className="is-left">PROFILE</th>
                <th>RUNNERS</th>
                <th>WINNERS</th>
                <th>WIN SHARE</th>
                <th>WIN RATE</th>
              </tr>
            </thead>
            <tbody>
              {model.patternRows.map((row) => (
                <tr key={row.label}>
                  <td className="is-left"><strong>{row.label}</strong></td>
                  <td>{valueOrUnavailable(row.runners)}</td>
                  <td>{valueOrUnavailable(row.winners)}</td>
                  <td>{valueOrUnavailable(row.winShare)}</td>
                  <td>{valueOrUnavailable(row.winRate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="eiq-track-v1-unavailable">
          <strong>Track pattern evidence unavailable.</strong>
          <p>Lane and settling-position evidence has not been supplied for this meeting context.</p>
        </div>
      )}
    </section>
  );
}

function HistoricalComparison({ model }: { model: MeetingTrackViewModel }) {
  return (
    <section className="eiq-track-v1-panel">
      <header>
        <span>Historical Profile</span>
        <strong>Recent comparable track evidence</strong>
      </header>
      {model.historicalRows.length ? (
        <div className="eiq-track-v1-table-scroll">
          <table className="eiq-track-v1-table">
            <thead>
              <tr>
                <th className="is-left">METRIC</th>
                <th>TODAY</th>
                <th>LAST 3 MEETINGS</th>
                <th>LAST 10 MEETINGS</th>
              </tr>
            </thead>
            <tbody>
              {model.historicalRows.map((row) => (
                <tr key={row.metric}>
                  <td className="is-left"><strong>{row.metric}</strong></td>
                  <td>{valueOrUnavailable(row.today)}</td>
                  <td>{valueOrUnavailable(row.last3Meetings)}</td>
                  <td>{valueOrUnavailable(row.last10Meetings)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="eiq-track-v1-unavailable">
          <strong>Historical track profile unavailable.</strong>
          <p>No comparable historical track profile has been supplied for this meeting context.</p>
        </div>
      )}
    </section>
  );
}

function TrackNotes({ model }: { model: MeetingTrackViewModel }) {
  return (
    <section className="eiq-track-v1-panel">
      <header>
        <span>Track Notes</span>
        <strong>Official and governed context</strong>
      </header>
      {model.notes.length ? (
        <ul className="eiq-track-v1-notes">
          {model.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      ) : (
        <div className="eiq-track-v1-unavailable">
          <strong>Track notes unavailable.</strong>
          <p>No official or governed note has been supplied for this meeting.</p>
        </div>
      )}
    </section>
  );
}

export function MeetingTrackWorkspace({ meeting }: MeetingTrackWorkspaceProps) {
  const [feeds, setFeeds] = useState<TrackTerminalFeeds | null>(null);
  const [loading, setLoading] = useState(true);
  const [sourceError, setSourceError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    loadTrackTerminalFeeds()
      .then((nextFeeds) => {
        if (cancelled) return;
        setFeeds(nextFeeds);
        setSourceError(nextFeeds.sourceError ?? null);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setSourceError(error instanceof Error ? error.message : String(error));
        setFeeds({
          officialConditions: [],
          mapManifest: [],
          trueTrackRows: [],
          profileRows: [],
          profileV2Rows: [],
          sourceError: error instanceof Error ? error.message : String(error),
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
    () => (feeds ? buildMeetingTrackViewModel(meeting, feeds, { sourceError }) : null),
    [feeds, meeting, sourceError],
  );

  if (loading || !model) {
    return (
      <section className="eiq-track-v1">
        <div className="eiq-track-v1-loading">
          <span>TRACK</span>
          <strong>Loading official track profile...</strong>
        </div>
      </section>
    );
  }

  return (
    <section className="eiq-track-v1" aria-label="Track workspace">
      <WorkspaceHeader model={model} />
      <div className="eiq-track-v1-layout">
        <main className="eiq-track-v1-stack">
          <TrackCondition model={model} />
          <div className="eiq-track-v1-grid">
            <TrackMapPanel model={model} />
            <TrackDetails model={model} />
          </div>
          <PatternAnalysis model={model} />
          <HistoricalComparison model={model} />
          <TrackNotes model={model} />
        </main>
      </div>
    </section>
  );
}
