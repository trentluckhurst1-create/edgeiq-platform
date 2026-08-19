from pathlib import Path

rail = Path("src/edgeiq-os/command/components/OperationsRailV2.tsx")
smoke = Path("scripts/smoke_edgeiq_operational_state_v1.py")

rail.write_text(r'''
import type { OperationalRaceState } from "../../services/operational-state";

type OperationsRailV2Props = {
  raceState: OperationalRaceState;
};

function statusLabel(status: string): string {
  return status === "READY" ? "Available" : "Waiting";
}

export function OperationsRailV2({ raceState }: OperationsRailV2Props) {
  const ready = raceState.feedHealth.filter((engine) => engine.status === "READY");
  const waiting = raceState.feedHealth.filter((engine) => engine.status !== "READY");

  return (
    <section className="eiq-command-v4-rail">
      <header>
        <span>Engine Status</span>
        <strong>{ready.length}/{raceState.feedHealth.length} online</strong>
      </header>

      <div className="eiq-command-v4-rail__group">
        <span>Available</span>
        {ready.map((engine) => (
          <article key={engine.key}>
            <i />
            <strong>{engine.label}</strong>
            <small>{statusLabel(engine.status)}</small>
          </article>
        ))}
      </div>

      <div className="eiq-command-v4-rail__group">
        <span>Still Monitoring</span>
        {waiting.map((engine) => (
          <article key={engine.key}>
            <i />
            <strong>{engine.label}</strong>
            <small>{statusLabel(engine.status)}</small>
          </article>
        ))}
      </div>

      <footer>
        <span>System</span>
        <strong>{raceState.decision.state}</strong>
        <small>{raceState.confidence}% confidence</small>
      </footer>
    </section>
  );
}
'''.lstrip(), encoding="utf-8")

text = smoke.read_text(encoding="utf-8")
text = text.replace('"OperationalStateRail",', '"OperationsRailV2",')
text = text.replace('"OperationalStateRail.tsx": [', '"OperationsRailV2.tsx": [')
text = text.replace('"raceState.coverage",', '"raceState.feedHealth",')
text = text.replace('"raceState.alerts",', '"raceState.decision",')
text = text.replace(
    'COMMAND is wired to OperationalRaceState, operational evidence drawer, briefing composer, and OS rail.',
    'COMMAND is wired to OperationalRaceState, operational evidence workspace, briefing composer, and OperationsRailV2.'
)
smoke.write_text(text, encoding="utf-8")

print("[EDGEIQ] COMMAND V4 rail and smoke repaired")
