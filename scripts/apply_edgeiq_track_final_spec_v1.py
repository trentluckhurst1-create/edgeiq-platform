from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT_DIR = ROOT / "docs" / "full-product-implementation" / "checkpoints" / f"TRACK_FINAL_SPEC_V1_{STAMP}"

COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingTrackWorkspace.tsx"
MEETING_COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "trackFeed.ts"
CSS_FILE = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
TRACE_FILE = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_TRACK_TRACE_V1.md"


COMPONENT_SOURCE = r'''import { useEffect, useMemo, useState } from "react";
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
'''


SERVICE_SOURCE = r'''import type { ThreeDayMeeting, ThreeDayRace } from "./threeDayCatalog";

export type TrackWorkspaceStatus = "loading" | "empty" | "unavailable" | "error" | "current";

export type TrackValue = {
  label: string;
  value: string | null;
  tone?: "firm" | "good" | "soft" | "heavy";
};

export type TrackHistoricalComparisonRow = {
  metric: string;
  today: string | null;
  last3Meetings: string | null;
  last10Meetings: string | null;
};

export type TrackPatternRow = {
  label: string;
  runners: string | null;
  winners: string | null;
  winShare: string | null;
  winRate: string | null;
};

export type TrackTerminalFeeds = {
  officialConditions: TrackOfficialRecord[];
  mapManifest: TrackMapManifestRow[];
  trueTrackRows: TrackTrueTrackRow[];
  profileRows: TrackProfileRow[];
  profileV2Rows: TrackIntelligenceProfileRow[];
  sourceError?: string | null;
};

export type MeetingTrackViewModel = {
  workspaceId: "BETA-006";
  meetingKey: string;
  generatedAt: string | null;
  status: TrackWorkspaceStatus;
  trackName: string;
  railPosition: string | null;
  officialFields: TrackValue[];
  map: {
    asset: string | null;
    status: "available" | "missing";
    courseType: string | null;
    direction: string | null;
    distances: string | null;
    notes: string | null;
  };
  details: TrackValue[];
  patternRows: TrackPatternRow[];
  historicalRows: TrackHistoricalComparisonRow[];
  notes: string[];
};

type TrackOfficialRecord = {
  meeting_key?: string;
  meeting?: string;
  meeting_date?: string;
  source_name?: string;
  fetched_at_utc?: string;
  track_type?: string;
  official_track_rating?: string;
  penetrometer?: string | number | null;
  weather_forecast?: string;
  official_rail?: string;
  irrigation?: string | null;
  rainfall_report?: string;
  rainfall_24h_mm?: string | number | null;
  rainfall_7day_mm?: string | number | null;
  comment?: string;
  additional_information?: string;
  source_status?: string;
};

type TrackMapManifestRow = {
  track?: string;
  map_file?: string;
  course_type?: string;
  direction?: string;
  distances?: string;
  has_inner_track?: string;
  notes?: string;
};

type TrackTrueTrackRow = {
  race_date?: string;
  track?: string;
  race_no?: string;
  official_condition?: string;
  edgeiq_condition?: string;
  surface_delta?: string;
  variant_summary?: string;
  variant_band?: string;
  built_at?: string;
};

type TrackProfileRow = Record<string, string | undefined>;
type TrackIntelligenceProfileRow = Record<string, string | undefined>;

const OFFICIAL_URL = "/data/edgeiq_vic_official_track_conditions_v1.json";
const MAP_URL = "/data/edgeiq_track_map_manifest_v1.csv";
const TRUE_TRACK_URL = "/data/edgeiq_current_true_track_feed_v1.csv";
const PROFILE_URL = "/data/edgeiq_track_profile_v2.csv";
const PROFILE_V2_URL = "/data/edgeiq_track_intelligence_profile_v2.csv";

let cachedFeeds: TrackTerminalFeeds | null = null;
let pendingFeeds: Promise<TrackTerminalFeeds> | null = null;

function usable(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value).trim();
  if (!text || text === "-" || text === "—") return "";
  if (["null", "undefined", "none", "n/a", "na"].includes(text.toLowerCase())) return "";
  return text;
}

function firstText(...values: unknown[]): string {
  for (const value of values) {
    const text = usable(value);
    if (text) return text;
  }
  return "";
}

function normaliseTrack(value: unknown): string {
  return String(value ?? "")
    .toUpperCase()
    .replace(/\b(BET365|SPORTSBET|LADBROKES|TAB|THE)\b/g, " ")
    .replace(/\b(RACECOURSE|RACING|TRACK)\b/g, " ")
    .replace(/[^A-Z0-9]+/g, "");
}

function slugTrack(value: unknown): string {
  return String(value ?? "")
    .toLowerCase()
    .replace(/\b(bet365|sportsbet|ladbrokes|tab|the)\b/g, " ")
    .replace(/\b(racecourse|racing|track)\b/g, " ")
    .trim()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function raceNo(value: unknown): string {
  const match = String(value ?? "").match(/\d+/);
  return match?.[0] ?? "";
}

function csvCells(line: string): string[] {
  const cells: string[] = [];
  let value = "";
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    if (char === '"' && line[i + 1] === '"') {
      value += '"';
      i += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      cells.push(value);
      value = "";
    } else {
      value += char;
    }
  }
  cells.push(value);
  return cells;
}

function parseCsv<T extends Record<string, string | undefined>>(text: string): T[] {
  const lines = text.split(/\r?\n/).filter((line) => line.trim());
  if (!lines.length) return [];
  const headers = csvCells(lines[0]).map((header) => header.trim());
  return lines.slice(1).map((line) => {
    const cells = csvCells(line);
    const row: Record<string, string> = {};
    headers.forEach((header, index) => {
      row[header] = cells[index] ?? "";
    });
    return row as T;
  });
}

async function loadCsv<T extends Record<string, string | undefined>>(url: string): Promise<T[]> {
  const response = await fetch(`${url}?updated=${encodeURIComponent(String(Date.now()))}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`${url} failed with ${response.status}`);
  const rows = parseCsv<T>(await response.text());
  if (rows.length > 10000) {
    console.warn("EDGEiQ rejected oversized track feed", url, rows.length);
    return [];
  }
  return rows;
}

async function loadOfficialConditions(): Promise<TrackOfficialRecord[]> {
  const response = await fetch(`${OFFICIAL_URL}?updated=${encodeURIComponent(String(Date.now()))}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`${OFFICIAL_URL} failed with ${response.status}`);
  const payload = await response.json();
  const records = Array.isArray(payload?.records) ? payload.records : [];
  if (records.length > 10000) {
    console.warn("EDGEiQ rejected oversized official track conditions feed", records.length);
    return [];
  }
  return records;
}

export async function loadTrackTerminalFeeds(force = false): Promise<TrackTerminalFeeds> {
  if (!force && cachedFeeds) return cachedFeeds;
  if (pendingFeeds) return pendingFeeds;
  pendingFeeds = Promise.all([
    loadOfficialConditions(),
    loadCsv<TrackMapManifestRow>(MAP_URL),
    loadCsv<TrackTrueTrackRow>(TRUE_TRACK_URL),
    loadCsv<TrackProfileRow>(PROFILE_URL),
    loadCsv<TrackIntelligenceProfileRow>(PROFILE_V2_URL),
  ])
    .then(([officialConditions, mapManifest, trueTrackRows, profileRows, profileV2Rows]) => ({
      officialConditions,
      mapManifest,
      trueTrackRows,
      profileRows,
      profileV2Rows,
      sourceError: null,
    }))
    .then((feeds) => {
      cachedFeeds = feeds;
      return feeds;
    })
    .finally(() => {
      pendingFeeds = null;
    });
  return pendingFeeds;
}

function representativeRace(meeting: ThreeDayMeeting): ThreeDayRace | null {
  return meeting.races[0] ?? null;
}

function findOfficial(meeting: ThreeDayMeeting, feeds: TrackTerminalFeeds): TrackOfficialRecord | null {
  const track = normaliseTrack(meeting.meeting);
  return (
    feeds.officialConditions.find(
      (record) => normaliseTrack(record.meeting_key ?? record.meeting) === track && firstText(record.meeting_date) === meeting.date,
    ) ??
    feeds.officialConditions.find((record) => normaliseTrack(record.meeting_key ?? record.meeting) === track) ??
    null
  );
}

function findMap(meeting: ThreeDayMeeting, feeds: TrackTerminalFeeds): TrackMapManifestRow | null {
  const track = normaliseTrack(meeting.meeting);
  return feeds.mapManifest.find((row) => normaliseTrack(row.track) === track) ?? null;
}

function findTrueTrack(meeting: ThreeDayMeeting, race: ThreeDayRace | null, feeds: TrackTerminalFeeds): TrackTrueTrackRow | null {
  const track = normaliseTrack(meeting.meeting);
  const raceNumber = raceNo(race?.raceNumber);
  return (
    feeds.trueTrackRows.find(
      (row) => firstText(row.race_date) === meeting.date && normaliseTrack(row.track) === track && raceNo(row.race_no) === raceNumber,
    ) ??
    feeds.trueTrackRows.find((row) => normaliseTrack(row.track) === track) ??
    null
  );
}

function conditionGroup(value: unknown): string {
  const text = firstText(value).toUpperCase();
  if (text.includes("HEAVY")) return "HEAVY";
  if (text.includes("SOFT")) return "SOFT";
  if (text.includes("GOOD")) return "GOOD";
  if (text.includes("SYNTH")) return "SYNTHETIC";
  return "";
}

function distanceBucket(distance: unknown): string {
  const num = Number(String(distance ?? "").replace(/[^\d.]/g, ""));
  if (!Number.isFinite(num) || num <= 0) return "";
  const lower = Math.floor(num / 200) * 200;
  return `${lower}-${lower + 199}`;
}

function findProfile(meeting: ThreeDayMeeting, race: ThreeDayRace | null, official: TrackOfficialRecord | null, feeds: TrackTerminalFeeds): TrackProfileRow | null {
  const track = normaliseTrack(meeting.meeting);
  const bucket = distanceBucket(race?.distance);
  const condition = conditionGroup(official?.official_track_rating ?? race?.trackCondition ?? meeting.trackCondition);
  return (
    feeds.profileRows.find(
      (row) =>
        normaliseTrack(row.track_key ?? row.track) === track &&
        (!bucket || row.distance_bucket === bucket) &&
        (!condition || row.condition_group === condition),
    ) ??
    feeds.profileRows.find((row) => normaliseTrack(row.track_key ?? row.track) === track) ??
    null
  );
}

function findProfileV2(meeting: ThreeDayMeeting, race: ThreeDayRace | null, feeds: TrackTerminalFeeds): TrackIntelligenceProfileRow | null {
  const track = normaliseTrack(meeting.meeting);
  const bucket = distanceBucket(race?.distance);
  return (
    feeds.profileV2Rows.find((row) => normaliseTrack(row.track_key ?? row.track) === track && (!bucket || row.distance_bucket === bucket)) ??
    feeds.profileV2Rows.find((row) => normaliseTrack(row.track_key ?? row.track) === track) ??
    null
  );
}

function conditionTone(value: unknown): TrackValue["tone"] | undefined {
  const text = firstText(value).toUpperCase();
  if (/FIRM\s*[12]|\bFIRM\b/.test(text)) return "firm";
  if (/GOOD\s*[34]|\bGOOD\b/.test(text)) return "good";
  if (/SOFT\s*[5-7]|\bSOFT\b/.test(text)) return "soft";
  if (/HEAVY\s*(8|9|10)|\bHEAVY\b/.test(text)) return "heavy";
  return undefined;
}

function value(label: string, val: unknown, tone?: TrackValue["tone"]): TrackValue {
  return { label, value: firstText(val) || null, tone };
}

function pct(value: unknown): string | null {
  const text = firstText(value);
  if (!text) return null;
  const num = Number(text);
  if (!Number.isFinite(num)) return text;
  return `${num.toFixed(num % 1 === 0 ? 0 : 1)}%`;
}

function patternRows(profile: TrackProfileRow | null, profileV2: TrackIntelligenceProfileRow | null): TrackPatternRow[] {
  const row = profile ?? profileV2;
  if (!row) return [];
  return [
    ["Inside", row.inside_runners ?? row.inside_runs, row.inside_winners, row.inside_winner_share, row.inside_win_rate],
    ["Middle", row.middle_runners ?? row.middle_runs, row.middle_winners, row.middle_winner_share, row.middle_win_rate],
    ["Wide", row.outside_runners ?? row.outside_runs, row.outside_winners, row.outside_winner_share, row.outside_win_rate],
    ["Leaders", row.leader_runners ?? row.leader_runs, row.leader_winners, row.leader_winner_share, row.leader_win_rate],
    ["On Pace", row.onpace_runners ?? row.on_pace_runs, row.onpace_winners ?? row.on_pace_winners, row.onpace_winner_share ?? row.on_pace_winner_share, row.onpace_win_rate ?? row.on_pace_win_rate],
    ["Midfield", row.midfield_runners ?? row.midfield_runs, row.midfield_winners, row.midfield_winner_share, row.midfield_win_rate],
    ["Backmarkers", row.backmarker_runners ?? row.backmarker_runs, row.backmarker_winners, row.backmarker_winner_share, row.backmarker_win_rate],
  ].map(([label, runners, winners, share, rate]) => ({
    label: String(label),
    runners: firstText(runners) || null,
    winners: firstText(winners) || null,
    winShare: pct(share),
    winRate: pct(rate),
  }));
}

function historicalRows(pattern: TrackPatternRow[]): TrackHistoricalComparisonRow[] {
  const byLabel = new Map(pattern.map((row) => [row.label, row]));
  const metricPairs: Array<[string, string]> = [
    ["Inner Barrier Win %", "Inside"],
    ["Middle Barrier Win %", "Middle"],
    ["Outside Barrier Win %", "Wide"],
    ["Leaders Win %", "Leaders"],
    ["On-Pace Win %", "On Pace"],
    ["Midfield Win %", "Midfield"],
    ["Backmarker Win %", "Backmarkers"],
  ];
  return metricPairs
    .map(([metric, key]) => {
      const item = byLabel.get(key);
      return {
        metric,
        today: item?.winRate ?? null,
        last3Meetings: null,
        last10Meetings: null,
      };
    })
    .filter((row) => row.today || row.last3Meetings || row.last10Meetings);
}

export function buildMeetingTrackViewModel(
  meeting: ThreeDayMeeting,
  feeds: TrackTerminalFeeds,
  options: { sourceError?: string | null } = {},
): MeetingTrackViewModel {
  const race = representativeRace(meeting);
  const official = findOfficial(meeting, feeds);
  const map = findMap(meeting, feeds);
  const trueTrack = findTrueTrack(meeting, race, feeds);
  const profile = findProfile(meeting, race, official, feeds);
  const profileV2 = findProfileV2(meeting, race, feeds);
  const raceSource = race?.source;
  const officialRating = official?.official_track_rating ?? race?.trackCondition ?? raceSource?.track_condition;
  const slugAsset = `/assets/tracks/${slugTrack(meeting.meeting)}.png`;
  const asset = firstText(map?.map_file, slugAsset) || null;
  const pattern = patternRows(profile, profileV2);
  const status: TrackWorkspaceStatus = options.sourceError
    ? "error"
    : official || pattern.length || map
      ? "current"
      : "unavailable";

  const officialFields = [
    value("OFFICIAL RATING", officialRating, conditionTone(officialRating)),
    value("RAIL", official?.official_rail ?? raceSource?.rail_position),
    value("TRACK TYPE", official?.track_type),
    value("PENETROMETER AVERAGE", official?.penetrometer ?? official?.additional_information?.match(/PENETRATION\s+([\d.]+)/i)?.[1]),
    value("GOING STICK", official?.additional_information?.match(/STICK\s+([\d.]+)/i)?.[1]),
    value("RAIN 24H", official?.rainfall_24h_mm ?? raceSource?.rainfall),
    value("RAIN 7D", official?.rainfall_7day_mm),
    value("IRRIGATION 24H", official?.irrigation),
    value("IRRIGATION 7D", null),
  ];

  const details = [
    value("SURFACE", official?.track_type),
    value("COURSE TYPE", map?.course_type),
    value("DIRECTION", map?.direction),
    value("DISTANCES", firstText(map?.distances)?.replace(/"+$/g, "")),
    value("EDGEIQ TRUE TRACK", trueTrack?.edgeiq_condition, conditionTone(trueTrack?.edgeiq_condition)),
    value("SURFACE DELTA", trueTrack?.surface_delta),
  ];

  return {
    workspaceId: "BETA-006",
    meetingKey: meeting.meetingKey,
    generatedAt: trueTrack?.built_at ?? official?.fetched_at_utc ?? null,
    status,
    trackName: meeting.meeting,
    railPosition: firstText(official?.official_rail, raceSource?.rail_position) || null,
    officialFields,
    map: {
      asset,
      status: asset ? "available" : "missing",
      courseType: firstText(map?.course_type) || null,
      direction: firstText(map?.direction) || null,
      distances: firstText(map?.distances)?.replace(/"+$/g, "") || null,
      notes: firstText(map?.notes)?.replace(/"+$/g, "") || null,
    },
    details,
    patternRows: pattern,
    historicalRows: historicalRows(pattern),
    notes: [
      firstText(trueTrack?.variant_summary),
      firstText(official?.additional_information),
      firstText(official?.comment),
      firstText(map?.notes)?.replace(/"+$/g, ""),
    ].filter(Boolean),
  };
}
'''


