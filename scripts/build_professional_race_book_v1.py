from pathlib import Path

service = Path("src/edgeiq-os/services/RaceFileService.ts")
race = Path("src/edgeiq-os/race/RaceFileV3.tsx")
css = Path("src/styles/edgeiqProductTerminalV1.css")

service.write_text(r'''
import { buildRaceFileV2 } from "./race-file-v2";
import { buildRaceStrengthBreakdown } from "./RaceStrengthService";
import { buildRunRatingBreakdown } from "./RunRatingService";

export type {
  RaceFileModelV1,
  RaceFileRunnerProfile,
  HistoricalRun,
  OfficialRaceData,
  OfficialRunnerData,
  EdgeiqSpeedProfileSplit,
} from "./race-file-model";

export function buildProfessionalRaceBook() {
  const file = buildRaceFileV2();

  return {
    ...file,
    raceBook: {
      official: {
        meeting: file.officialRace.meeting,
        raceNumber: file.officialRace.raceNumber,
        raceName: file.officialRace.raceName,
        distance: file.officialRace.distance,
        raceClass: file.officialRace.raceClass,
        trackCondition: file.officialRace.trackCondition,
        rail: file.officialRace.rail,
        officialRaceTime: file.officialRace.officialRaceTime ?? "Pending",
        prizeMoney: file.officialRace.prizeMoney ?? "Pending",
        fieldSize: file.field.length,
      },
      intelligence: {
        raceFlow: file.raceRead.raceFlow,
        pressure: file.raceRead.pressure,
        tempo: file.raceRead.tempo,
        trackSignature: file.raceRead.trackSignature,
        speedProfile: file.raceRead.speedProfile,
        confidence: file.raceRead.confidence,
        raceStrength: buildRaceStrengthBreakdown(),
        runRating: buildRunRatingBreakdown(),
      },
    },
  };
}

export const RaceFileService = {
  build: buildRaceFileV2,
  buildRaceBook: buildProfessionalRaceBook,
};

export { buildRaceFileV2, buildRaceFileV2 as buildRaceFile };
'''.lstrip(), encoding="utf-8")

