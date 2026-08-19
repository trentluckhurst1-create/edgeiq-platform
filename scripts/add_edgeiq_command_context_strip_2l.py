from pathlib import Path

root = Path.cwd()
component = root / "src/components/workspaces/RaceCommandExecutiveWorkspace.tsx"

text = component.read_text(encoding="utf-8")

if "raceContextStrip" not in text:
    text = text.replace(
'''  market: {
    overlay: string;
    confidence: string;
    movement: string;
  };''',
'''  market: {
    overlay: string;
    confidence: string;
    movement: string;
  };
  raceContextStrip?: string[];'''
    )

service = root / "src/services/buildCommandExecutiveSummary.ts"
svc = service.read_text(encoding="utf-8")

if "raceContextStrip" not in svc:
    svc = svc.replace(
'''    market: {
      overlay: "Awaiting race context",
      confidence: "Awaiting race context",
      movement: "Awaiting race context",
    },''',
'''    market: {
      overlay: "Awaiting race context",
      confidence: "Awaiting race context",
      movement: "Awaiting race context",
    },
    raceContextStrip: [
      raceContext?.meeting ?? "Meeting pending",
      raceContext?.race ?? "Race pending",
      raceContext?.distance ?? "Distance pending",
      raceContext?.track ?? "Track pending",
      raceContext?.rail ?? "Rail pending",
      raceContext?.jump ?? "Jump pending",
    ],'''
    )
    service.write_text(svc, encoding="utf-8")

text = component.read_text(encoding="utf-8")

if "edgeiq-command-executive__context-strip" not in text:
    text = text.replace(
'''      <section className="edgeiq-command-executive__assessment">''',
'''      <section className="edgeiq-command-executive__context-strip">
        {summary.raceContextStrip?.map((item) => (
          <span key={item}>{item}</span>
        ))}
      </section>

      <section className="edgeiq-command-executive__assessment">'''
    )

component.write_text(text, encoding="utf-8")

css = root / "src/components/shell/edgeiqOsShell.css"
css_text = css.read_text(encoding="utf-8")

if ".edgeiq-command-executive__context-strip" not in css_text:
    css_text += r'''

.edgeiq-command-executive__context-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  border: 1px solid var(--edgeiq-border);
  background: var(--edgeiq-bg-secondary);
  padding: 12px;
}

.edgeiq-command-executive__context-strip span {
  border: 1px solid var(--edgeiq-border-muted);
  background: var(--edgeiq-panel);
  color: var(--edgeiq-text-secondary);
  padding: 8px 10px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
'''
    css.write_text(css_text, encoding="utf-8")

print("[EDGEIQ_COMMAND_2L] race context strip added to COMMAND")
