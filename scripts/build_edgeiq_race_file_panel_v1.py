from pathlib import Path
import re

services = Path("src/edgeiq-os/services")
race = Path("src/edgeiq-os/race/EdgeiqRaceWorkspace.tsx")
css = Path("src/styles/edgeiqProductTerminalV1.css")

(services / "race-file.ts").write_text(r'''
import { getOperationalRaceState } from "./intelligence-orchestrator";
import { buildSpeedProfile } from "./speed-profile";
import { buildTrackSignature } from "./track-signature";
import { buildPressureEngine } from "./pressure-engine";
import { buildTempoEngine } from "./tempo-engine";
import { buildPositionEngine } from "./position-engine";

export type RaceFileRunner = {
  no: number;
  runner: string;
  barrier: number;
  rating: string;
  form: string;
  speedProfile: string;
  runnerDNA: string;
  market: string;
  assessment: string;
};

export type RaceFileModel = {
  race: {
    meeting: string;
    raceNumber: number;
    raceName: string;
    distance: string;
    className: string;
    condition: string;
    rail: string;
  };
  raceRead: {
    pressure: string;
    tempo: string;
    position: string;
    trackSignature: string;
    speedProfile: string;
  };
  runners: RaceFileRunner[];
};

export function buildRaceFile(): RaceFileModel {
  const state = getOperationalRaceState();
  const speed = buildSpeedProfile(state);
  const track = buildTrackSignature(state);
  const pressure = buildPressureEngine(state);
  const tempo = buildTempoEngine(state);
  const position = buildPositionEngine(state);

  const runnerNames = [
    state.referenceRunner,
    "Runner Profile 2",
    "Runner Profile 3",
    "Runner Profile 4",
    "Runner Profile 5",
    "Runner Profile 6",
    "Runner Profile 7",
    "Runner Profile 8",
  ].filter(Boolean);

  const runners = runnerNames.map((runner, index) => ({
    no: index + 1,
    runner,
    barrier: index + 2,
    rating: index === 0 ? "Primary watch" : index < 3 ? "Positive" : "Developing",
    form: index === 0 ? "Consistent" : index < 4 ? "Mixed" : "Unknown",
    speedProfile: index === 0 ? speed.confidence : index < 3 ? "Strong" : "Developing",
    runnerDNA: index === 0 ? "Aligned" : index < 4 ? "Neutral" : "Watch",
    market: index === 0 ? "Monitor" : index < 3 ? "Neutral" : "Unconfirmed",
    assessment: index === 0 ? "Key reference runner" : index < 3 ? "Contender profile" : "Needs evidence",
  }));

  return {
    race: {
      meeting: state.meetingName,
      raceNumber: state.raceNumber,
      raceName: state.raceName,
      distance: state.distance,
      className: state.raceClass,
      condition: state.trackCondition,
      rail: state.rail,
    },
    raceRead: {
      pressure: pressure.band,
      tempo: tempo.band,
      position: position.position,
      trackSignature: track.todayPattern,
      speedProfile: speed.confidence,
    },
    runners,
  };
}
'''.lstrip(), encoding="utf-8")

race_file_component = Path("src/edgeiq-os/race/RaceFilePanel.tsx")

race_file_component.write_text(r'''
import { buildRaceFile } from "../services/race-file";

const raceFile = buildRaceFile();

export function RaceFilePanel() {
  return (
    <section className="eiq-race-file">
      <header>
        <span>Race File</span>
        <strong>Details, form and ratings</strong>
        <p>
          A racing-first view of the field: race conditions, ratings, form, SpeedProfile,
          RunnerDNA, MarketBehaviour and the current EDGEiQ assessment.
        </p>
      </header>

      <div className="eiq-race-file__details">
        <article><span>Meeting</span><strong>{raceFile.race.meeting}</strong></article>
        <article><span>Race</span><strong>R{raceFile.race.raceNumber}</strong></article>
        <article><span>Distance</span><strong>{raceFile.race.distance}</strong></article>
        <article><span>Class</span><strong>{raceFile.race.className}</strong></article>
        <article><span>Track</span><strong>{raceFile.race.condition}</strong></article>
        <article><span>Rail</span><strong>{raceFile.race.rail}</strong></article>
      </div>

      <div className="eiq-race-file__read">
        <article><span>Pressure</span><strong>{raceFile.raceRead.pressure}</strong></article>
        <article><span>Tempo</span><strong>{raceFile.raceRead.tempo}</strong></article>
        <article><span>Position</span><strong>{raceFile.raceRead.position}</strong></article>
        <article><span>TrackSignature</span><strong>{raceFile.raceRead.trackSignature}</strong></article>
        <article><span>SpeedProfile</span><strong>{raceFile.raceRead.speedProfile}</strong></article>
      </div>

      <div className="eiq-race-file__table-wrap">
        <table className="eiq-race-file__table">
          <thead>
            <tr>
              <th>No</th>
              <th>Runner</th>
              <th>Bar</th>
              <th>Rating</th>
              <th>Form</th>
              <th>SpeedProfile</th>
              <th>RunnerDNA</th>
              <th>MarketBehaviour</th>
              <th>EDGEiQ Assessment</th>
            </tr>
          </thead>

          <tbody>
            {raceFile.runners.map((runner) => (
              <tr key={`${runner.no}-${runner.runner}`}>
                <td>{runner.no}</td>
                <td><strong>{runner.runner}</strong></td>
                <td>{runner.barrier}</td>
                <td>{runner.rating}</td>
                <td>{runner.form}</td>
                <td>{runner.speedProfile}</td>
                <td>{runner.runnerDNA}</td>
                <td>{runner.market}</td>
                <td>{runner.assessment}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
'''.lstrip(), encoding="utf-8")

