
import type { OperationalTimelineEvent } from "../operational-state";

const events: OperationalTimelineEvent[] = [];

export function appendTimelineEvent(event: OperationalTimelineEvent): void {
  events.unshift(event);
}

export function getTimelineEvents(): OperationalTimelineEvent[] {
  return [...events];
}

export function clearTimelineEvents(): void {
  events.splice(0, events.length);
}

export function seedTimeline(): OperationalTimelineEvent[] {
  if (events.length === 0) {
    appendTimelineEvent({
      id: "timeline-engine-ready",
      time: "NOW",
      title: "Timeline engine online",
      summary: "Operational timeline service is ready for snapshot and change events.",
      severity: "IMPORTANT",
    });
  }

  return getTimelineEvents();
}
