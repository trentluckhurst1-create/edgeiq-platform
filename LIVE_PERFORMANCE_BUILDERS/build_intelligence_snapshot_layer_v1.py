from pathlib import Path

folder = Path("src/edgeiq-os/services/intelligence-snapshot")
folder.mkdir(parents=True, exist_ok=True)

(folder / "IntelligenceSnapshotTypes.ts").write_text(r'''
import type { FeedRow } from "../feed-loader";
import type { ActiveRaceContext } from "../feed-context";

export interface IntelligenceSnapshot {
  context: ActiveRaceContext;

  raceShape: FeedRow[];
  runnerDna: FeedRow[];
  explainability: FeedRow[];

  connections: FeedRow[];
  track: FeedRow[];
  weather: FeedRow[];
  market: FeedRow[];
  sectionals: FeedRow[];
}
''', encoding="utf-8")

(folder / "IntelligenceSnapshotService.ts").write_text(r'''
import { loadBundledCsv } from "../feed-loader";
import {
  getActiveRaceContext,
  findActiveRaceRows,
} from "../feed-context";

import type { IntelligenceSnapshot } from "./IntelligenceSnapshotTypes";

function rows(path: string) {
  return loadBundledCsv(path).rows;
}

export function buildIntelligenceSnapshot(): IntelligenceSnapshot {
  const context = getActiveRaceContext();

  return {
    context,

    raceShape: findActiveRaceRows(
      rows("/data/edgeiq_race_shape_story_v1.csv"),
      context,
    ),

    runnerDna: findActiveRaceRows(
      rows("/data/edgeiq_runner_dna_drawer_feed_v2.csv"),
      context,
    ),

    explainability: findActiveRaceRows(
      rows("/data/edgeiq_explainability_terminal_feed_v1_2.csv"),
      context,
    ),

    connections: findActiveRaceRows(
      rows("/data/edgeiq_connection_intelligence_v2_1.csv"),
      context,
    ),

    track: findActiveRaceRows(
      rows("/data/edgeiq_live_track_intelligence_v2_1.csv"),
      context,
    ),

    weather: findActiveRaceRows(
      rows("/data/edgeiq_live_weather_feed_v1.csv"),
      context,
    ),

    market: findActiveRaceRows(
      rows("/data/edgeiq_market_intelligence_v1.csv"),
      context,
    ),

    sectionals: findActiveRaceRows(
      rows("/data/edgeiq_live_sectional_intelligence_v1.csv"),
      context,
    ),
  };
}
''', encoding="utf-8")

(folder / "index.ts").write_text(r'''
export * from "./IntelligenceSnapshotTypes";
export * from "./IntelligenceSnapshotService";
''', encoding="utf-8")

print("[EDGEIQ] Intelligence Snapshot layer created")
