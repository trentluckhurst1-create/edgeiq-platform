import { useState } from "react";
import { LiveStatusStrip } from "./components/LiveStatusStrip";
import { UnifiedCommandBrief } from "./components/UnifiedCommandBrief";
import { CommandExecutiveBrief } from "./components/CommandExecutiveBrief";
import { CommandOperationalStack } from "./components/CommandOperationalStack";
import { IntelligenceExplorer } from "./components/IntelligenceExplorer";
import { EvidenceWorkspace } from "./components/EvidenceWorkspace";
import { OperationalInbox } from "./components/OperationalInbox";
import { OperationalAlertsBar } from "./components/OperationalAlertsBar";
import { OperationsRailV2 } from "./components/OperationsRailV2";
import { DecisionTimeline } from "./components/DecisionTimeline";

import { getOperationalRaceState } from "../services/intelligence-orchestrator";
import { buildAssessmentJourney } from "../services/assessment-journey";
import { buildDecisionTimeline } from "../services/decision-timeline";

const raceState = getOperationalRaceState();
const assessmentJourney = buildAssessmentJourney(raceState);
const decisionTimeline = buildDecisionTimeline(raceState);

const liveStatus = [
  { label: "Decision", value: raceState.decision.state, tone: "info" },
  { label: "Confidence", value: `${raceState.confidence}%`, tone: "good" },
  { label: "Consensus", value: raceState.correlation.agreementBand, tone: "neutral" },
  {
    label: "Engines",
    value: `${raceState.executiveSummary.systemHealth.feedsReady}/${raceState.executiveSummary.systemHealth.feedsTotal}`,
    tone: "info",
  },
];

export function EdgeiqCommandWorkspace() {
  const [activeEvidence, setActiveEvidence] = useState<string>(raceState.evidence[0]?.title ?? "");

  return (
    <section className="eiq-command-v4">
      <header className="eiq-command-v4__hero">
        <div>
          <span className="eiq-command-v4__eyebrow">Victoria Racing Intelligence</span>
          <h1>RACE DESK</h1>
          <p>{raceState.raceName}</p>
        </div>

        <LiveStatusStrip items={liveStatus} />
      </header>

      <OperationalAlertsBar raceState={raceState} />

      <main className="eiq-command-v4__layout">
        <section className="eiq-command-v4__main">
          <UnifiedCommandBrief raceState={raceState} />

          <CommandExecutiveBrief raceState={raceState} />

          <CommandOperationalStack raceState={raceState} journey={assessmentJourney} />

          <section className="eiq-command-v4__section">
            <header className="eiq-command-v4__section-head">
              <span>Decision Drivers</span>
              <strong>{raceState.findings.length} active observations</strong>
            </header>

            <div className="eiq-command-v4__findings">
              {raceState.findings.slice(0, 4).map((finding) => (
                <article key={finding.id}>
                  <span>{finding.priority}</span>
                  <strong>{finding.title}</strong>
                  <p>{finding.summary}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="eiq-command-v4__workbench">
            <IntelligenceExplorer
              raceState={raceState}
              activeEvidence={activeEvidence}
              onSelect={setActiveEvidence}
            />

            <EvidenceWorkspace evidence={raceState.evidence} activeEvidence={activeEvidence} />
          </section>

          <DecisionTimeline timeline={decisionTimeline} />

          <section className="eiq-command-v4__section">
            <header className="eiq-command-v4__section-head">
              <span>Live Operations</span>
              <strong>{raceState.events.length} updates</strong>
            </header>
            <OperationalInbox events={raceState.events} />
          </section>
        </section>

        <aside className="eiq-command-v4__rail">
          <OperationsRailV2 raceState={raceState} />
        </aside>
      </main>
    </section>
  );
}
