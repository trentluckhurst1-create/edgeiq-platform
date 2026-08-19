from pathlib import Path

service = Path("src/edgeiq-os/services/assessment-journey.ts")
command = Path("src/edgeiq-os/command/EdgeiqCommandWorkspace.tsx")
component = Path("src/edgeiq-os/command/components/AssessmentJourney.tsx")
css = Path("src/styles/edgeiqProductTerminalV1.css")

service.write_text(r'''
import type { OperationalRaceState, IntelligenceStatus } from "./operational-state";
import { formatDecisionState, formatConfidenceLabel } from "../design-system";

export type AssessmentJourneyStage = {
  id: string;
  label: string;
  status: IntelligenceStatus;
  summary: string;
  confidence: string;
  watch: string;
};

export type AssessmentJourneyModel = {
  title: string;
  decision: string;
  confidence: string;
  stages: AssessmentJourneyStage[];
};

function findStatus(raceState: OperationalRaceState, labels: string[]): IntelligenceStatus {
  const match = raceState.feedHealth.find((engine) =>
    labels.some((label) => engine.label.toLowerCase().includes(label.toLowerCase()))
  );

  return match?.status ?? "PARTIAL";
}

function statusSummary(status: IntelligenceStatus, ready: string, pending: string): string {
  return status === "READY" ? ready : pending;
}

export function buildAssessmentJourney(raceState: OperationalRaceState): AssessmentJourneyModel {
  const raceShapeStatus = findStatus(raceState, ["shape", "pace"]);
  const runnerStatus = findStatus(raceState, ["runner", "dna", "profile"]);
  const environmentStatus = findStatus(raceState, ["track", "weather", "environment"]);
  const marketStatus = findStatus(raceState, ["market"]);

  return {
    title: "Assessment Journey",
    decision: formatDecisionState(raceState.decision.state),
    confidence: formatConfidenceLabel(raceState.confidence),
    stages: [
      {
        id: "race-shape",
        label: "Race Shape",
        status: raceShapeStatus,
        summary: statusSummary(
          raceShapeStatus,
          "Pace intelligence is contributing to the current operational view.",
          "Race shape intelligence is still building."
        ),
        confidence: raceShapeStatus === "READY" ? "High" : "Developing",
        watch: "Late tempo changes or scratchings that alter pressure.",
      },
      {
        id: "runner-intelligence",
        label: "Runner Intelligence",
        status: runnerStatus,
        summary: statusSummary(
          runnerStatus,
          "Runner profile intelligence is reinforcing the assessment.",
          "Runner profile intelligence is awaiting further confirmation."
        ),
        confidence: runnerStatus === "READY" ? "High" : "Developing",
        watch: "Profile mismatches against today's race conditions.",
      },
      {
        id: "environment",
        label: "Track & Environment",
        status: environmentStatus,
        summary: statusSummary(
          environmentStatus,
          "Environment intelligence is aligned with the current assessment.",
          "Track and weather intelligence remain under observation."
        ),
        confidence: environmentStatus === "READY" ? "High" : "Developing",
        watch: "Track downgrade, rainfall or rail pattern changes.",
      },
      {
        id: "market",
        label: "Market Behaviour",
        status: marketStatus,
        summary: statusSummary(
          marketStatus,
          "Market intelligence is available for validation.",
          "Market confirmation has not yet fully aligned with the assessment."
        ),
        confidence: marketStatus === "READY" ? "Moderate" : "Developing",
        watch: "Late support, drift or disagreement with the operational view.",
      },
    ],
  };
}
'''.lstrip(), encoding="utf-8")

