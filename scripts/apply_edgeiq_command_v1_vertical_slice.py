from pathlib import Path

root = Path.cwd()

service = root / "src/services/buildCommandExecutiveSummary.ts"

service.write_text(r'''export type CommandFindingTone = "info" | "opportunity" | "risk";

export type CommandFinding = {
  label: string;
  text: string;
  tone: CommandFindingTone;
};

export type CommandContender = {
  role: string;
  title: string;
  detail: string;
};

export type CommandRaceContext = {
  meeting?: string;
  race?: string;
  distance?: string;
  track?: string;
  rail?: string;
  jump?: string;
};

export type CommandExecutiveSummary = {
  assessment: string;
  findings: CommandFinding[];
  contenders: CommandContender[];
  market: {
    overlay: string;
    confidence: string;
    movement: string;
  };
  tactical: {
    speed: string;
    settle: string;
    close: string;
  };
  raceContextStrip?: string[];
};

export function buildCommandExecutiveSummary(raceContext?: CommandRaceContext): CommandExecutiveSummary {
  const hasRaceContext = Boolean(raceContext?.meeting || raceContext?.race);

  return {
    assessment: hasRaceContext
      ? `EDGEiQ COMMAND has assembled ${raceContext?.meeting ?? "the selected meeting"} ${raceContext?.race ?? "race"} into an executive intelligence briefing. The race should be read through tactical position, market behaviour, confidence, opportunity and risk rather than isolated ratings.`
      : "Select a race to activate the full EDGEiQ COMMAND briefing. The executive layer will translate race shape, market behaviour and runner evidence into a professional decision view.",
    findings: [
      {
        label: "Tactical Read",
        text: "The first read is race shape: early speed, settling positions, pressure and where the winning move is likely to form.",
        tone: "info",
      },
      {
        label: "Market Read",
        text: "The market assessment focuses on opportunity and mispricing without exposing EDGEiQ pricing calculations.",
        tone: "opportunity",
      },
      {
        label: "Risk Read",
        text: "Primary risk is separated from opportunity so users understand what could break the race scenario.",
        tone: "risk",
      },
    ],
    contenders: [
      {
        role: "Top Intelligence Call",
        title: "Primary race read",
        detail: "Reserved for the runner with the strongest combined intelligence profile once live race data is connected.",
      },
      {
        role: "Best Opportunity",
        title: "Market overlay",
        detail: "Reserved for the runner where current market price most clearly exceeds assessed opportunity.",
      },
      {
        role: "Main Risk",
        title: "Scenario threat",
        detail: "Reserved for the runner or race condition most likely to disrupt the expected shape.",
      },
    ],
    market: {
      overlay: "Awaiting live selection",
      confidence: "Awaiting live selection",
      movement: "Awaiting live selection",
    },
    tactical: {
      speed: "Barrier Speed",
      settle: "Settling Shape",
      close: "Closing Strength",
    },
    raceContextStrip: [
      raceContext?.meeting ?? "Meeting pending",
      raceContext?.race ?? "Race pending",
      raceContext?.distance ?? "Distance pending",
      raceContext?.track ?? "Track pending",
      raceContext?.rail ?? "Rail pending",
      raceContext?.jump ?? "Jump pending",
    ],
  };
}
''', encoding="utf-8")

component = root / "src/components/workspaces/RaceCommandExecutiveWorkspace.tsx"

