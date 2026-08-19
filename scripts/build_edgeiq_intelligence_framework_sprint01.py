from pathlib import Path

intel_dir = Path("src/edgeiq-os/intelligence")
intel_dir.mkdir(parents=True, exist_ok=True)

css = Path("src/styles/edgeiqProductTerminalV1.css")
race_workspace = Path("src/edgeiq-os/race/EdgeiqRaceWorkspace.tsx")
race_workspace.parent.mkdir(parents=True, exist_ok=True)

shell = Path("src/edgeiq-os/shell/EdgeiqOsShell.tsx")

(intel_dir / "IntelligenceReport.tsx").write_text(r'''
export type IntelligenceEvidence = {
  label: string;
  value: string;
  detail?: string;
};

export type IntelligenceReportModel = {
  title: string;
  assessment: string;
  operationalMeaning: string;
  evidence: IntelligenceEvidence[];
  watch: string[];
  confidence: string;
  lastUpdated: string;
};

type IntelligenceReportProps = {
  report: IntelligenceReportModel;
};

export function IntelligenceReport({ report }: IntelligenceReportProps) {
  return (
    <section className="eiq-intel-report">
      <header>
        <span>Intelligence Report</span>
        <strong>{report.title}</strong>
      </header>

      <div className="eiq-intel-report__body">
        <article>
          <span>Assessment</span>
          <p>{report.assessment}</p>
        </article>

        <article>
          <span>Operational Meaning</span>
          <p>{report.operationalMeaning}</p>
        </article>

        <article>
          <span>Supporting Evidence</span>
          <div className="eiq-intel-report__evidence">
            {report.evidence.map((item) => (
              <div key={`${item.label}-${item.value}`}>
                <strong>{item.label}</strong>
                <b>{item.value}</b>
                {item.detail ? <small>{item.detail}</small> : null}
              </div>
            ))}
          </div>
        </article>

        <article>
          <span>Things To Watch</span>
          <ul>
            {report.watch.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>

        <footer>
          <div>
            <span>Confidence</span>
            <strong>{report.confidence}</strong>
          </div>
          <div>
            <span>Updated</span>
            <strong>{report.lastUpdated}</strong>
          </div>
        </footer>
      </div>
    </section>
  );
}
'''.lstrip(), encoding="utf-8")

(intel_dir / "index.ts").write_text(r'''
export * from "./IntelligenceReport";
'''.lstrip(), encoding="utf-8")

report_service = Path("src/edgeiq-os/services/intelligence-report.ts")
report_service.write_text(r'''
import type { IntelligenceReportModel } from "../intelligence";
import type { OperationalRaceState } from "./operational-state";
import { getOperationalRaceState } from "./intelligence-orchestrator";
import { buildPressureEngine } from "./pressure-engine";
import { buildTempoEngine } from "./tempo-engine";
import { buildPositionEngine } from "./position-engine";

export function buildRaceFlowReport(
  raceState: OperationalRaceState = getOperationalRaceState(),
): IntelligenceReportModel {
  const pressure = buildPressureEngine(raceState);
  const tempo = buildTempoEngine(raceState);
  const position = buildPositionEngine(raceState);

  return {
    title: "RaceFlow",
    assessment: `${pressure.summary} ${tempo.raceRead}`,
    operationalMeaning: `${pressure.tacticalRead} ${position.tacticalRead}`,
    evidence: [
      {
        label: "Pressure Engine",
        value: pressure.band,
        detail: pressure.summary,
      },
      {
        label: "Tempo Engine",
        value: tempo.band,
        detail: tempo.expectedChange,
      },
      {
        label: "Position Engine",
        value: position.position,
        detail: position.summary,
      },
      {
        label: "Lane Read",
        value: position.lane,
        detail: "Lane intelligence is shown as evidence, not as proprietary calculation.",
      },
    ],
    watch: [
      ...pressure.watch.slice(0, 2),
      ...tempo.watch.slice(0, 2),
      ...position.watch.slice(0, 2),
    ],
    confidence: pressure.confidence,
    lastUpdated: "Live",
  };
}
'''.lstrip(), encoding="utf-8")

