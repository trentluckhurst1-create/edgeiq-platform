type RaceResultsWorkspaceProps = {
  raceBook: any;
  field: any[];
  clean: (value: any) => string;
  market: (value: any) => string;
};

function valueOrPending(value: any, fallback = "Pending") {
  const text = String(value ?? "").trim();
  if (!text || text === "-" || /^not available$/i.test(text) || /^unavailable$/i.test(text)) return fallback;
  return text;
}

function firstValue(...values: any[]) {
  for (const value of values) {
    const text = String(value ?? "").trim();
    if (text && text !== "-" && !/^not available$/i.test(text) && !/^unavailable$/i.test(text)) return text;
  }
  return "";
}

function runnerName(runner: any) {
  return firstValue(runner?.official?.runner, runner?.runner, runner?.horse, runner?.runnerName, runner?.name);
}

function runnerNumber(runner: any) {
  return firstValue(runner?.official?.number, runner?.number, runner?.runnerNumber, runner?.saddlecloth, runner?.no);
}

function runnerStatus(runner: any) {
  const raw = firstValue(runner?.status, runner?.official?.status, runner?.marketStatus, runner?.scratchingStatus);
  if (/scratch/i.test(raw)) return "SCRATCHED";
  return raw || "Pending";
}

function runnerFinish(runner: any) {
  return firstValue(runner?.result?.finish, runner?.finish, runner?.position, runner?.official?.finish);
}

function runnerMargin(runner: any) {
  return firstValue(runner?.result?.margin, runner?.margin, runner?.official?.margin);
}

function runnerSp(runner: any) {
  return firstValue(runner?.result?.sp, runner?.sp, runner?.official?.sp, runner?.market?.sp, runner?.marketPrice);
}

function runnerEpi(runner: any) {
  return firstValue(
    runner?.epi,
    runner?.edgeiqRunRating,
    runner?.performance?.epi,
    runner?.professionalForm?.evidence?.runRating?.overall,
  );
}

function runnerEri(runner: any) {
  return firstValue(
    runner?.eri,
    runner?.edgeiqRaceStrength,
    runner?.performance?.eri,
    runner?.professionalForm?.evidence?.raceStrength?.overall,
  );
}

export function RaceResultsWorkspace({ raceBook, field, clean, market }: RaceResultsWorkspaceProps) {
  const official = raceBook?.official ?? {};
  const runners = Array.isArray(field) ? field : [];
  const resultRows = runners.map((runner, index) => ({
    key: `${runnerNumber(runner) || index}-${runnerName(runner) || index}`,
    no: runnerNumber(runner),
    horse: runnerName(runner),
    jockey: firstValue(runner?.official?.jockey, runner?.jockey),
    trainer: firstValue(runner?.official?.trainer, runner?.trainer),
    finish: runnerFinish(runner),
    margin: runnerMargin(runner),
    sp: runnerSp(runner),
    epi: runnerEpi(runner),
    eri: runnerEri(runner),
    status: runnerStatus(runner),
  }));
  const completedRows = resultRows.filter((row) => row.finish && !/pending/i.test(row.finish));
  const winner = completedRows.find((row) => /^1(st)?$/i.test(row.finish)) ?? completedRows[0] ?? null;
  const raceLabel = `${clean(official.meeting)} R${clean(official.raceNumber)}`;
  const resultStatus = completedRows.length ? "Result connected" : "Awaiting official result";

  return (
    <section
      className="eiq-results-live-workspace"
      data-edgeiq-workspace-key="RESULTS"
      data-edgeiq-mounted-component="RaceResultsWorkspace"
      aria-label="Results"
    >
      <header className="eiq-results-live-workspace__header">
        <div>
          <span>RESULTS</span>
          <strong>{raceLabel}</strong>
          <p>{resultStatus}. The approved review structure remains available while official result fields are pending.</p>
        </div>
        <aside>
          <span>Status</span>
          <strong>{resultStatus}</strong>
        </aside>
      </header>

      <section className="eiq-results-live-workspace__summary" aria-label="Result summary">
        <div><span>Winner</span><strong>{winner ? winner.horse : "Pending"}</strong></div>
        <div><span>Race Rating</span><strong>{valueOrPending(official.raceRating ?? official.rating, "Pending")}</strong></div>
        <div><span>Sectionals</span><strong>Lengths vs standard when governed</strong></div>
        <div><span>Stewards</span><strong>{valueOrPending(official.stewardsStatus, "Pending")}</strong></div>
      </section>

      <div className="eiq-results-live-workspace__grid">
        <section className="eiq-results-live-panel eiq-results-live-table">
          <header>
            <span>Official Finishing Order</span>
            <strong>{completedRows.length ? "Result rows" : "Pending result structure"}</strong>
          </header>
          <div>
            <table>
              <thead>
                <tr>
                  <th>Pos</th>
                  <th>No</th>
                  <th className="is-left">Horse</th>
                  <th className="is-left">Jockey</th>
                  <th className="is-left">Trainer</th>
                  <th>SP</th>
                  <th>Margin</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {resultRows.map((row) => (
                  <tr key={row.key} className={/scratch/i.test(row.status) ? "is-scratched" : ""}>
                    <td>{valueOrPending(row.finish)}</td>
                    <td>{clean(row.no || "-")}</td>
                    <td className="is-left"><strong>{clean(row.horse || "Runner")}</strong></td>
                    <td className="is-left">{clean(row.jockey || "-")}</td>
                    <td className="is-left">{clean(row.trainer || "-")}</td>
                    <td>{row.sp ? market(row.sp) : "Pending"}</td>
                    <td>{valueOrPending(row.margin)}</td>
                    <td>{row.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <aside className="eiq-results-live-panel">
          <span>Runner Performance Snapshot</span>
          <strong>Governed EPI / ERI</strong>
          <p>Current runner performance fields remain visible; official sectional review unlocks when result and sectional feeds are governed.</p>
          <dl>
            {resultRows.slice(0, 6).map((row) => (
              <div key={`${row.key}-snapshot`}>
                <dt>{row.horse || row.no || "Runner"}</dt>
                <dd>EPI {valueOrPending(row.epi, "-")} / ERI {valueOrPending(row.eri, "-")}</dd>
              </div>
            ))}
          </dl>
        </aside>
      </div>

      <section className="eiq-results-live-panel">
        <header>
          <span>Review Notes</span>
          <strong>Pending-safe review state</strong>
        </header>
        <ul className="eiq-results-live-workspace__notes">
          <li>Official finishing order, SP and margins are populated only when governed result rows exist.</li>
          <li>Sectional lengths versus standard remain unavailable until the governed sectional source is connected.</li>
          <li>No replay or simulated result data is displayed.</li>
        </ul>
      </section>
    </section>
  );
}
