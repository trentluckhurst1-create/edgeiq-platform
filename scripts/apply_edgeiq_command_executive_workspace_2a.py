from pathlib import Path

root = Path.cwd()

component = root / "src/components/workspaces/RaceCommandExecutiveWorkspace.tsx"
component.write_text(r'''import { ReactNode } from "react";

type RaceCommandExecutiveWorkspaceProps = {
  legacyCommand?: ReactNode;
};

const findings = [
  "Race shape, market pressure and runner evidence will be surfaced here.",
  "This workspace will become the clean executive briefing for the selected race.",
  "Existing intelligence remains preserved while the OS rebuild progresses.",
];

const contenders = [
  "Primary contender intelligence",
  "Value opportunity intelligence",
  "Main risk intelligence",
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
        <div className="edgeiq-command-executive__state">Sprint 2A</div>
      </header>

      <section className="edgeiq-command-executive__assessment">
        <div className="edgeiq-command-executive__label">Executive Assessment</div>
        <div className="edgeiq-command-executive__assessment-text">
          EDGEiQ OS will summarise the race into a professional decision briefing here: tactical setup,
          market position, confidence, opportunity and risk.
        </div>
      </section>

      <section className="edgeiq-command-executive__grid">
        <article className="edgeiq-command-executive__panel">
          <div className="edgeiq-command-executive__label">Key Findings</div>
          <div className="edgeiq-command-executive__stack">
            {findings.map((finding) => (
              <div className="edgeiq-command-executive__finding" key={finding}>
                {finding}
              </div>
            ))}
          </div>
        </article>

        <article className="edgeiq-command-executive__panel">
          <div className="edgeiq-command-executive__label">Tactical Projection</div>
          <div className="edgeiq-command-executive__map-preview">
            <div className="edgeiq-command-executive__lane is-fast">Barrier Speed</div>
            <div className="edgeiq-command-executive__lane is-settle">Settling Position</div>
            <div className="edgeiq-command-executive__lane is-close">Closing Strength</div>
          </div>
        </article>

        <article className="edgeiq-command-executive__panel">
          <div className="edgeiq-command-executive__label">Market Assessment</div>
          <div className="edgeiq-command-executive__metric-row">
            <span>Overlay</span>
            <strong>Reserved</strong>
          </div>
          <div className="edgeiq-command-executive__metric-row">
            <span>Confidence</span>
            <strong>Reserved</strong>
          </div>
          <div className="edgeiq-command-executive__metric-row">
            <span>Movement</span>
            <strong>Reserved</strong>
          </div>
        </article>

        <article className="edgeiq-command-executive__panel">
          <div className="edgeiq-command-executive__label">Primary Contenders</div>
          <div className="edgeiq-command-executive__stack">
            {contenders.map((contender) => (
              <div className="edgeiq-command-executive__contender" key={contender}>
                {contender}
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="edgeiq-command-executive__evidence">
        <div className="edgeiq-command-executive__evidence-header">
          <div>
            <div className="edgeiq-command-executive__label">Supporting Evidence</div>
            <p>Existing COMMAND intelligence remains available while the executive briefing is rebuilt.</p>
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

router = root / "src/components/workspaces/EdgeiqWorkspaceRouter.tsx"
text = router.read_text(encoding="utf-8")

if 'RaceCommandExecutiveWorkspace' not in text:
    text = text.replace(
        'import { useEdgeiqOs } from "../../state/edgeiqOsStore";',
        'import { useEdgeiqOs } from "../../state/edgeiqOsStore";\nimport { RaceCommandExecutiveWorkspace } from "./RaceCommandExecutiveWorkspace";'
    )

text = text.replace(
'''  if (activeWorkspace === "COMMAND") {
    return <CommandWorkspaceFrame>{commandWorkspace}</CommandWorkspaceFrame>;
  }''',
'''  if (activeWorkspace === "COMMAND") {
    return (
      <CommandWorkspaceFrame>
        <RaceCommandExecutiveWorkspace legacyCommand={commandWorkspace} />
      </CommandWorkspaceFrame>
    );
  }'''
)

router.write_text(text, encoding="utf-8")

css = root / "src/components/shell/edgeiqOsShell.css"
css_text = css.read_text(encoding="utf-8")

if ".edgeiq-command-executive" not in css_text:
    css_text += r'''

.edgeiq-command-executive {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.edgeiq-command-executive__hero,
.edgeiq-command-executive__assessment,
.edgeiq-command-executive__panel,
.edgeiq-command-executive__evidence {
  border: 1px solid var(--edgeiq-border);
  background: var(--edgeiq-panel);
}

.edgeiq-command-executive__hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 22px;
  padding: 32px;
}

.edgeiq-command-executive__eyebrow,
.edgeiq-command-executive__label {
  color: var(--edgeiq-accent);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.edgeiq-command-executive__hero h1 {
  margin: 12px 0 0;
  color: var(--edgeiq-text);
  font-size: clamp(38px, 5vw, 68px);
  line-height: 0.9;
  letter-spacing: -0.07em;
}

.edgeiq-command-executive__hero p {
  margin: 18px 0 0;
  color: var(--edgeiq-text-secondary);
  font-size: 21px;
}

.edgeiq-command-executive__state {
  border: 1px solid var(--edgeiq-border);
  background: var(--edgeiq-bg-secondary);
  color: var(--edgeiq-text-muted);
  padding: 9px 12px;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  white-space: nowrap;
}

.edgeiq-command-executive__assessment {
  padding: 28px 32px;
}

.edgeiq-command-executive__assessment-text {
  max-width: 980px;
  margin-top: 16px;
  color: var(--edgeiq-text);
  font-size: 24px;
  line-height: 1.3;
  letter-spacing: -0.035em;
}

.edgeiq-command-executive__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(280px, 1fr));
  gap: 18px;
}

