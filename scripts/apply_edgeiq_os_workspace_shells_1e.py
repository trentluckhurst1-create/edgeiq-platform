from pathlib import Path

root = Path.cwd()

router = root / "src/components/workspaces/EdgeiqWorkspaceRouter.tsx"

router.write_text(r'''import { ReactNode } from "react";
import { useEdgeiqOs } from "../../state/edgeiqOsStore";

type EdgeiqWorkspaceRouterProps = {
  commandWorkspace: ReactNode;
};

type WorkspaceSpec = {
  title: string;
  question: string;
  sections: string[];
  status: string;
};

const workspaceSpecs: Record<string, WorkspaceSpec> = {
  HOME: {
    title: "HOME",
    question: "What is happening today?",
    status: "Mission Control reserved for today’s racing intelligence.",
    sections: ["Today's Meetings", "Highest Confidence", "Largest Overlay", "Track Alerts", "Model Health"],
  },
  TODAY: {
    title: "TODAY",
    question: "Which races matter right now?",
    status: "Today workspace reserved for meeting and race prioritisation.",
    sections: ["Meeting Queue", "Race Timeline", "Confidence Watch", "Alerts", "Feed Status"],
  },
  FIELD: {
    title: "FIELD",
    question: "What do I know about every runner?",
    status: "Runner Intelligence workspace reserved for dossier buildout.",
    sections: ["Runner Dossiers", "Strengths", "Risks", "Map Fit", "Market Fit"],
  },
  MAP: {
    title: "MAP",
    question: "How will this race unfold?",
    status: "EDGEiQ Tactical Map workspace reserved for tactical visualisation.",
    sections: ["Barrier Speed", "Settling Position", "Closing Speed", "Pace Pressure", "Track Bias"],
  },
  MARKET: {
    title: "MARKET",
    question: "Where is the market wrong?",
    status: "Trading Intelligence workspace reserved for overlay and movement analysis.",
    sections: ["Live Market", "EDGEiQ Price", "Overlay", "Movement", "Confidence", "Liquidity"],
  },
  PERFORMANCE: {
    title: "PERFORMANCE",
    question: "Why is this horse rated here?",
    status: "Explainability workspace reserved for evidence without exposing calculations.",
    sections: ["Rating Position", "Strength Drivers", "Risk Drivers", "Trend", "Similar Profiles"],
  },
  CONDITIONS: {
    title: "CONDITIONS",
    question: "What external factors matter?",
    status: "Conditions workspace reserved for track, rail, weather, wind and bias intelligence.",
    sections: ["Track", "Rail", "Weather", "Wind", "Bias", "Race Impact"],
  },
  RESULTS: {
    title: "RESULTS",
    question: "Did reality match the projection?",
    status: "Replay workspace reserved for post-race model review.",
    sections: ["Expected Shape", "Actual Shape", "Winner Profile", "Market Accuracy", "Learning Notes"],
  },
  LAB: {
    title: "LAB",
    question: "What happens if assumptions change?",
    status: "Scenario workspace reserved for premium simulation features.",
    sections: ["Tempo", "Rail", "Bias", "Runner Removal", "Track Change", "Updated Projection"],
  },
  SETTINGS: {
    title: "SETTINGS",
    question: "How should EDGEiQ OS behave for this user?",
    status: "Settings workspace reserved for preferences and account controls.",
    sections: ["Theme", "Display", "Notifications", "Workspace Defaults", "Account"],
  },
};

function WorkspaceShell({ spec }: { spec: WorkspaceSpec }) {
  return (
    <div className="edgeiq-workspace-shell">
      <div className="edgeiq-workspace-shell__header">
        <div>
          <div className="edgeiq-workspace-shell__eyebrow">EDGEiQ OS WORKSPACE</div>
          <h1>{spec.title}</h1>
          <p>{spec.question}</p>
        </div>
        <div className="edgeiq-workspace-shell__badge">Reserved</div>
      </div>

      <div className="edgeiq-workspace-shell__body">
        <section className="edgeiq-workspace-shell__brief">
          <div className="edgeiq-workspace-shell__label">Workspace intent</div>
          <div className="edgeiq-workspace-shell__statement">{spec.status}</div>
        </section>

        <section className="edgeiq-workspace-shell__grid">
          {spec.sections.map((section) => (
            <article className="edgeiq-workspace-shell__module" key={section}>
              <div className="edgeiq-workspace-shell__module-title">{section}</div>
              <div className="edgeiq-workspace-shell__module-line" />
              <div className="edgeiq-workspace-shell__module-text">
                Future EDGEiQ OS module. Intelligence layer remains unchanged.
              </div>
            </article>
          ))}
        </section>
      </div>
    </div>
  );
}

export function EdgeiqWorkspaceRouter({ commandWorkspace }: EdgeiqWorkspaceRouterProps) {
  const { activeSection, activeWorkspace } = useEdgeiqOs();

  if (activeSection !== "RACES") {
    return <WorkspaceShell spec={workspaceSpecs[activeSection]} />;
  }

  if (activeWorkspace === "COMMAND") {
    return <>{commandWorkspace}</>;
  }

  return <WorkspaceShell spec={workspaceSpecs[activeWorkspace]} />;
}
''', encoding="utf-8")

