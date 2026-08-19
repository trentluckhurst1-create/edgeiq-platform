from pathlib import Path

root = Path(".")
command = root / "src" / "edgeiq-os" / "command" / "EdgeiqCommandWorkspace.tsx"
brief = root / "src" / "edgeiq-os" / "command" / "components" / "UnifiedCommandBrief.tsx"
explorer = root / "src" / "edgeiq-os" / "command" / "components" / "IntelligenceExplorer.tsx"
evidence = root / "src" / "edgeiq-os" / "command" / "components" / "EvidenceWorkspace.tsx"
rail = root / "src" / "edgeiq-os" / "command" / "components" / "OperationsRailV2.tsx"
css = root / "src" / "styles" / "edgeiqProductTerminalV1.css"

command.write_text(r'''
import { useState } from "react";
import { LiveStatusStrip } from "./components/LiveStatusStrip";
import { UnifiedCommandBrief } from "./components/UnifiedCommandBrief";
import { IntelligenceExplorer } from "./components/IntelligenceExplorer";
import { EvidenceWorkspace } from "./components/EvidenceWorkspace";
import { OperationalInbox } from "./components/OperationalInbox";
import { OperationalAlertsBar } from "./components/OperationalAlertsBar";
import { OperationsRailV2 } from "./components/OperationsRailV2";
import { getOperationalRaceState } from "../services/intelligence-orchestrator";

const raceState = getOperationalRaceState();

const liveStatus = [
  { label: "Decision", value: raceState.decision.state, tone: "info" },
  { label: "Confidence", value: `${raceState.confidence}%`, tone: "good" },
  { label: "Consensus", value: raceState.correlation.agreementBand, tone: "neutral" },
  {
    label: "Engines",
    value: `${raceState.executiveSummary.systemHealth.feedsReady}/${raceState.executiveSummary.systemHealth.feedsTotal}`,
    tone: "info",
  },
];

export function EdgeiqCommandWorkspace() {
  const [activeEvidence, setActiveEvidence] = useState<string>(raceState.evidence[0]?.title ?? "");

  return (
    <section className="eiq-command-v4">
      <header className="eiq-command-v4__hero">
        <div>
          <span className="eiq-command-v4__eyebrow">Victoria Racing Intelligence</span>
          <h1>COMMAND</h1>
          <p>{raceState.raceName}</p>
        </div>

        <LiveStatusStrip items={liveStatus} />
      </header>

      <OperationalAlertsBar raceState={raceState} />

      <main className="eiq-command-v4__layout">
        <section className="eiq-command-v4__main">
          <UnifiedCommandBrief raceState={raceState} />

          <section className="eiq-command-v4__section">
            <header className="eiq-command-v4__section-head">
              <span>Key Intelligence</span>
              <strong>{raceState.findings.length} active observations</strong>
            </header>

            <div className="eiq-command-v4__findings">
              {raceState.findings.slice(0, 4).map((finding) => (
                <article key={finding.id}>
                  <span>{finding.priority}</span>
                  <strong>{finding.title}</strong>
                  <p>{finding.summary}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="eiq-command-v4__workbench">
            <IntelligenceExplorer
              raceState={raceState}
              activeEvidence={activeEvidence}
              onSelect={setActiveEvidence}
            />

            <EvidenceWorkspace evidence={raceState.evidence} activeEvidence={activeEvidence} />
          </section>

          <section className="eiq-command-v4__section">
            <header className="eiq-command-v4__section-head">
              <span>Live Operations</span>
              <strong>{raceState.events.length} updates</strong>
            </header>
            <OperationalInbox events={raceState.events} />
          </section>
        </section>

        <aside className="eiq-command-v4__rail">
          <OperationsRailV2 raceState={raceState} />
        </aside>
      </main>
    </section>
  );
}
'''.lstrip(), encoding="utf-8")

