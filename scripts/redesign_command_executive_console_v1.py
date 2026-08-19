from pathlib import Path

workspace = Path("src/edgeiq-os/command/EdgeiqCommandWorkspace.tsx")

workspace.write_text(r'''
import { useState } from "react";
import { LiveStatusStrip } from "./components/LiveStatusStrip";
import { ExecutiveDecisionPanel } from "./components/ExecutiveDecisionPanel";
import { OperationalTimelinePanel } from "./components/OperationalTimelinePanel";
import { EvidenceDrawer } from "./components/EvidenceDrawer";
import { OperationalStateRail } from "./components/OperationalStateRail";
import { getOperationalRaceState } from "../services/intelligence-orchestrator";

const raceState = getOperationalRaceState();

const liveStatus = [
  { label: "Decision", value: raceState.decision.state, tone: "info" },
  { label: "Confidence", value: `${raceState.confidence}%`, tone: "good" },
  { label: "Agreement", value: `${raceState.correlation.agreementScore}%`, tone: "neutral" },
  { label: "Coverage", value: `${raceState.executiveSummary.systemHealth.coverage}%`, tone: "neutral" },
  { label: "Feeds", value: `${raceState.executiveSummary.systemHealth.feedsReady}/${raceState.executiveSummary.systemHealth.feedsTotal}`, tone: "info" },
];

const evidence = raceState.evidence.map((item) => item.title);

export function EdgeiqCommandWorkspace() {
  const [activeEvidence, setActiveEvidence] = useState<string>(evidence[0] ?? "");

  return (
    <section className="eiq-command-live eiq-command-executive">
      <main className="eiq-command-live__main">
        <header className="eiq-command-live__header">
          <div>
            <h1>COMMAND</h1>
            <strong>{raceState.raceName}</strong>
            <p>
              Executive operations console · {raceState.decision.state} · {raceState.confidence}% confidence
            </p>
          </div>

          <LiveStatusStrip items={liveStatus} />
        </header>

        <section className="eiq-command-live__body has-drawer">
          <div className="eiq-command-live__content">
            <ExecutiveDecisionPanel summary={raceState.executiveSummary} />

            <section className="eiq-command-brief-grid">
              <article>
                <span>Recommended Action</span>
                <strong>{raceState.decision.state}</strong>
                <p>{raceState.decision.headline}</p>
              </article>

              <article>
                <span>Why</span>
                <strong>{raceState.correlation.agreementBand}</strong>
                <p>{raceState.decision.rationale}</p>
              </article>

              <article>
                <span>Operational Confidence</span>
                <strong>{raceState.confidence}%</strong>
                <p>
                  {raceState.correlation.supportingModules.length} intelligence engine(s) supporting the current view.
                </p>
              </article>
            </section>

            <section className="eiq-command-findings">
              <header>
                <span>Top Operational Findings</span>
                <strong>{raceState.findings.length}</strong>
              </header>

              {raceState.findings.slice(0, 4).map((finding) => (
                <article key={finding.id}>
                  <span>{finding.priority}</span>
                  <strong>{finding.title}</strong>
                  <p>{finding.summary}</p>
                  <small>{finding.supportingEngines.join(" + ")}</small>
                </article>
              ))}
            </section>

            <section className="eiq-command-evidence-groups">
              <header>
                <span>Evidence Explorer</span>
                <strong>{raceState.evidence.length} items</strong>
              </header>

              <div className="eiq-command-evidence-list">
                {evidence.map((item) => (
                  <button
                    className={item === activeEvidence ? "is-active" : ""}
                    type="button"
                    key={item}
                    onClick={() => setActiveEvidence(item)}
                  >
                    <span>› {item}</span>
                    <small>Open evidence</small>
                    <b>›</b>
                  </button>
                ))}
              </div>
            </section>

            <OperationalTimelinePanel events={raceState.events} />
          </div>

          <EvidenceDrawer
            activeEvidence={activeEvidence}
            evidence={raceState.evidence}
            onClose={() => setActiveEvidence("")}
          />

          <OperationalStateRail raceState={raceState} />
        </section>
      </main>
    </section>
  );
}
''', encoding="utf-8")

css = Path("src/styles/edgeiqProductTerminalV1.css")
text = css.read_text(encoding="utf-8", errors="ignore")

addition = r'''

/* EDGEIQ OS V2 Executive COMMAND */
.eiq-command-executive .eiq-command-live__content {
  display: grid;
  gap: 18px;
}

.eiq-command-brief-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.eiq-command-brief-grid article,
.eiq-command-findings,
.eiq-command-evidence-groups,
.eiq-executive-decision {
  border: 1px solid rgba(255,255,255,0.1);
  background: rgba(10, 14, 20, 0.74);
  border-radius: 18px;
  padding: 16px;
  box-shadow: 0 18px 50px rgba(0,0,0,0.22);
}

.eiq-command-brief-grid span,
.eiq-command-findings header span,
.eiq-command-evidence-groups header span,
.eiq-executive-decision header span {
  display: block;
  color: rgba(255,255,255,0.54);
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.eiq-command-brief-grid strong,
.eiq-command-findings header strong,
.eiq-command-evidence-groups header strong {
  display: block;
  margin-top: 6px;
  color: #fff;
  font-size: 18px;
  letter-spacing: -0.02em;
}

.eiq-command-brief-grid p {
  margin: 8px 0 0;
  color: rgba(255,255,255,0.68);
  line-height: 1.45;
}

.eiq-command-findings {
  display: grid;
  gap: 12px;
}

.eiq-command-findings header,
.eiq-command-evidence-groups header,
.eiq-executive-decision header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.eiq-command-findings article {
  border-top: 1px solid rgba(255,255,255,0.08);
  padding-top: 12px;
}

.eiq-command-findings article span {
  color: #f4c36a;
  font-size: 11px;
  letter-spacing: 0.12em;
}

.eiq-command-findings article strong {
  display: block;
  margin-top: 5px;
  color: #fff;
}

.eiq-command-findings article p {
  margin: 7px 0;
  color: rgba(255,255,255,0.7);
  line-height: 1.45;
}

.eiq-command-findings article small {
  color: rgba(255,255,255,0.46);
}

.eiq-executive-decision__hero {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 16px 0;
}

.eiq-executive-decision__hero div {
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  padding: 12px;
  background: rgba(255,255,255,0.03);
}

.eiq-executive-decision__hero small {
  display: block;
  color: rgba(255,255,255,0.48);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-size: 10px;
}

.eiq-executive-decision__hero b {
  display: block;
  margin-top: 6px;
  color: #fff;
  font-size: 20px;
}

.eiq-executive-decision > p {
  color: rgba(255,255,255,0.82);
  font-size: 16px;
  line-height: 1.45;
}

.eiq-executive-decision > small {
  color: rgba(255,255,255,0.55);
}

.eiq-executive-decision__findings {
  display: none;
}
'''

if "EDGEIQ OS V2 Executive COMMAND" not in text:
    text += addition

css.write_text(text, encoding="utf-8")

print("[EDGEIQ] COMMAND redesigned into executive operations console v1")
