
import type { OperationalRaceState } from "../../services/operational-state";

type OperationalAlertsBarProps = {
  raceState: OperationalRaceState;
};

export function OperationalAlertsBar({ raceState }: OperationalAlertsBarProps) {
  const partial = raceState.feedHealth.filter((feed) => feed.status !== "READY");
  const criticalEvents = raceState.events.filter((event) => event.severity === "CRITICAL" || event.severity === "WARNING");

  const alerts = [
    `${raceState.decision.state} mode`,
    `${raceState.confidence}% confidence`,
    partial.length ? `${partial.length} engine(s) pending` : "All engines available",
    criticalEvents.length ? `${criticalEvents.length} watch item(s)` : "No critical alerts",
  ];

  return (
    <section className="eiq-operational-alerts">
      {alerts.map((alert) => (
        <span key={alert}>● {alert}</span>
      ))}
    </section>
  );
}