brief.write_text(r'''
import type { OperationalRaceState } from "../../services/operational-state";
import { composeExecutiveBrief } from "../../services/executive-brief";

type UnifiedCommandBriefProps = {
  raceState: OperationalRaceState;
};

function cleanText(value: string): string {
  return value
    .replace("Operational State", "The race")
    .replace("operational confidence", "confidence")
    .replace("evidence", "intelligence")
    .replace("feeds", "engines");
}

export function UnifiedCommandBrief({ raceState }: UnifiedCommandBriefProps) {
  const brief = composeExecutiveBrief(raceState);

  return (
    <section className="eiq-command-v4-brief">
      <div className="eiq-command-v4-brief__status">
        <span>Current Decision</span>
        <strong>{raceState.decision.state}</strong>
        <small>{raceState.confidence}% confidence · {raceState.decision.priority} priority</small>
      </div>

      <div className="eiq-command-v4-brief__body">
        <span>Operational Brief</span>
        <p>{cleanText(brief.currentSituation)}</p>
        <b>{cleanText(brief.recommendedAction)}</b>
      </div>

      <div className="eiq-command-v4-brief__meta">
        <article>
          <span>Engine Consensus</span>
          <strong>{brief.evidenceAlignment}</strong>
        </article>
        <article>
          <span>Intelligence Coverage</span>
          <strong>{brief.evidenceAvailable}</strong>
        </article>
        <article>
          <span>Engines Contributing</span>
          <strong>{raceState.executiveSummary.systemHealth.feedsReady}/{raceState.executiveSummary.systemHealth.feedsTotal}</strong>
        </article>
      </div>
    </section>
  );
}
'''.lstrip(), encoding="utf-8")

explorer.write_text(r'''
import type { OperationalEvidenceItem, OperationalRaceState } from "../../services/operational-state";

type IntelligenceExplorerProps = {
  raceState: OperationalRaceState;
  activeEvidence: string;
  onSelect: (title: string) => void;
};

function label(value: string): string {
  return value.split("_").join(" ");
}

function statusText(items: OperationalEvidenceItem[]): string {
  return items.some((item) => item.status === "READY") ? "Available" : "Building";
}

export function IntelligenceExplorer({ raceState, activeEvidence, onSelect }: IntelligenceExplorerProps) {
  const grouped = raceState.evidence.reduce<Record<string, OperationalEvidenceItem[]>>((acc, item) => {
    const key = item.category;
    acc[key] = acc[key] ?? [];
    acc[key].push(item);
    return acc;
  }, {});

  return (
    <section className="eiq-command-v4-explorer">
      <header>
        <span>Intelligence Explorer</span>
        <strong>{Object.keys(grouped).length} systems</strong>
      </header>

      <div className="eiq-command-v4-explorer__list">
        {Object.entries(grouped).map(([category, items]) => {
          const selected = items.some((item) => item.title === activeEvidence);

          return (
            <button
              key={category}
              type="button"
              className={selected ? "is-active" : ""}
              onClick={() => onSelect(items[0]?.title ?? "")}
            >
              <span>{label(category)}</span>
              <strong>{statusText(items)}</strong>
              <small>{items.length} observation{items.length === 1 ? "" : "s"}</small>
            </button>
          );
        })}
      </div>
    </section>
  );
}
'''.lstrip(), encoding="utf-8")

evidence.write_text(r'''
import type { OperationalEvidenceItem } from "../../services/operational-state";

type EvidenceWorkspaceProps = {
  evidence: OperationalEvidenceItem[];
  activeEvidence: string;
};

function label(value: string): string {
  return value.split("_").join(" ");
}

function statusText(value: string): string {
  return value === "READY" ? "Confirmed" : "Still building";
}

export function EvidenceWorkspace({ evidence, activeEvidence }: EvidenceWorkspaceProps) {
  const item = evidence.find((entry) => entry.title === activeEvidence) ?? evidence[0];

  if (!item) {
    return (
      <section className="eiq-command-v4-evidence">
        <header><span>Why This Decision</span><strong>No intelligence selected</strong></header>
      </section>
    );
  }

  return (
    <section className="eiq-command-v4-evidence">
      <header>
        <span>Why This Decision</span>
        <strong>{label(item.category)}</strong>
      </header>

      <article>
        <span>{statusText(item.status)}</span>
        <h3>{item.title}</h3>
        <p>{item.summary}</p>
      </article>

      <div className="eiq-command-v4-evidence__metrics">
        <div><span>Confidence</span><strong>{item.confidence}</strong></div>
        <div><span>Influence</span><strong>{item.importance}/100</strong></div>
        <div><span>Assessment</span><strong>{statusText(item.status)}</strong></div>
      </div>
    </section>
  );
}
'''.lstrip(), encoding="utf-8")

