from pathlib import Path

components = Path("src/edgeiq-os/command/components")
workspace = Path("src/edgeiq-os/command/EdgeiqCommandWorkspace.tsx")
css = Path("src/styles/edgeiqProductTerminalV1.css")

components.mkdir(parents=True, exist_ok=True)

(components / "CommandExecutiveBrief.tsx").write_text(r'''
import type { OperationalRaceState } from "../../services/operational-state";
import { buildAgreementMatrix } from "../../services/agreement-matrix";
import { buildConfidenceProfile } from "../../services/confidence-profile";
import { buildRaceFlowReport } from "../../services/intelligence-report";
import { buildPressureEngine } from "../../services/pressure-engine";
import { buildTempoEngine } from "../../services/tempo-engine";
import { buildPositionEngine } from "../../services/position-engine";
import { formatDecisionState } from "../../design-system";

type CommandExecutiveBriefProps = {
  raceState: OperationalRaceState;
};

export function CommandExecutiveBrief({ raceState }: CommandExecutiveBriefProps) {
  const agreement = buildAgreementMatrix();
  const confidence = buildConfidenceProfile();
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
        <span>Executive Command Brief</span>
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
'''.lstrip(), encoding="utf-8")

text = workspace.read_text(encoding="utf-8")

import_line = 'import { CommandExecutiveBrief } from "./components/CommandExecutiveBrief";'

if import_line not in text:
    anchor = 'import { UnifiedCommandBrief } from "./components/UnifiedCommandBrief";'
    if anchor in text:
        text = text.replace(anchor, anchor + "\n" + import_line)
    else:
        text = import_line + "\n" + text

tag = '<CommandExecutiveBrief raceState={raceState} />'

if tag not in text:
    anchor = '<UnifiedCommandBrief raceState={raceState} />'
    if anchor in text:
        text = text.replace(anchor, anchor + "\n\n          " + tag, 1)
    else:
        fallback = '<AssessmentJourney journey={assessmentJourney} />'
        text = text.replace(fallback, tag + "\n\n          " + fallback, 1)

workspace.write_text(text, encoding="utf-8")

css_marker = "EDGEiQ Sprint 04A — Executive Command Brief"

existing_css = css.read_text(encoding="utf-8")

if css_marker not in existing_css:
    with css.open("a", encoding="utf-8") as f:
        f.write(r'''

/* ==========================================================================
   EDGEiQ Sprint 04A — Executive Command Brief
   ========================================================================== */

.eiq-command-exec {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(360px, 0.75fr);
  gap: 28px;
  margin: 34px 0 42px;
  padding: 34px;
  border: 1px solid rgba(246, 243, 234, 0.085);
  border-radius: 32px;
  background:
    radial-gradient(circle at top left, rgba(126, 220, 155, 0.085), transparent 35%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.035), rgba(255, 255, 255, 0.014));
}

.eiq-command-exec__main > span,
.eiq-command-exec__summary span,
.eiq-command-exec__rail header span,
.eiq-command-exec__stack span,
.eiq-command-exec__watch > span {
  display: block;
  color: rgba(246, 243, 234, 0.46);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.15em;
  text-transform: uppercase;
}

.eiq-command-exec__main h2 {
  max-width: 760px;
  margin: 12px 0 0;
  color: #f6f3ea;
  font-size: clamp(48px, 5vw, 78px);
  line-height: 0.9;
  letter-spacing: -0.08em;
}

.eiq-command-exec__main p {
  max-width: 860px;
  margin: 24px 0 0;
  color: rgba(246, 243, 234, 0.72);
  font-size: 16px;
  line-height: 1.7;
}

.eiq-command-exec__summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
  margin-top: 34px;
}

.eiq-command-exec__summary article {
  padding-top: 15px;
  border-top: 1px solid rgba(246, 243, 234, 0.10);
}

.eiq-command-exec__summary strong {
  display: block;
  margin-top: 9px;
  color: #f6f3ea;
  font-size: 21px;
  line-height: 1.05;
  letter-spacing: -0.05em;
}

.eiq-command-exec__rail {
  padding: 24px;
  border: 1px solid rgba(246, 243, 234, 0.075);
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.018);
}

.eiq-command-exec__rail header strong {
  display: block;
  margin-top: 8px;
  color: rgba(246, 243, 234, 0.70);
  font-size: 12px;
  line-height: 1.4;
}

.eiq-command-exec__stack {
  display: grid;
  gap: 14px;
  margin-top: 22px;
}

.eiq-command-exec__stack article {
  padding-top: 13px;
  border-top: 1px solid rgba(246, 243, 234, 0.085);
}

.eiq-command-exec__stack strong {
  display: block;
  margin-top: 8px;
  color: #f6f3ea;
  font-size: 20px;
  letter-spacing: -0.045em;
}

.eiq-command-exec__stack p {
  margin: 8px 0 0;
  color: rgba(246, 243, 234, 0.50);
  font-size: 11px;
  line-height: 1.45;
}

.eiq-command-exec__watch {
  grid-column: 1 / -1;
  padding-top: 22px;
  border-top: 1px solid rgba(246, 243, 234, 0.10);
}

.eiq-command-exec__watch div {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.eiq-command-exec__watch strong {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid rgba(246, 243, 234, 0.09);
  border-radius: 999px;
  color: rgba(246, 243, 234, 0.78);
  background: rgba(255, 255, 255, 0.022);
  font-size: 12px;
}

@media (max-width: 1250px) {
  .eiq-command-exec {
    grid-template-columns: 1fr;
  }

  .eiq-command-exec__summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .eiq-command-exec__summary {
    grid-template-columns: 1fr;
  }
}
''')

print("[EDGEIQ] Sprint04A Executive Command Brief built")
