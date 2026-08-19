from pathlib import Path

services = Path("src/edgeiq-os/services")
race = Path("src/edgeiq-os/race")
css = Path("src/styles/edgeiqProductTerminalV1.css")

(services / "race-file-v2.ts").write_text(r'''
import type { RaceFileModelV1, HistoricalRun } from "./race-file-model";
import { getOperationalRaceState } from "./intelligence-orchestrator";
import { buildPressureEngine } from "./pressure-engine";
import { buildTempoEngine } from "./tempo-engine";
import { buildPositionEngine } from "./position-engine";
import { buildSpeedProfile } from "./speed-profile";
import { buildTrackSignature } from "./track-signature";

function sampleRun(index: number, runner: string): HistoricalRun {
  return {
    date: index === 0 ? "2026-06-12" : "2026-05-25",
    track: index === 0 ? "FLEM" : "CAUL",
    race: index === 0 ? "BM84 HCP" : "BM78 HCP",
    distance: index === 0 ? "1400m" : "1300m",
    raceClass: index === 0 ? "BM84" : "BM78",
    condition: index === 0 ? "GOOD 4" : "SOFT 5",
    barrier: index + 3,
    weight: index === 0 ? "58.0kg" : "57.5kg",
    jockey: index === 0 ? "J Allen" : "B Melham",
    sp: index === 0 ? "$5.50" : "$7.00",
    finish: index === 0 ? "2nd" : "4th",
    margin: index === 0 ? "0.4L" : "1.8L",
    officialRaceTime: index === 0 ? "1:22.36" : "1:16.88",
    edgeiqRaceStrength: index === 0 ? 87.4 : 82.1,
    edgeiqRunRating: index === 0 ? 89.6 : 84.8,
    relativePerformance: index === 0 ? "+2.7" : "+0.8",
    positionInRunning: {
      jump: "8th",
      m800: "7th",
      m600: "5th",
      m400: "4th",
      m200: "2nd",
      finish: index === 0 ? "2nd" : "4th",
    },
    speedProfile: [
      { marker: "800m", position: "7th", lengthsVsStandard: "+2.3L", expected: "+2.8L", variance: "+0.5L" },
      { marker: "600m", position: "5th", lengthsVsStandard: "+1.6L", expected: "+2.2L", variance: "+0.6L" },
      { marker: "400m", position: "4th", lengthsVsStandard: "+0.8L", expected: "+1.3L", variance: "+0.5L" },
      { marker: "200m", position: "2nd", lengthsVsStandard: "+0.2L", expected: "+0.6L", variance: "+0.4L" },
      { marker: "FINISH", position: index === 0 ? "2nd" : "4th", lengthsVsStandard: index === 0 ? "-0.1L" : "+1.0L", expected: "+0.0L", variance: index === 0 ? "-0.1L" : "+1.0L" },
    ],
    pressureRating: index === 0 ? 91 : 84,
    tempoRating: index === 0 ? 88 : 80,
    trackSignatureMatch: index === 0 ? "92%" : "81%",
    raceFlowMatch: index === 0 ? "Positive" : "Neutral",
  };
}

export function buildRaceFileV2(): RaceFileModelV1 {
  const state = getOperationalRaceState();
  const pressure = buildPressureEngine(state);
  const tempo = buildTempoEngine(state);
  const position = buildPositionEngine(state);
  const speed = buildSpeedProfile(state);
  const track = buildTrackSignature(state);

  const names = [
    state.referenceRunner || "Reference Runner",
    "Runner Profile 2",
    "Runner Profile 3",
    "Runner Profile 4",
    "Runner Profile 5",
    "Runner Profile 6",
  ];

  return {
    officialRace: {
      meeting: state.meetingName,
      raceNumber: state.raceNumber,
      raceName: state.raceName,
      distance: state.distance,
      raceClass: state.raceClass,
      trackCondition: state.trackCondition,
      rail: state.rail,
      officialRaceTime: "Pending result",
      prizeMoney: "Race file",
    },
    raceRead: {
      raceFlow: position.position,
      pressure: pressure.band,
      tempo: tempo.band,
      trackSignature: track.todayPattern,
      speedProfile: speed.confidence,
      confidence: pressure.confidence,
    },
    field: names.map((runner, index) => ({
      official: {
        no: index + 1,
        runner,
        barrier: index + 2,
        weight: `${58 - index * 0.5}kg`,
        jockey: index === 0 ? "Primary jockey" : "Mapped jockey",
        trainer: index === 0 ? "Primary stable" : "Mapped stable",
        market: index === 0 ? "Monitor" : "Neutral",
        status: "ACTIVE",
      },
      edgeRating: index === 0 ? "89.6" : index < 3 ? "84.0" : "Developing",
      runnerDNA: index === 0 ? "Aligned" : index < 3 ? "Positive" : "Watch",
      speedProfile: index === 0 ? speed.confidence : index < 3 ? "Strong" : "Developing",
      trackSignature: index === 0 ? track.todayPattern : "Neutral",
      raceFlow: index === 0 ? "Positive" : "Monitoring",
      marketBehaviour: index === 0 ? "Monitor" : "Neutral",
      assessment: index === 0 ? "Key reference runner. Historical runs show above-standard SpeedProfile and positive race-strength form." : "Requires more evidence before firm assessment.",
      historicalRuns: [sampleRun(0, runner), sampleRun(1, runner)],
    })),
  };
}
'''.lstrip(), encoding="utf-8")