rail.write_text(r'''
import type { OperationalRaceState } from "../../services/operational-state";

type OperationsRailV2Props = {
  raceState: OperationalRaceState;
};

function statusLabel(status: string): string {
  return status === "READY" ? "Available" : "Waiting";
}

export function OperationsRailV2({ raceState }: OperationsRailV2Props) {
  const ready = raceState.moduleOutputs.filter((module) => module.status === "READY");
  const waiting = raceState.moduleOutputs.filter((module) => module.status !== "READY");

  return (
    <section className="eiq-command-v4-rail">
      <header>
        <span>Engine Status</span>
        <strong>{ready.length}/{raceState.moduleOutputs.length} online</strong>
      </header>

      <div className="eiq-command-v4-rail__group">
        <span>Available</span>
        {ready.map((module) => (
          <article key={module.key}>
            <i />
            <strong>{module.label}</strong>
            <small>{statusLabel(module.status)}</small>
          </article>
        ))}
      </div>

      <div className="eiq-command-v4-rail__group">
        <span>Still Monitoring</span>
        {waiting.map((module) => (
          <article key={module.key}>
            <i />
            <strong>{module.label}</strong>
            <small>{statusLabel(module.status)}</small>
          </article>
        ))}
      </div>

      <footer>
        <span>System</span>
        <strong>{raceState.decision.state}</strong>
        <small>{raceState.confidence}% confidence</small>
      </footer>
    </section>
  );
}
'''.lstrip(), encoding="utf-8")

