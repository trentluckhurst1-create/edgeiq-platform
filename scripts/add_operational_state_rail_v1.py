from pathlib import Path

rail = Path("src/edgeiq-os/command/components/OperationalStateRail.tsx")

rail.write_text(r'''
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
''', encoding="utf-8")

workspace = Path("src/edgeiq-os/command/EdgeiqCommandWorkspace.tsx")
text = workspace.read_text(encoding="utf-8")

text = text.replace(
'import { RaceStateRail } from "./components/RaceStateRail";',
'import { OperationalStateRail } from "./components/OperationalStateRail";'
)

text = text.replace(
'''          {/* RaceStateRail temporarily disabled during OS migration */}''',
'''          <OperationalStateRail raceState={raceState} />'''
)

workspace.write_text(text, encoding="utf-8")

print("[EDGEIQ] OperationalStateRail created and wired")