race_workspace.write_text(r'''
import { WorkspaceHeader, BriefSection, SectionHeader } from "../design-system";
import { IntelligenceReport } from "../intelligence";
import { buildRaceViewModel } from "../services/race-view-model";
import { buildPressureEngine } from "../services/pressure-engine";
import { buildTempoEngine } from "../services/tempo-engine";
import { buildPositionEngine } from "../services/position-engine";
import { buildRaceFlowReport } from "../services/intelligence-report";

const race = buildRaceViewModel();
const pressure = buildPressureEngine();
const tempo = buildTempoEngine();
const position = buildPositionEngine();
const raceFlowReport = buildRaceFlowReport();

const intelligence = [
  {
    label: "Pressure Engine",
    value: pressure.band,
    note: pressure.tacticalRead,
  },
  {
    label: "Tempo Engine",
    value: tempo.band,
    note: tempo.expectedChange,
  },
  {
    label: "Position Engine",
    value: position.position,
    note: position.tacticalRead,
  },
  {
    label: "Operational Decision",
    value: race.hero.decision,
    note: `${race.hero.confidence} confidence`,
  },
];

export function EdgeiqRaceWorkspace() {
  return (
    <section className="eiq-race-os">
      <WorkspaceHeader
        eyebrow="EDGEiQ RaceFlow"
        title="RACE"
        subtitle={`${race.race.meeting} R${race.race.raceNumber} · ${race.race.distance} · ${race.race.condition}`}
      />

      <BriefSection
        label="Race Situation"
        title={race.hero.title}
        body={race.hero.situation}
        action={`${race.hero.decision}. ${race.hero.confidence} confidence.`}
      />

      <section className="eiq-race-os__section">
        <SectionHeader
          eyebrow="Tactical Intelligence"
          title="RaceFlow Intelligence"
          meta="Evidence visible / formula protected"
        />

        <div className="eiq-race-os__strip">
          {intelligence.map((item) => (
            <article key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <p>{item.note}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="eiq-race-os__projection">
        <SectionHeader
          eyebrow="Projection Canvas"
          title="Tactical Projection"
          meta="Animation layer reserved"
        />

        <div className="eiq-race-os__canvas">
          <div>
            <span>Launch</span>
            <strong>{pressure.zones[0]?.pressure ?? "BUILDING"}</strong>
          </div>
          <div>
            <span>Mid Race</span>
            <strong>{pressure.zones[1]?.pressure ?? "BUILDING"}</strong>
          </div>
          <div>
            <span>Late</span>
            <strong>{pressure.zones[2]?.pressure ?? "BUILDING"}</strong>
          </div>
          <div>
            <span>Finish</span>
            <strong>{tempo.band}</strong>
          </div>
        </div>
      </section>

      <IntelligenceReport report={raceFlowReport} />
    </section>
  );
}
'''.lstrip(), encoding="utf-8")

if shell.exists():
    text = shell.read_text(encoding="utf-8")

    if "EdgeiqRaceWorkspace" not in text:
        text = text.replace(
            'import { EdgeiqOsHome } from "../home/EdgeiqOsHome";',
            'import { EdgeiqOsHome } from "../home/EdgeiqOsHome";\nimport { EdgeiqRaceWorkspace } from "../race/EdgeiqRaceWorkspace";'
        )

    replacements = [
        ('raceView === "RACE"', 'raceView === "RACE"'),
        ('raceView === "MAP"', 'raceView === "RACE"'),
    ]

    for old, new in replacements:
        text = text.replace(old, new)

    marker_candidates = [
        'if (raceView === "COMMAND")',
        'raceView === "COMMAND"',
    ]

    if "EdgeiqRaceWorkspace />" not in text:
        text = text.replace(
            'if (raceView === "COMMAND") {',
            'if (raceView === "RACE") {\n    return <EdgeiqRaceWorkspace />;\n  }\n\n  if (raceView === "COMMAND") {'
        )

    shell.write_text(text, encoding="utf-8")

