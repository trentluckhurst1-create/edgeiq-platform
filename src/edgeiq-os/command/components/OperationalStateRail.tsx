
import type { OperationalRaceState } from "../../services/operational-state";

type OperationalStateRailProps = {
  raceState: OperationalRaceState;
};

export function OperationalStateRail({ raceState }: OperationalStateRailProps) {
  return (
    <aside className="eiq-command-rail">
      <section>
        <span>System State</span>
        <strong>{raceState.status}</strong>
        <p>{raceState.confidence}% operational confidence</p>
      </section>

      <section>
        <span>Feed Health</span>
        <dl>
          {raceState.feedHealth.map((feed) => (
            <div key={feed.key}>
              <dt>{feed.label}</dt>
              <dd>{feed.status}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section>
        <span>Coverage</span>
        <dl>
          {raceState.coverage.map((item) => (
            <div key={item.key}>
              <dt>{item.label}</dt>
              <dd>{item.coveragePct}%</dd>
            </div>
          ))}
        </dl>
      </section>

      <section>
        <span>Alerts</span>
        {raceState.alerts.length ? (
          raceState.alerts.map((alert) => (
            <p key={alert.id}>
              <strong>{alert.severity}</strong> · {alert.title}
            </p>
          ))
        ) : (
          <p>No active alerts.</p>
        )}
      </section>
    </aside>
  );
}