component.write_text(r'''import { ReactNode } from "react";
import {
  buildCommandExecutiveSummary,
  type CommandExecutiveSummary,
} from "../../services/buildCommandExecutiveSummary";

type RaceCommandExecutiveWorkspaceProps = {
  legacyCommand?: ReactNode;
  summary?: CommandExecutiveSummary;
};

export function RaceCommandExecutiveWorkspace({
  legacyCommand,
  summary = buildCommandExecutiveSummary(),
}: RaceCommandExecutiveWorkspaceProps) {
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

      <section className="edgeiq-command-executive__context-strip">
        {summary.raceContextStrip?.map((item) => (
          <span key={item}>{item}</span>
        ))}
      </section>

      <section className="edgeiq-command-executive__assessment edgeiq-command-executive__assessment--premium">
        <div className="edgeiq-command-executive__label">Executive Assessment</div>
        <div className="edgeiq-command-executive__assessment-text">{summary.assessment}</div>
      </section>

      <section className="edgeiq-command-executive__command-flow">
        <article className="edgeiq-command-executive__panel edgeiq-command-executive__panel--findings">
          <div className="edgeiq-command-executive__label">Key Findings</div>
          <div className="edgeiq-command-executive__stack">
            {summary.findings.map((finding) => (
              <div className={`edgeiq-command-executive__finding is-${finding.tone}`} key={finding.label}>
                <span>{finding.label}</span>
                <strong>{finding.text}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="edgeiq-command-executive__panel edgeiq-command-executive__panel--tactical">
          <div className="edgeiq-command-executive__label">Tactical Projection</div>
          <div className="edgeiq-command-executive__tactical-board">
            <div className="edgeiq-command-executive__tactical-row">
              <span>01</span>
              <strong>{summary.tactical.speed}</strong>
              <em>Who crosses, who holds, who gets buried.</em>
            </div>
            <div className="edgeiq-command-executive__tactical-row">
              <span>02</span>
              <strong>{summary.tactical.settle}</strong>
              <em>Where the field is expected to organise.</em>
            </div>
            <div className="edgeiq-command-executive__tactical-row">
              <span>03</span>
              <strong>{summary.tactical.close}</strong>
              <em>Who is advantaged when the race turns for home.</em>
            </div>
          </div>
        </article>

        <article className="edgeiq-command-executive__panel edgeiq-command-executive__panel--market">
          <div className="edgeiq-command-executive__label">Market Assessment</div>
          <div className="edgeiq-command-executive__metric-row">
            <span>Overlay</span>
            <strong>{summary.market.overlay}</strong>
          </div>
          <div className="edgeiq-command-executive__metric-row">
            <span>Confidence</span>
            <strong>{summary.market.confidence}</strong>
          </div>
          <div className="edgeiq-command-executive__metric-row">
            <span>Movement</span>
            <strong>{summary.market.movement}</strong>
          </div>
        </article>

        <article className="edgeiq-command-executive__panel edgeiq-command-executive__panel--contenders">
          <div className="edgeiq-command-executive__label">Primary Contenders</div>
          <div className="edgeiq-command-executive__contender-grid">
            {summary.contenders.map((contender) => (
              <div className="edgeiq-command-executive__contender" key={contender.role}>
                <span>{contender.role}</span>
                <h3>{contender.title}</h3>
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
            <p>Existing COMMAND remains available during migration. No ratings, pricing, services or calculations were changed.</p>
          </div>
        </div>
        <div className="edgeiq-command-executive__legacy">{legacyCommand}</div>
      </section>
    </div>
  );
}
''', encoding="utf-8")

css = root / "src/components/shell/edgeiqOsShell.css"
text = css.read_text(encoding="utf-8")

if ".edgeiq-command-executive__command-flow" not in text:
    text += r'''

.edgeiq-command-executive__command-flow {
  display: grid;
  grid-template-columns: minmax(360px, 1.15fr) minmax(320px, 0.85fr);
  gap: 18px;
}

.edgeiq-command-executive__assessment--premium {
  background:
    linear-gradient(135deg, rgba(216, 184, 106, 0.075), transparent 62%),
    var(--edgeiq-panel);
}

.edgeiq-command-executive__panel--findings,
.edgeiq-command-executive__panel--contenders {
  grid-column: span 1;
}

.edgeiq-command-executive__panel--tactical,
.edgeiq-command-executive__panel--market {
  grid-column: span 1;
}

.edgeiq-command-executive__tactical-board {
  display: grid;
  gap: 12px;
  margin-top: 20px;
}

.edgeiq-command-executive__tactical-row {
  display: grid;
  grid-template-columns: 42px minmax(130px, 0.7fr) minmax(180px, 1fr);
  gap: 14px;
  align-items: center;
  border: 1px solid var(--edgeiq-border-muted);
  background: var(--edgeiq-bg-secondary);
  padding: 14px;
}

.edgeiq-command-executive__tactical-row span {
  color: var(--edgeiq-accent);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.14em;
}

.edgeiq-command-executive__tactical-row strong {
  color: var(--edgeiq-text);
  font-size: 13px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.edgeiq-command-executive__tactical-row em {
  color: var(--edgeiq-text-muted);
  font-size: 13px;
  font-style: normal;
  line-height: 1.35;
}

.edgeiq-command-executive__contender h3 {
  margin: 0;
  color: var(--edgeiq-text);
  font-size: 22px;
  letter-spacing: -0.04em;
}

@media (max-width: 1280px) {
  .edgeiq-command-executive__command-flow {
    grid-template-columns: 1fr;
  }

  .edgeiq-command-executive__tactical-row {
    grid-template-columns: 1fr;
  }
}
'''
    css.write_text(text, encoding="utf-8")

print("[EDGEIQ_COMMAND_V1] production COMMAND vertical slice applied")
