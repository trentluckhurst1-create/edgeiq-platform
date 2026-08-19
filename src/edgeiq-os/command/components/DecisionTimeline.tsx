import type { DecisionTimelineModel } from "../../services/decision-timeline";

type DecisionTimelineProps = {
  timeline: DecisionTimelineModel;
};

export function DecisionTimeline({ timeline }: DecisionTimelineProps) {
  return (
    <section className="eiq-decision-timeline">
      <header>
        <span>Evolution</span>
        <strong>{timeline.title}</strong>
      </header>

      <div className="eiq-decision-timeline__track">
        {timeline.events.map((event) => (
          <article key={event.id}>
            <time>{event.time}</time>
            <div>
              <span>{event.status}</span>
              <strong>{event.title}</strong>
              <p>{event.summary}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