CSS_BLOCK = r'''.eiq-track-v1 {
  display: grid;
  gap: 14px;
  color: #172033;
}

.eiq-track-v1-header,
.eiq-track-v1-panel,
.eiq-track-v1-loading {
  border: 1px solid #e5e8ee;
  border-radius: 14px;
  background: #ffffff;
}

.eiq-track-v1-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  padding: 16px;
}

.eiq-track-v1-header span,
.eiq-track-v1-panel > header span,
.eiq-track-v1-loading span {
  display: block;
  color: #1f5fd6;
  font-size: 11px;
  font-weight: 850;
  letter-spacing: .12em;
  text-transform: uppercase;
}

.eiq-track-v1-header h2 {
  margin: 4px 0 0;
  color: #172033;
  font-size: 22px;
  font-weight: 780;
}

.eiq-track-v1-header p {
  margin: 5px 0 0;
  color: #5c6675;
  font-size: 13px;
}

.eiq-track-v1-layout,
.eiq-track-v1-stack {
  display: grid;
  gap: 14px;
}

.eiq-track-v1-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(260px, .75fr);
  gap: 14px;
}

.eiq-track-v1-panel > header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: baseline;
  padding: 12px 14px;
  border-bottom: 1px solid #e5e8ee;
  background: #fafbfc;
  border-radius: 14px 14px 0 0;
}

.eiq-track-v1-panel > header strong {
  color: #172033;
  font-size: 13px;
  font-weight: 760;
  text-align: right;
}

.eiq-track-v1-field-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0;
  margin: 0;
}

.eiq-track-v1-field-grid div {
  min-height: 74px;
  padding: 12px;
  border-right: 1px solid #e5e8ee;
  border-bottom: 1px solid #e5e8ee;
}

.eiq-track-v1-field-grid div:nth-child(5n) {
  border-right: 0;
}

.eiq-track-v1-field-grid dt {
  color: #7c8798;
  font-size: 10px;
  font-weight: 850;
  letter-spacing: .08em;
  text-transform: uppercase;
}

.eiq-track-v1-field-grid dd {
  margin: 5px 0 0;
  color: #172033;
  font-size: 15px;
  font-weight: 760;
}

.eiq-track-v1-field-grid div.is-firm dd {
  color: #b91c1c;
}

.eiq-track-v1-field-grid div.is-good dd {
  color: #15803d;
}

.eiq-track-v1-field-grid div.is-soft dd {
  color: #1f5fd6;
}

.eiq-track-v1-field-grid div.is-heavy {
  background: #172033;
}

.eiq-track-v1-field-grid div.is-heavy dt,
.eiq-track-v1-field-grid div.is-heavy dd {
  color: #ffffff;
}

.eiq-track-v1-map {
  margin: 0;
  padding: 14px;
}

.eiq-track-v1-map img {
  display: block;
  width: 100%;
  max-height: 300px;
  object-fit: contain;
  border: 1px solid #e5e8ee;
  border-radius: 12px;
  background: #fafbfc;
}

.eiq-track-v1-table-scroll {
  width: 100%;
  overflow-x: auto;
}

.eiq-track-v1-table {
  width: 100%;
  min-width: 720px;
  border-collapse: collapse;
}

.eiq-track-v1-table th {
  height: 36px;
  padding: 0 10px;
  border-bottom: 1px solid #d7dce5;
  color: #5c6675;
  font-size: 11px;
  font-weight: 850;
  letter-spacing: .08em;
  text-align: center;
  text-transform: uppercase;
  white-space: nowrap;
}

.eiq-track-v1-table td {
  height: 40px;
  padding: 0 10px;
  border-bottom: 1px solid #e5e8ee;
  color: #172033;
  font-size: 13px;
  text-align: center;
  white-space: nowrap;
}

.eiq-track-v1-table th.is-left,
.eiq-track-v1-table td.is-left {
  text-align: left;
}

.eiq-track-v1-table td strong {
  color: #172033;
  font-weight: 760;
}

.eiq-track-v1-unavailable,
.eiq-track-v1-loading {
  padding: 16px;
}

.eiq-track-v1-unavailable strong,
.eiq-track-v1-loading strong {
  display: block;
  color: #172033;
  font-size: 16px;
  font-weight: 780;
}

.eiq-track-v1-unavailable p {
  margin: 6px 0 0;
  color: #5c6675;
  font-size: 13px;
  line-height: 1.45;
}

.eiq-track-v1-notes {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 14px 18px 14px 32px;
  color: #172033;
  font-size: 13px;
  line-height: 1.45;
}

@media (max-width: 1200px) {
  .eiq-track-v1-grid {
    grid-template-columns: 1fr;
  }

  .eiq-track-v1-field-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .eiq-track-v1-field-grid div:nth-child(5n) {
    border-right: 1px solid #e5e8ee;
  }

  .eiq-track-v1-field-grid div:nth-child(2n) {
    border-right: 0;
  }
}
'''