css = root / "src/components/shell/edgeiqOsShell.css"
text = css.read_text(encoding="utf-8")

if ".edgeiq-workspace-shell" not in text:
    text += r'''

.edgeiq-workspace-shell {
  padding: 42px;
  min-height: 100%;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.025), transparent 260px),
    var(--edgeiq-bg);
}

.edgeiq-workspace-shell__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding-bottom: 30px;
  border-bottom: 1px solid var(--edgeiq-border);
}

.edgeiq-workspace-shell__eyebrow {
  color: var(--edgeiq-accent);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.2em;
  margin-bottom: 14px;
}

.edgeiq-workspace-shell h1 {
  margin: 0;
  color: var(--edgeiq-text);
  font-size: clamp(42px, 5vw, 72px);
  line-height: 0.9;
  letter-spacing: -0.07em;
}

.edgeiq-workspace-shell p {
  max-width: 760px;
  margin: 18px 0 0;
  color: var(--edgeiq-text-secondary);
  font-size: 22px;
  line-height: 1.35;
}

.edgeiq-workspace-shell__badge {
  border: 1px solid var(--edgeiq-border);
  background: var(--edgeiq-panel);
  color: var(--edgeiq-text-muted);
  padding: 9px 12px;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.edgeiq-workspace-shell__body {
  display: grid;
  grid-template-columns: minmax(260px, 360px) minmax(0, 1fr);
  gap: 24px;
  margin-top: 26px;
}

.edgeiq-workspace-shell__brief,
.edgeiq-workspace-shell__module {
  border: 1px solid var(--edgeiq-border);
  background: var(--edgeiq-panel);
}

.edgeiq-workspace-shell__brief {
  padding: 24px;
  min-height: 260px;
}

.edgeiq-workspace-shell__label {
  color: var(--edgeiq-text-muted);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  margin-bottom: 18px;
}

.edgeiq-workspace-shell__statement {
  color: var(--edgeiq-text);
  font-size: 20px;
  line-height: 1.35;
  letter-spacing: -0.02em;
}

.edgeiq-workspace-shell__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(220px, 1fr));
  gap: 14px;
}

.edgeiq-workspace-shell__module {
  min-height: 150px;
  padding: 20px;
}

.edgeiq-workspace-shell__module-title {
  color: var(--edgeiq-text);
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.edgeiq-workspace-shell__module-line {
  height: 1px;
  background: var(--edgeiq-border-muted);
  margin: 16px 0;
}

.edgeiq-workspace-shell__module-text {
  color: var(--edgeiq-text-muted);
  font-size: 13px;
  line-height: 1.45;
}

@media (max-width: 1100px) {
  .edgeiq-workspace-shell__body {
    grid-template-columns: 1fr;
  }

  .edgeiq-workspace-shell__grid {
    grid-template-columns: 1fr;
  }
}
'''
    css.write_text(text, encoding="utf-8")

print("[EDGEIQ_OS_WORKSPACE_SHELLS] professional placeholder workspace shells applied")
