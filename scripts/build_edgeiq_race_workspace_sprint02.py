from pathlib import Path

intel = Path("src/edgeiq-os/intelligence")
services = Path("src/edgeiq-os/services")
race = Path("src/edgeiq-os/race/EdgeiqRaceWorkspace.tsx")
css = Path("src/styles/edgeiqProductTerminalV1.css")

(intel / "IntelligenceReport.tsx").write_text(r'''
import { useState } from "react";

export type IntelligenceEvidence = {
  label: string;
  value: string;
  detail?: string;
};

export type SupportingEngine = {
  label: string;
  status: string;
};

export type IntelligenceReportModel = {
  title: string;
  assessment: string;
  operationalMeaning: string;
  evidence: IntelligenceEvidence[];
  supportingEngines?: SupportingEngine[];
  watch: string[];
  confidence: string;
  lastUpdated: string;
};

type IntelligenceReportProps = {
  report: IntelligenceReportModel;
};

export function IntelligenceReport({ report }: IntelligenceReportProps) {
  const [open, setOpen] = useState(false);

  return (
    <section className="eiq-intel-report eiq-intel-report--v2">
      <header>
        <span>EDGEiQ Intelligence Report</span>
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

        {report.supportingEngines?.length ? (
          <article>
            <span>Supported By</span>
            <div className="eiq-intel-report__engines">
              {report.supportingEngines.map((engine) => (
                <div key={engine.label}>
                  <i />
                  <strong>{engine.label}</strong>
                  <small>{engine.status}</small>
                </div>
              ))}
            </div>
          </article>
        ) : null}

        <article>
          <button className="eiq-intel-report__evidence-toggle" type="button" onClick={() => setOpen(!open)}>
            Evidence {open ? "▲" : "▼"}
          </button>

          {open ? (
            <div className="eiq-intel-report__evidence">
              {report.evidence.map((item) => (
                <div key={`${item.label}-${item.value}`}>
                  <strong>{item.label}</strong>
                  <b>{item.value}</b>
                  {item.detail ? <small>{item.detail}</small> : null}
                </div>
              ))}
            </div>
          ) : null}
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

(services / "speed-profile.ts").write_text(r'''
import type { OperationalRaceState } from "./operational-state";
import { getOperationalRaceState } from "./intelligence-orchestrator";

export type SpeedProfileModel = {
  title: string;
  assessment: string;
  operationalMeaning: string;
  launch: string;
  cruise: string;
  pressureResponse: string;
  finishStrength: string;
  recovery: string;
  confidence: string;
  watch: string[];
};

function band(score: number): string {
  if (score >= 85) return "Elite";
  if (score >= 70) return "Strong";
  if (score >= 55) return "Positive";
  if (score >= 40) return "Developing";
  return "Unknown";
}

export function buildSpeedProfile(raceState: OperationalRaceState = getOperationalRaceState()): SpeedProfileModel {
  const confidence = raceState.confidence;
  const paceEvidence = raceState.evidence.find((item) => item.category === "SECTIONALS" || item.category === "PACE");

  return {
    title: "SpeedProfile",
    assessment: paceEvidence?.summary ?? "SpeedProfile intelligence is forming from available pace, sectional and race-shape evidence.",
    operationalMeaning: "SpeedProfile describes how runners are expected to travel through the race without exposing proprietary sectional calculations.",
    launch: band(confidence - 8),
    cruise: band(confidence),
    pressureResponse: band(confidence - 5),
    finishStrength: band(confidence + 3),
    recovery: band(confidence - 2),
    confidence: band(confidence),
    watch: [
      "Compressed sprint finish",
      "Sustained tempo through middle stages",
      "Runner forced wider than expected",
      "Late race pressure change",
    ],
  };
}
'''.lstrip(), encoding="utf-8")

(services / "track-signature.ts").write_text(r'''
import type { OperationalRaceState } from "./operational-state";
import { getOperationalRaceState } from "./intelligence-orchestrator";

export type TrackSignatureModel = {
  title: string;
  assessment: string;
  operationalMeaning: string;
  rail: string;
  surface: string;
  wind: string;
  moisture: string;
  historicalPattern: string;
  todayPattern: string;
  confidence: string;
  watch: string[];
};

function confidenceLabel(value: number): string {
  if (value >= 85) return "Very High";
  if (value >= 70) return "High";
  if (value >= 55) return "Moderate";
  if (value >= 40) return "Developing";
  return "Low";
}

export function buildTrackSignature(raceState: OperationalRaceState = getOperationalRaceState()): TrackSignatureModel {
  const trackEvidence = raceState.evidence.find((item) => item.category === "TRACK" || item.category === "ENVIRONMENT");

  return {
    title: "TrackSignature",
    assessment: trackEvidence?.summary ?? "TrackSignature is monitoring rail, surface and environment behaviour.",
    operationalMeaning: "TrackSignature explains how today's surface and rail setup may influence tactical advantage without exposing internal bias modelling.",
    rail: raceState.rail || "Monitoring",
    surface: raceState.trackCondition || "Monitoring",
    wind: "Monitoring",
    moisture: raceState.trackCondition?.toLowerCase().includes("soft") || raceState.trackCondition?.toLowerCase().includes("heavy")
      ? "Influential"
      : "Controlled",
    historicalPattern: "Reserved",
    todayPattern: trackEvidence ? "Active" : "Building",
    confidence: confidenceLabel(raceState.confidence),
    watch: [
      "Track downgrade",
      "Rail pattern shift",
      "Wind change",
      "Inside or outside lane advantage emerging",
    ],
  };
}
'''.lstrip(), encoding="utf-8")

(services / "intelligence-report.ts").write_text(r'''
import type { IntelligenceReportModel } from "../intelligence";
import type { OperationalRaceState } from "./operational-state";
import { getOperationalRaceState } from "./intelligence-orchestrator";
import { buildPressureEngine } from "./pressure-engine";
import { buildTempoEngine } from "./tempo-engine";
import { buildPositionEngine } from "./position-engine";
import { buildSpeedProfile } from "./speed-profile";
import { buildTrackSignature } from "./track-signature";

export function buildRaceFlowReport(
  raceState: OperationalRaceState = getOperationalRaceState(),
): IntelligenceReportModel {
  const pressure = buildPressureEngine(raceState);
  const tempo = buildTempoEngine(raceState);
  const position = buildPositionEngine(raceState);
  const speed = buildSpeedProfile(raceState);
  const track = buildTrackSignature(raceState);

  return {
    title: "RaceFlow",
    assessment: `${pressure.summary} ${tempo.raceRead}`,
    operationalMeaning: `${pressure.tacticalRead} ${position.tacticalRead}`,
    supportingEngines: [
      { label: "Pressure Engine", status: pressure.band },
      { label: "Tempo Engine", status: tempo.band },
      { label: "Position Engine", status: position.position },
      { label: "SpeedProfile", status: speed.confidence },
      { label: "TrackSignature", status: track.todayPattern },
    ],
    evidence: [
      { label: "Pressure Engine", value: pressure.band, detail: pressure.summary },
      { label: "Tempo Engine", value: tempo.band, detail: tempo.expectedChange },
      { label: "Position Engine", value: position.position, detail: position.summary },
      { label: "Lane Read", value: position.lane, detail: "Lane evidence is shown without proprietary weighting." },
      { label: "SpeedProfile", value: speed.confidence, detail: speed.assessment },
      { label: "TrackSignature", value: track.todayPattern, detail: track.assessment },
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

export function buildSpeedProfileReport(
  raceState: OperationalRaceState = getOperationalRaceState(),
): IntelligenceReportModel {
  const speed = buildSpeedProfile(raceState);

  return {
    title: "SpeedProfile",
    assessment: speed.assessment,
    operationalMeaning: speed.operationalMeaning,
    supportingEngines: [
      { label: "Launch", status: speed.launch },
      { label: "Cruise", status: speed.cruise },
      { label: "Pressure Response", status: speed.pressureResponse },
      { label: "Finish Strength", status: speed.finishStrength },
      { label: "Recovery", status: speed.recovery },
    ],
    evidence: [
      { label: "Launch", value: speed.launch, detail: "Early acceleration profile." },
      { label: "Cruise", value: speed.cruise, detail: "Sustained travel through the race." },
      { label: "Pressure Response", value: speed.pressureResponse, detail: "Ability to maintain efficiency under pressure." },
      { label: "Finish Strength", value: speed.finishStrength, detail: "Late-race closing capability." },
      { label: "Recovery", value: speed.recovery, detail: "Ability to absorb the race shape." },
    ],
    watch: speed.watch,
    confidence: speed.confidence,
    lastUpdated: "Live",
  };
}

export function buildTrackSignatureReport(
  raceState: OperationalRaceState = getOperationalRaceState(),
): IntelligenceReportModel {
  const track = buildTrackSignature(raceState);

  return {
    title: "TrackSignature",
    assessment: track.assessment,
    operationalMeaning: track.operationalMeaning,
    supportingEngines: [
      { label: "Rail", status: track.rail },
      { label: "Surface", status: track.surface },
      { label: "Moisture", status: track.moisture },
      { label: "Today Pattern", status: track.todayPattern },
    ],
    evidence: [
      { label: "Rail", value: track.rail, detail: "Rail setup included as evidence." },
      { label: "Surface", value: track.surface, detail: "Current track condition." },
      { label: "Wind", value: track.wind, detail: "Environment component reserved for active feed." },
      { label: "Moisture", value: track.moisture, detail: "Moisture influence interpreted at assessment level." },
      { label: "Historical Pattern", value: track.historicalPattern, detail: "Historical bias evidence reserved." },
      { label: "Today Pattern", value: track.todayPattern, detail: "Current-day pattern status." },
    ],
    watch: track.watch,
    confidence: track.confidence,
    lastUpdated: "Live",
  };
}
'''.lstrip(), encoding="utf-8")

race.write_text(r'''
import { WorkspaceHeader, BriefSection, SectionHeader } from "../design-system";
import { IntelligenceReport } from "../intelligence";
import { buildRaceViewModel } from "../services/race-view-model";
import { buildPressureEngine } from "../services/pressure-engine";
import { buildTempoEngine } from "../services/tempo-engine";
import { buildPositionEngine } from "../services/position-engine";
import {
  buildRaceFlowReport,
  buildSpeedProfileReport,
  buildTrackSignatureReport,
} from "../services/intelligence-report";

const race = buildRaceViewModel();
const pressure = buildPressureEngine();
const tempo = buildTempoEngine();
const position = buildPositionEngine();

const reports = [
  buildRaceFlowReport(),
  buildSpeedProfileReport(),
  buildTrackSignatureReport(),
];

const intelligence = [
  { label: "RaceFlow", value: pressure.band, note: pressure.tacticalRead },
  { label: "SpeedProfile", value: tempo.band, note: tempo.expectedChange },
  { label: "TrackSignature", value: race.race.condition, note: race.race.rail },
  { label: "Position", value: position.position, note: position.tacticalRead },
];

const projection = [
  { stage: "Launch", value: pressure.zones[0]?.pressure ?? "BUILDING", note: "Early pressure" },
  { stage: "Pressure Build", value: pressure.band, note: "Opening tactical pressure" },
  { stage: "Settling", value: position.position, note: "Expected tactical position" },
  { stage: "Mid Race", value: pressure.zones[1]?.pressure ?? "BUILDING", note: "Race rhythm" },
  { stage: "Turn", value: position.lane, note: "Lane and cover watch" },
  { stage: "Straight", value: tempo.band, note: "Late tempo read" },
  { stage: "Finish", value: race.hero.decision, note: "Operational decision" },
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
        <SectionHeader eyebrow="Tactical Intelligence" title="EDGEiQ Intelligence Stack" meta="Evidence visible / formula protected" />

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

      <section className="eiq-race-os__projection eiq-race-os__projection--v2">
        <SectionHeader eyebrow="Projection Canvas" title="RaceFlow Projection" meta="Animation-ready data" />

        <div className="eiq-race-os__flow">
          {projection.map((item, index) => (
            <article key={item.stage}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <strong>{item.stage}</strong>
              <b>{item.value}</b>
              <p>{item.note}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="eiq-race-os__reports">
        {reports.map((report) => (
          <IntelligenceReport key={report.title} report={report} />
        ))}
      </section>
    </section>
  );
}
'''.lstrip(), encoding="utf-8")

css_block = r'''

/* ==========================================================================
   EDGEiQ Race Workspace Sprint 02
   ========================================================================== */

.eiq-intel-report--v2 {
  margin-top: 0;
}

.eiq-intel-report__engines {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
  margin-top: 14px;
}

.eiq-intel-report__engines div {
  padding-top: 12px;
  border-top: 1px solid rgba(246, 243, 234, 0.11);
}

.eiq-intel-report__engines i {
  display: block;
  width: 7px;
  height: 7px;
  margin-bottom: 10px;
  border-radius: 999px;
  background: #7edc9b;
}

.eiq-intel-report__engines strong,
.eiq-intel-report__engines small {
  display: block;
}

.eiq-intel-report__engines strong {
  color: #f6f3ea;
  font-size: 12px;
}

.eiq-intel-report__engines small {
  margin-top: 5px;
  color: rgba(246, 243, 234, 0.52);
  font-size: 11px;
  line-height: 1.35;
}

.eiq-intel-report__evidence-toggle {
  appearance: none;
  padding: 0;
  color: rgba(246, 243, 234, 0.72);
  background: transparent;
  border: 0;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  cursor: pointer;
}

.eiq-race-os__projection--v2 {
  padding-bottom: 44px;
}

.eiq-race-os__flow {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 12px;
  margin-top: 22px;
}

.eiq-race-os__flow article {
  min-height: 250px;
  padding: 16px;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.018));
  border: 1px solid rgba(246, 243, 234, 0.10);
  border-radius: 22px;
}

.eiq-race-os__flow span {
  display: block;
  color: rgba(246, 243, 234, 0.42);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.eiq-race-os__flow strong {
  display: block;
  margin-top: 14px;
  color: #f6f3ea;
  font-size: 16px;
  letter-spacing: -0.035em;
}

.eiq-race-os__flow b {
  display: block;
  margin-top: 58px;
  color: #f6f3ea;
  font-size: 23px;
  letter-spacing: -0.055em;
}

.eiq-race-os__flow p {
  margin: 12px 0 0;
  color: rgba(246, 243, 234, 0.52);
  font-size: 11px;
  line-height: 1.45;
}

.eiq-race-os__reports {
  display: grid;
  gap: 0;
}

@media (max-width: 1380px) {
  .eiq-race-os__flow {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .eiq-intel-report__engines {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .eiq-race-os__flow,
  .eiq-intel-report__engines {
    grid-template-columns: 1fr;
  }
}
'''

css.write_text(css.read_text(encoding="utf-8") + css_block, encoding="utf-8")

print("[EDGEIQ] Race Workspace Sprint 02 built")
