import type {
  EdgeiqWeatherFeed,
  EdgeiqWeatherRecord,
} from "./WeatherTypes";

const WEATHER_FEED_URL = "/data/edgeiq_metropolitan_weather_v1.json";
const WEATHER_CACHE_TTL_MS = 4 * 60 * 1000;

let cachedFeed: EdgeiqWeatherFeed | null = null;
let cachedAt = 0;
let pendingFeed: Promise<EdgeiqWeatherFeed> | null = null;

function normaliseMeeting(value: unknown): string {
  const normalised = String(value ?? "")
    .trim()
    .toUpperCase()
    .replace(/^SPORTSBET[-\s]+/, "")
    .replace(/^LADBROKES[-\s]+/, "")
    .replace(/\s+/g, " ");

  const aliases: Record<string, string> = {
    "CAULFIELD HEATH": "CAULFIELD",
    "CAULFIELD": "CAULFIELD",
    "SANDOWN HILLSIDE": "SANDOWN",
    "SANDOWN LAKESIDE": "SANDOWN",
    "PARK HILLSIDE": "SANDOWN",
    "PARK LAKESIDE": "SANDOWN",
    "PARK": "SANDOWN",
    "MORNINGTON": "MORNINGTON",
    "FLEMINGTON": "FLEMINGTON",
  };

  return aliases[normalised] ?? normalised;
}

async function loadFeed(force = false): Promise<EdgeiqWeatherFeed> {
  const now = Date.now();
  const cacheIsFresh =
    cachedFeed !== null &&
    now - cachedAt < WEATHER_CACHE_TTL_MS;

  if (!force && cacheIsFresh && cachedFeed) {
    return cachedFeed;
  }

  if (pendingFeed) {
    return pendingFeed;
  }

  const requestUrl =
    `${WEATHER_FEED_URL}?updated=${encodeURIComponent(String(now))}`;

  pendingFeed = fetch(requestUrl, {
    cache: "no-store",
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(
          `Weather feed request failed with status ${response.status}`,
        );
      }

      return (await response.json()) as EdgeiqWeatherFeed;
    })
    .then((feed) => {
      cachedFeed = feed;
      cachedAt = Date.now();
      return feed;
    })
    .finally(() => {
      pendingFeed = null;
    });

  return pendingFeed;
}

export async function getMeetingWeather(
  meeting: unknown,
  force = false,
): Promise<EdgeiqWeatherRecord | null> {
  const key = normaliseMeeting(meeting);

  if (!key) return null;

  const feed = await loadFeed(force);

  return (
    feed.records.find((record) => {
      const recordKey = normaliseMeeting(
        record.meeting_key || record.meeting || record.course,
      );

      return (
        recordKey === key ||
        key.includes(recordKey) ||
        recordKey.includes(key)
      );
    }) ?? null
  );
}

export function clearWeatherFeedCache() {
  cachedFeed = null;
  cachedAt = 0;
  pendingFeed = null;
}