TRACE = r'''# EDGEiQ Track Trace V1

Status: implemented as the TRACK final-spec tranche.

## Canonical Inputs

- Current meeting and race context: `src/edgeiq-os/race/services/threeDayCatalog.ts`.
- Official track condition records: `public/data/edgeiq_vic_official_track_conditions_v1.json`.
- Curated track map manifest: `public/data/edgeiq_track_map_manifest_v1.csv`.
- Current true-track feed: `public/data/edgeiq_current_true_track_feed_v1.csv`.
- Historical track profile feeds: `public/data/edgeiq_track_profile_v2.csv` and `public/data/edgeiq_track_intelligence_profile_v2.csv`.
- Installed track maps are resolved by `src/edgeiq-os/race/services/trackMapAssets.ts`.

## Display Contract

- TRACK displays current track information, rail, condition, curated map, current operational profile, lane/settling-position evidence, historical profile and official/governed track notes.
- TRACK does not display source station IDs, internal registry labels, confidence, builder timestamps, source-state panels, track records, class records, official time records, margin records or venue-tourism copy.
- TRACK uses approved condition colours only for track condition values.

## Removed Development/Product Leakage

- Removed the TRACK fixture query path and missing-map/missing-history query paths from the meeting workspace.
- Removed the service fixture data builder.
- Removed the visible refresh-feed button, source-state rail and source labels from the component.

## Legitimate Gaps

- Separate Sandown Hillside and Sandown Lakeside image files are not present in `public/track-maps`; the existing curated registry contains `Sandown.png` only. EDGEiQ does not invent a replacement layout.
- Circumference/straight values are displayed only if supplied by governed sources.
'''


