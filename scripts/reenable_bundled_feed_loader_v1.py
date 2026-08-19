from pathlib import Path

loader = Path("src/edgeiq-os/services/feed-loader/FeedLoader.ts")

loader.write_text(r'''
import { parseCsv } from "./FeedParser";
import type { FeedLoadResult } from "./FeedTypes";

import raceShapeStory from "../../../../public/data/edgeiq_race_shape_story_v1.csv?raw";
import runnerDnaDrawer from "../../../../public/data/edgeiq_runner_dna_drawer_feed_v2.csv?raw";
import explainabilityTerminal from "../../../../public/data/edgeiq_explainability_terminal_feed_v1_2.csv?raw";
import connectionIntelligence from "../../../../public/data/edgeiq_connection_intelligence_v2_1.csv?raw";
import trackIntelligence from "../../../../public/data/edgeiq_live_track_intelligence_v2_1.csv?raw";
import weatherFeed from "../../../../public/data/edgeiq_live_weather_feed_v1.csv?raw";
import marketIntelligence from "../../../../public/data/edgeiq_market_intelligence_v1.csv?raw";
import sectionalIntelligence from "../../../../public/data/edgeiq_live_sectional_intelligence_v1.csv?raw";

const feedCache = new Map<string, FeedLoadResult>();

const bundledFeeds: Record<string, string> = {
  "/data/edgeiq_race_shape_story_v1.csv": raceShapeStory,
  "/data/edgeiq_runner_dna_drawer_feed_v2.csv": runnerDnaDrawer,
  "/data/edgeiq_explainability_terminal_feed_v1_2.csv": explainabilityTerminal,
  "/data/edgeiq_connection_intelligence_v2_1.csv": connectionIntelligence,
  "/data/edgeiq_live_track_intelligence_v2_1.csv": trackIntelligence,
  "/data/edgeiq_live_weather_feed_v1.csv": weatherFeed,
  "/data/edgeiq_market_intelligence_v1.csv": marketIntelligence,
  "/data/edgeiq_live_sectional_intelligence_v1.csv": sectionalIntelligence,
};

export function loadBundledCsv(path: string): FeedLoadResult {
  const normalisedPath = path.startsWith("/") ? path : `/${path}`;

  if (feedCache.has(normalisedPath)) {
    return feedCache.get(normalisedPath)!;
  }

  const text = bundledFeeds[normalisedPath];

  if (typeof text !== "string") {
    const result: FeedLoadResult = {
      path: normalisedPath,
      rows: [],
      loaded: false,
      error: `Bundled feed not found: ${normalisedPath}`,
    };

    feedCache.set(normalisedPath, result);
    return result;
  }

  const result: FeedLoadResult = {
    path: normalisedPath,
    rows: parseCsv(text),
    loaded: true,
  };

  feedCache.set(normalisedPath, result);
  return result;
}

export function clearFeedCache(): void {
  feedCache.clear();
}
''', encoding="utf-8")

print("[EDGEIQ] FeedLoader re-enabled with explicit bundled production feeds")
