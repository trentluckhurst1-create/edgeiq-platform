
import type { OperationalEvent } from "../../services/operational-state";

type OperationalTimelinePanelProps = {
  events: OperationalEvent[];
};

export function OperationalTimelinePanel({ events }: OperationalTimelinePanelProps) {
  return (
    <section className="eiq-command-changes">
      <div>
        <span>Operational Timeline</span>
        <strong>LIVE</strong>
      </div>

      {events.slice(0, 6).map((event) => (
        <article key={event.id}>
          <span>{event.time} · {event.source}</span>
          <strong>{event.severity}</strong>
          <p>{event.title} — {event.detail}</p>
        </article>
      ))}

      <button type="button">View History</button>
    </section>
  );
}