(race / "RaceFileV2.tsx").write_text(r'''
import { buildRaceFileV2 } from "../services/race-file-v2";

const file = buildRaceFileV2();
const primary = file.field[0];

export function RaceFileV2() {
  return (
    <section className="eiq-race-book">
      <header className="eiq-race-book__header">
        <span>EDGEiQ Race File</span>
        <strong>{file.officialRace.meeting} R{file.officialRace.raceNumber}</strong>
        <p>{file.officialRace.raceName} · {file.officialRace.distance} · {file.officialRace.raceClass} · {file.officialRace.trackCondition} · {file.officialRace.rail}</p>
      </header>

      <section className="eiq-race-book__read">
        <article><span>RaceFlow</span><strong>{file.raceRead.raceFlow}</strong></article>
        <article><span>Pressure</span><strong>{file.raceRead.pressure}</strong></article>
        <article><span>Tempo</span><strong>{file.raceRead.tempo}</strong></article>
        <article><span>TrackSignature</span><strong>{file.raceRead.trackSignature}</strong></article>
        <article><span>SpeedProfile</span><strong>{file.raceRead.speedProfile}</strong></article>
        <article><span>Confidence</span><strong>{file.raceRead.confidence}</strong></article>
      </section>

      <section className="eiq-race-book__field">
        <header>
          <span>Field Overview</span>
          <strong>Official data + EDGEiQ intelligence</strong>
        </header>

        <div className="eiq-race-book__cards">
          {file.field.map((runner) => (
            <article key={runner.official.no}>
              <div className="eiq-race-book__runner-no">{runner.official.no}</div>
              <strong>{runner.official.runner}</strong>
              <p>Bar {runner.official.barrier} · {runner.official.weight} · {runner.official.jockey}</p>

              <dl>
                <div><dt>EDGE Rating</dt><dd>{runner.edgeRating}</dd></div>
                <div><dt>RunnerDNA</dt><dd>{runner.runnerDNA}</dd></div>
                <div><dt>SpeedProfile</dt><dd>{runner.speedProfile}</dd></div>
                <div><dt>RaceFlow</dt><dd>{runner.raceFlow}</dd></div>
                <div><dt>MarketBehaviour</dt><dd>{runner.marketBehaviour}</dd></div>
              </dl>
            </article>
          ))}
        </div>
      </section>

      {primary ? (
        <section className="eiq-runner-file">
          <header>
            <span>Runner File</span>
            <strong>{primary.official.runner}</strong>
            <p>{primary.assessment}</p>
          </header>

          <div className="eiq-runner-file__identity">
            <article><span>Trainer</span><strong>{primary.official.trainer}</strong></article>
            <article><span>Jockey</span><strong>{primary.official.jockey}</strong></article>
            <article><span>Barrier</span><strong>{primary.official.barrier}</strong></article>
            <article><span>Weight</span><strong>{primary.official.weight}</strong></article>
            <article><span>Market</span><strong>{primary.official.market}</strong></article>
          </div>

          <div className="eiq-form-table-wrap">
            <table className="eiq-form-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Track</th>
                  <th>Dist</th>
                  <th>Class</th>
                  <th>Cond</th>
                  <th>Bar</th>
                  <th>Wt</th>
                  <th>Jockey</th>
                  <th>SP</th>
                  <th>Pos</th>
                  <th>Margin</th>
                  <th>Official Time</th>
                  <th>Race Strength™</th>
                  <th>Run Rating™</th>
                  <th>Δ Std</th>
                  <th>800</th>
                  <th>600</th>
                  <th>400</th>
                  <th>200</th>
                  <th>PIR</th>
                </tr>
              </thead>

              <tbody>
                {primary.historicalRuns.map((run) => (
                  <tr key={`${run.date}-${run.track}-${run.race}`}>
                    <td>{run.date}</td>
                    <td>{run.track}</td>
                    <td>{run.distance}</td>
                    <td>{run.raceClass}</td>
                    <td>{run.condition}</td>
                    <td>{run.barrier}</td>
                    <td>{run.weight}</td>
                    <td>{run.jockey}</td>
                    <td>{run.sp}</td>
                    <td>{run.finish}</td>
                    <td>{run.margin}</td>
                    <td>{run.officialRaceTime}</td>
                    <td>{run.edgeiqRaceStrength}</td>
                    <td>{run.edgeiqRunRating}</td>
                    <td>{run.relativePerformance}</td>
                    <td>{run.speedProfile[0]?.lengthsVsStandard}</td>
                    <td>{run.speedProfile[1]?.lengthsVsStandard}</td>
                    <td>{run.speedProfile[2]?.lengthsVsStandard}</td>
                    <td>{run.speedProfile[3]?.lengthsVsStandard}</td>
                    <td>{run.positionInRunning.m800} / {run.positionInRunning.m600} / {run.positionInRunning.m400} / {run.positionInRunning.m200}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </section>
  );
}
'''.lstrip(), encoding="utf-8")

