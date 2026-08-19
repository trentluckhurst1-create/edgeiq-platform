import type { ThreeDayMeeting, ThreeDayRace } from "./threeDayCatalog";

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
