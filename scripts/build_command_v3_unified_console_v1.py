from pathlib import Path

components = Path("src/edgeiq-os/command/components")

(components / "UnifiedCommandBrief.tsx").write_text(r'''
import type { OperationalRaceState } from "../../services/operational-state";
import { composeExecutiveBrief } from "../../services/executive-brief";

type UnifiedCommandBriefProps = {
  raceState: OperationalRaceState;
};

export function UnifiedCommandBrief({ raceState }: UnifiedCommandBriefProps) {
  const brief = composeExecutiveBrief(raceState);

  return (
    <section className="eiq-command-v3-brief">
      <div className="eiq-command-v3-brief__decision">
        <span>Decision</span>
        <strong>{raceState.decision.state}</strong>
        <small>{raceState.confidence}% operational confidence</small>
      </div>

      <div className="eiq-command-v3-brief__copy">
        <span>Executive Command Brief</span>
        <p>{brief.currentSituation}</p>
        <b>{brief.recommendedAction}</b>
      </div>

      <div className="eiq-command-v3-brief__metrics">
        <article><span>Priority</span><strong>{raceState.decision.priority}</strong></article>
        <article><span>Consensus</span><strong>{brief.evidenceAlignment}</strong></article>
        <article><span>Coverage</span><strong>{brief.evidenceAvailable}</strong></article>
        <article><span>Feeds</span><strong>{raceState.executiveSummary.systemHealth.feedsReady}/{raceState.executiveSummary.systemHealth.feedsTotal}</strong></article>
      </div>
    </section>
  );
}
''', encoding="utf-8")

(components / "IntelligenceExplorer.tsx").write_text(r'''
import type { OperationalEvidenceItem, OperationalRaceState } from "../../services/operational-state";

type IntelligenceExplorerProps = {
  raceState: OperationalRaceState;
  activeEvidence: string;
  onSelect: (title: string) => void;
};

function categoryLabel(category: string): string {
  return category.replaceAll("_", " ");
}

export function IntelligenceExplorer({ raceState, activeEvidence, onSelect }: IntelligenceExplorerProps) {
  const grouped = raceState.evidence.reduce<Record<string, OperationalEvidenceItem[]>>((acc, item) => {
    const key = item.category;
    acc[key] = acc[key] ?? [];
    acc[key].push(item);
    return acc;
  }, {});

  return (
    <section className="eiq-intelligence-explorer">
      <header>
        <span>Intelligence Explorer</span>
        <strong>{Object.keys(grouped).length} engines</strong>
      </header>

      <div className="eiq-intelligence-explorer__list">
        {Object.entries(grouped).map(([category, items]) => {
          const readyCount = items.filter((item) => item.status === "READY").length;
          const selected = items.some((item) => item.title === activeEvidence);

          return (
            <button
              key={category}
              type="button"
              className={selected ? "is-active" : ""}
              onClick={() => onSelect(items[0]?.title ?? "")}
            >
              <span>{categoryLabel(category)}</span>
              <strong>{readyCount > 0 ? "READY" : "PENDING"}</strong>
              <small>{items.length} evidence item(s)</small>
            </button>
          );
        })}
      </div>
    </section>
  );
}
''', encoding="utf-8")

(components / "EvidenceWorkspace.tsx").write_text(r'''
import type { OperationalEvidenceItem } from "../../services/operational-state";

type EvidenceWorkspaceProps = {
  evidence: OperationalEvidenceItem[];
  activeEvidence: string;
};

export function EvidenceWorkspace({ evidence, activeEvidence }: EvidenceWorkspaceProps) {
  const item = evidence.find((entry) => entry.title === activeEvidence) ?? evidence[0];

  if (!item) {
    return (
      <section className="eiq-evidence-workspace">
        <header><span>Evidence Workspace</span><strong>No evidence selected</strong></header>
      </section>
    );
  }

  return (
    <section className="eiq-evidence-workspace">
      <header>
        <span>Evidence Workspace</span>
        <strong>{item.category.replaceAll("_", " ")}</strong>
      </header>

      <article>
        <span>{item.status}</span>
        <h3>{item.title}</h3>
        <p>{item.summary}</p>
      </article>

      <div className="eiq-evidence-workspace__metrics">
        <div><span>Confidence</span><strong>{item.confidence}</strong></div>
        <div><span>Importance</span><strong>{item.importance}/100</strong></div>
        <div><span>Status</span><strong>{item.status}</strong></div>
      </div>
    </section>
  );
}
''', encoding="utf-8")

