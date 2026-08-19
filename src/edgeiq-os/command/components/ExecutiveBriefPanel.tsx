
import type { OperationalRaceState } from "../../services/operational-state";
import { composeExecutiveBrief } from "../../services/executive-brief";

type ExecutiveBriefPanelProps = {
  raceState: OperationalRaceState;
};

export function ExecutiveBriefPanel({ raceState }: ExecutiveBriefPanelProps) {
  const brief = composeExecutiveBrief(raceState);

  return (
    <section className="eiq-executive-brief">
      <header>
        <span>{brief.title}</span>
        <strong>{raceState.decision.state}</strong>
      </header>

      <p className="eiq-executive-brief__lead">{brief.currentSituation}</p>

      <div className="eiq-executive-brief__grid">
        <article>
          <span>Recommended Action</span>
          <strong>{brief.recommendedAction}</strong>
        </article>

        <article>
          <span>Evidence Alignment</span>
          <strong>{brief.evidenceAlignment}</strong>
        </article>

        <article>
          <span>Evidence Available</span>
          <strong>{brief.evidenceAvailable}</strong>
        </article>
      </div>

      <div className="eiq-executive-brief__columns">
        <article>
          <span>Current Risks</span>
          <ul>
            {brief.keyRisks.map((risk) => (
              <li key={risk}>{risk}</li>
            ))}
          </ul>
        </article>

        <article>
          <span>Current Opportunities</span>
          <ul>
            {brief.keyOpportunities.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
      </div>

      <footer>{brief.nextWatch}</footer>
    </section>
  );
}