.edgeiq-command-executive__panel {
  padding: 24px;
  min-height: 260px;
}

.edgeiq-command-executive__stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 18px;
}

.edgeiq-command-executive__finding,
.edgeiq-command-executive__contender,
.edgeiq-command-executive__metric-row {
  border: 1px solid var(--edgeiq-border-muted);
  background: var(--edgeiq-bg-secondary);
  color: var(--edgeiq-text-secondary);
  padding: 13px 14px;
  font-size: 13px;
  line-height: 1.4;
}

.edgeiq-command-executive__contender {
  color: var(--edgeiq-text);
  font-weight: 700;
}

.edgeiq-command-executive__metric-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-top: 12px;
}

.edgeiq-command-executive__metric-row span {
  color: var(--edgeiq-text-muted);
}

.edgeiq-command-executive__metric-row strong {
  color: var(--edgeiq-text);
}

.edgeiq-command-executive__map-preview {
  margin-top: 20px;
  display: grid;
  gap: 12px;
}

.edgeiq-command-executive__lane {
  min-height: 48px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  border: 1px solid var(--edgeiq-border-muted);
  background: var(--edgeiq-bg-secondary);
  color: var(--edgeiq-text-secondary);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.edgeiq-command-executive__lane.is-fast {
  border-left: 3px solid var(--edgeiq-info);
}

.edgeiq-command-executive__lane.is-settle {
  border-left: 3px solid var(--edgeiq-warning);
}

.edgeiq-command-executive__lane.is-close {
  border-left: 3px solid var(--edgeiq-success);
}

.edgeiq-command-executive__evidence {
  padding: 24px;
}

.edgeiq-command-executive__evidence-header {
  margin-bottom: 18px;
}

.edgeiq-command-executive__evidence-header p {
  margin: 10px 0 0;
  color: var(--edgeiq-text-muted);
  font-size: 13px;
}

.edgeiq-command-executive__legacy {
  border-top: 1px solid var(--edgeiq-border-muted);
  padding-top: 18px;
}

@media (max-width: 1200px) {
  .edgeiq-command-executive__grid {
    grid-template-columns: 1fr;
  }
}
'''
    css.write_text(css_text, encoding="utf-8")

print("[EDGEIQ_COMMAND_EXECUTIVE_WORKSPACE] Sprint 2A component created and routed")
