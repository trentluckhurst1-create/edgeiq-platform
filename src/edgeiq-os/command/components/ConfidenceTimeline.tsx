
import type { OperationalRaceState } from "../../services/operational-state";

type ConfidenceTimelineProps = {
  raceState: OperationalRaceState;
};

export function ConfidenceTimeline({ raceState }: ConfidenceTimelineProps) {
  const base = Math.max(20, raceState.confidence - 8);
  const points = [
    { label: "Open", value: base },
    { label: "Shape", value: Math.min(95, base + 3) },
    { label: "Explain", value: Math.min(95, base + 7) },
    { label: "Current", value: raceState.confidence },
  ];

  return (
    <section className="eiq-confidence-timeline">
      <header>
        <span>Confidence Trend</span>
        <strong>{raceState.confidence}%</strong>
      </header>

      <div className="eiq-confidence-timeline__track">
        {points.map((point) => (
          <article key={point.label}>
            <b style={{ height: `${point.value}%` }} />
            <span>{point.label}</span>
            <small>{point.value}%</small>
          </article>
        ))}
      </div>

      <p>{raceState.confidence >= base ? "Confidence stable to improving." : "Confidence under pressure."}</p>
    </section>
  );
}