css_block = r'''

/* ==========================================================================
   EDGEiQ Intelligence Framework Sprint 01
   ========================================================================== */

.eiq-intel-report {
  padding: 34px 0 38px;
  border-bottom: 1px solid rgba(246, 243, 234, 0.10);
}

.eiq-intel-report > header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 24px;
}

.eiq-intel-report > header span,
.eiq-intel-report article span,
.eiq-intel-report footer span,
.eiq-race-os__strip span,
.eiq-race-os__canvas span {
  display: block;
  color: rgba(246, 243, 234, 0.46);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.15em;
  text-transform: uppercase;
}

.eiq-intel-report > header strong {
  color: #f6f3ea;
  font-size: 26px;
  letter-spacing: -0.045em;
}

.eiq-intel-report__body {
  display: grid;
  gap: 24px;
}

.eiq-intel-report article {
  padding-top: 18px;
  border-top: 1px solid rgba(246, 243, 234, 0.085);
}

.eiq-intel-report article p {
  max-width: 920px;
  margin: 10px 0 0;
  color: rgba(246, 243, 234, 0.76);
  font-size: 15px;
  line-height: 1.65;
}

.eiq-intel-report__evidence {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
  margin-top: 14px;
}

.eiq-intel-report__evidence div {
  padding-top: 14px;
  border-top: 1px solid rgba(246, 243, 234, 0.11);
}

.eiq-intel-report__evidence strong {
  display: block;
  color: rgba(246, 243, 234, 0.66);
  font-size: 12px;
}

.eiq-intel-report__evidence b {
  display: block;
  margin-top: 8px;
  color: #f6f3ea;
  font-size: 22px;
  letter-spacing: -0.045em;
}

.eiq-intel-report__evidence small {
  display: block;
  margin-top: 8px;
  color: rgba(246, 243, 234, 0.46);
  font-size: 11px;
  line-height: 1.45;
}

.eiq-intel-report ul {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 22px;
  margin: 14px 0 0;
  padding: 0;
  list-style: none;
}

.eiq-intel-report li {
  color: rgba(246, 243, 234, 0.68);
  font-size: 13px;
  line-height: 1.45;
}

.eiq-intel-report li::before {
  content: "• ";
  color: rgba(246, 243, 234, 0.9);
}

.eiq-intel-report footer {
  display: flex;
  gap: 34px;
  padding-top: 20px;
  border-top: 1px solid rgba(246, 243, 234, 0.10);
}

.eiq-intel-report footer strong {
  display: block;
  margin-top: 6px;
  color: #f6f3ea;
  font-size: 16px;
}

.eiq-race-os {
  min-height: 100%;
  padding: 28px;
  color: #f6f3ea;
}

.eiq-race-os__section {
  padding: 32px 0;
  border-bottom: 1px solid rgba(246, 243, 234, 0.10);
}

.eiq-race-os__strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 22px;
}

.eiq-race-os__strip article {
  padding-top: 16px;
  border-top: 1px solid rgba(246, 243, 234, 0.14);
}

.eiq-race-os__strip strong {
  display: block;
  margin-top: 10px;
  color: #f6f3ea;
  font-size: 28px;
  line-height: 0.95;
  letter-spacing: -0.06em;
}

.eiq-race-os__strip p {
  margin: 12px 0 0;
  color: rgba(246, 243, 234, 0.56);
  font-size: 12px;
  line-height: 1.55;
}

.eiq-race-os__projection {
  padding: 34px 0 38px;
  border-bottom: 1px solid rgba(246, 243, 234, 0.10);
}

.eiq-race-os__canvas {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  min-height: 260px;
  gap: 18px;
  align-items: stretch;
  margin-top: 20px;
}

.eiq-race-os__canvas div {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 22px;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.055), rgba(255,255,255,0.018));
  border: 1px solid rgba(246, 243, 234, 0.10);
  border-radius: 24px;
}

.eiq-race-os__canvas strong {
  color: #f6f3ea;
  font-size: 30px;
  letter-spacing: -0.055em;
}

@media (max-width: 1180px) {
  .eiq-intel-report__evidence,
  .eiq-race-os__strip,
  .eiq-race-os__canvas {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
'''

css.write_text(css.read_text(encoding="utf-8") + css_block, encoding="utf-8")

print("[EDGEIQ] Intelligence Framework Sprint 01 built")
