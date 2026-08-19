import type { OperationalRaceState } from "../../services/operational-state";
import type { AssessmentJourneyModel } from "../../services/assessment-journey";
import { AgreementMatrix } from "./AgreementMatrix";
import { ConfidenceProfile } from "./ConfidenceProfile";
import { IntelligenceTimeline } from "./IntelligenceTimeline";
import { AssessmentJourney } from "./AssessmentJourney";

type CommandOperationalStackProps = {
  raceState: OperationalRaceState;
  journey: AssessmentJourneyModel;
};

export function CommandOperationalStack({ raceState, journey }: CommandOperationalStackProps) {
  const risks = raceState.alerts.slice(0, 4);
  const drivers = raceState.findings.slice(0, 4);

  return (
    <section className="eiq-command-stack">
      <header className="eiq-command-stack__header">
        <span>Operational Intelligence Stack</span>
        <strong>Evidence-backed race view</strong>
        <p>
          EDGEiQ connects RaceFlow, SpeedProfile, TrackSignature and engine agreement into one inspectable
          operational view. The model remains protected while the evidence remains visible.
        </p>
      </header>

      <div className="eiq-command-stack__grid">
        <div className="eiq-command-stack__primary">
          <AssessmentJourney journey={journey} />

          <section className="eiq-command-stack__drivers">
            <header>
              <span>Decision Drivers</span>
              <strong>{drivers.length} active signals</strong>
            </header>

            <div>
              {drivers.map((driver) => (
                <article key={driver.id}>
                  <span>{driver.priority}</span>
                  <strong>{driver.title}</strong>
                  <p>{driver.summary}</p>
                </article>
              ))}
            </div>
          </section>

          <IntelligenceTimeline />
        </div>

        <aside className="eiq-command-stack__rail">
          <ConfidenceProfile />
          <AgreementMatrix />

          <section className="eiq-command-stack__watch">
            <header>
              <span>Things To Watch</span>
              <strong>{risks.length || 4} watch points</strong>
            </header>

            <div>
              {(risks.length ? risks : [
                { id: "market", severity: "WATCH", title: "Late market disagreement", summary: "MarketBehaviour may change the operational read." },
                { id: "track", severity: "WATCH", title: "Track downgrade", summary: "TrackSignature may shift if conditions deteriorate." },
                { id: "pressure", severity: "WATCH", title: "Unexpected early pressure", summary: "RaceFlow may change if the lead scenario changes." },
                { id: "scratch", severity: "WATCH", title: "Leader scratching", summary: "Pressure Engine should be re-read after material scratchings." },
              ]).map((risk) => (
                <article key={risk.id}>
                  <span>{risk.severity}</span>
                  <strong>{risk.title}</strong>
                  <p>{"summary" in risk ? risk.summary : risk.summary}</p>
                </article>
              ))}
            </div>
          </section>
        </aside>
      </div>
    </section>
  );
}
