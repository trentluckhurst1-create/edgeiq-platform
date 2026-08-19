import { RaceFileService } from "../services/RaceFileService";

const file = RaceFileService.build();
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
                  <th>Race Strength</th>
                  <th>Run Rating</th>
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
