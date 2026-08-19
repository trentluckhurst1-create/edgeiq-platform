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
