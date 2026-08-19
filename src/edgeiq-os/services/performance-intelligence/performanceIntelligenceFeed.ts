import { loadJsonFeed } from "../feed-loader/ProductFeedCache";
import type { PerformanceIntelligenceFeed } from "./types";

const URL = "/performance-intelligence/edgeiq_performance_intelligence_product_feeds_v1.json";
const MAX_ROWS_PER_INDEX = 10000;
const MAX_FEED_BYTES = 5_000_000;

function asArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

function assertSmallFeed(feed: PerformanceIntelligenceFeed): PerformanceIntelligenceFeed {
  const rowCounts = {
    race_intelligence_index: feed.race_intelligence_index.length,
    horse_intelligence_index: feed.horse_intelligence_index.length,
    historical_performance_intelligence_index: feed.historical_performance_intelligence_index.length,
    benchmark_explanation_index: feed.benchmark_explanation_index.length,
  };

  const oversized = Object.entries(rowCounts).find(([, count]) => count > MAX_ROWS_PER_INDEX);
  if (oversized) {
    console.warn("EDGEiQ rejected oversized performance intelligence feed", oversized[0], oversized[1]);
    return {
      manifest: {
        ...(feed.manifest ?? {}),
        row_counts: rowCounts,
        known_limitations: [
          ...((feed.manifest?.known_limitations ?? []) as string[]),
          `Rejected oversized ${oversized[0]} with ${oversized[1]} rows.`,
        ],
      },
      race_intelligence_index: [],
      horse_intelligence_index: [],
      historical_performance_intelligence_index: [],
      benchmark_explanation_index: [],
    };
  }

  return feed;
}

function normaliseFeed(payload: unknown): PerformanceIntelligenceFeed {
  const raw = payload as Partial<PerformanceIntelligenceFeed> | null;
  const feed: PerformanceIntelligenceFeed = {
    manifest: raw?.manifest ?? {},
    race_intelligence_index: asArray(raw?.race_intelligence_index),
    horse_intelligence_index: asArray(raw?.horse_intelligence_index),
    historical_performance_intelligence_index: asArray(raw?.historical_performance_intelligence_index),
    benchmark_explanation_index: asArray(raw?.benchmark_explanation_index),
  };
  return assertSmallFeed(feed);
}

export async function loadPerformanceIntelligenceFeed(force = false): Promise<PerformanceIntelligenceFeed> {
  return loadJsonFeed<PerformanceIntelligenceFeed>(URL, {
    force,
    cacheKey: "performance-intelligence-product-v1",
    maxBytes: MAX_FEED_BYTES,
    normalise: normaliseFeed,
  });
}
