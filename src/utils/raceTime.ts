
export type AnyRaceRow = Record<string, any>;

export const STATE_TIMEZONES: Record<string, string> = {
  WA: "Australia/Perth",
  SA: "Australia/Adelaide",
  NT: "Australia/Darwin",
  QLD: "Australia/Brisbane",
  NSW: "Australia/Sydney",
  VIC: "Australia/Melbourne",
  TAS: "Australia/Hobart",
  ACT: "Australia/Sydney",
};

export const TRACK_TIMEZONE_HINTS: Record<string, string> = {
  pinjarra: "Australia/Perth",
  ascot: "Australia/Perth",
  belmont: "Australia/Perth",
  bunbury: "Australia/Perth",
  geraldton: "Australia/Perth",
  kalgoorlie: "Australia/Perth",
  northam: "Australia/Perth",
  york: "Australia/Perth",
  broome: "Australia/Perth",
  albany: "Australia/Perth",
  narrogin: "Australia/Perth",
  esperance: "Australia/Perth",
  morphettville: "Australia/Adelaide",
  gawler: "Australia/Adelaide",
  balaklava: "Australia/Adelaide",
  strathalbyn: "Australia/Adelaide",
  darwin: "Australia/Darwin",
  alice: "Australia/Darwin",
  eagle: "Australia/Brisbane",
  doomben: "Australia/Brisbane",
  ipswich: "Australia/Brisbane",
  gold: "Australia/Brisbane",
  sunshine: "Australia/Brisbane",
  townsville: "Australia/Brisbane",
  cairns: "Australia/Brisbane",
  mackay: "Australia/Brisbane",
  rockhampton: "Australia/Brisbane",
  flemington: "Australia/Melbourne",
  caulfield: "Australia/Melbourne",
  moonee: "Australia/Melbourne",
  sandown: "Australia/Melbourne",
  bendigo: "Australia/Melbourne",
  ballarat: "Australia/Melbourne",
  geelong: "Australia/Melbourne",
  pakenham: "Australia/Melbourne",
  cranbourne: "Australia/Melbourne",
  mornington: "Australia/Melbourne",
  randwick: "Australia/Sydney",
  rosehill: "Australia/Sydney",
  warwick: "Australia/Sydney",
  canterbury: "Australia/Sydney",
  gosford: "Australia/Sydney",
  hawkesbury: "Australia/Sydney",
  newcastle: "Australia/Sydney",
  kembla: "Australia/Sydney",
  hobart: "Australia/Hobart",
  launceston: "Australia/Hobart",
  devonport: "Australia/Hobart",
};

export function cleanText(v: unknown): string {
  return String(v ?? "").trim();
}

function firstText(...values: unknown[]): string {
  for (const value of values) {
    const cleaned = cleanText(value);
    if (cleaned) return cleaned;
  }
  return "";
}

export function inferRaceTimeZone(row?: AnyRaceRow, race?: AnyRaceRow): string {
  const explicit = firstText(
    row?.track_timezone,
    row?.timezone,
    row?.race_timezone,
    race?.track_timezone,
    race?.timezone,
    race?.race_timezone
  );
  if (explicit) return explicit;

  const state = firstText(row?.state, race?.state).toUpperCase();
  if (STATE_TIMEZONES[state]) return STATE_TIMEZONES[state];

  const track = firstText(row?.track, row?.meeting, race?.track, race?.meeting).toLowerCase();
  for (const [hint, timeZone] of Object.entries(TRACK_TIMEZONE_HINTS)) {
    if (track.includes(hint)) return timeZone;
  }

  return "Australia/Melbourne";
}

export function parseClockTime(timeValue: unknown): { hour: number; minute: number } | null {
  const text = cleanText(timeValue).replace(/\./g, ":").replace(/\s+/g, "").toUpperCase();
  const meridiemMatch = text.match(/^(\d{1,2}):?(\d{2})(AM|PM)$/);
  if (meridiemMatch) {
    let hour = Number(meridiemMatch[1]);
    const minute = Number(meridiemMatch[2]);
    if (!Number.isFinite(hour) || !Number.isFinite(minute)) return null;
    if (meridiemMatch[3] === "PM" && hour < 12) hour += 12;
    if (meridiemMatch[3] === "AM" && hour === 12) hour = 0;
    return { hour, minute };
  }

  const twentyFourHourMatch = text.match(/^(\d{1,2}):(\d{2})$/);
  if (twentyFourHourMatch) {
    const hour = Number(twentyFourHourMatch[1]);
    const minute = Number(twentyFourHourMatch[2]);
    if (!Number.isFinite(hour) || !Number.isFinite(minute)) return null;
    return { hour, minute };
  }

  return null;
}

