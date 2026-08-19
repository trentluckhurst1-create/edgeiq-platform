import type { OperationalRaceState } from "./operational-state";
import { formatDecisionState, formatConfidenceLabel, formatIntelligenceStatus } from "../design-system";

export type DecisionTimelineEvent = {
  id: string;
  time: string;
  title: string;
  summary: string;
  status: string;
};

export type DecisionTimelineModel = {
  title: string;
  decision: string;
  confidence: string;
  events: DecisionTimelineEvent[];
};

function fallbackTime(index: number): string {
  const base = 9 * 60;
  const minutes = base + index * 7;
  const hh = Math.floor(minutes / 60).toString().padStart(2, "0");
  const mm = (minutes % 60).toString().padStart(2, "0");
  return `${hh}:${mm}`;
}

export function buildDecisionTimeline(raceState: OperationalRaceState): DecisionTimelineModel {
  const feedEvents = raceState.feedHealth.slice(0, 6).map((feed, index) => ({
    id: `feed-${feed.key}`,
    time: fallbackTime(index),
    title: feed.label,
    summary: feed.status === "READY"
      ? `${feed.label} is contributing to the current operational view.`
      : `${feed.label} remains under observation.`,
    status: formatIntelligenceStatus(feed.status),
  }));

  const operationalEvents = raceState.events.slice(0, 3).map((event, index) => ({
    id: `event-${event.id}`,
    time: event.time || fallbackTime(feedEvents.length + index),
    title: event.title,
    summary: event.detail,
    status: event.severity,
  }));

  return {
    title: "Decision Timeline",
    decision: formatDecisionState(raceState.decision.state),
    confidence: formatConfidenceLabel(raceState.confidence),
    events: [
      ...feedEvents,
      ...operationalEvents,
      {
        id: "current-decision",
        time: "Now",
        title: formatDecisionState(raceState.decision.state),
        summary: `${formatConfidenceLabel(raceState.confidence)} confidence. Current position remains active until the next material confirmation signal.`,
        status: "Current Position",
      },
    ],
  };
}
