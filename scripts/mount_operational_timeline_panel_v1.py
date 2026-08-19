from pathlib import Path

panel = Path("src/edgeiq-os/command/components/OperationalTimelinePanel.tsx")

panel.write_text(r'''
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
''', encoding="utf-8")

workspace = Path("src/edgeiq-os/command/EdgeiqCommandWorkspace.tsx")
text = workspace.read_text(encoding="utf-8")

if 'OperationalTimelinePanel' not in text:
    text = text.replace(
        'import { ChangesSincePanel } from "./components/ChangesSincePanel";',
        'import { ChangesSincePanel } from "./components/ChangesSincePanel";\nimport { OperationalTimelinePanel } from "./components/OperationalTimelinePanel";'
    )

text = text.replace(
    '<ChangesSincePanel since={"LIVE"} items={changes} />',
    '<OperationalTimelinePanel events={raceState.events} />'
)

workspace.write_text(text, encoding="utf-8")

print("[EDGEIQ] OperationalTimelinePanel created and mounted")
