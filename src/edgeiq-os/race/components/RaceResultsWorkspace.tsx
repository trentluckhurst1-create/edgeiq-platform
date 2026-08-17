import {
  EiqBadge,
  EiqCard,
  EiqDataTable,
  EiqEmptyState,
  EiqMetric,
  EiqPanel,
  EiqSectionHeader,
  EiqSidePanel,
  EiqStatusBadge,
} from "../../design-system/v1";

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

function runnerStatusTone(status: string): "neutral" | "success" | "warning" | "danger" {
  if (/scratch/i.test(status)) return "danger";
  if (/official|result|complete|active|loaded/i.test(status)) return "success";
  if (/pending|await/i.test(status)) return "warning";
  return "neutral";
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
  const summaryMetrics = [
    {
      label: "Winner",
      value: winner ? clean(winner.horse) : "Pending",
      detail: winner?.jockey ? `Jockey ${clean(winner.jockey)}` : "Official winner feed",
    },
    {
      label: "Race Rating",
      value: valueOrPending(official.raceRating ?? official.rating, "Pending"),
      detail: "Governed race strength field",
    },
    {
      label: "Sectionals",
      value: "Lengths vs standard",
      detail: "Available when governed",
    },
    {
      label: "Stewards",
      value: valueOrPending(official.stewardsStatus, "Pending"),
      detail: "Official review state",
    },
  ];

  return (
    <section className="eiq-results-v1-workspace" aria-label="Results" data-edgeiq-results-body="v1">
      <EiqPanel className="eiq-results-v1-workspace__intro">
        <EiqSectionHeader
          eyebrow="RESULTS"
          title={raceLabel}
          meta={<EiqStatusBadge status={resultStatus} />}
        />
        <p>{resultStatus}. The approved review structure remains available while official result fields are pending.</p>
      </EiqPanel>

      <section className="eiq-results-v1-workspace__summary" aria-label="Result summary">
        {summaryMetrics.map((metric) => (
          <EiqCard key={metric.label} density="compact" className="eiq-results-v1-workspace__metric-card">
            <EiqMetric label={metric.label} value={metric.value} detail={metric.detail} />
          </EiqCard>
        ))}
      </section>

      <div className="eiq-results-v1-workspace__grid">
        <EiqPanel className="eiq-results-v1-workspace__table-panel">
          <EiqSectionHeader
            eyebrow="Official Finishing Order"
            title={completedRows.length ? "Result rows" : "Pending result structure"}
            meta={<EiqBadge tone={completedRows.length ? "success" : "warning"}>{completedRows.length} completed</EiqBadge>}
          />
          {resultRows.length ? (
            <EiqDataTable density="compact" wrapperProps={{ className: "eiq-results-v1-workspace__table-scroll" }}>
              <thead>
                <tr>
                  <th>Pos</th>
                  <th>No</th>
                  <th>Horse</th>
                  <th>Jockey</th>
                  <th>Trainer</th>
                  <th>SP</th>
                  <th>Margin</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {resultRows.map((row) => (
                  <tr
                    key={row.key}
                    className={/scratch/i.test(row.status) ? "eiq-results-v1-workspace__row--scratched" : ""}
                  >
                    <td>{valueOrPending(row.finish)}</td>
                    <td>{clean(row.no || "-")}</td>
                    <td><strong>{clean(row.horse || "Runner")}</strong></td>
                    <td>{clean(row.jockey || "-")}</td>
                    <td>{clean(row.trainer || "-")}</td>
                    <td>{row.sp ? market(row.sp) : "Pending"}</td>
                    <td>{valueOrPending(row.margin)}</td>
                    <td><EiqBadge tone={runnerStatusTone(row.status)}>{row.status}</EiqBadge></td>
                  </tr>
                ))}
              </tbody>
            </EiqDataTable>
          ) : (
            <EiqEmptyState
              title="No result rows available"
              detail="Official finishing order, SP and margins are populated only when governed result rows exist."
            />
          )}
        </EiqPanel>

        <EiqSidePanel className="eiq-results-v1-workspace__side-panel">
          <EiqSectionHeader eyebrow="Runner Performance Snapshot" title="Governed EPI / ERI" />
          <p>Current runner performance fields remain visible; official sectional review unlocks when result and sectional feeds are governed.</p>
          {resultRows.length ? (
            <dl className="eiq-results-v1-workspace__snapshot-list">
              {resultRows.slice(0, 6).map((row) => (
                <div key={`${row.key}-snapshot`}>
                  <dt>{clean(row.horse || row.no || "Runner")}</dt>
                  <dd>EPI {valueOrPending(row.epi, "-")} / ERI {valueOrPending(row.eri, "-")}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <EiqEmptyState title="Runner snapshot pending" detail="EPI and ERI remain pending until governed runner rows are present." />
          )}
        </EiqSidePanel>
      </div>

      <EiqPanel className="eiq-results-v1-workspace__notes-panel" density="compact">
        <EiqSectionHeader eyebrow="Review Notes" title="Pending-safe review state" />
        <ul className="eiq-results-v1-workspace__notes">
          <li>Official finishing order, SP and margins are populated only when governed result rows exist.</li>
          <li>Sectional lengths versus standard remain unavailable until the governed sectional source is connected.</li>
          <li>No replay or simulated result data is displayed.</li>
        </ul>
      </EiqPanel>
    </section>
  );
}
