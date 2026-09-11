import { Fragment, useMemo, useState, type KeyboardEvent } from "react";
import { buildFieldWorkspaceRows } from "../services/fieldWorkspaceViewModel";
import type { FormGuideRaceDisplay, FormGuideRecentRun } from "../services/formGuideNormaliser";

type FieldWorkspaceProps = {
  field: any[];
  formGuide?: FormGuideRaceDisplay | null;
  clean: (value: any) => string;
  weight: (value: any) => string;
  market: (value: any) => string;
  onOpenRunner: (index: number) => void;
};

function display(value: unknown, fallback = "-"): string {
  if (value === null || value === undefined) return fallback;
  const text = String(value).trim();
  if (!text || text === "-" || /^(none|null|undefined|nan|not available|pending market)$/i.test(text)) return fallback;
  return text;
}

function hasValue(value: unknown): boolean {
  return display(value, "") !== "";
}

function runColumnFlags(runs: FormGuideRecentRun[]) {
  return {
    epi: runs.some((run) => hasValue(run.epi)),
    eri: runs.some((run) => hasValue(run.eri)),
  };
}

function rowStatusClass(status: string): string {
  return status.toLowerCase().includes("scratch") ? "is-scratched" : "";
}

export function FieldWorkspace({ field, formGuide, weight, market, onOpenRunner }: FieldWorkspaceProps) {
  const [expandedKey, setExpandedKey] = useState<string | null>(null);
  const rows = useMemo(() => buildFieldWorkspaceRows({ field, formGuide, weight, market }), [field, formGuide, weight, market]);
  const scratchedCount = rows.filter((runner) => runner.isScratched).length;
  const activeCount = Math.max(0, rows.length - scratchedCount);
  const gearCount = rows.filter((runner) => hasValue(runner.gear)).length;
  const barrierKnown = rows.filter((runner) => hasValue(runner.barrier)).length;

  const toggleRunner = (key: string) => {
    setExpandedKey((current) => (current === key ? null : key));
  };

  const handleRunnerKeyDown = (event: KeyboardEvent<HTMLTableRowElement>, key: string) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    toggleRunner(key);
  };

  return (
    <section className="eiq-workspace-panel eiq-field-workspace-v1" aria-label="Field workspace">
      <header className="eiq-field-v1__header">
        <div>
          <span>FIELD</span>
          <strong>Official declarations</strong>
          <p>Barrier, weight, rider, trainer, status and declared gear. Expand a row for the last five starts or open the runner profile for deeper analysis.</p>
        </div>
        <aside className="eiq-field-v1__counts" aria-label="Field counts">
          <strong>{rows.length} DECLARED</strong>
          <span>{activeCount} ACTIVE | {scratchedCount} SCRATCHED</span>
        </aside>
      </header>

      <section className="eiq-field-v1__summary" aria-label="Declaration summary">
        <div><span>ACTIVE</span><strong>{activeCount}</strong></div>
        <div><span>SCRATCHED</span><strong>{scratchedCount}</strong></div>
        <div><span>BARRIERS PUBLISHED</span><strong>{barrierKnown}/{rows.length}</strong></div>
        <div><span>GEAR / CHANGES</span><strong>{gearCount}</strong></div>
      </section>

      <div className="eiq-table-wrap eiq-field-table-wrap-v1">
        <table className="eiq-field-table-v1">
          <colgroup>
            <col className="eiq-field-col-no" />
            <col className="eiq-field-col-silk" />
            <col className="eiq-field-col-runner" />
            <col className="eiq-field-col-bar" />
            <col className="eiq-field-col-wgt" />
            <col className="eiq-field-col-jockey" />
            <col className="eiq-field-col-trainer" />
            <col className="eiq-field-col-gear" />
            <col className="eiq-field-col-status" />
            <col className="eiq-field-col-action" />
          </colgroup>
          <thead>
            <tr>
              <th>NO</th>
              <th>SILK</th>
              <th className="is-left">RUNNER</th>
              <th>BAR</th>
              <th>WGT</th>
              <th className="is-left">JOCKEY</th>
              <th className="is-left">TRAINER</th>
              <th className="is-left">GEAR / CHANGES</th>
              <th>STATUS</th>
              <th>PROFILE</th>
            </tr>
          </thead>
          <tbody>
            {rows.length ? rows.map((runner) => {
              const expanded = expandedKey === runner.key;
              const flags = runColumnFlags(runner.recentRuns);
              return (
                <Fragment key={runner.key}>
                  <tr
                    className={`eiq-field-runner-row ${rowStatusClass(runner.status)} ${expanded ? "is-expanded" : ""}`}
                    tabIndex={0}
                    role="button"
                    aria-expanded={expanded}
                    aria-label={`${runner.runner || "Runner"} last five starts`}
                    onClick={() => toggleRunner(runner.key)}
                    onKeyDown={(event) => handleRunnerKeyDown(event, runner.key)}
                  >
                    <td className="eiq-field-cell-no">{display(runner.no)}</td>
                    <td>
                      {runner.silkUrl && runner.silkUrl.startsWith("http") ? (
                        <img className="eiq-field-table-v1__silk" src={runner.silkUrl} alt="" loading="lazy" />
                      ) : (
                        <span className="eiq-field-table-v1__silk eiq-race-intel-silk--empty" aria-hidden="true" />
                      )}
                    </td>
                    <td className="is-left">
                      <button
                        type="button"
                        className="eiq-field-runner-button"
                        onClick={(event) => {
                          event.stopPropagation();
                          toggleRunner(runner.key);
                        }}
                        aria-expanded={expanded}
                      >
                        <strong>{display(runner.runner)}</strong>
                        <small>{expanded ? "Hide last five" : "Show last five"}</small>
                      </button>
                    </td>
                    <td>{display(runner.barrier)}</td>
                    <td>{display(runner.weight)}</td>
                    <td className="is-left">{display(runner.jockey)}</td>
                    <td className="is-left">{display(runner.trainer)}</td>
                    <td className="is-left">{display(runner.gear, "No change supplied")}</td>
                    <td><span className="eiq-field-status-pill">{display(runner.status)}</span></td>
                    <td>
                      <button
                        type="button"
                        className="eiq-approved-button"
                        disabled={runner.isScratched}
                        onClick={(event) => {
                          event.stopPropagation();
                          onOpenRunner(runner.sourceIndex);
                        }}
                      >
                        {runner.isScratched ? "Scratched" : "Open"}
                      </button>
                    </td>
                  </tr>
                  {expanded ? (
                    <tr className="eiq-field-expanded-row">
                      <td colSpan={10}>
                        <div className="eiq-field-recent-panel">
                          <header>
                            <div><span>LAST FIVE STARTS</span><strong>{display(runner.runner)}</strong></div>
                            {!runner.isScratched ? <button type="button" className="eiq-approved-button" onClick={() => onOpenRunner(runner.sourceIndex)}>Open Full Runner Profile</button> : null}
                          </header>
                          {runner.recentRuns.length ? (
                            <table>
                              <thead>
                                <tr>
                                  <th>DATE</th>
                                  <th>TRACK</th>
                                  <th>DIST</th>
                                  <th>CLASS</th>
                                  <th>POS</th>
                                  <th>MARGIN</th>
                                  <th>JOCKEY</th>
                                  <th>WGT</th>
                                  <th>SP</th>
                                  {flags.epi ? <th>EPI</th> : null}
                                  {flags.eri ? <th>ERI</th> : null}
                                </tr>
                              </thead>
                              <tbody>
                                {runner.recentRuns.slice(0, 5).map((run, index) => (
                                  <tr key={`${runner.key}-run-${index}`}>
                                    <td>{display(run.date)}</td>
                                    <td>{display(run.track)}</td>
                                    <td>{display(run.distance)}</td>
                                    <td>{display(run.raceClass)}</td>
                                    <td>{display(run.position)}</td>
                                    <td>{display(run.margin)}</td>
                                    <td>{display(run.jockey)}</td>
                                    <td>{display(run.weight)}</td>
                                    <td>{display(run.sp)}</td>
                                    {flags.epi ? <td>{display(run.epi)}</td> : null}
                                    {flags.eri ? <td>{display(run.eri)}</td> : null}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          ) : (
                            <div className="eiq-field-recent-empty">NO PREVIOUS STARTS PUBLISHED</div>
                          )}
                        </div>
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              );
            }) : (
              <tr className="eiq-field-empty-row">
                <td colSpan={10}>No official runners are published for this race.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