text = race.read_text(encoding="utf-8")

import_line = 'import { RaceFilePanel } from "./RaceFilePanel";'
if import_line not in text:
  text = text.replace('import { IntelligenceReport } from "../intelligence";', 'import { IntelligenceReport } from "../intelligence";\n' + import_line)

tag = '<RaceFilePanel />'
if tag not in text:
  text = text.replace('<section className="eiq-race-os__reports">', tag + '\n\n      <section className="eiq-race-os__reports">')

race.write_text(text, encoding="utf-8")

marker = "EDGEiQ Race File Panel"
existing = css.read_text(encoding="utf-8")

if marker not in existing:
  css.write_text(existing + r'''

/* ==========================================================================
   EDGEiQ Race File Panel
   ========================================================================== */

.eiq-race-file {
  padding: 36px 0 38px;
  border-bottom: 1px solid rgba(246, 243, 234, 0.10);
}

.eiq-race-file > header {
  max-width: 880px;
  margin-bottom: 26px;
}

.eiq-race-file > header span,
.eiq-race-file__details span,
.eiq-race-file__read span {
  display: block;
  color: rgba(246, 243, 234, 0.46);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.15em;
  text-transform: uppercase;
}

.eiq-race-file > header strong {
  display: block;
  margin-top: 10px;
  color: #f6f3ea;
  font-size: clamp(30px, 3vw, 46px);
  line-height: 0.96;
  letter-spacing: -0.06em;
}

.eiq-race-file > header p {
  margin: 14px 0 0;
  color: rgba(246, 243, 234, 0.62);
  font-size: 14px;
  line-height: 1.65;
}

.eiq-race-file__details,
.eiq-race-file__read {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 18px;
  margin-top: 22px;
}

.eiq-race-file__read {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

.eiq-race-file__details article,
.eiq-race-file__read article {
  padding-top: 14px;
  border-top: 1px solid rgba(246, 243, 234, 0.10);
}

.eiq-race-file__details strong,
.eiq-race-file__read strong {
  display: block;
  margin-top: 8px;
  color: #f6f3ea;
  font-size: 16px;
  line-height: 1.1;
  letter-spacing: -0.035em;
}

.eiq-race-file__table-wrap {
  overflow-x: auto;
  margin-top: 30px;
  border: 1px solid rgba(246, 243, 234, 0.08);
  border-radius: 22px;
}

.eiq-race-file__table {
  width: 100%;
  min-width: 1080px;
  border-collapse: collapse;
}

.eiq-race-file__table th,
.eiq-race-file__table td {
  padding: 14px 16px;
  border-bottom: 1px solid rgba(246, 243, 234, 0.075);
  text-align: left;
  font-size: 12px;
  color: rgba(246, 243, 234, 0.68);
}

.eiq-race-file__table th {
  color: rgba(246, 243, 234, 0.46);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.13em;
  text-transform: uppercase;
}

.eiq-race-file__table td strong {
  color: #f6f3ea;
  font-size: 13px;
}

.eiq-race-file__table tbody tr:hover {
  background: rgba(255, 255, 255, 0.026);
}

@media (max-width: 1180px) {
  .eiq-race-file__details,
  .eiq-race-file__read {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
''', encoding="utf-8")

print("[EDGEIQ] Race File Panel built")
