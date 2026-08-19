
import type { OperationalEvent } from "../../services/operational-state";

type OperationalInboxProps = {
  events: OperationalEvent[];
};

export function OperationalInbox({ events }: OperationalInboxProps) {
  return (
    <section className="eiq-operational-inbox">
      <header>
        <span>Live Events</span>
        <strong>{events.length}</strong>
      </header>

      <div>
        {events.slice(0, 8).map((event) => (
          <article key={event.id}>
            <time>{event.time}</time>
            <div>
              <strong>{event.title}</strong>
              <p>{event.detail}</p>
              <small>{event.source} · {event.severity}</small>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
