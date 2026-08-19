from pathlib import Path

race = Path("src/edgeiq-os/race")
css = Path("src/styles/edgeiqProductTerminalV1.css")

(race / "RaceFileV3.tsx").write_text(r'''
import { RaceFileService } from "../services/RaceFileService";

const file = RaceFileService.build();
const primary = file.field[0];

function verdict(runRating: number, raceStrength: number, relativePerformance: string): string {
  const delta = Number(String(relativePerformance).replace("+", ""));
  if (runRating >= 90 && raceStrength >= 86) return "Strong In Defeat";
  if (delta >= 2.5) return "Hidden Merit";
  if (runRating >= 88) return "Positive Run";
  return "Needs Context";
}

export function RaceFileV3() {
  return (
    <section className="eiq-race-file-v3">
      <header className="eiq-race-file-v3__hero">
        <div>
          <span>EDGEiQ Race File</span>
          <strong>{file.officialRace.meeting} R{file.officialRace.raceNumber}</strong>
          <p>
            {file.officialRace.raceName} · {file.officialRace.distance} · {file.officialRace.raceClass} ·
            {file.officialRace.trackCondition} · {file.officialRace.rail}
          </p>
        </div>

        <aside>
          <article><span>RaceFlow™</span><strong>{file.raceRead.raceFlow}</strong></article>
          <article><span>Pressure</span><strong>{file.raceRead.pressure}</strong></article>
          <article><span>Tempo</span><strong>{file.raceRead.tempo}</strong></article>
          <article><span>Confidence</span><strong>{file.raceRead.confidence}</strong></article>
        </aside>
      </header>

      <section className="eiq-race-file-v3__assessment">
        <header>
          <span>Today's Race Read</span>
          <strong>Official racing data plus EDGEiQ intelligence</strong>
        </header>

        <div>
          <article><span>TrackSignature™</span><strong>{file.raceRead.trackSignature}</strong><p>Current track pattern and suitability read.</p></article>
          <article><span>SpeedProfile™</span><strong>{file.raceRead.speedProfile}</strong><p>Measured against EDGEiQ proprietary standards.</p></article>
          <article><span>RaceFlow™</span><strong>{file.raceRead.raceFlow}</strong><p>Expected tactical shape of the race.</p></article>
        </div>
      </section>

      <section className="eiq-race-file-v3__field">
        <header>
          <span>Field Intelligence</span>
          <strong>Runner-by-runner view</strong>
        </header>

        <div>
          {file.field.map((runner) => (
            <article key={runner.official.no}>
              <b>{runner.official.no}</b>
              <strong>{runner.official.runner}</strong>
              <p>Bar {runner.official.barrier} · {runner.official.weight} · {runner.official.jockey}</p>

              <dl>
                <div><dt>EDGE Rating</dt><dd>{runner.edgeRating}</dd></div>
                <div><dt>RunnerDNA™</dt><dd>{runner.runnerDNA}</dd></div>
                <div><dt>SpeedProfile™</dt><dd>{runner.speedProfile}</dd></div>
                <div><dt>TrackSignature™</dt><dd>{runner.trackSignature}</dd></div>
                <div><dt>RaceFlow™</dt><dd>{runner.raceFlow}</dd></div>
                <div><dt>MarketBehaviour™</dt><dd>{runner.marketBehaviour}</dd></div>
              </dl>
            </article>
          ))}
        </div>
      </section>

      {primary ? (
        <section className="eiq-runner-dossier-v3">
          <header>
            <span>Runner File</span>
            <strong>{primary.official.runner}</strong>
            <p>{primary.assessment}</p>
          </header>

          <div className="eiq-runner-dossier-v3__snapshot">
            <article><span>Trainer</span><strong>{primary.official.trainer}</strong></article>
            <article><span>Jockey</span><strong>{primary.official.jockey}</strong></article>
            <article><span>Barrier</span><strong>{primary.official.barrier}</strong></article>
            <article><span>Weight</span><strong>{primary.official.weight}</strong></article>
            <article><span>Market</span><strong>{primary.official.market}</strong></article>
          </div>

          <section className="eiq-historical-form-v3">
            <header>
              <span>Historical Form Intelligence</span>
              <strong>Official facts, EDGEiQ figures and race context</strong>
            </header>

            {primary.historicalRuns.map((run) => (
              <article className="eiq-historical-run-v3" key={`${run.date}-${run.track}-${run.race}`}>
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

                <div className="eiq-historical-run-v3__facts">
                  <article><span>Finish</span><strong>{run.finish}</strong></article>
                  <article><span>Margin</span><strong>{run.margin}</strong></article>
                  <article><span>Official Time</span><strong>{run.officialRaceTime}</strong></article>
                  <article><span>Race Strength™</span><strong>{run.edgeiqRaceStrength}</strong></article>
                  <article><span>Run Rating™</span><strong>{run.edgeiqRunRating}</strong></article>
                  <article><span>Δ Standard</span><strong>{run.relativePerformance}</strong></article>
                </div>

                <div className="eiq-historical-run-v3__split">
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

                <div className="eiq-historical-run-v3__pir">
                  <span>Position In Running</span>
                  <strong>
                    Jump {run.positionInRunning.jump} · 800 {run.positionInRunning.m800} · 600 {run.positionInRunning.m600} ·
                    400 {run.positionInRunning.m400} · 200 {run.positionInRunning.m200} · Finish {run.positionInRunning.finish}
                  </strong>
                </div>
              </article>
            ))}
          </section>
        </section>
      ) : null}
    </section>
  );
}
'''.lstrip(), encoding="utf-8")