export function offsetMsForZone(timeZone: string, utcMs: number): number {
  const dtf = new Intl.DateTimeFormat("en-AU", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  });

  const parts = Object.fromEntries(
    dtf.formatToParts(new Date(utcMs)).map((part) => [part.type, part.value])
  );

  const zonedAsUtc = Date.UTC(
    Number(parts.year),
    Number(parts.month) - 1,
    Number(parts.day),
    Number(parts.hour),
    Number(parts.minute),
    Number(parts.second)
  );

  return zonedAsUtc - utcMs;
}

export function localRaceTimeToUtcMs(
  raceDate: unknown,
  raceTime: unknown,
  timeZone: string
): number | null {
  const dateText = cleanText(raceDate);
  const parsedTime = parseClockTime(raceTime);
  if (!dateText || !parsedTime) return null;

  const [year, month, day] = dateText.split("-").map(Number);
  if (!year || !month || !day) return null;

  const naiveUtc = Date.UTC(year, month - 1, day, parsedTime.hour, parsedTime.minute, 0);
  return naiveUtc - offsetMsForZone(timeZone, naiveUtc);
}

export function raceDateTimeMs(row?: AnyRaceRow, race?: AnyRaceRow): number | null {
  const utc = firstText(
    row?.race_time_utc,
    row?.raceTimeUtc,
    row?.raceTimeUTC,
    race?.race_time_utc,
    race?.raceTimeUtc,
    race?.raceTimeUTC
  );

  if (utc) {
    const ms = new Date(utc).getTime();
    if (Number.isFinite(ms)) return ms;
  }

  const raceDate = firstText(row?.raceDate, row?.race_date, row?.date, race?.raceDate, race?.race_date, race?.date);
  const raceTime = firstText(
    row?.raceTime,
    row?.race_time,
    row?.time,
    row?.startTime,
    row?.start_time,
    row?.jump_time,
    race?.raceTime,
    race?.race_time,
    race?.time,
    race?.startTime,
    race?.start_time,
    race?.jump_time
  );

  return localRaceTimeToUtcMs(raceDate, raceTime, inferRaceTimeZone(row, race));
}

export function formatUserLocalRaceTime(
  row?: AnyRaceRow,
  race?: AnyRaceRow,
  fallback = "TIME TBC"
): string {
  const ms = raceDateTimeMs(row, race);
  if (ms !== null) {
    return new Date(ms).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }

  return firstText(row?.raceTime, row?.race_time, row?.time, race?.raceTime, race?.race_time, race?.time) || fallback;
}

export function minutesToJump(row?: AnyRaceRow, race?: AnyRaceRow): number | null {
  const ms = raceDateTimeMs(row, race);
  if (ms === null) return null;
  return Math.round((ms - Date.now()) / 60000);
}

export function countdownLabel(row?: AnyRaceRow, race?: AnyRaceRow): string {
  const minutes = minutesToJump(row, race);
  if (minutes === null) return "";
  if (minutes > 90) return `${Math.round(minutes / 60)}h`;
  if (minutes > 0) return `${minutes}m`;
  if (minutes >= -5) return "jump";
  return "closed";
}

export function formatLastUpdatedFromRows(rows: AnyRaceRow[], fallback = ""): string {
  const fields = ["timestamp", "captured_at_utc", "updated_at", "last_updated", "created_at", "timestamp_dt"];
  let latestMs = 0;

  for (const row of rows) {
    for (const field of fields) {
      const value = cleanText(row?.[field]);
      if (!value) continue;
      const ms = new Date(value).getTime();
      if (Number.isFinite(ms) && ms > latestMs) latestMs = ms;
    }
  }

  if (latestMs > 0) {
    return new Date(latestMs).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }

  return fallback;
}
