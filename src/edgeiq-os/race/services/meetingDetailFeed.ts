import type { ThreeDayMeeting, ThreeDayRace } from "./threeDayCatalog";

export type MeetingDetailTab =
  | "RACES"
  | "SCRATCHINGS"
  | "GEAR_CHANGES"
  | "TRACK"
  | "WEATHER"
  | "RESULTS";

export const MEETING_DETAIL_TAB_ORDER: Array<{
  key: MeetingDetailTab;
  label: string;
  pendingMessage?: string;
}> = [
  { key: "RACES", label: "RACES" },
  {
    key: "SCRATCHINGS",
    label: "SCRATCHINGS",
    pendingMessage: "Official scratchings for this meeting will appear here.",
  },
  {
    key: "GEAR_CHANGES",
    label: "GEAR CHANGES",
    pendingMessage: "Official gear changes for this meeting will appear here.",
  },
  {
    key: "TRACK",
    label: "TRACK",
    pendingMessage: "Detailed track intelligence will appear here.",
  },
  {
    key: "WEATHER",
    label: "WEATHER",
    pendingMessage: "Detailed weather intelligence will appear here.",
  },
  {
    key: "RESULTS",
    label: "RESULTS",
    pendingMessage: "Official meeting results will appear here as races are completed.",
  },
];

export type MeetingDetailTone = "positive" | "negative" | "caution" | "muted";

export type MeetingConditionStripItem = {
  label:
    | "TRACK"
    | "RAIL"
    | "WEATHER"
    | "WIND"
    | "TEMPERATURE"
    | "RAIN 24H"
    | "IRRIGATION 24H"
    | "OFFICIAL UPDATE";
  value: string;
  tone?: MeetingDetailTone;
};

export type MeetingDetailValue = {
  label: string;
  value: string;
  tone?: MeetingDetailTone;
};

export type MeetingDetailRaceRow = {
  raceKey: string;
  raceIndex: number;
  race: ThreeDayRace;
  raceLabel: string;
  time: string;
  raceName: string;
  secondary: string;
  distance: string;
  raceClass: string;
  fieldSize: string;
  scratchings: string;
  track: string;
  status: string;
  statusTone: MeetingDetailTone;
};

export type RaceOperationalIntelligence = {
  title: string;
  body: string;
  evidence: MeetingDetailValue[];
} | null;

export type MeetingDetailSelectedRace = {
  row: MeetingDetailRaceRow;
  details: MeetingDetailValue[];
  intelligence: RaceOperationalIntelligence;
};

export type MeetingDataStatus = {
  label: string;
  value: string;
  tone?: MeetingDetailTone;
};

export type MeetingDetailViewModel = {
  meetingKey: string;
  meetingName: string;
  displayDate: string;
  venueLine: string;
  summary: MeetingDetailValue[];
  conditionStrip: MeetingConditionStripItem[];
  races: MeetingDetailRaceRow[];
  highlights: string[];
  notes: string[];
  trackMapAsset: string | null;
  trackMapMessage: string;
  dataStatus: MeetingDataStatus[];
  pendingTabs: Record<Exclude<MeetingDetailTab, "RACES">, string>;
};

function usable(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value).trim();
  if (!text || text === "-" || text === "\u2014") return "";
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

function sourceValue(source: Record<string, unknown> | undefined, keys: string[]): string {
  for (const key of keys) {
    const direct = firstText(source?.[key]);
    if (direct) return direct;
  }
  return "";
}

function formatDateLong(value: unknown): string {
  const text = usable(value);
  if (!text) return "Unavailable";
  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) return text;
  return new Intl.DateTimeFormat("en-AU", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(parsed);
}

function formatLocalTime(value: unknown): string {
  const text = usable(value);
  if (!text) return "";
  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) return text;
  return new Intl.DateTimeFormat("en-AU", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZone: "Australia/Sydney",
  })
    .format(parsed)
    .replace(/\s/g, "")
    .toLowerCase();
}

function money(value: unknown): string {
  const text = firstText(value);
  if (!text) return "";
  const number = Number(text.replace(/[$,]/g, ""));
  if (!Number.isFinite(number)) return text;
  return new Intl.NumberFormat("en-AU", {
    style: "currency",
    currency: "AUD",
    maximumFractionDigits: 0,
  }).format(number);
}

function raceTime(race: ThreeDayRace): string {
  return firstText(race.raceTime, formatLocalTime(race.source?.race_time_utc));
}

function trackRating(race?: ThreeDayRace | null, meeting?: ThreeDayMeeting): string {
  const condition = firstText(
    race?.trackCondition,
    sourceValue(race?.source, ["track_condition", "TrackCondition", "going"]),
    meeting?.trackCondition,
  );
  const rating = sourceValue(race?.source, ["track_rating", "true_track_rating", "edgeiq_track_rating"]);
  if (condition && rating && !condition.toLowerCase().includes(rating.toLowerCase())) {
    return `${condition} ${rating}`;
  }
  return condition;
}