workspace = Path("src/edgeiq-os/command/EdgeiqCommandWorkspace.tsx")
workspace.write_text(r'''
import { useState } from "react";
import { LiveStatusStrip } from "./components/LiveStatusStrip";
import { UnifiedCommandBrief } from "./components/UnifiedCommandBrief";
import { IntelligenceExplorer } from "./components/IntelligenceExplorer";
import { EvidenceWorkspace } from "./components/EvidenceWorkspace";
import { OperationalInbox } from "./components/OperationalInbox";
import { OperationalAlertsBar } from "./components/OperationalAlertsBar";
import { OperationalStateRail } from "./components/OperationalStateRail";
import { getOperationalRaceState } from "../services/intelligence-orchestrator";

const raceState = getOperationalRaceState();

const liveStatus = [
  { label: "Decision", value: raceState.decision.state, tone: "info" },
  { label: "Confidence", value: `${raceState.confidence}%`, tone: "good" },
  { label: "Consensus", value: raceState.correlation.agreementBand, tone: "neutral" },
  { label: "Feeds", value: `${raceState.executiveSummary.systemHealth.feedsReady}/${raceState.executiveSummary.systemHealth.feedsTotal}`, tone: "info" },
];

export function EdgeiqCommandWorkspace() {
  const [activeEvidence, setActiveEvidence] = useState<string>(raceState.evidence[0]?.title ?? "");

  return (
    <section className="eiq-command-v3-shell">
      <header className="eiq-command-v3-shell__header">
        <div>
          <span>Victoria</span>
          <h1>COMMAND</h1>
          <strong>{raceState.raceName}</strong>
        </div>

        <LiveStatusStrip items={liveStatus} />
      </header>

      <OperationalAlertsBar raceState={raceState} />

      <main className="eiq-command-v3-shell__grid">
        <section className="eiq-command-v3-shell__primary">
          <UnifiedCommandBrief raceState={raceState} />

          <section className="eiq-command-v3-findings">
            <header>
              <span>Key Findings</span>
              <strong>{raceState.findings.length}</strong>
            </header>

            {raceState.findings.slice(0, 4).map((finding) => (
              <article key={finding.id}>
                <span>{finding.priority}</span>
                <strong>{finding.title}</strong>
                <p>{finding.summary}</p>
              </article>
            ))}
          </section>

          <section className="eiq-command-v3-explorer-grid">
            <IntelligenceExplorer
              raceState={raceState}
              activeEvidence={activeEvidence}
              onSelect={setActiveEvidence}
            />
            <EvidenceWorkspace evidence={raceState.evidence} activeEvidence={activeEvidence} />
          </section>
        </section>

        <aside className="eiq-command-v3-shell__events">
          <OperationalInbox events={raceState.events} />
        </aside>

        <aside className="eiq-command-v3-shell__rail">
          <OperationalStateRail raceState={raceState} />
        </aside>
      </main>
    </section>
  );
}
''', encoding="utf-8")

css = Path("src/styles/edgeiqProductTerminalV1.css")
text = css.read_text(encoding="utf-8", errors="ignore")