race_ws = race / "EdgeiqRaceWorkspace.tsx"
text = race_ws.read_text(encoding="utf-8")

if 'import { RaceFileV3 } from "./RaceFileV3";' not in text:
    if 'import { RaceFileV2 } from "./RaceFileV2";' in text:
        text = text.replace('import { RaceFileV2 } from "./RaceFileV2";', 'import { RaceFileV2 } from "./RaceFileV2";\nimport { RaceFileV3 } from "./RaceFileV3";')
    else:
        text = 'import { RaceFileV3 } from "./RaceFileV3";\n' + text

if "<RaceFileV3 />" not in text:
    text = text.replace("<RaceFileV2 />", "<RaceFileV3 />")

race_ws.write_text(text, encoding="utf-8")

marker = "EDGEiQ Race File V3"
existing = css.read_text(encoding="utf-8")

if marker not in existing:
    css.write_text(existing + r'''

/* ==========================================================================
   EDGEiQ Race File V3
   ========================================================================== */

.eiq-race-file-v3 {
  padding: 38px 0 48px;
}

.eiq-race-file-v3__hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(420px, .55fr);
  gap: 28px;
  padding: 34px;
  border: 1px solid rgba(246,243,234,.09);
  border-radius: 34px;
  background:
    radial-gradient(circle at top left, rgba(126,220,155,.08), transparent 34%),
    linear-gradient(180deg, rgba(255,255,255,.035), rgba(255,255,255,.014));
}

.eiq-race-file-v3 span,
.eiq-race-file-v3 dt {
  display: block;
  color: rgba(246,243,234,.46);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: .15em;
  text-transform: uppercase;
}

.eiq-race-file-v3__hero > div > strong {
  display: block;
  margin-top: 10px;
  color: #f6f3ea;
  font-size: clamp(42px, 5vw, 74px);
  line-height: .9;
  letter-spacing: -.08em;
}

.eiq-race-file-v3__hero p,
.eiq-race-file-v3__assessment p,
.eiq-race-file-v3__field p,
.eiq-runner-dossier-v3 p {
  margin: 14px 0 0;
  color: rgba(246,243,234,.62);
  font-size: 13px;
  line-height: 1.6;
}

.eiq-race-file-v3__hero aside {
  display: grid;
  grid-template-columns: repeat(2, minmax(0,1fr));
  gap: 16px;
}

.eiq-race-file-v3__hero aside article,
.eiq-race-file-v3__assessment article,
.eiq-race-file-v3__field article,
.eiq-runner-dossier-v3__snapshot article {
  padding: 18px;
  border: 1px solid rgba(246,243,234,.075);
  border-radius: 22px;
  background: rgba(255,255,255,.018);
}

.eiq-race-file-v3__hero aside strong,
.eiq-race-file-v3__assessment strong,
.eiq-race-file-v3__field article > strong,
.eiq-runner-dossier-v3__snapshot strong {
  display: block;
  margin-top: 8px;
  color: #f6f3ea;
  font-size: 18px;
  letter-spacing: -.04em;
}

.eiq-race-file-v3__assessment,
.eiq-race-file-v3__field,
.eiq-runner-dossier-v3,
.eiq-historical-form-v3 {
  margin-top: 34px;
}

.eiq-race-file-v3__assessment > header strong,
.eiq-race-file-v3__field > header strong,
.eiq-runner-dossier-v3 > header strong,
.eiq-historical-form-v3 > header strong {
  display: block;
  margin-top: 8px;
  color: #f6f3ea;
  font-size: 30px;
  line-height: 1;
  letter-spacing: -.06em;
}

.eiq-race-file-v3__assessment > div {
  display: grid;
  grid-template-columns: repeat(3, minmax(0,1fr));
  gap: 18px;
  margin-top: 22px;
}

.eiq-race-file-v3__field > div {
  display: grid;
  grid-template-columns: repeat(3, minmax(0,1fr));
  gap: 18px;
  margin-top: 22px;
}

.eiq-race-file-v3__field b {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  color: #07100c;
  background: #f6f3ea;
  font-size: 13px;
  font-weight: 900;
}

.eiq-race-file-v3__field dl {
  display: grid;
  gap: 10px;
  margin: 18px 0 0;
}

.eiq-race-file-v3__field dl div {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 14px;
  padding-top: 9px;
  border-top: 1px solid rgba(246,243,234,.075);
}

.eiq-race-file-v3__field dd {
  margin: 0;
  color: #f6f3ea;
  font-size: 12px;
  font-weight: 900;
}

.eiq-runner-dossier-v3__snapshot {
  display: grid;
  grid-template-columns: repeat(5, minmax(0,1fr));
  gap: 16px;
  margin-top: 22px;
}

.eiq-historical-form-v3 {
  display: grid;
  gap: 20px;
}

.eiq-historical-run-v3 {
  padding: 26px;
  border: 1px solid rgba(246,243,234,.085);
  border-radius: 28px;
  background:
    linear-gradient(180deg, rgba(255,255,255,.03), rgba(255,255,255,.012));
}

.eiq-historical-run-v3 > header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
}

.eiq-historical-run-v3 > header strong {
  display: block;
  margin-top: 8px;
  color: #f6f3ea;
  font-size: 22px;
  letter-spacing: -.05em;
}

.eiq-historical-run-v3 > header aside {
  min-width: 220px;
  padding: 16px;
  border-radius: 20px;
  border: 1px solid rgba(126,220,155,.20);
  background: rgba(126,220,155,.055);
}

.eiq-historical-run-v3 > header aside strong {
  color: #7edc9b;
  font-size: 18px;
}

.eiq-historical-run-v3__facts {
  display: grid;
  grid-template-columns: repeat(6, minmax(0,1fr));
  gap: 14px;
  margin-top: 24px;
}

.eiq-historical-run-v3__facts article {
  padding-top: 12px;
  border-top: 1px solid rgba(246,243,234,.08);
}

.eiq-historical-run-v3__facts strong {
  display: block;
  margin-top: 7px;
  color: #f6f3ea;
  font-size: 16px;
}

.eiq-historical-run-v3__split {
  margin-top: 24px;
  padding: 20px;
  border-radius: 22px;
  background: rgba(255,255,255,.018);
  border: 1px solid rgba(246,243,234,.075);
}

.eiq-historical-run-v3__split header strong {
  display: block;
  margin-top: 6px;
  color: #f6f3ea;
  font-size: 16px;
}

.eiq-historical-run-v3__split > div {
  display: grid;
  grid-template-columns: repeat(5, minmax(0,1fr));
  gap: 14px;
  margin-top: 18px;
}

.eiq-historical-run-v3__split article {
  padding-top: 12px;
  border-top: 1px solid rgba(246,243,234,.08);
}

.eiq-historical-run-v3__split article strong {
  display: block;
  margin-top: 8px;
  color: #f6f3ea;
  font-size: 24px;
  letter-spacing: -.06em;
}

.eiq-historical-run-v3__split small {
  display: block;
  margin-top: 6px;
  color: rgba(246,243,234,.54);
  font-size: 11px;
}

.eiq-historical-run-v3__pir {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid rgba(246,243,234,.08);
}

.eiq-historical-run-v3__pir strong {
  display: block;
  margin-top: 8px;
  color: rgba(246,243,234,.82);
  font-size: 13px;
  line-height: 1.6;
}

@media(max-width:1200px){
  .eiq-race-file-v3__hero,
  .eiq-race-file-v3__assessment > div,
  .eiq-race-file-v3__field > div,
  .eiq-runner-dossier-v3__snapshot,
  .eiq-historical-run-v3__facts,
  .eiq-historical-run-v3__split > div {
    grid-template-columns: 1fr;
  }

  .eiq-historical-run-v3 > header {
    flex-direction: column;
  }
}
''', encoding="utf-8")

print("[EDGEIQ] Race File V3 built")
