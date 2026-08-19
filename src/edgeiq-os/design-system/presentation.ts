const PLACEHOLDER_VALUES = new Set([
  "",
  "-",
  "--",
  "UNAVAILABLE",
  "UNKNOWN",
  "NOT LOADED",
  "SOURCE GAP",
  "NULL",
  "UNDEFINED",
  "NAN",
  "NONE",
  "N/A",
  "NA",
]);

const TRACK_ALIASES: Array<[RegExp, string]> = [
  [/^SPORTSBET\s+BALLARAT\s+SYNTHETIC$/i, "Ball Syn"],
  [/^BALLARAT\s+SYNTHETIC$/i, "Ball Syn"],
  [/^SPORTSBET\s+BALLARAT$/i, "Ballarat"],
  [/^SPORTSBET\s+PAKENHAM\s+SYNTHETIC$/i, "Pak Syn"],
  [/^PAKENHAM\s+SYNTHETIC$/i, "Pak Syn"],
  [/^SPORTSBET\s+PAKENHAM$/i, "Pakenham"],
  [/^SOUTHSIDE\s+PAKENHAM\s+SYNTHETIC$/i, "Pak Syn"],
  [/^SOUTHSIDE\s+PAKENHAM$/i, "Pakenham"],
  [/^SOUTHSIDE\s+CRANBOURNE$/i, "Cranbourne"],
  [/^LADBROKES\s+GEELONG$/i, "Geelong"],
  [/^SPORTSBET\s+SANDOWN\s+HILLSIDE$/i, "Sandown Hillside"],
  [/^SPORTSBET\s+SANDOWN\s+LAKESIDE$/i, "Sandown Lakeside"],
];

export function cleanProductText(value: unknown, fallback = "-"): string {
  const text = String(value ?? "").replace(/\s+/g, " ").trim();
  if (PLACEHOLDER_VALUES.has(text.toUpperCase())) return fallback;
  return text;
}

export function canonicalTrackDisplayName(value: unknown): string {
  let text = cleanProductText(value, "");
  if (!text) return "";
  text = text.replace(/\s+/g, " ").trim();
  for (const [pattern, replacement] of TRACK_ALIASES) {
    if (pattern.test(text)) return replacement;
  }
  return text
    .replace(/^SPORTSBET\s+/i, "")
    .replace(/^LADBROKES\s+/i, "")
    .replace(/^BET365\s+/i, "")
    .replace(/^TAB\s+/i, "")
    .trim();
}

function normaliseRecordTrackFields(record: Record<string, unknown> | undefined): Record<string, unknown> | undefined {
  if (!record) return record;
  const next: Record<string, unknown> = { ...record };
  for (const key of ["meeting", "meetingName", "track", "trackName", "venue", "venueName", "canonicalTrack", "displayTrack"]) {
    if (typeof next[key] === "string") next[key] = canonicalTrackDisplayName(next[key]);
  }
  return next;
}

export function normaliseCatalogTrackNames<T extends { meetings?: any[] }>(catalog: T): T {
  if (!catalog || !Array.isArray(catalog.meetings)) return catalog;
  return {
    ...catalog,
    meetings: catalog.meetings.map((meeting) => ({
      ...meeting,
      meeting: canonicalTrackDisplayName(meeting?.meeting),
      source: normaliseRecordTrackFields(meeting?.source),
      races: Array.isArray(meeting?.races)
        ? meeting.races.map((race: any) => ({
            ...race,
            source: normaliseRecordTrackFields(race?.source),
            runners: Array.isArray(race?.runners)
              ? race.runners.map((runner: any) => ({
                  ...runner,
                  source: normaliseRecordTrackFields(runner?.source),
                }))
              : race?.runners,
          }))
        : meeting?.races,
    })),
  };
}

export function marketDisplayStatus(status: unknown, hasMarket: boolean, isClosed = false): string {
  const text = cleanProductText(status, "");
  if (isClosed || /closed|scratched/i.test(text)) return "Market Closed";
  if (hasMarket || /available|live|snapshot/i.test(text)) return "Market Available";
  return "Awaiting Feed";
}


export function canonicalTrackRatingDisplay(value: unknown, fallback = "Awaiting Track Rating"): string {
  const text = cleanProductText(value, "");
  if (!text) return fallback;
  if (/synthetic/i.test(text)) return "Synthetic";
  const match = text.match(/\b(Firm|Good|Soft|Heavy)\s*([0-9]{1,2})?\b/i);
  if (!match) return fallback;
  const label = `${match[1][0].toUpperCase()}${match[1].slice(1).toLowerCase()}${match[2] ? ` ${match[2]}` : ""}`;
  return label.length > 24 ? fallback : label;
}

export function canonicalWeatherDisplay(value: unknown, fallback = "Awaiting Weather Feed"): string {
  const text = cleanProductText(value, "");
  if (!text) return fallback;
  if (/not\s+published/i.test(text)) return "Weather Not Published";
  if (/sun|fine|clear/i.test(text)) return /fine/i.test(text) ? "Fine" : "Sunny";
  if (/cloud/i.test(text)) return "Cloudy";
  if (/overcast/i.test(text)) return "Overcast";
  if (/shower/i.test(text)) return "Showers";
  if (/rain|storm|wet/i.test(text)) return "Rain";
  if (/wind/i.test(text)) return "Windy";
  return text.length > 24 ? fallback : text;
}

export function canonicalRailDisplay(value: unknown, fallback = "Not Supplied"): string {
  const text = cleanProductText(value, "");
  if (!text) return fallback;
  return text.length > 32 ? fallback : text;
}


const PROMOTIONAL_RACE_TITLE_PATTERNS: Array<[RegExp, string]> = [
  [/\bLADBROKES\s+SALE\s+CUP\s+25TH\s+OCTOBER\s*[\u2013\u2014-]?\s*BOOK\s+NOW\s*/gi, "Sale Cup "],
  [/\bTHANKYOU\s+MEMBERS\s*&\s*SPONSORS\s+FOR\s+SEASON\s+2025\/?26\s*/gi, ""],
  [/\bLADBROKES\s+PLACE\s+EXTRA\s+TO\s+10TH\s*/gi, ""],
  [/\bLADBROKES\s+ODDS\s+SURGE\s*/gi, ""],
  [/\bBOOK\s+NOW\b/gi, ""],
  [/\bBET\s+NOW\b/gi, ""],
  [/\bODDS\s+SURGE\b/gi, ""],
  [/\bPLACE\s+EXTRA\b/gi, ""],
  [/\bMEMBERS\s*&\s*SPONSORS\s+FOR\s+SEASON\s+2025\/?26\b/gi, ""],
];

export function canonicalRaceTitleDisplay(value: unknown): string {
  let text = cleanProductText(value, "");
  if (!text) return "";
  for (const [pattern, replacement] of PROMOTIONAL_RACE_TITLE_PATTERNS) {
    text = text.replace(pattern, replacement);
  }
  return text.replace(/\s*[\u2013\u2014-]\s*$/g, "").replace(/\s{2,}/g, " ").trim();
}
