import { ReactNode } from "react";
import { useEdgeiqOs } from "../../state/edgeiqOsStore";
import { RaceCommandExecutiveWorkspace } from "./RaceCommandExecutiveWorkspace";
import { buildCommandExecutiveSummary } from "../../services/buildCommandExecutiveSummary";

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

function CommandWorkspaceFrame({ children }: { children: ReactNode }) {
  return (
    <div className="edgeiq-command-frame">
      <div className="edgeiq-command-frame__header">
        <div>
          <div className="edgeiq-command-frame__eyebrow">RACE COMMAND</div>
          <h1>Executive Race Briefing</h1>
          <p>What is this race telling me?</p>
        </div>
        <div className="edgeiq-command-frame__status">Live Intelligence</div>
      </div>

      <div className="edgeiq-command-frame__notice">
        Existing COMMAND intelligence is preserved here while the EDGEiQ OS executive briefing is rebuilt.
      </div>

      <div className="edgeiq-command-frame__legacy">
        {children}
      </div>
    </div>
  );
}

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
  const { activeSection, activeWorkspace, raceContext } = useEdgeiqOs();
  const commandSummary = buildCommandExecutiveSummary(raceContext);

  if (activeSection !== "RACES") {
    return <WorkspaceShell spec={workspaceSpecs[activeSection]} />;
  }

  if (activeWorkspace === "COMMAND") {
    return (
      <RaceCommandExecutiveWorkspace summary={commandSummary} />
    );
  }

  return <WorkspaceShell spec={workspaceSpecs[activeWorkspace]} />;
}
