from pathlib import Path

root = Path("src/edgeiq-os/services/executive-brief")
root.mkdir(parents=True, exist_ok=True)

(root / "ExecutiveBriefTypes.ts").write_text(r'''
export interface ExecutiveBrief {
  title: string;
  currentSituation: string;
  recommendedAction: string;
  evidenceAlignment: string;
  evidenceAvailable: string;
  keyRisks: string[];
  keyOpportunities: string[];
  nextWatch: string;
}
''', encoding="utf-8")

(root / "ExecutiveBriefService.ts").write_text(r'''
import type { OperationalRaceState } from "../operational-state";
import type { ExecutiveBrief } from "./ExecutiveBriefTypes";

function alignmentLabel(score: number): string {
  if (score >= 80) return "Strong alignment";
  if (score >= 55) return "Mixed but usable";
  if (score > 0) return "Low alignment";
  return "Insufficient evidence";
}

function availabilityLabel(coverage: number): string {
  if (coverage >= 85) return "Broad evidence available";
  if (coverage >= 60) return "Partial evidence available";
  if (coverage > 0) return "Limited evidence available";
  return "Evidence unavailable";
}

export function composeExecutiveBrief(state: OperationalRaceState): ExecutiveBrief {
  const summary = state.executiveSummary;
  const decision = state.decision;
  const correlation = state.correlation;

  const partialFeeds = state.feedHealth
    .filter((feed) => feed.status !== "READY")
    .map((feed) => feed.label);

  const readyFeeds = state.feedHealth
    .filter((feed) => feed.status === "READY")
    .map((feed) => feed.label);

  const keyRisks =
    partialFeeds.length > 0
      ? partialFeeds.slice(0, 4).map((feed) => `${feed} is not yet fully available.`)
      : ["No major engine availability risks detected."];

  const keyOpportunities =
    readyFeeds.length > 0
      ? readyFeeds.slice(0, 4).map((feed) => `${feed} is currently contributing intelligence.`)
      : ["Awaiting stronger intelligence coverage."];

  const currentSituation =
    `${state.raceName} is currently in ${decision.state} mode. ` +
    `${alignmentLabel(correlation.agreementScore)} across available engines. ` +
    `${availabilityLabel(summary.systemHealth.coverage)}.`;

  const recommendedAction =
    decision.state === "EXECUTE"
      ? "Proceed only if market and late feed checks remain stable."
      : decision.state === "MONITOR"
      ? "Continue monitoring. Do not escalate until missing engines improve or market confirms the assessment."
      : decision.state === "REVIEW"
      ? "Review conflicting engines before acting."
      : "Wait for stronger operational alignment before taking action.";

  return {
    title: "Executive Brief",
    currentSituation,
    recommendedAction,
    evidenceAlignment: alignmentLabel(correlation.agreementScore),
    evidenceAvailable: availabilityLabel(summary.systemHealth.coverage),
    keyRisks,
    keyOpportunities,
    nextWatch:
      partialFeeds.length > 0
        ? `Next watch: ${partialFeeds[0]} update.`
        : "Next watch: market movement and late confidence shift.",
  };
}
''', encoding="utf-8")

(root / "index.ts").write_text(r'''
export * from "./ExecutiveBriefTypes";
export * from "./ExecutiveBriefService";
''', encoding="utf-8")

component = Path("src/edgeiq-os/command/components/ExecutiveBriefPanel.tsx")
component.write_text(r'''
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
''', encoding="utf-8")

workspace = Path("src/edgeiq-os/command/EdgeiqCommandWorkspace.tsx")
text = workspace.read_text(encoding="utf-8")

if 'ExecutiveBriefPanel' not in text:
    text = text.replace(
        'import { ExecutiveDecisionPanel } from "./components/ExecutiveDecisionPanel";',
        'import { ExecutiveDecisionPanel } from "./components/ExecutiveDecisionPanel";\nimport { ExecutiveBriefPanel } from "./components/ExecutiveBriefPanel";'
    )

if "<ExecutiveBriefPanel" not in text:
    text = text.replace(
        '<ExecutiveDecisionPanel summary={raceState.executiveSummary} />',
        '<ExecutiveBriefPanel raceState={raceState} />\n\n            <ExecutiveDecisionPanel summary={raceState.executiveSummary} />'
    )

workspace.write_text(text, encoding="utf-8")

css = Path("src/styles/edgeiqProductTerminalV1.css")
css_text = css.read_text(encoding="utf-8", errors="ignore")

addition = r'''

/* EDGEIQ OS V2 Executive Brief */
.eiq-executive-brief {
  border: 1px solid rgba(255,255,255,0.11);
  background:
    linear-gradient(135deg, rgba(99, 232, 215, 0.06), transparent 34%),
    rgba(8, 12, 18, 0.84);
  border-radius: 20px;
  padding: 18px;
  box-shadow: 0 22px 60px rgba(0,0,0,0.28);
}

.eiq-executive-brief header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.eiq-executive-brief header span,
.eiq-executive-brief__grid span,
.eiq-executive-brief__columns span {
  color: rgba(255,255,255,0.52);
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.eiq-executive-brief header strong {
  color: #fff;
  font-size: 28px;
  letter-spacing: -0.03em;
}

.eiq-executive-brief__lead {
  max-width: 920px;
  color: rgba(255,255,255,0.84);
  font-size: 18px;
  line-height: 1.5;
  margin: 0 0 16px;
}

.eiq-executive-brief__grid {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 12px;
  margin-bottom: 14px;
}

.eiq-executive-brief__grid article,
.eiq-executive-brief__columns article {
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  background: rgba(255,255,255,0.035);
  padding: 14px;
}

.eiq-executive-brief__grid strong {
  display: block;
  margin-top: 8px;
  color: #fff;
  font-size: 15px;
  line-height: 1.4;
}

.eiq-executive-brief__columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.eiq-executive-brief__columns ul {
  margin: 10px 0 0;
  padding-left: 18px;
  color: rgba(255,255,255,0.72);
  line-height: 1.55;
}

.eiq-executive-brief footer {
  margin-top: 14px;
  color: #f4c36a;
  font-size: 13px;
}
'''

if "EDGEIQ OS V2 Executive Brief" not in css_text:
    css_text += addition

css.write_text(css_text, encoding="utf-8")

print("[EDGEIQ] Executive Brief V2 created and mounted")
