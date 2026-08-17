import { Fragment, useMemo, useState, type KeyboardEvent } from "react";
import { buildFieldWorkspaceRows } from "../services/fieldWorkspaceViewModel";
import type { FormGuideRaceDisplay, FormGuideRecentRun } from "../services/formGuideNormaliser";
import { EiqButton, EiqDataTable, EiqEmptyState, EiqPanel, EiqSectionHeader, EiqStatusBadge } from "../../design-system/v1";

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

export function FieldWorkspace({ field, formGuide, weight, market }: FieldWorkspaceProps) {
  const [expandedKey, setExpandedKey] = useState<string | null>(null);
  const rows = useMemo(() => buildFieldWorkspaceRows({ field, formGuide, weight, market }), [field, formGuide, weight, market]);
  const scratchedCount = rows.filter((runner) => runner.isScratched).length;
  const activeCount = Math.max(0, rows.length - scratchedCount);

  const toggleRunner = (key: string) => {
    setExpandedKey((current) => (current === key ? null : key));
  };

  const handleRunnerKeyDown = (event: KeyboardEvent<HTMLTableRowElement>, key: string) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    toggleRunner(key);
  };

  return (
    <section className="eiq-field-v2-workspace eiq-v1-standard-workspace" aria-label="Field workspace">
      <EiqPanel className="eiq-field-v2-intro">
        <div className="eiq-field-v2-intro__copy">
          <EiqSectionHeader eyebrow="FIELD" title="Official declared runners" />
          <p className="eiq-v1-analytical-copy">Click a runner to review their latest available starts.</p>
        </div>
        <div className="eiq-field-v2-counts" aria-label={`Field counts: ${rows.length} runners, ${activeCount} active, ${scratchedCount} scratched`}>
          <strong>{rows.length} RUNNERS</strong>
          <span>ACTIVE {activeCount} <em aria-hidden="true">|</em> SCRATCHED {scratchedCount}</span>
        </div>
      </EiqPanel>

      <EiqPanel className="eiq-v1-standard-table-panel">
        <EiqSectionHeader eyebrow="Runner Table" title="Field and market context" />
        <EiqDataTable
          density="compact"
          className="eiq-field-v2-table"
          wrapperProps={{ className: "eiq-v1-standard-table-scroll" }}
        >
          <colgroup>
            <col className="eiq-field-col-no" />
            <col className="eiq-field-col-silk" />
            <col className="eiq-field-col-runner" />
            <col className="eiq-field-col-bar" />
            <col className="eiq-field-col-wgt" />
            <col className="eiq-field-col-jockey" />
            <col className="eiq-field-col-trainer" />
            <col className="eiq-field-col-epi" />
            <col className="eiq-field-col-market" />
            <col className="eiq-field-col-status" />
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
              <th>EPR</th>
              <th>MARKET</th>
              <th>STATUS</th>
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
                      <EiqButton
                        type="button"
                        className="eiq-field-v2-runner-button"
                        variant="ghost"
                        size="compact"
                        onClick={(event) => {
                          event.stopPropagation();
                          toggleRunner(runner.key);
                        }}
                        aria-expanded={expanded}
                      >
                        <strong>{display(runner.runner)}</strong>
                        <small>{expanded ? "Hide recent starts" : "View recent starts"}</small>
                      </EiqButton>
                    </td>
                    <td>{display(runner.barrier)}</td>
                    <td>{display(runner.weight)}</td>
                    <td className="is-left">{display(runner.jockey)}</td>
                    <td className="is-left">{display(runner.trainer)}</td>
                    <td>{runner.isScratched ? "-" : display(runner.edgeiq)}</td>
                    <td>{display(runner.market, runner.isScratched ? "Scratched" : "-")}</td>
                    <td><EiqStatusBadge status={display(runner.status)} /></td>
                  </tr>
                  {expanded ? (
                    <tr className="eiq-field-expanded-row">
                      <td colSpan={10}>
                        <div className="eiq-field-recent-panel">
                          <EiqSectionHeader eyebrow="Last Five Starts" title={display(runner.runner)} />
                          {runner.recentRuns.length ? (
                            <EiqDataTable density="dense" className="eiq-field-v2-recent-table">
                              <thead>
                                <tr>
                                  <th>Date</th>
                                  <th>Track</th>
                                  <th>Dist</th>
                                  <th>Class</th>
                                  <th>Pos</th>
                                  <th>Margin</th>
                                  <th>Jockey</th>
                                  <th>Wgt</th>
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
                            </EiqDataTable>
                          ) : (
                            <EiqEmptyState title="No previous starts" />
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
        </EiqDataTable>
      </EiqPanel>
    </section>
  );
}