function railPosition(race?: ThreeDayRace | null, meeting?: ThreeDayMeeting): string {
  return firstText(
    race?.rail,
    sourceValue(race?.source, ["rail_position", "rail", "RailPosition"]),
    meeting?.rail,
  );
}

function statusFromRace(race: ThreeDayRace): string {
  const raw = firstText(
    sourceValue(race.source, ["result_status", "race_status", "full_status", "meet_status", "status"]),
  ).toUpperCase();
  if (raw.includes("OFFICIAL")) return "OFFICIAL";
  if (raw.includes("UNOFFICIAL")) return "UNOFFICIAL";
  if (raw.includes("ABANDON")) return "ABANDONED";
  if (raw.includes("DELAY")) return "DELAYED";
  if (raw.includes("LIVE") || raw.includes("RUNNING")) return "LIVE";
  if (raw.includes("FINAL") || raw.includes("ACCEPT")) return "READY";
  if (raw.includes("RESULT")) return "RESULTS";
  return race.runners.length ? "READY" : "UNAVAILABLE";
}

function statusTone(status: string): MeetingDetailTone {
  if (["OFFICIAL", "READY", "LIVE", "RESULTS"].includes(status)) return "positive";
  if (["UNOFFICIAL", "DELAYED"].includes(status)) return "caution";
  if (status === "ABANDONED") return "negative";
  return "muted";
}

function scratchedCount(race: ThreeDayRace): number {
  return race.runners.filter((runner) => {
    const official = runner.official as Record<string, unknown>;
    const source = runner.source ?? {};
    const flag = firstText(
      official.scratched,
      source.scratched,
      source.is_scratched,
      source.runner_status,
      source.status,
    ).toLowerCase();
    return flag === "true" || flag === "scratched" || flag.includes("scratched");
  }).length;
}

function marketStatus(race: ThreeDayRace): string {
  const hasMarket = race.runners.some((runner) => firstText(runner.official.market, runner.source?.market));
  return hasMarket ? "Market loaded" : "Pending Market";
}

function raceSecondaryLine(race: ThreeDayRace): string {
  return [race.distance, race.raceClass].filter(Boolean).join(" | ");
}

function buildRaceRows(meeting: ThreeDayMeeting): MeetingDetailRaceRow[] {
  return meeting.races.map((race, index) => {
    const status = statusFromRace(race);
    return {
      raceKey: race.raceKey,
      raceIndex: index,
      race,
      raceLabel: `R${race.raceNumber}`,
      time: raceTime(race) || "Unavailable",
      raceName: race.raceName || `Race ${race.raceNumber}`,
      secondary: raceSecondaryLine(race),
      distance: firstText(race.distance, "Not supplied"),
      raceClass: firstText(race.raceClass, "Not supplied"),
      fieldSize: race.runners.length ? String(race.runners.length) : "Not supplied",
      scratchings: String(scratchedCount(race)),
      track: trackRating(race, meeting) || "Track rating unavailable",
      status,
      statusTone: statusTone(status),
    };
  });
}

function buildConditionStrip(meeting: ThreeDayMeeting, race: ThreeDayRace | null): MeetingConditionStripItem[] {
  const source = race?.source ?? meeting.source ?? {};
  const windSpeed = sourceValue(source, ["weather_wind_speed", "wind_speed", "windSpeed"]);
  const windDirection = sourceValue(source, ["weather_wind_direction", "wind_direction", "windDirection"]);
  const temperature = sourceValue(source, ["weather_temperature", "temperature", "temp"]);
  const rain = sourceValue(source, ["weather_rain", "rainfall_24h", "rain_24h", "rainfall"]);
  const irrigation = sourceValue(source, ["irrigation_24h", "irrigation"]);
  const officialUpdate = firstText(
    sourceValue(source, ["official_update", "inspection_time", "built_at", "updated_at"]),
    meeting.source?.built_at,
  );

  return [
    { label: "TRACK", value: trackRating(race, meeting) || "Track rating unavailable" },
    { label: "RAIL", value: railPosition(race, meeting) || "Not supplied" },
    { label: "WEATHER", value: sourceValue(source, ["weather", "weather_summary"]) || "Weather unavailable" },
    {
      label: "WIND",
      value: windSpeed || windDirection ? [windDirection, windSpeed].filter(Boolean).join(" ") : "Weather unavailable",
    },
    { label: "TEMPERATURE", value: temperature || "Weather unavailable" },
    { label: "RAIN 24H", value: rain || "Not supplied" },
    { label: "IRRIGATION 24H", value: irrigation || "Not supplied" },
    { label: "OFFICIAL UPDATE", value: officialUpdate || "Unavailable" },
  ];
}

