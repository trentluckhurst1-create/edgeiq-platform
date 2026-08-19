
import { pick } from "../feed-loader";
import type { FeedRow } from "../feed-loader";
import type { ActiveRaceContext } from "../feed-context";

function normalise(value: string): string {
  return value.trim().toUpperCase();
}

export function describeFeedMatch(
  rows: FeedRow[],
  context: ActiveRaceContext,
  label: string,
): string {
  if (!rows.length) {
    return `${label}: feed loaded but contains no rows for active race ${context.track} R${context.raceNo}.`;
  }

  const sample = rows[0];
  const track = normalise(pick(sample, ["track", "normalised_track"], "UNKNOWN"));
  const raceNo = pick(sample, ["race_no"], "UNKNOWN");
  const raceDate = pick(sample, ["race_date"], "");

  if (track === context.track && raceNo === context.raceNo) {
    return `${label}: active race match ${context.track} R${context.raceNo}${raceDate ? ` (${raceDate})` : ""}; ${rows.length} row(s) available.`;
  }

  return `${label}: no active race match for ${context.track} R${context.raceNo}. Latest available sample is ${track} R${raceNo}${raceDate ? ` (${raceDate})` : ""}.`;
}

export function describeActiveRace(context: ActiveRaceContext): string {
  return `${context.track} R${context.raceNo}${context.raceDate ? ` (${context.raceDate})` : ""}`;
}
