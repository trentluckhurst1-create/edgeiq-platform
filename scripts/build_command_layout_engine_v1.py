from pathlib import Path

layout = Path("src/edgeiq-os/command/components/CommandLayout.tsx")

layout.write_text(r'''
import type { ReactNode } from "react";

type CommandLayoutProps = {
  header: ReactNode;
  alerts: ReactNode;
  brief: ReactNode;
  decision: ReactNode;
  operations: ReactNode;
  findings: ReactNode;
  explorer: ReactNode;
  inbox: ReactNode;
  drawer: ReactNode;
  rail: ReactNode;
};

export function CommandLayout({
  header,
  alerts,
  brief,
  decision,
  operations,
  findings,
  explorer,
  inbox,
  drawer,
  rail,
}: CommandLayoutProps) {
  return (
    <section className="eiq-command-v3">
      <main className="eiq-command-v3__main">
        {header}
        {alerts}

        <section className="eiq-command-v3__grid">
          <div className="eiq-command-v3__primary">
            {brief}
            {decision}
            {operations}
            {findings}
            {explorer}
          </div>

          <div className="eiq-command-v3__activity">
            {inbox}
          </div>

          {drawer}
          {rail}
        </section>
      </main>
    </section>
  );
}
''', encoding="utf-8")

workspace = Path("src/edgeiq-os/command/EdgeiqCommandWorkspace.tsx")
text = workspace.read_text(encoding="utf-8")

if 'CommandLayout' not in text:
    text = text.replace(
        'import { ConfidenceTimeline } from "./components/ConfidenceTimeline";',
        'import { ConfidenceTimeline } from "./components/ConfidenceTimeline";\nimport { CommandLayout } from "./components/CommandLayout";'
    )

start = text.find('  return (')
end = text.rfind('\n  );\n}')
new_return = r'''  return (
    <CommandLayout
      header={
        <header className="eiq-command-live__header">
          <div>
            <h1>COMMAND</h1>
            <strong>{raceState.raceName}</strong>
            <p>
              Executive operations console · {raceState.decision.state} · {raceState.confidence}% confidence
            </p>
          </div>

          <LiveStatusStrip items={liveStatus} />
        </header>
      }
      alerts={<OperationalAlertsBar raceState={raceState} />}
      brief={<ExecutiveBriefPanel raceState={raceState} />}
      decision={<ExecutiveDecisionPanel summary={raceState.executiveSummary} />}
      operations={
        <section className="eiq-command-ops-grid">
          <EngineAgreementMatrix raceState={raceState} />
          <ConfidenceTimeline raceState={raceState} />
        </section>
      }
      findings={
        <section className="eiq-command-findings">
          <header>
            <span>Key Findings</span>
            <strong>{raceState.findings.length}</strong>
          </header>

          {raceState.findings.slice(0, 4).map((finding) => (
            <article key={finding.id}>
              <span>{finding.priority}</span>
              <strong>{finding.title}</strong>
              <p>{finding.summary}</p>
              <small>{finding.supportingEngines.join(" + ")}</small>
            </article>
          ))}
        </section>
      }
      explorer={
        <section className="eiq-command-evidence-groups">
          <header>
            <span>Intelligence Explorer</span>
            <strong>{raceState.evidence.length} items</strong>
          </header>

          <div className="eiq-command-evidence-list">
            {evidence.map((item) => (
              <button
                className={item === activeEvidence ? "is-active" : ""}
                type="button"
                key={item}
                onClick={() => setActiveEvidence(item)}
              >
                <span>› {item}</span>
                <small>Open evidence</small>
                <b>›</b>
              </button>
            ))}
          </div>
        </section>
      }
      inbox={<OperationalInbox events={raceState.events} />}
      drawer={
        <EvidenceDrawer
          activeEvidence={activeEvidence}
          evidence={raceState.evidence}
          onClose={() => setActiveEvidence("")}
        />
      }
      rail={<OperationalStateRail raceState={raceState} />}
    />
  );
}'''

if start != -1 and end != -1:
    text = text[:start] + new_return

workspace.write_text(text, encoding="utf-8")

css = Path("src/styles/edgeiqProductTerminalV1.css")
css_text = css.read_text(encoding="utf-8", errors="ignore")

addition = r'''

/* EDGEIQ OS V3 Command Layout Engine */
.eiq-command-v3 {
  min-height: 100%;
}

.eiq-command-v3__main {
  display: grid;
  gap: 16px;
}

.eiq-command-v3__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px 360px 280px;
  gap: 16px;
  align-items: start;
}

.eiq-command-v3__primary {
  display: grid;
  gap: 16px;
  min-width: 0;
}

.eiq-command-v3__activity {
  position: sticky;
  top: 18px;
}

.eiq-command-v3 .eiq-operational-inbox {
  min-height: 520px;
}

.eiq-command-v3 .eiq-command-drawer,
.eiq-command-v3 .eiq-command-rail {
  position: sticky;
  top: 18px;
}

.eiq-command-v3 .eiq-command-ops-grid {
  grid-template-columns: 1fr 1fr;
}

@media (max-width: 1500px) {
  .eiq-command-v3__grid {
    grid-template-columns: minmax(0, 1fr) 320px;
  }

  .eiq-command-v3__activity,
  .eiq-command-v3 .eiq-command-drawer,
  .eiq-command-v3 .eiq-command-rail {
    position: static;
  }
}
'''

if "EDGEIQ OS V3 Command Layout Engine" not in css_text:
    css_text += addition

css.write_text(css_text, encoding="utf-8")

print("[EDGEIQ] COMMAND Layout Engine V1 created and mounted")
