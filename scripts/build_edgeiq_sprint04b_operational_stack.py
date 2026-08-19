from pathlib import Path
import re

components = Path("src/edgeiq-os/command/components")
workspace = Path("src/edgeiq-os/command/EdgeiqCommandWorkspace.tsx")
css = Path("src/styles/edgeiqProductTerminalV1.css")

components.mkdir(parents=True, exist_ok=True)

(components / "CommandOperationalStack.tsx").write_text(r'''
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
        <strong>Evidence-backed command view</strong>
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
'''.lstrip(), encoding="utf-8")

text = workspace.read_text(encoding="utf-8")

# Remove older standalone experimental hero/two-column blocks from Sprint 03D if present.
text = re.sub(
    r'\n\s*<section className="eiq-command-hero">.*?</section>\s*\n\s*<section className="eiq-command-two-column">.*?</section>\s*',
    "\n",
    text,
    flags=re.S,
)

# Remove standalone blocks now owned by CommandOperationalStack.
text = text.replace("\n          <ConfidenceProfile />\n", "\n")
text = text.replace("\n          <AgreementMatrix />\n", "\n")
text = text.replace("\n          <IntelligenceTimeline />\n", "\n")
text = text.replace("\n          <AssessmentJourney journey={assessmentJourney} />\n", "\n")

# Remove imports no longer needed directly by workspace.
remove_imports = {
    'import { ConfidenceProfile } from "./components/ConfidenceProfile";',
    'import { AgreementMatrix } from "./components/AgreementMatrix";',
    'import { IntelligenceTimeline } from "./components/IntelligenceTimeline";',
    'import { AssessmentJourney } from "./components/AssessmentJourney";',
}
lines = [line for line in text.splitlines() if line.strip() not in remove_imports]
text = "\n".join(lines) + "\n"

import_line = 'import { CommandOperationalStack } from "./components/CommandOperationalStack";'
if import_line not in text:
    anchor = 'import { CommandExecutiveBrief } from "./components/CommandExecutiveBrief";'
    if anchor in text:
        text = text.replace(anchor, anchor + "\n" + import_line)
    else:
        text = import_line + "\n" + text

tag = '<CommandOperationalStack raceState={raceState} journey={assessmentJourney} />'
if tag not in text:
    anchor = '<CommandExecutiveBrief raceState={raceState} />'
    if anchor in text:
        text = text.replace(anchor, anchor + "\n\n          " + tag, 1)
    else:
        text = text.replace('<UnifiedCommandBrief raceState={raceState} />', '<UnifiedCommandBrief raceState={raceState} />\n\n          ' + tag, 1)

workspace.write_text(text, encoding="utf-8")

css_marker = "EDGEiQ Sprint 04B — Operational Intelligence Stack"
existing_css = css.read_text(encoding="utf-8")

if css_marker not in existing_css:
    with css.open("a", encoding="utf-8") as f:
        f.write(r'''

/* ==========================================================================
   EDGEiQ Sprint 04B — Operational Intelligence Stack
   ========================================================================== */

.eiq-command-stack {
  margin: 36px 0 46px;
  padding: 34px;
  border: 1px solid rgba(246, 243, 234, 0.085);
  border-radius: 34px;
  background:
    radial-gradient(circle at top right, rgba(126, 220, 155, 0.06), transparent 35%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.028), rgba(255, 255, 255, 0.012));
}

.eiq-command-stack__header {
  max-width: 920px;
  margin-bottom: 30px;
}

.eiq-command-stack__header span,
.eiq-command-stack__drivers header span,
.eiq-command-stack__drivers article span,
.eiq-command-stack__watch header span,
.eiq-command-stack__watch article span {
  display: block;
  color: rgba(246, 243, 234, 0.46);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.15em;
  text-transform: uppercase;
}

.eiq-command-stack__header strong {
  display: block;
  margin-top: 10px;
  color: #f6f3ea;
  font-size: clamp(32px, 3vw, 48px);
  line-height: 0.96;
  letter-spacing: -0.065em;
}

.eiq-command-stack__header p {
  margin: 16px 0 0;
  color: rgba(246, 243, 234, 0.64);
  font-size: 14px;
  line-height: 1.7;
}

.eiq-command-stack__grid {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(360px, 0.85fr);
  gap: 30px;
  align-items: start;
}

.eiq-command-stack__primary {
  display: grid;
  gap: 28px;
}

.eiq-command-stack__primary > .eiq-assessment-journey,
.eiq-command-stack__primary > .eiq-decision-timeline {
  margin: 0;
  padding: 28px;
  border: 1px solid rgba(246, 243, 234, 0.075);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.016);
}

.eiq-command-stack__drivers {
  padding: 28px;
  border: 1px solid rgba(246, 243, 234, 0.075);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.016);
}

.eiq-command-stack__drivers header,
.eiq-command-stack__watch header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 20px;
}

.eiq-command-stack__drivers header strong,
.eiq-command-stack__watch header strong {
  color: rgba(246, 243, 234, 0.68);
  font-size: 12px;
  text-transform: uppercase;
}

.eiq-command-stack__drivers > div {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.eiq-command-stack__drivers article {
  padding-top: 15px;
  border-top: 1px solid rgba(246, 243, 234, 0.09);
}

.eiq-command-stack__drivers article strong,
.eiq-command-stack__watch article strong {
  display: block;
  margin-top: 8px;
  color: #f6f3ea;
  font-size: 15px;
  letter-spacing: -0.025em;
}

.eiq-command-stack__drivers article p,
.eiq-command-stack__watch article p {
  margin: 9px 0 0;
  color: rgba(246, 243, 234, 0.54);
  font-size: 12px;
  line-height: 1.55;
}

.eiq-command-stack__rail {
  position: sticky;
  top: 24px;
  display: grid;
  gap: 24px;
}

.eiq-command-stack__rail > .eiq-confidence-profile,
.eiq-command-stack__rail > .eiq-agreement {
  margin: 0;
}

.eiq-command-stack__rail .eiq-confidence-profile,
.eiq-command-stack__rail .eiq-agreement,
.eiq-command-stack__watch {
  padding: 26px;
  border-radius: 28px;
}

.eiq-command-stack__rail .eiq-confidence-profile__meta,
.eiq-command-stack__rail .eiq-agreement-grid {
  grid-template-columns: 1fr;
}

.eiq-command-stack__rail .eiq-confidence-profile__signals article {
  grid-template-columns: 1fr;
}

.eiq-command-stack__rail .eiq-confidence-profile__signals small {
  text-align: left;
}

.eiq-command-stack__rail .eiq-agreement-score {
  font-size: 54px;
}

.eiq-command-stack__watch {
  border: 1px solid rgba(246, 243, 234, 0.075);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.026), rgba(255, 255, 255, 0.012));
}

.eiq-command-stack__watch > div {
  display: grid;
  gap: 14px;
}

.eiq-command-stack__watch article {
  padding-top: 14px;
  border-top: 1px solid rgba(246, 243, 234, 0.085);
}

@media (max-width: 1280px) {
  .eiq-command-stack__grid {
    grid-template-columns: 1fr;
  }

  .eiq-command-stack__rail {
    position: static;
  }

  .eiq-command-stack__drivers > div {
    grid-template-columns: 1fr;
  }
}
''')

print("[EDGEIQ] Sprint04B Operational Intelligence Stack built")