race.write_text(r'''
import { RaceFileService } from "../services/RaceFileService";

const file = RaceFileService.buildRaceBook();
const primary = file.field[0];

function verdict(runRating: number, raceStrength: number, relativePerformance: string): string {
  const delta = Number(String(relativePerformance).replace("+", ""));
  if (runRating >= 90 && raceStrength >= 86) return "STRONG IN DEFEAT";
  if (delta >= 2.5) return "HIDDEN MERIT";
  if (runRating >= 88) return "POSITIVE RUN";
  return "NEEDS CONTEXT";
}

export function RaceFileV3() {
  return (
    <section className="eiq-race-book-pro">
      <header className="eiq-race-book-pro__hero">
        <span>EDGEiQ Race Book</span>
        <strong>{file.raceBook.official.meeting} R{file.raceBook.official.raceNumber}</strong>
        <p>
          {file.raceBook.official.raceName} · {file.raceBook.official.distance} · {file.raceBook.official.raceClass} · {file.raceBook.official.trackCondition} · {file.raceBook.official.rail}
        </p>
      </header>

      <section className="eiq-race-book-pro__grid">
        <article>
          <span>Official Race</span>
          <strong>{file.raceBook.official.distance}</strong>
          <p>{file.raceBook.official.raceClass} · Field {file.raceBook.official.fieldSize}</p>
        </article>
        <article>
          <span>RaceFlow™</span>
          <strong>{file.raceBook.intelligence.raceFlow}</strong>
          <p>Expected tactical shape.</p>
        </article>
        <article>
          <span>Pressure</span>
          <strong>{file.raceBook.intelligence.pressure}</strong>
          <p>Projected pressure read.</p>
        </article>
        <article>
          <span>Tempo</span>
          <strong>{file.raceBook.intelligence.tempo}</strong>
          <p>Expected race speed.</p>
        </article>
        <article>
          <span>TrackSignature™</span>
          <strong>{file.raceBook.intelligence.trackSignature}</strong>
          <p>Track pattern and suitability.</p>
        </article>
        <article>
          <span>SpeedProfile™</span>
          <strong>{file.raceBook.intelligence.speedProfile}</strong>
          <p>Measured against EDGEiQ standards.</p>
        </article>
      </section>

      <section className="eiq-race-book-pro__section">
        <header>
          <span>Field Intelligence</span>
          <strong>Runner-by-runner assessment</strong>
        </header>

        <div className="eiq-race-book-pro__table-wrap">
          <table>
            <thead>
              <tr>
                <th>No</th>
                <th>Runner</th>
                <th>Bar</th>
                <th>Weight</th>
                <th>Jockey</th>
                <th>Trainer</th>
                <th>Market</th>
                <th>EDGE Rating™</th>
                <th>RunnerDNA™</th>
                <th>SpeedProfile™</th>
                <th>TrackSignature™</th>
                <th>RaceFlow™</th>
                <th>Assessment</th>
              </tr>
            </thead>
            <tbody>
              {file.field.map((runner) => (
                <tr key={runner.official.no}>
                  <td>{runner.official.no}</td>
                  <td><strong>{runner.official.runner}</strong></td>
                  <td>{runner.official.barrier}</td>
                  <td>{runner.official.weight}</td>
                  <td>{runner.official.jockey}</td>
                  <td>{runner.official.trainer}</td>
                  <td>{runner.official.market}</td>
                  <td>{runner.edgeRating}</td>
                  <td>{runner.runnerDNA}</td>
                  <td>{runner.speedProfile}</td>
                  <td>{runner.trackSignature}</td>
                  <td>{runner.raceFlow}</td>
                  <td>{runner.assessment}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {primary ? (
        <section className="eiq-race-book-pro__section">
          <header>
            <span>Runner File</span>
            <strong>{primary.official.runner}</strong>
            <p>{primary.assessment}</p>
          </header>

          <div className="eiq-race-book-pro__runner-snapshot">
            <article><span>Trainer</span><strong>{primary.official.trainer}</strong></article>
            <article><span>Jockey</span><strong>{primary.official.jockey}</strong></article>
            <article><span>Barrier</span><strong>{primary.official.barrier}</strong></article>
            <article><span>Weight</span><strong>{primary.official.weight}</strong></article>
            <article><span>Market</span><strong>{primary.official.market}</strong></article>
          </div>

          <div className="eiq-race-book-pro__runs">
            {primary.historicalRuns.map((run) => (
              <article key={`${run.date}-${run.track}-${run.race}`}>
                <header>
                  <div>
                    <span>{run.date}</span>
                    <strong>{run.track} · {run.distance} · {run.raceClass}</strong>
                    <p>{run.condition} · Bar {run.barrier} · {run.weight} · {run.jockey} · SP {run.sp}</p>
                  </div>
                  <aside>
                    <span>EDGEiQ Verdict</span>
                    <strong>{verdict(run.edgeiqRunRating, run.edgeiqRaceStrength, run.relativePerformance)}</strong>
                  </aside>
                </header>

                <div className="eiq-race-book-pro__facts">
                  <article><span>Finish</span><strong>{run.finish}</strong></article>
                  <article><span>Margin</span><strong>{run.margin}</strong></article>
                  <article><span>Official Time</span><strong>{run.officialRaceTime}</strong></article>
                  <article><span>Race Strength™</span><strong>{run.edgeiqRaceStrength}</strong></article>
                  <article><span>Run Rating™</span><strong>{run.edgeiqRunRating}</strong></article>
                  <article><span>Δ Standard</span><strong>{run.relativePerformance}</strong></article>
                  <article><span>Pressure</span><strong>{run.pressureRating}</strong></article>
                  <article><span>Tempo</span><strong>{run.tempoRating}</strong></article>
                  <article><span>TrackSignature™</span><strong>{run.trackSignatureMatch}</strong></article>
                  <article><span>RaceFlow™</span><strong>{run.raceFlowMatch}</strong></article>
                </div>

                <div className="eiq-race-book-pro__speed">
                  <header>
                    <span>SpeedProfile™</span>
                    <strong>Lengths vs EDGEiQ standard</strong>
                  </header>

                  <div>
                    {run.speedProfile.map((split) => (
                      <article key={split.marker}>
                        <span>{split.marker}</span>
                        <strong>{split.lengthsVsStandard}</strong>
                        <small>{split.position}</small>
                      </article>
                    ))}
                  </div>
                </div>

                <div className="eiq-race-book-pro__pir">
                  <span>Position In Running</span>
                  <strong>
                    Jump {run.positionInRunning.jump} · 800 {run.positionInRunning.m800} · 600 {run.positionInRunning.m600} · 400 {run.positionInRunning.m400} · 200 {run.positionInRunning.m200} · Finish {run.positionInRunning.finish}
                  </strong>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </section>
  );
}
'''.lstrip(), encoding="utf-8")

marker = "EDGEiQ Professional Race Book"
existing = css.read_text(encoding="utf-8")

