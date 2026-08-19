import type { OperationalRaceState } from "../../services/operational-state";
import { composeExecutiveBrief } from "../../services/executive-brief";
import { formatDecisionState, formatPriority, formatConfidenceLabel } from "../../design-system";

type UnifiedCommandBriefProps = {
  raceState: OperationalRaceState;
};

function cleanText(value: string): string {
  return value
    .replace(/Operational\s+State/g, "The race")
    .replace("operational confidence", "confidence")
    .replace("evidence", "intelligence")
    .replace("feeds", "engines")
    .replace("Continue monitoring.", "Maintain monitoring.")
    .replace("Do not escalate", "No escalation is recommended");
}

function buildHeroSituation(raceState: OperationalRaceState, currentSituation: string): string {
  const ready = raceState.feedHealth.filter((engine) => engine.status === "READY").map((engine) => engine.label);
  const waiting = raceState.feedHealth.filter((engine) => engine.status !== "READY").map((engine) => engine.label);

  const readyText = ready.length
    ? `${ready.slice(0, 3).join(", ")} ${ready.length > 3 ? "and supporting intelligence" : ""} are contributing to the current view.`
    : "The primary intelligence systems are still building the current view.";

  const waitingText = waiting.length
    ? `${waiting.slice(0, 3).join(", ")} ${waiting.length > 3 ? "and other systems" : ""} remain under observation.`
    : "All key intelligence systems are currently contributing.";

  return `${cleanText(currentSituation)} ${readyText} ${waitingText}`;
}

export function UnifiedCommandBrief({ raceState }: UnifiedCommandBriefProps) {
  const brief = composeExecutiveBrief(raceState);
  const decision = formatDecisionState(raceState.decision.state);
  const confidence = formatConfidenceLabel(raceState.confidence);
  const priority = formatPriority(raceState.decision.priority);

  return (
    <section className="eiq-command-v5-hero">
      <div className="eiq-command-v5-hero__decision">
        <span>Current Position</span>
        <strong>{decision}</strong>
        <small>{confidence} confidence · {priority}</small>
      </div>

      <div className="eiq-command-v5-hero__brief">
        <span>Race Brief</span>
        <p>{buildHeroSituation(raceState, brief.currentSituation)}</p>
        <b>{cleanText(brief.recommendedAction)}</b>
      </div>

      <div className="eiq-command-v5-hero__signals">
        <article>
          <span>Next Trigger</span>
          <strong>Market confirmation</strong>
        </article>
        <article>
          <span>Engine Agreement</span>
          <strong>{brief.evidenceAlignment}</strong>
        </article>
        <article>
          <span>Intelligence Online</span>
          <strong>{raceState.executiveSummary.systemHealth.feedsReady}/{raceState.executiveSummary.systemHealth.feedsTotal}</strong>
        </article>
      </div>
    </section>
  );
}
