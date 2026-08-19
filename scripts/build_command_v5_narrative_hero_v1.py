from pathlib import Path

brief = Path("src/edgeiq-os/command/components/UnifiedCommandBrief.tsx")
rail = Path("src/edgeiq-os/command/components/OperationsRailV2.tsx")
css = Path("src/styles/edgeiqProductTerminalV1.css")

brief.write_text(r'''
import type { OperationalRaceState } from "../../services/operational-state";
import { composeExecutiveBrief } from "../../services/executive-brief";
import { formatDecisionState, formatPriority, formatConfidenceLabel } from "../../design-system";

type UnifiedCommandBriefProps = {
  raceState: OperationalRaceState;
};

function cleanText(value: string): string {
  return value
    .replace("Operational State", "The race")
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
        <span>Command Brief</span>
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
'''.lstrip(), encoding="utf-8")

rail.write_text(r'''
import type { OperationalRaceState } from "../../services/operational-state";
import { formatDecisionState, formatConfidenceLabel } from "../../design-system";

type OperationsRailV2Props = {
  raceState: OperationalRaceState;
};

export function OperationsRailV2({ raceState }: OperationsRailV2Props) {
  const ready = raceState.feedHealth.filter((engine) => engine.status === "READY");
  const waiting = raceState.feedHealth.filter((engine) => engine.status !== "READY");

  return (
    <section className="eiq-command-v5-rail">
      <header>
        <span>System</span>
        <strong>{ready.length}/{raceState.feedHealth.length}</strong>
      </header>

      <div className="eiq-command-v5-rail__list">
        {ready.map((engine) => (
          <article key={engine.key}>
            <i className="is-ready" />
            <strong>{engine.label}</strong>
          </article>
        ))}

        {waiting.map((engine) => (
          <article key={engine.key}>
            <i />
            <strong>{engine.label}</strong>
          </article>
        ))}
      </div>

      <footer>
        <span>Position</span>
        <strong>{formatDecisionState(raceState.decision.state)}</strong>
        <small>{formatConfidenceLabel(raceState.confidence)} confidence</small>
      </footer>
    </section>
  );
}
'''.lstrip(), encoding="utf-8")

css_block = r'''

/* ==========================================================================
   EDGEiQ COMMAND V5 — Narrative Hero + Compact System Rail
   ========================================================================== */

.eiq-command-v5-hero {
  display: grid;
  grid-template-columns: 250px minmax(0, 1fr) 230px;
  gap: 34px;
  padding: 36px 0 40px;
  border-bottom: 1px solid rgba(246, 243, 234, 0.10);
}

.eiq-command-v5-hero__decision span,
.eiq-command-v5-hero__brief span,
.eiq-command-v5-hero__signals span,
.eiq-command-v5-rail header span,
.eiq-command-v5-rail footer span {
  display: block;
  color: rgba(246, 243, 234, 0.46);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.15em;
  text-transform: uppercase;
}

.eiq-command-v5-hero__decision strong {
  display: block;
  margin-top: 14px;
  color: #f6f3ea;
  font-size: clamp(38px, 4vw, 58px);
  line-height: 0.94;
  letter-spacing: -0.07em;
}

.eiq-command-v5-hero__decision small {
  display: block;
  margin-top: 14px;
  color: rgba(246, 243, 234, 0.58);
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
}

.eiq-command-v5-hero__brief p {
  max-width: 920px;
  margin: 14px 0 0;
  color: rgba(246, 243, 234, 0.90);
  font-size: clamp(23px, 2.25vw, 34px);
  line-height: 1.28;
  letter-spacing: -0.055em;
}

.eiq-command-v5-hero__brief b {
  display: block;
  max-width: 780px;
  margin-top: 22px;
  color: #f6f3ea;
  font-size: 15px;
  line-height: 1.6;
}

.eiq-command-v5-hero__signals {
  display: grid;
  align-content: start;
  gap: 14px;
}

.eiq-command-v5-hero__signals article {
  padding-top: 13px;
  border-top: 1px solid rgba(246, 243, 234, 0.10);
}

.eiq-command-v5-hero__signals strong {
  display: block;
  margin-top: 7px;
  color: rgba(246, 243, 234, 0.86);
  font-size: 13px;
  line-height: 1.25;
}

.eiq-command-v5-rail {
  position: sticky;
  top: 24px;
  padding: 18px;
  background: rgba(255, 255, 255, 0.022);
  border: 1px solid rgba(246, 243, 234, 0.075);
  border-radius: 22px;
}

.eiq-command-v5-rail header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(246, 243, 234, 0.08);
}

.eiq-command-v5-rail header strong {
  color: #f6f3ea;
  font-size: 18px;
  letter-spacing: -0.04em;
}

.eiq-command-v5-rail__list {
  display: grid;
  gap: 4px;
  padding: 14px 0;
}

.eiq-command-v5-rail__list article {
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  min-height: 26px;
}

.eiq-command-v5-rail__list i {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: rgba(246, 243, 234, 0.24);
}

.eiq-command-v5-rail__list i.is-ready {
  background: #7edc9b;
}

.eiq-command-v5-rail__list strong {
  overflow: hidden;
  color: rgba(246, 243, 234, 0.72);
  font-size: 12px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.eiq-command-v5-rail footer {
  padding-top: 14px;
  border-top: 1px solid rgba(246, 243, 234, 0.08);
}

.eiq-command-v5-rail footer strong {
  display: block;
  margin-top: 6px;
  color: #f6f3ea;
  font-size: 14px;
}

.eiq-command-v5-rail footer small {
  display: block;
  margin-top: 4px;
  color: rgba(246, 243, 234, 0.50);
  font-size: 11px;
}

@media (max-width: 1180px) {
  .eiq-command-v5-hero {
    grid-template-columns: 1fr;
  }
}
'''

css.write_text(css.read_text(encoding="utf-8") + css_block, encoding="utf-8")

print("[EDGEIQ] COMMAND V5 narrative hero built")