function buildMeetingSummary(meeting: ThreeDayMeeting, races: MeetingDetailRaceRow[]): MeetingDetailValue[] {
  const first = races[0]?.time || "Unavailable";
  const last = races[races.length - 1]?.time || "Unavailable";
  const completed = races.filter((race) => ["OFFICIAL", "UNOFFICIAL", "RESULTS"].includes(race.status)).length;
  const totalRunners = meeting.races.reduce((sum, race) => sum + race.runners.length, 0);
  const totalScratchings = meeting.races.reduce((sum, race) => sum + scratchedCount(race), 0);
  const status = races.length && completed === races.length ? "COMPLETED" : races.length ? "READY" : "FIELDS PENDING";
  const condition = buildConditionStrip(meeting, meeting.races[0] ?? null);
  const officialUpdate = condition.find((item) => item.label === "OFFICIAL UPDATE")?.value ?? "Unavailable";

  return [
    { label: "STATE", value: firstText(meeting.source?.State, "Not supplied") },
    { label: "RACES", value: String(meeting.raceCount || races.length) },
    { label: "RUNNERS", value: totalRunners ? String(totalRunners) : "Not supplied" },
    { label: "SCRATCHINGS", value: String(totalScratchings) },
    { label: "FIRST", value: first },
    { label: "LAST", value: last },
    { label: "STATUS", value: status, tone: statusTone(status) },
    { label: "OFFICIAL UPDATE", value: officialUpdate },
  ];
}

function buildSelectedDetails(row: MeetingDetailRaceRow, meeting: ThreeDayMeeting): MeetingDetailValue[] {
  const race = row.race;
  const source = race.source ?? {};
  return [
    { label: "Prize Money", value: money(sourceValue(source, ["prize_money", "prizemoney"])) || "Not supplied" },
    { label: "Race Class", value: row.raceClass },
    { label: "Age / Sex", value: sourceValue(source, ["age_sex", "age_restriction", "age", "sex_restriction"]) || "Not supplied" },
    { label: "Weight Conditions", value: sourceValue(source, ["weight_conditions", "weight_range"]) || "Not supplied" },
    { label: "Acceptances", value: row.fieldSize },
    { label: "Scratchings", value: row.scratchings },
    { label: "Track", value: row.track },
    { label: "Rail", value: railPosition(race, meeting) || "Not supplied" },
    { label: "Market Status", value: marketStatus(race) },
    { label: "Data Coverage", value: race.runners.length ? "Field loaded" : "Not supplied" },
  ];
}

function buildRaceIntelligence(row: MeetingDetailRaceRow): RaceOperationalIntelligence {
  const source = row.race.source ?? {};
  const pressure = sourceValue(source, ["tempo_pressure", "pressure", "race_pressure"]);
  const shape = sourceValue(source, ["race_shape", "race_shape_story"]);
  const trackRead = sourceValue(source, ["track_playing", "true_track_read"]);
  const evidence = [
    pressure ? { label: "Pressure", value: pressure } : null,
    shape ? { label: "Race Shape", value: shape } : null,
    trackRead ? { label: "Track Read", value: trackRead } : null,
  ].filter(Boolean) as MeetingDetailValue[];

  if (!evidence.length) return null;
  return {
    title: "Race Intelligence",
    body: "Selected race detail is supplied for this meeting.",
    evidence,
  };
}

export function buildMeetingDetailViewModel(meeting: ThreeDayMeeting): MeetingDetailViewModel {
  const races = buildRaceRows(meeting);
  const firstRace = meeting.races[0] ?? null;

  return {
    meetingKey: meeting.meetingKey,
    meetingName: meeting.meeting,
    displayDate: formatDateLong(meeting.date),
    venueLine: `${meeting.meeting} | ${formatDateLong(meeting.date)}`,
    summary: buildMeetingSummary(meeting, races),
    conditionStrip: buildConditionStrip(meeting, firstRace),
    races,
    highlights: [],
    notes: [],
    trackMapAsset: null,
    trackMapMessage: "Curated EDGEiQ track map is not supplied for this meeting.",
    dataStatus: [
      { label: "Meeting", value: meeting.races.length ? "Loaded" : "Unavailable", tone: meeting.races.length ? "positive" : "muted" },
      { label: "Race rows", value: races.length ? String(races.length) : "Unavailable", tone: races.length ? "positive" : "muted" },
      { label: "Runner rows", value: String(meeting.races.reduce((sum, race) => sum + race.runners.length, 0)) },
    ],
    pendingTabs: {
      SCRATCHINGS: "Official scratchings for this meeting will appear here.",
      GEAR_CHANGES: "Official gear changes for this meeting will appear here.",
      TRACK: "Detailed track intelligence will appear here.",
      WEATHER: "Detailed weather intelligence will appear here.",
      RESULTS: "Official meeting results will appear here as races are completed.",
    },
  };
}

export function buildMeetingDetailSelectedRace(
  model: MeetingDetailViewModel,
  meeting: ThreeDayMeeting,
  raceKey: string,
): MeetingDetailSelectedRace | null {
  const row = model.races.find((race) => race.raceKey === raceKey) ?? model.races[0] ?? null;
  if (!row) return null;
  return {
    row,
    details: buildSelectedDetails(row, meeting),
    intelligence: buildRaceIntelligence(row),
  };
}

export function buildMeetingConditionStripForRace(
  meeting: ThreeDayMeeting,
  race: ThreeDayRace | null,
): MeetingConditionStripItem[] {
  return buildConditionStrip(meeting, race);
}