def checkpoint(path: Path) -> None:
  if path.exists():
    target = CHECKPOINT_DIR / path.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)


def replace_between(text: str, start: str, end: str, replacement: str) -> str:
  start_index = text.find(start)
  if start_index == -1:
    raise RuntimeError(f"Start marker not found: {start}")
  end_index = text.find(end, start_index)
  if end_index == -1:
    raise RuntimeError(f"End marker not found: {end}")
  return text[:start_index] + replacement.rstrip() + "\n\n" + text[end_index:]


def main() -> int:
  for path in [COMPONENT, MEETING_COMPONENT, SERVICE, CSS_FILE]:
    checkpoint(path)

  COMPONENT.write_text(COMPONENT_SOURCE, encoding="utf-8")
  SERVICE.write_text(SERVICE_SOURCE, encoding="utf-8")

  meeting = MEETING_COMPONENT.read_text(encoding="utf-8")
  meeting = meeting.replace(
    '''  const trackFixtureMode =
    typeof window !== "undefined" && new URLSearchParams(window.location.search).get("edgeiqTrackFixture") === "1";
  const trackMissingMapMode =
    typeof window !== "undefined" && new URLSearchParams(window.location.search).get("edgeiqTrackMissingMap") === "1";
  const trackMissingHistoricalMode =
    typeof window !== "undefined" && new URLSearchParams(window.location.search).get("edgeiqTrackMissingHistorical") === "1";
''',
    "",
  )
  meeting = meeting.replace(
    '''            <MeetingTrackWorkspace
              meeting={meeting}
              fixtureMode={trackFixtureMode}
              missingMapMode={trackMissingMapMode}
              missingHistoricalMode={trackMissingHistoricalMode}
            />''',
    '''            <MeetingTrackWorkspace meeting={meeting} />''',
  )
  MEETING_COMPONENT.write_text(meeting, encoding="utf-8")

  css = CSS_FILE.read_text(encoding="utf-8")
  css = replace_between(css, ".eiq-track-v1 {", ".eiq-weather-v1 {", CSS_BLOCK)
  CSS_FILE.write_text(css, encoding="utf-8")

  TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
  TRACE_FILE.write_text(TRACE, encoding="utf-8")

  print("EDGEIQ_TRACK_FINAL_SPEC_PATCH_APPLIED")
  print(f"Checkpoint: {CHECKPOINT_DIR}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
