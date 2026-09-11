import { edgeiqDataPath } from "../../../config/edgeiqDataOrigin";
import type { ThreeDayRace } from "./threeDayCatalog";

type RaceDetailFeed = {
  schemaVersion: string;
  generatedAt: string;
  date: string;
  meetingKey: string;
  raceKey: string;
  race: ThreeDayRace;
};

const MAX_RACE_DETAIL_BYTES = 4_000_000;
const raceCache = new Map<string, ThreeDayRace>();
const racePending = new Map<string, Promise<ThreeDayRace>>();

function slug(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "item";
}

export async function loadRaceDetail(
  date: string,
  meetingKey: string,
  raceKey: string,
  force = false,
): Promise<ThreeDayRace> {
  const cacheKey = `${date}|${meetingKey}|${raceKey}`;
  if (!force && raceCache.has(cacheKey)) return raceCache.get(cacheKey)!;
  if (racePending.has(cacheKey)) return racePending.get(cacheKey)!;

  const url = edgeiqDataPath(`/data/races/${date}_${slug(meetingKey)}_${slug(raceKey)}.json`);
  const pending = fetch(`${url}?updated=${encodeURIComponent(String(Date.now()))}`, {
    cache: force ? "reload" : "no-store",
  })
    .then(async (response) => {
      if (!response.ok) throw new Error(`Race detail failed with ${response.status}`);
      const text = await response.text();
      if (text.length > MAX_RACE_DETAIL_BYTES) throw new Error(`Race detail exceeds ${MAX_RACE_DETAIL_BYTES} bytes`);
      const payload = JSON.parse(text) as RaceDetailFeed;
      if (!payload.race || payload.raceKey !== raceKey || payload.race.raceKey !== raceKey) {
        throw new Error("Race detail is invalid");
      }
      raceCache.set(cacheKey, payload.race);
      return payload.race;
    })
    .finally(() => {
      racePending.delete(cacheKey);
    });

  racePending.set(cacheKey, pending);
  return pending;
}