race_ws = race / "EdgeiqRaceWorkspace.tsx"
text = race_ws.read_text(encoding="utf-8")
if 'import { RaceFileV2 } from "./RaceFileV2";' not in text:
    text = text.replace('import { RaceFilePanel } from "./RaceFilePanel";', 'import { RaceFilePanel } from "./RaceFilePanel";\nimport { RaceFileV2 } from "./RaceFileV2";')
if '<RaceFileV2 />' not in text:
    text = text.replace('<RaceFilePanel />', '<RaceFileV2 />')
race_ws.write_text(text, encoding="utf-8")

marker = "EDGEiQ Race File V2"
existing = css.read_text(encoding="utf-8")
if marker not in existing:
    css.write_text(existing + r'''

/* ==========================================================================
   EDGEiQ Race File V2
   ========================================================================== */

.eiq-race-book {
  padding: 38px 0;
  border-bottom: 1px solid rgba(246,243,234,.10);
}

.eiq-race-book__header span,
.eiq-race-book__read span,
.eiq-race-book__field header span,
.eiq-runner-file header span,
.eiq-runner-file__identity span {
  display: block;
  color: rgba(246,243,234,.46);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: .15em;
  text-transform: uppercase;
}

.eiq-race-book__header strong,
.eiq-runner-file header strong {
  display:block;
  margin-top:10px;
  color:#f6f3ea;
  font-size: clamp(34px, 4vw, 58px);
  line-height:.94;
  letter-spacing:-.07em;
}

.eiq-race-book__header p,
.eiq-runner-file header p {
  max-width: 900px;
  margin: 16px 0 0;
  color: rgba(246,243,234,.62);
  font-size: 14px;
  line-height: 1.65;
}

.eiq-race-book__read,
.eiq-runner-file__identity {
  display:grid;
  grid-template-columns: repeat(6, minmax(0,1fr));
  gap:18px;
  margin-top:30px;
}

.eiq-race-book__read article,
.eiq-runner-file__identity article {
  padding-top:15px;
  border-top:1px solid rgba(246,243,234,.10);
}

.eiq-race-book__read strong,
.eiq-runner-file__identity strong {
  display:block;
  margin-top:8px;
  color:#f6f3ea;
  font-size:18px;
  line-height:1.05;
  letter-spacing:-.045em;
}

.eiq-race-book__field,
.eiq-runner-file {
  margin-top:38px;
}

.eiq-race-book__field header strong {
  display:block;
  margin-top:8px;
  color:#f6f3ea;
  font-size:26px;
  letter-spacing:-.05em;
}

.eiq-race-book__cards {
  display:grid;
  grid-template-columns: repeat(3,minmax(0,1fr));
  gap:18px;
  margin-top:22px;
}

.eiq-race-book__cards article {
  position:relative;
  padding:22px;
  border:1px solid rgba(246,243,234,.085);
  border-radius:24px;
  background:linear-gradient(180deg,rgba(255,255,255,.035),rgba(255,255,255,.014));
}

.eiq-race-book__runner-no {
  width:34px;
  height:34px;
  display:grid;
  place-items:center;
  border-radius:999px;
  color:#07100c;
  background:#f6f3ea;
  font-size:13px;
  font-weight:900;
}

.eiq-race-book__cards article > strong {
  display:block;
  margin-top:16px;
  color:#f6f3ea;
  font-size:18px;
  letter-spacing:-.04em;
}

.eiq-race-book__cards article > p {
  margin:8px 0 0;
  color:rgba(246,243,234,.56);
  font-size:12px;
}

.eiq-race-book__cards dl {
  display:grid;
  gap:10px;
  margin:18px 0 0;
}

.eiq-race-book__cards dl div {
  display:flex;
  justify-content:space-between;
  gap:14px;
  padding-top:9px;
  border-top:1px solid rgba(246,243,234,.075);
}

.eiq-race-book__cards dt {
  color:rgba(246,243,234,.45);
  font-size:11px;
}

.eiq-race-book__cards dd {
  margin:0;
  color:#f6f3ea;
  font-size:12px;
  font-weight:800;
}

.eiq-form-table-wrap {
  overflow-x:auto;
  margin-top:26px;
  border:1px solid rgba(246,243,234,.085);
  border-radius:24px;
}

.eiq-form-table {
  width:100%;
  min-width:1700px;
  border-collapse:collapse;
}

.eiq-form-table th,
.eiq-form-table td {
  padding:13px 14px;
  border-bottom:1px solid rgba(246,243,234,.07);
  text-align:left;
  color:rgba(246,243,234,.68);
  font-size:12px;
  white-space:nowrap;
}

.eiq-form-table th {
  color:rgba(246,243,234,.46);
  font-size:10px;
  font-weight:900;
  letter-spacing:.12em;
  text-transform:uppercase;
}

.eiq-form-table td:nth-child(13),
.eiq-form-table td:nth-child(14),
.eiq-form-table td:nth-child(15),
.eiq-form-table td:nth-child(16),
.eiq-form-table td:nth-child(17),
.eiq-form-table td:nth-child(18),
.eiq-form-table td:nth-child(19) {
  color:#f6f3ea;
  font-weight:800;
}

.eiq-form-table tbody tr:hover {
  background:rgba(255,255,255,.026);
}

@media(max-width:1200px){
  .eiq-race-book__cards{grid-template-columns:1fr;}
  .eiq-race-book__read,
  .eiq-runner-file__identity{grid-template-columns:repeat(2,minmax(0,1fr));}
}
''', encoding="utf-8")

print("[EDGEIQ] Race File V2 professional form book built")