component.write_text(r'''
import type { AssessmentJourneyModel } from "../../services/assessment-journey";
import { formatIntelligenceStatus } from "../../design-system";

type AssessmentJourneyProps = {
  journey: AssessmentJourneyModel;
};

function marker(status: string): string {
  return status === "READY" ? "✓" : "○";
}

export function AssessmentJourney({ journey }: AssessmentJourneyProps) {
  return (
    <section className="eiq-assessment-journey">
      <header>
        <span>Reasoning</span>
        <strong>{journey.title}</strong>
      </header>

      <div className="eiq-assessment-journey__path">
        {journey.stages.map((stage) => (
          <article key={stage.id}>
            <div className="eiq-assessment-journey__marker">{marker(stage.status)}</div>
            <div>
              <span>{formatIntelligenceStatus(stage.status)}</span>
              <strong>{stage.label}</strong>
              <p>{stage.summary}</p>
              <small>Watch: {stage.watch}</small>
            </div>
          </article>
        ))}

        <article className="is-decision">
          <div className="eiq-assessment-journey__marker">◎</div>
          <div>
            <span>Current Position</span>
            <strong>{journey.decision}</strong>
            <p>{journey.confidence} confidence. Maintain focus on the next material confirmation signal.</p>
          </div>
        </article>
      </div>
    </section>
  );
}
'''.lstrip(), encoding="utf-8")

text = command.read_text(encoding="utf-8")

if 'buildAssessmentJourney' not in text:
    text = text.replace(
        'import { OperationsRailV2 } from "./components/OperationsRailV2";',
        '''import { OperationsRailV2 } from "./components/OperationsRailV2";
import { AssessmentJourney } from "./components/AssessmentJourney";'''
    )

    text = text.replace(
        'import { getOperationalRaceState } from "../services/intelligence-orchestrator";',
        '''import { getOperationalRaceState } from "../services/intelligence-orchestrator";
import { buildAssessmentJourney } from "../services/assessment-journey";'''
    )

    text = text.replace(
        'const raceState = getOperationalRaceState();',
        '''const raceState = getOperationalRaceState();
const assessmentJourney = buildAssessmentJourney(raceState);'''
    )

    text = text.replace(
        '''          <section className="eiq-command-v4__section">
            <header className="eiq-command-v4__section-head">
              <span>Key Intelligence</span>
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
          </section>''',
        '''          <AssessmentJourney journey={assessmentJourney} />

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
          </section>'''
    )

command.write_text(text, encoding="utf-8")

css_block = r'''

/* ==========================================================================
   EDGEiQ COMMAND V6 — Assessment Journey
   ========================================================================== */

.eiq-assessment-journey {
  padding: 34px 0 36px;
  border-bottom: 1px solid rgba(246, 243, 234, 0.10);
}

.eiq-assessment-journey > header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 22px;
}

.eiq-assessment-journey > header span,
.eiq-assessment-journey__path article span {
  display: block;
  color: rgba(246, 243, 234, 0.46);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.15em;
  text-transform: uppercase;
}

.eiq-assessment-journey > header strong {
  color: #f6f3ea;
  font-size: 25px;
  letter-spacing: -0.045em;
}

.eiq-assessment-journey__path {
  display: grid;
  gap: 0;
}

.eiq-assessment-journey__path article {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr);
  gap: 16px;
  padding: 18px 0;
  border-top: 1px solid rgba(246, 243, 234, 0.085);
}

.eiq-assessment-journey__path article.is-decision {
  margin-top: 8px;
  border-top-color: rgba(246, 243, 234, 0.18);
}

.eiq-assessment-journey__marker {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  color: #f6f3ea;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(246, 243, 234, 0.12);
  border-radius: 999px;
  font-size: 13px;
  font-weight: 900;
}

.eiq-assessment-journey__path article strong {
  display: block;
  margin-top: 6px;
  color: #f6f3ea;
  font-size: 18px;
  letter-spacing: -0.035em;
}

.eiq-assessment-journey__path article p {
  max-width: 850px;
  margin: 8px 0 0;
  color: rgba(246, 243, 234, 0.67);
  font-size: 14px;
  line-height: 1.58;
}

.eiq-assessment-journey__path article small {
  display: block;
  margin-top: 8px;
  color: rgba(246, 243, 234, 0.48);
  font-size: 12px;
  line-height: 1.45;
}
'''

css.write_text(css.read_text(encoding="utf-8") + css_block, encoding="utf-8")

print("[EDGEIQ] COMMAND V6 assessment journey built")
