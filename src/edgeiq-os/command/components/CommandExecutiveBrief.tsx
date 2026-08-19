import type { OperationalRaceState } from "../../services/operational-state";
import { CommandService } from "../../services/CommandService";
import { buildRaceFlowReport } from "../../services/RaceFlowService";
import { buildPressureEngine } from "../../services/PressureService";
import { buildTempoEngine } from "../../services/TempoService";
import { buildPositionEngine } from "../../services/PositionService";
import { formatDecisionState } from "../../design-system";

type CommandExecutiveBriefProps = {
  raceState: OperationalRaceState;
};

export function CommandExecutiveBrief({ raceState }: CommandExecutiveBriefProps) {
  const agreement = CommandService.buildAgreementMatrix();
  const confidence = CommandService.buildConfidenceProfile();
  const raceFlow = buildRaceFlowReport(raceState);
  const pressure = buildPressureEngine(raceState);
  const tempo = buildTempoEngine(raceState);
  const position = buildPositionEngine(raceState);

  const watch = [
    "Late market support",
    "Track downgrade",
    "Unexpected early pressure",
    "Leader scratching",
  ];

  const stack = [
    { label: "RaceFlow", value: raceFlow.confidence, note: "Operational race assessment" },
    { label: "Pressure Engine", value: pressure.band, note: pressure.tacticalRead },
    { label: "Tempo Engine", value: tempo.band, note: tempo.expectedChange },
    { label: "Position Engine", value: position.position, note: position.tacticalRead },
  ];

  return (
    <section className="eiq-command-exec">
      <div className="eiq-command-exec__main">
        <span>Executive Race Brief</span>
        <h2>{formatDecisionState(raceState.decision.state)}</h2>
        <p>
          {raceFlow.assessment} {raceFlow.operationalMeaning}
        </p>

        <div className="eiq-command-exec__summary">
          <article>
            <span>Agreement</span>
            <strong>{agreement.agreement}%</strong>
          </article>

          <article>
            <span>Confidence</span>
            <strong>{confidence.band.replace("_", " ")}</strong>
          </article>

          <article>
            <span>Strongest Signal</span>
            <strong>{confidence.strongestSignal.label}</strong>
          </article>

          <article>
            <span>Weakest Signal</span>
            <strong>{confidence.weakestSignal.label}</strong>
          </article>
        </div>
      </div>

      <aside className="eiq-command-exec__rail">
        <header>
          <span>Intelligence Stack</span>
          <strong>Evidence visible / model protected</strong>
        </header>

        <div className="eiq-command-exec__stack">
          {stack.map((item) => (
            <article key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <p>{item.note}</p>
            </article>
          ))}
        </div>
      </aside>

      <div className="eiq-command-exec__watch">
        <span>Things To Watch</span>
        <div>
          {watch.map((item) => (
            <strong key={item}>{item}</strong>
          ))}
        </div>
      </div>
    </section>
  );
}
