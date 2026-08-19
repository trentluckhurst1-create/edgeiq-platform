
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
