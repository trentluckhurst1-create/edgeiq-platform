from pathlib import Path

service = Path("src/edgeiq-os/services/decision-timeline.ts")
component = Path("src/edgeiq-os/command/components/DecisionTimeline.tsx")
command = Path("src/edgeiq-os/command/EdgeiqCommandWorkspace.tsx")
css = Path("src/styles/edgeiqProductTerminalV1.css")

service.write_text(r'''
import type { OperationalRaceState } from "./operational-state";
import { formatDecisionState, formatConfidenceLabel, formatIntelligenceStatus } from "../design-system";

export type DecisionTimelineEvent = {
  id: string;
  time: string;
  title: string;
  summary: string;
  status: string;
};

export type DecisionTimelineModel = {
  title: string;
  decision: string;
  confidence: string;
  events: DecisionTimelineEvent[];
};

function fallbackTime(index: number): string {
  const base = 9 * 60;
  const minutes = base + index * 7;
  const hh = Math.floor(minutes / 60).toString().padStart(2, "0");
  const mm = (minutes % 60).toString().padStart(2, "0");
  return `${hh}:${mm}`;
}

export function buildDecisionTimeline(raceState: OperationalRaceState): DecisionTimelineModel {
  const feedEvents = raceState.feedHealth.slice(0, 6).map((feed, index) => ({
    id: `feed-${feed.key}`,
    time: fallbackTime(index),
    title: feed.label,
    summary: feed.status === "READY"
      ? `${feed.label} is contributing to the current operational view.`
      : `${feed.label} remains under observation.`,
    status: formatIntelligenceStatus(feed.status),
  }));

  const operationalEvents = raceState.events.slice(0, 3).map((event, index) => ({
    id: `event-${event.id}`,
    time: event.time || fallbackTime(feedEvents.length + index),
    title: event.title,
    summary: event.detail,
    status: event.severity,
  }));

  return {
    title: "Decision Timeline",
    decision: formatDecisionState(raceState.decision.state),
    confidence: formatConfidenceLabel(raceState.confidence),
    events: [
      ...feedEvents,
      ...operationalEvents,
      {
        id: "current-decision",
        time: "Now",
        title: formatDecisionState(raceState.decision.state),
        summary: `${formatConfidenceLabel(raceState.confidence)} confidence. Current position remains active until the next material confirmation signal.`,
        status: "Current Position",
      },
    ],
  };
}
'''.lstrip(), encoding="utf-8")

component.write_text(r'''
import type { DecisionTimelineModel } from "../../services/decision-timeline";

type DecisionTimelineProps = {
  timeline: DecisionTimelineModel;
};

export function DecisionTimeline({ timeline }: DecisionTimelineProps) {
  return (
    <section className="eiq-decision-timeline">
      <header>
        <span>Evolution</span>
        <strong>{timeline.title}</strong>
      </header>

      <div className="eiq-decision-timeline__track">
        {timeline.events.map((event) => (
          <article key={event.id}>
            <time>{event.time}</time>
            <div>
              <span>{event.status}</span>
              <strong>{event.title}</strong>
              <p>{event.summary}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
'''.lstrip(), encoding="utf-8")

text = command.read_text(encoding="utf-8")

if 'buildDecisionTimeline' not in text:
    text = text.replace(
        'import { AssessmentJourney } from "./components/AssessmentJourney";',
        '''import { AssessmentJourney } from "./components/AssessmentJourney";
import { DecisionTimeline } from "./components/DecisionTimeline";'''
    )

    text = text.replace(
        'import { buildAssessmentJourney } from "../services/assessment-journey";',
        '''import { buildAssessmentJourney } from "../services/assessment-journey";
import { buildDecisionTimeline } from "../services/decision-timeline";'''
    )

    text = text.replace(
        'const assessmentJourney = buildAssessmentJourney(raceState);',
        '''const assessmentJourney = buildAssessmentJourney(raceState);
const decisionTimeline = buildDecisionTimeline(raceState);'''
    )

    text = text.replace(
        '''          <section className="eiq-command-v4__section">
            <header className="eiq-command-v4__section-head">
              <span>Live Operations</span>
              <strong>{raceState.events.length} updates</strong>
            </header>
            <OperationalInbox events={raceState.events} />
          </section>''',
        '''          <DecisionTimeline timeline={decisionTimeline} />

          <section className="eiq-command-v4__section">
            <header className="eiq-command-v4__section-head">
              <span>Live Operations</span>
              <strong>{raceState.events.length} updates</strong>
            </header>
            <OperationalInbox events={raceState.events} />
          </section>'''
    )

command.write_text(text, encoding="utf-8")

css_block = r'''

/* ==========================================================================
   EDGEiQ COMMAND V7 — Decision Timeline
   ========================================================================== */

.eiq-decision-timeline {
  padding: 34px 0 36px;
  border-bottom: 1px solid rgba(246, 243, 234, 0.10);
}

.eiq-decision-timeline > header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 22px;
}

.eiq-decision-timeline > header span,
.eiq-decision-timeline__track article span {
  display: block;
  color: rgba(246, 243, 234, 0.46);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.15em;
  text-transform: uppercase;
}

.eiq-decision-timeline > header strong {
  color: #f6f3ea;
  font-size: 25px;
  letter-spacing: -0.045em;
}

.eiq-decision-timeline__track {
  display: grid;
  gap: 0;
}

.eiq-decision-timeline__track article {
  display: grid;
  grid-template-columns: 76px minmax(0, 1fr);
  gap: 18px;
  padding: 17px 0;
  border-top: 1px solid rgba(246, 243, 234, 0.085);
}

.eiq-decision-timeline__track time {
  color: rgba(246, 243, 234, 0.58);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eiq-decision-timeline__track article strong {
  display: block;
  margin-top: 6px;
  color: #f6f3ea;
  font-size: 16px;
  letter-spacing: -0.03em;
}

.eiq-decision-timeline__track article p {
  max-width: 820px;
  margin: 8px 0 0;
  color: rgba(246, 243, 234, 0.62);
  font-size: 13px;
  line-height: 1.55;
}
'''

css.write_text(css.read_text(encoding="utf-8") + css_block, encoding="utf-8")

print("[EDGEIQ] COMMAND V7 decision timeline built")
