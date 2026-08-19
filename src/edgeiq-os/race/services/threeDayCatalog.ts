import { loadJsonFeed } from "../../services/feed-loader/ProductFeedCache";
import { normaliseCatalogTrackNames } from "../../design-system/presentation";

export type ThreeDayRunner = {
  official: {
    no?: unknown;
    number?: unknown;
    runner?: string | null;
    barrier?: unknown;
    jockey?: string | null;
    trainer?: string | null;
    weight?: string | null;
    market?: unknown;
  };
  source?: Record<string, unknown>;
  historicalRuns?: unknown[];
  evidenceRuns?: unknown[];
};

export type ThreeDayRace = {
  raceKey: string;
  raceNumber: number;
  raceName: string;
  distance: string | null;
  raceClass: string | null;
  raceTime: string | null;
  trackCondition: string | null;
  rail: string | null;
  runners: ThreeDayRunner[];
  source?: Record<string, unknown>;
};

export type ThreeDayMeeting = {
  meetingKey: string;
  meeting: string;
  providerMeetingKey: string;
  date: string;
  trackCondition: string | null;
  rail: string | null;
  raceCount: number;
  races: ThreeDayRace[];
  source?: Record<string, unknown>;
};

export type ThreeDayCatalog = {
  schemaVersion: string;
  generatedAt: string;
  dates: string[];
  dayLabels: Record<string, string>;
  meetings: ThreeDayMeeting[];
};

const URL = "/data/edgeiq_three_day_product_catalog_v1.json";
const MAX_CATALOG_BYTES = 15_000_000;

export async function loadThreeDayCatalog(
  force = false,
): Promise<ThreeDayCatalog> {
  const catalog = await loadJsonFeed<ThreeDayCatalog>(URL, {
    force,
    cacheKey: "three-day-product-catalog-v1",
    maxBytes: MAX_CATALOG_BYTES,
  });
  return normaliseCatalogTrackNames(catalog);
}