if marker not in existing:
    css.write_text(existing + r'''

/* ==========================================================================
   EDGEiQ Professional Race Book
   ========================================================================== */

.eiq-race-book-pro {
  padding: 28px 0 56px;
}

.eiq-race-book-pro span {
  display: block;
  color: rgba(246,243,234,.46);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: .15em;
  text-transform: uppercase;
}

.eiq-race-book-pro__hero {
  padding: 36px;
  border: 1px solid rgba(246,243,234,.09);
  border-radius: 34px;
  background:
    radial-gradient(circle at top left, rgba(126,220,155,.09), transparent 34%),
    linear-gradient(180deg, rgba(255,255,255,.035), rgba(255,255,255,.014));
}

.eiq-race-book-pro__hero strong {
  display: block;
  margin-top: 10px;
  color: #f6f3ea;
  font-size: clamp(42px, 5vw, 76px);
  line-height: .9;
  letter-spacing: -.08em;
}

.eiq-race-book-pro p {
  margin: 12px 0 0;
  color: rgba(246,243,234,.62);
  font-size: 13px;
  line-height: 1.6;
}

.eiq-race-book-pro__grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 16px;
  margin-top: 22px;
}

.eiq-race-book-pro__grid article,
.eiq-race-book-pro__runner-snapshot article {
  padding: 18px;
  border: 1px solid rgba(246,243,234,.08);
  border-radius: 22px;
  background: rgba(255,255,255,.018);
}

.eiq-race-book-pro__grid strong,
.eiq-race-book-pro__runner-snapshot strong {
  display: block;
  margin-top: 8px;
  color: #f6f3ea;
  font-size: 18px;
  letter-spacing: -.04em;
}

.eiq-race-book-pro__section {
  margin-top: 36px;
}

.eiq-race-book-pro__section > header strong {
  display: block;
  margin-top: 8px;
  color: #f6f3ea;
  font-size: 32px;
  line-height: 1;
  letter-spacing: -.06em;
}

.eiq-race-book-pro__table-wrap {
  overflow-x: auto;
  margin-top: 22px;
  border: 1px solid rgba(246,243,234,.085);
  border-radius: 24px;
}

.eiq-race-book-pro table {
  width: 100%;
  min-width: 1420px;
  border-collapse: collapse;
}

.eiq-race-book-pro th,
.eiq-race-book-pro td {
  padding: 13px 14px;
  border-bottom: 1px solid rgba(246,243,234,.07);
  text-align: left;
  color: rgba(246,243,234,.68);
  font-size: 12px;
  white-space: nowrap;
}

.eiq-race-book-pro th {
  color: rgba(246,243,234,.46);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: .12em;
  text-transform: uppercase;
}

.eiq-race-book-pro td strong {
  color: #f6f3ea;
}

.eiq-race-book-pro tbody tr:hover {
  background: rgba(255,255,255,.026);
}

.eiq-race-book-pro__runner-snapshot {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 16px;
  margin-top: 22px;
}

.eiq-race-book-pro__runs {
  display: grid;
  gap: 22px;
  margin-top: 28px;
}

.eiq-race-book-pro__runs > article {
  padding: 26px;
  border: 1px solid rgba(246,243,234,.085);
  border-radius: 28px;
  background: linear-gradient(180deg, rgba(255,255,255,.03), rgba(255,255,255,.012));
}

.eiq-race-book-pro__runs > article > header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
}

.eiq-race-book-pro__runs > article > header strong {
  display: block;
  margin-top: 8px;
  color: #f6f3ea;
  font-size: 22px;
  letter-spacing: -.05em;
}

.eiq-race-book-pro__runs aside {
  min-width: 230px;
  padding: 16px;
  border-radius: 20px;
  border: 1px solid rgba(126,220,155,.20);
  background: rgba(126,220,155,.055);
}

.eiq-race-book-pro__runs aside strong {
  color: #7edc9b !important;
  font-size: 18px !important;
}

.eiq-race-book-pro__facts {
  display: grid;
  grid-template-columns: repeat(5, minmax(0,1fr));
  gap: 14px;
  margin-top: 24px;
}

.eiq-race-book-pro__facts article {
  padding-top: 12px;
  border-top: 1px solid rgba(246,243,234,.08);
}

.eiq-race-book-pro__facts strong {
  display: block;
  margin-top: 7px;
  color: #f6f3ea;
  font-size: 16px;
}

.eiq-race-book-pro__speed {
  margin-top: 24px;
  padding: 20px;
  border-radius: 22px;
  background: rgba(255,255,255,.018);
  border: 1px solid rgba(246,243,234,.075);
}

.eiq-race-book-pro__speed header strong {
  display: block;
  margin-top: 6px;
  color: #f6f3ea;
  font-size: 16px;
}

.eiq-race-book-pro__speed > div {
  display: grid;
  grid-template-columns: repeat(5, minmax(0,1fr));
  gap: 14px;
  margin-top: 18px;
}

.eiq-race-book-pro__speed article {
  padding-top: 12px;
  border-top: 1px solid rgba(246,243,234,.08);
}

.eiq-race-book-pro__speed article strong {
  display: block;
  margin-top: 8px;
  color: #f6f3ea;
  font-size: 24px;
  letter-spacing: -.06em;
}

.eiq-race-book-pro__speed small {
  display: block;
  margin-top: 6px;
  color: rgba(246,243,234,.54);
  font-size: 11px;
}

.eiq-race-book-pro__pir {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid rgba(246,243,234,.08);
}

.eiq-race-book-pro__pir strong {
  display: block;
  margin-top: 8px;
  color: rgba(246,243,234,.82);
  font-size: 13px;
  line-height: 1.6;
}

@media(max-width:1200px){
  .eiq-race-book-pro__grid,
  .eiq-race-book-pro__runner-snapshot,
  .eiq-race-book-pro__facts,
  .eiq-race-book-pro__speed > div {
    grid-template-columns: 1fr;
  }

  .eiq-race-book-pro__runs > article > header {
    flex-direction: column;
  }
}
''', encoding="utf-8")

print("[EDGEIQ] Professional Race Book wired to RaceFileService")
