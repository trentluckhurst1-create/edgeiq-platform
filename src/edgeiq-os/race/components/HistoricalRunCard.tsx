import { type ReactNode, useState } from "react";

type HistoricalRunCardProps = {
  run: any;
  esiOverall?: ReactNode;
  colSpan?: number;
  clean: (value: any) => string;
  weight: (value: any) => string;
  market: (value: any) => string;
  ratingBand: (value: any) => string;
  verdict: (run: any) => string;
  narrative: (run: any) => string;
  reasons: (run: any) => string[];
  renderCompare: (run: any) => ReactNode;
};

function firstAvailable(clean: (value: any) => string, ...values: any[]) {
  const value = values.find(hasValue);
  if (value === null || value === undefined || value === "") return "Not available";
  return clean(value);
}

function hasValue(value: any) {
  return value !== null && value !== undefined && value !== "" && value !== "Not available" && value !== "Not recorded";
}

function evidenceLabel(value: string) {
  if (value === "LOW RELEVANCE" || value === "BACKGROUND") return "Watch";
  if (value === "REFERENCE") return "Useful Run";
  if (value === "SUPPORTING") return "Genuine Chance";
  if (value === "PRIMARY") return "Key Run";
  return value;
}

export function HistoricalRunCard({
  run,
  esiOverall,
  colSpan = 15,
  clean,
  weight,
  market,
  ratingBand,
  verdict,
  narrative,
  reasons,
  renderCompare,
}: HistoricalRunCardProps) {
  const [showCompare, setShowCompare] = useState(false);
  const official = run.professionalForm?.official ?? {};
  const evidence = run.professionalForm?.evidence ?? {};
  const positionFields = [
    ["Settling", official.settlingPosition, run.settlingPosition, run.positionInRunning?.settling, run.positionInRunning?.settlingPosition],
    ["600m", official.position600m, official.m600Position, run.position600m, run.m600Position, run.positionInRunning?.m600],
    ["400m", official.position400m, official.m400Position, run.position400m, run.m400Position, run.positionInRunning?.m400],
    ["200m", official.position200m, official.m200Position, run.position200m, run.m200Position, run.positionInRunning?.m200],
  ];
  const hasPositionFields = positionFields.some(([, ...values]) => values.some(hasValue));
  const stewardsNotes = firstAvailable(clean, official.stewardsReportNotes, official.stewardsNotes, run.stewardsReportNotes, run.stewardsReport, run.stewardsNotes);

  return (
    <tr className="eiq-form-report-row">
      <td colSpan={colSpan}>
        <section className="eiq-run-detail-v17">
          <header className="eiq-run-detail-v17__header">
            <div>
              <span>Historical Run Detail</span>
              <strong>{clean(official.track)} | {clean(official.distance)} | {clean(official.raceClass)}</strong>
              <p>{clean(official.date)} | {clean(official.condition)}</p>
            </div>

            <div className="eiq-run-detail-v17__result">
              <b>{clean(official.finish)}</b>
              <em>{clean(official.margin)} margin | SP {market(official.sp)}</em>
            </div>
          </header>

          <div className="eiq-run-detail-v17__grid">
            <article>
              <span>Race Context</span>
              <dl>
                <div><dt>Track</dt><dd>{clean(official.track)}</dd></div>
                <div><dt>Distance</dt><dd>{clean(official.distance)}</dd></div>
                <div><dt>Class</dt><dd>{clean(official.raceClass)}</dd></div>
                <div><dt>Condition</dt><dd>{clean(official.condition)}</dd></div>
                <div><dt>Rail</dt><dd>{firstAvailable(clean, official.rail, run.rail)}</dd></div>
                <div><dt>Barrier</dt><dd>{clean(official.barrier)}</dd></div>
                <div><dt>Weight</dt><dd>{weight(official.weight)}</dd></div>
                <div><dt>Jockey</dt><dd>{clean(official.jockey)}</dd></div>
                <div><dt>Field</dt><dd>{clean(official.fieldSize)}</dd></div>
                {/* TODO: Restore position fields when reliable in-running data is connected. */}
                {hasPositionFields ? positionFields.map(([label, ...values]) => (
                  <div key={label}><dt>{label}</dt><dd>{firstAvailable(clean, ...values)}</dd></div>
                )) : null}
                {hasValue(stewardsNotes) ? <div><dt>Stewards Notes</dt><dd>{stewardsNotes}</dd></div> : null}
              </dl>
            </article>

            <article>
              <span>Performance</span>
              <div className="eiq-run-detail-v17__metrics">
                <div><small>EPI</small><strong>{clean(evidence.runRating?.overall ?? run.edgeiqRunRating)}</strong><em>{ratingBand(evidence.runRating?.overall ?? run.edgeiqRunRating)}</em></div>
                <div><small>ERI</small><strong>{clean(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength)}</strong><em>{ratingBand(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength)}</em></div>
                <div><small>ESI Overall</small><strong>{esiOverall ?? "Not available"}</strong><em>Lengths vs standard</em></div>
                <div><small>Pressure</small><strong>{clean(evidence.pressure)}</strong><em>Race profile</em></div>
                <div><small>Tempo</small><strong>{clean(evidence.tempo)}</strong><em>Race speed</em></div>
              </div>
            </article>

            <article>
              <span>EDGEiQ Run Notes</span>
              <strong>{evidenceLabel(verdict(run))}</strong>
              <p>{narrative(run)}</p>
              <ul>
                {reasons(run).slice(0, 3).map((x) => <li key={x}>- {x}</li>)}
              </ul>
            </article>
          </div>

          <footer className="eiq-run-detail-v17__actions">
            <button type="button" onClick={() => setShowCompare(!showCompare)}>
              Compare
            </button>
            <button type="button">Open Results</button>
            <button type="button">Run Notes</button>
          </footer>

          {showCompare ? (
            <section className="eiq-run-detail-v17__compare">
              {renderCompare(run)}
            </section>
          ) : null}
        </section>
      </td>
    </tr>
  );
}
