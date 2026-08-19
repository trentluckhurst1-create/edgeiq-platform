from pathlib import Path

root = Path.cwd()
path = root / "src/components/workspaces/RaceCommandExecutiveWorkspace.tsx"

path.write_text(r'''import { ReactNode } from "react";

type RaceCommandExecutiveWorkspaceProps = {
  legacyCommand?: ReactNode;
};

const executiveFindings = [
  {
    label: "Race Shape",
    text: "Tactical setup will be summarised here from existing EDGEiQ intelligence feeds.",
    tone: "info",
  },
  {
    label: "Market Position",
    text: "Overlay, price movement and confidence signals will be surfaced without exposing calculations.",
    tone: "opportunity",
  },
  {
    label: "Risk Profile",
    text: "Primary race risks will be translated into plain professional intelligence.",
    tone: "risk",
  },
];

const primaryContenders = [
  {
    role: "Top Intelligence Call",
    detail: "Reserved for selected race leader from existing command summary.",
  },
  {
    role: "Best Overlay",
    detail: "Reserved for value opportunity from current market intelligence.",
  },
  {
    role: "Main Watch",
    detail: "Reserved for key tactical or confidence risk.",
  },
];

export function RaceCommandExecutiveWorkspace({ legacyCommand }: RaceCommandExecutiveWorkspaceProps) {
  return (
    <div className="edgeiq-command-executive">
      <header className="edgeiq-command-executive__hero">
        <div>
          <div className="edgeiq-command-executive__eyebrow">COMMAND</div>
          <h1>Executive Race Briefing</h1>
          <p>What is this race telling me?</p>
        </div>
        <div className="edgeiq-command-executive__state">Live Intelligence</div>
      </header>

      <section className="edgeiq-command-executive__assessment">
        <div className="edgeiq-command-executive__label">Executive Assessment</div>
        <div className="edgeiq-command-executive__assessment-text">
          EDGEiQ COMMAND converts race shape, market behaviour, confidence, opportunity and risk into a single
          professional race briefing.
        </div>
      </section>

      <section className="edgeiq-command-executive__grid">
        <article className="edgeiq-command-executive__panel edgeiq-command-executive__panel--wide">
          <div className="edgeiq-command-executive__label">Key Findings</div>
          <div className="edgeiq-command-executive__stack">
            {executiveFindings.map((finding) => (
              <div className={`edgeiq-command-executive__finding is-${finding.tone}`} key={finding.label}>
                <span>{finding.label}</span>
                <strong>{finding.text}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="edgeiq-command-executive__panel">
          <div className="edgeiq-command-executive__label">Tactical Projection</div>
          <div className="edgeiq-command-executive__map-preview">
            <div className="edgeiq-command-executive__lane is-fast">
              <span>01</span>
              <strong>Barrier Speed</strong>
            </div>
            <div className="edgeiq-command-executive__lane is-settle">
              <span>02</span>
              <strong>Settling Shape</strong>
            </div>
            <div className="edgeiq-command-executive__lane is-close">
              <span>03</span>
              <strong>Closing Strength</strong>
            </div>
          </div>
        </article>

        <article className="edgeiq-command-executive__panel">
          <div className="edgeiq-command-executive__label">Market Assessment</div>
          <div className="edgeiq-command-executive__metric-row">
            <span>Overlay</span>
            <strong>Awaiting race context</strong>
          </div>
          <div className="edgeiq-command-executive__metric-row">
            <span>Confidence</span>
            <strong>Awaiting race context</strong>
          </div>
          <div className="edgeiq-command-executive__metric-row">
            <span>Movement</span>
            <strong>Awaiting race context</strong>
          </div>
        </article>

        <article className="edgeiq-command-executive__panel edgeiq-command-executive__panel--wide">
          <div className="edgeiq-command-executive__label">Primary Contenders</div>
          <div className="edgeiq-command-executive__contender-grid">
            {primaryContenders.map((contender) => (
              <div className="edgeiq-command-executive__contender" key={contender.role}>
                <span>{contender.role}</span>
                <strong>{contender.detail}</strong>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="edgeiq-command-executive__evidence">
        <div className="edgeiq-command-executive__evidence-header">
          <div>
            <div className="edgeiq-command-executive__label">Supporting Evidence</div>
            <p>Legacy COMMAND remains available during migration. No ratings, pricing, services or calculations were changed.</p>
          </div>
        </div>
        <div className="edgeiq-command-executive__legacy">
          {legacyCommand}
        </div>
      </section>
    </div>
  );
}
''', encoding="utf-8")

css = root / "src/components/shell/edgeiqOsShell.css"
text = css.read_text(encoding="utf-8")

add = r'''

.edgeiq-command-executive__panel--wide {
  grid-column: span 2;
}

.edgeiq-command-executive__finding {
  display: grid;
  grid-template-columns: 160px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.edgeiq-command-executive__finding span,
.edgeiq-command-executive__contender span {
  color: var(--edgeiq-text-muted);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.edgeiq-command-executive__finding strong,
.edgeiq-command-executive__contender strong {
  color: var(--edgeiq-text);
  font-size: 14px;
  line-height: 1.45;
}

.edgeiq-command-executive__finding.is-info {
  border-left: 3px solid var(--edgeiq-info);
}

.edgeiq-command-executive__finding.is-opportunity {
  border-left: 3px solid var(--edgeiq-success);
}

.edgeiq-command-executive__finding.is-risk {
  border-left: 3px solid var(--edgeiq-danger);
}

.edgeiq-command-executive__lane {
  justify-content: space-between;
}

.edgeiq-command-executive__lane span {
  color: var(--edgeiq-text-muted);
}

.edgeiq-command-executive__lane strong {
  color: var(--edgeiq-text);
}

.edgeiq-command-executive__contender-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(180px, 1fr));
  gap: 12px;
  margin-top: 18px;
}

.edgeiq-command-executive__contender {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 130px;
}

@media (max-width: 1200px) {
  .edgeiq-command-executive__panel--wide {
    grid-column: span 1;
  }

  .edgeiq-command-executive__contender-grid {
    grid-template-columns: 1fr;
  }

  .edgeiq-command-executive__finding {
    grid-template-columns: 1fr;
  }
}
'''

if "edgeiq-command-executive__panel--wide" not in text:
    css.write_text(text + add, encoding="utf-8")

print("[EDGEIQ_COMMAND_2B] COMMAND executive layout hardened")