css_block = r'''

/* ==========================================================================
   EDGEiQ OS COMMAND V4 — Premium Operational Briefing Layout
   ========================================================================== */

.eiq-command-v4 {
  min-height: 100%;
  padding: 28px;
  color: #f6f3ea;
}

.eiq-command-v4__hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 28px;
  padding: 4px 0 26px;
  border-bottom: 1px solid rgba(246, 243, 234, 0.12);
}

.eiq-command-v4__eyebrow,
.eiq-command-v4__section-head span,
.eiq-command-v4-brief__body span,
.eiq-command-v4-brief__status span,
.eiq-command-v4-explorer header span,
.eiq-command-v4-evidence header span,
.eiq-command-v4-rail header span {
  display: block;
  color: rgba(246, 243, 234, 0.54);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.eiq-command-v4__hero h1 {
  margin: 8px 0 2px;
  font-size: clamp(42px, 5vw, 72px);
  line-height: 0.92;
  letter-spacing: -0.07em;
}

.eiq-command-v4__hero p {
  margin: 0;
  color: rgba(246, 243, 234, 0.74);
  font-size: 15px;
  font-weight: 700;
}

.eiq-command-v4__layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 292px;
  gap: 28px;
  margin-top: 28px;
}

.eiq-command-v4__main {
  min-width: 0;
}

.eiq-command-v4__rail {
  min-width: 0;
}

.eiq-command-v4-brief {
  display: grid;
  grid-template-columns: 210px minmax(0, 1fr) 240px;
  gap: 28px;
  padding: 30px 0 34px;
  border-bottom: 1px solid rgba(246, 243, 234, 0.10);
}

.eiq-command-v4-brief__status strong {
  display: block;
  margin-top: 12px;
  font-size: 34px;
  line-height: 1;
  letter-spacing: -0.05em;
}

.eiq-command-v4-brief__status small {
  display: block;
  margin-top: 10px;
  color: rgba(246, 243, 234, 0.56);
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
}

.eiq-command-v4-brief__body p {
  max-width: 850px;
  margin: 12px 0 0;
  color: rgba(246, 243, 234, 0.88);
  font-size: 22px;
  line-height: 1.45;
  letter-spacing: -0.035em;
}

.eiq-command-v4-brief__body b {
  display: block;
  max-width: 780px;
  margin-top: 18px;
  color: #f6f3ea;
  font-size: 15px;
  line-height: 1.55;
}

.eiq-command-v4-brief__meta {
  display: grid;
  gap: 10px;
}

.eiq-command-v4-brief__meta article {
  padding: 0 0 12px;
  border-bottom: 1px solid rgba(246, 243, 234, 0.08);
}

.eiq-command-v4-brief__meta span,
.eiq-command-v4-evidence__metrics span,
.eiq-command-v4-rail footer span {
  display: block;
  color: rgba(246, 243, 234, 0.46);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.eiq-command-v4-brief__meta strong,
.eiq-command-v4-evidence__metrics strong,
.eiq-command-v4-rail footer strong {
  display: block;
  margin-top: 4px;
  font-size: 14px;
}

.eiq-command-v4__section {
  padding: 28px 0;
  border-bottom: 1px solid rgba(246, 243, 234, 0.10);
}

.eiq-command-v4__section-head {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
}

.eiq-command-v4__section-head strong {
  color: rgba(246, 243, 234, 0.62);
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
}

.eiq-command-v4__findings {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.eiq-command-v4__findings article {
  padding-top: 14px;
  border-top: 1px solid rgba(246, 243, 234, 0.16);
}

.eiq-command-v4__findings article span {
  color: rgba(246, 243, 234, 0.42);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.eiq-command-v4__findings article strong {
  display: block;
  margin-top: 8px;
  font-size: 15px;
}

.eiq-command-v4__findings article p {
  margin: 8px 0 0;
  color: rgba(246, 243, 234, 0.58);
  font-size: 12px;
  line-height: 1.55;
}

.eiq-command-v4__workbench {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 24px;
  padding: 30px 0;
  border-bottom: 1px solid rgba(246, 243, 234, 0.10);
}

.eiq-command-v4-explorer,
.eiq-command-v4-evidence,
.eiq-command-v4-rail {
  min-width: 0;
}

.eiq-command-v4-explorer header,
.eiq-command-v4-evidence header,
.eiq-command-v4-rail header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.eiq-command-v4-explorer header strong,
.eiq-command-v4-evidence header strong,
.eiq-command-v4-rail header strong {
  color: rgba(246, 243, 234, 0.66);
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
}

.eiq-command-v4-explorer__list {
  display: grid;
  gap: 8px;
}

.eiq-command-v4-explorer__list button {
  width: 100%;
  padding: 14px 14px;
  text-align: left;
  color: #f6f3ea;
  background: transparent;
  border: 1px solid rgba(246, 243, 234, 0.08);
  border-radius: 16px;
  cursor: pointer;
}

.eiq-command-v4-explorer__list button.is-active {
  background: rgba(246, 243, 234, 0.06);
  border-color: rgba(246, 243, 234, 0.22);
}

.eiq-command-v4-explorer__list button span {
  display: block;
  color: rgba(246, 243, 234, 0.86);
  font-size: 13px;
  font-weight: 900;
  text-transform: capitalize;
}

.eiq-command-v4-explorer__list button strong {
  display: block;
  margin-top: 7px;
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.eiq-command-v4-explorer__list button small {
  display: block;
  margin-top: 6px;
  color: rgba(246, 243, 234, 0.45);
  font-size: 11px;
}

.eiq-command-v4-evidence {
  padding: 0 0 0 24px;
  border-left: 1px solid rgba(246, 243, 234, 0.10);
}

.eiq-command-v4-evidence article {
  max-width: 760px;
}

.eiq-command-v4-evidence article span {
  display: inline-flex;
  padding: 5px 9px;
  border: 1px solid rgba(246, 243, 234, 0.12);
  border-radius: 999px;
  color: rgba(246, 243, 234, 0.68);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.eiq-command-v4-evidence h3 {
  margin: 14px 0 0;
  font-size: 26px;
  line-height: 1.08;
  letter-spacing: -0.045em;
}

.eiq-command-v4-evidence p {
  margin: 14px 0 0;
  color: rgba(246, 243, 234, 0.66);
  font-size: 15px;
  line-height: 1.65;
}

.eiq-command-v4-evidence__metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 28px;
}

.eiq-command-v4-evidence__metrics div {
  padding-top: 12px;
  border-top: 1px solid rgba(246, 243, 234, 0.10);
}

.eiq-command-v4-rail {
  position: sticky;
  top: 24px;
  padding: 20px;
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid rgba(246, 243, 234, 0.08);
  border-radius: 24px;
}

.eiq-command-v4-rail__group {
  display: grid;
  gap: 8px;
  padding: 18px 0;
  border-top: 1px solid rgba(246, 243, 234, 0.08);
}

.eiq-command-v4-rail__group > span {
  color: rgba(246, 243, 234, 0.44);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.eiq-command-v4-rail__group article {
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr);
  column-gap: 10px;
  align-items: center;
  padding: 8px 0;
}

.eiq-command-v4-rail__group article i {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: rgba(246, 243, 234, 0.62);
}

.eiq-command-v4-rail__group article strong {
  font-size: 12px;
}

.eiq-command-v4-rail__group article small {
  grid-column: 2;
  color: rgba(246, 243, 234, 0.42);
  font-size: 10px;
  font-weight: 800;
  text-transform: uppercase;
}

.eiq-command-v4-rail footer {
  padding-top: 18px;
  border-top: 1px solid rgba(246, 243, 234, 0.08);
}

@media (max-width: 1180px) {
  .eiq-command-v4__layout,
  .eiq-command-v4-brief,
  .eiq-command-v4__workbench {
    grid-template-columns: 1fr;
  }

  .eiq-command-v4__findings {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .eiq-command-v4-evidence {
    padding-left: 0;
    border-left: 0;
  }
}
'''

css.write_text(css.read_text(encoding="utf-8") + css_block, encoding="utf-8")

print("[EDGEIQ] COMMAND V4 operational briefing layout built")