addition = r'''

/* EDGEIQ OS V3 Unified COMMAND */
.eiq-command-v3-shell {
  display: grid;
  gap: 16px;
}

.eiq-command-v3-shell__header {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 18px;
  align-items: end;
}

.eiq-command-v3-shell__header span {
  color: rgba(255,255,255,0.46);
  text-transform: uppercase;
  letter-spacing: 0.18em;
  font-size: 11px;
}

.eiq-command-v3-shell__header h1 {
  margin: 4px 0;
  color: #fff;
  letter-spacing: 0.14em;
  font-size: 24px;
}

.eiq-command-v3-shell__header strong {
  color: rgba(255,255,255,0.72);
}

.eiq-command-v3-shell__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px 250px;
  gap: 16px;
  align-items: start;
}

.eiq-command-v3-shell__primary {
  display: grid;
  gap: 16px;
}

.eiq-command-v3-shell__events,
.eiq-command-v3-shell__rail {
  position: sticky;
  top: 18px;
}

.eiq-command-v3-brief {
  border: 1px solid rgba(255,255,255,0.1);
  background:
    linear-gradient(135deg, rgba(110,231,183,0.08), transparent 38%),
    rgba(8,12,18,0.86);
  border-radius: 24px;
  padding: 22px;
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 20px;
}

.eiq-command-v3-brief__decision span,
.eiq-command-v3-brief__copy span,
.eiq-command-v3-brief__metrics span,
.eiq-command-v3-findings header span,
.eiq-intelligence-explorer header span,
.eiq-evidence-workspace header span {
  color: rgba(255,255,255,0.52);
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.eiq-command-v3-brief__decision strong {
  display: block;
  margin: 10px 0 4px;
  color: #fff;
  font-size: 42px;
  letter-spacing: -0.05em;
}

.eiq-command-v3-brief__decision small {
  color: #6ee7b7;
  font-size: 13px;
}

.eiq-command-v3-brief__copy p {
  margin: 8px 0 14px;
  color: rgba(255,255,255,0.84);
  font-size: 18px;
  line-height: 1.5;
}

.eiq-command-v3-brief__copy b {
  color: #fff;
  font-size: 15px;
}

.eiq-command-v3-brief__metrics {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  border-top: 1px solid rgba(255,255,255,0.08);
  padding-top: 16px;
  gap: 12px;
}

.eiq-command-v3-brief__metrics article {
  border-left: 2px solid rgba(110,231,183,0.35);
  padding-left: 12px;
}

.eiq-command-v3-brief__metrics strong {
  display: block;
  margin-top: 6px;
  color: #fff;
}

.eiq-command-v3-findings,
.eiq-intelligence-explorer,
.eiq-evidence-workspace {
  border: 1px solid rgba(255,255,255,0.09);
  background: rgba(8,12,18,0.72);
  border-radius: 20px;
  padding: 18px;
}

.eiq-command-v3-findings header,
.eiq-intelligence-explorer header,
.eiq-evidence-workspace header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 14px;
}

.eiq-command-v3-findings header strong,
.eiq-intelligence-explorer header strong,
.eiq-evidence-workspace header strong {
  color: #fff;
}

.eiq-command-v3-findings article {
  border-top: 1px solid rgba(255,255,255,0.07);
  padding: 14px 0;
}

.eiq-command-v3-findings article span {
  color: #f4c36a;
  font-size: 11px;
  letter-spacing: 0.12em;
}

.eiq-command-v3-findings article strong {
  display: block;
  color: #fff;
  margin: 5px 0;
}

.eiq-command-v3-findings article p {
  margin: 0;
  color: rgba(255,255,255,0.68);
  line-height: 1.45;
}

.eiq-command-v3-explorer-grid {
  display: grid;
  grid-template-columns: 310px minmax(0, 1fr);
  gap: 16px;
}

.eiq-intelligence-explorer__list {
  display: grid;
  gap: 8px;
}

.eiq-intelligence-explorer__list button {
  text-align: left;
  border: 1px solid rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.03);
  color: #fff;
  border-radius: 14px;
  padding: 12px;
  cursor: pointer;
}

.eiq-intelligence-explorer__list button.is-active {
  border-color: rgba(110,231,183,0.45);
  background: rgba(110,231,183,0.08);
}

.eiq-intelligence-explorer__list button span,
.eiq-intelligence-explorer__list button strong,
.eiq-intelligence-explorer__list button small {
  display: block;
}

.eiq-intelligence-explorer__list button span {
  font-weight: 800;
}

.eiq-intelligence-explorer__list button strong {
  margin-top: 5px;
  color: #6ee7b7;
  font-size: 11px;
}

.eiq-intelligence-explorer__list button small {
  margin-top: 4px;
  color: rgba(255,255,255,0.48);
}

.eiq-evidence-workspace article span {
  color: #6ee7b7;
  font-size: 11px;
  letter-spacing: 0.12em;
}

.eiq-evidence-workspace h3 {
  color: #fff;
  font-size: 24px;
  margin: 8px 0;
}

.eiq-evidence-workspace p {
  color: rgba(255,255,255,0.72);
  line-height: 1.55;
}

.eiq-evidence-workspace__metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 18px;
}

.eiq-evidence-workspace__metrics div {
  border-top: 1px solid rgba(255,255,255,0.08);
  padding-top: 12px;
}

.eiq-evidence-workspace__metrics span,
.eiq-evidence-workspace__metrics strong {
  display: block;
}

.eiq-evidence-workspace__metrics span {
  color: rgba(255,255,255,0.48);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.eiq-evidence-workspace__metrics strong {
  color: #fff;
  margin-top: 6px;
}
'''

if "EDGEIQ OS V3 Unified COMMAND" not in text:
    text += addition

css.write_text(text, encoding="utf-8")

print("[EDGEIQ] COMMAND V3 unified operations console built")
