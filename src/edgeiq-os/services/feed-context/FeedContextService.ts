
import { loadBundledCsv, pick } from "../feed-loader";
import type { FeedRow } from "../feed-loader";
import type { ActiveRaceContext } from "./FeedContextTypes";

const PRIMARY_CONTEXT_FEED = "/data/edgeiq_explainability_terminal_feed_v1_2.csv";

function normalise(value: string): string {
  return value.trim().toUpperCase();
}

export function getActiveRaceContext(): ActiveRaceContext {
  const feed = loadBundledCsv(PRIMARY_CONTEXT_FEED);
  const row = feed.rows[0];

  return {
    track: normalise(pick(row, ["track"], "UNKNOWN")),
    raceNo: pick(row, ["race_no"], "1"),
    raceDate: pick(row, ["race_date"], ""),
  };
}

export function rowMatchesActiveRace(row: FeedRow, context: ActiveRaceContext): boolean {
  const rowTrack = normalise(pick(row, ["track", "normalised_track"], ""));
  const rowRaceNo = pick(row, ["race_no"], "");

  return rowTrack === context.track && rowRaceNo === context.raceNo;
}

export function findActiveRaceRows(rows: FeedRow[], context: ActiveRaceContext): FeedRow[] {
  return rows.filter((row) => rowMatchesActiveRace(row, context));
}

export function findFirstActiveRaceRow(rows: FeedRow[], context: ActiveRaceContext): FeedRow | undefined {
  return findActiveRaceRows(rows, context)[0];
}
