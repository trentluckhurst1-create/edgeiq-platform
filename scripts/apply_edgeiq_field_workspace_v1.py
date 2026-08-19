from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DOC_ROOT = ROOT / "docs" / "full-product-implementation"

FIELD_TSX = ROOT / "src" / "edgeiq-os" / "race" / "components" / "FieldWorkspace.tsx"
VM_TS = ROOT / "src" / "edgeiq-os" / "race" / "services" / "fieldWorkspaceViewModel.ts"
RACE_TSX = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
FORENSIC = DOC_ROOT / "EDGEIQ_FIELD_WORKSPACE_V1_FORENSIC_REPORT.md"

FIELD_CONTENT = r'''import { Fragment, useMemo, useState, type KeyboardEvent } from "react";
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
    <section className="eiq-workspace-panel eiq-field-workspace-v1" aria-label="Field workspace">
      <header className="eiq-field-v1__header">
        <div>
          <span>FIELD</span>
          <strong>Official declared runners</strong>
          <p>Click a runner to review their latest available starts.</p>
        </div>
        <aside className="eiq-field-v1__counts" aria-label="Field counts">
          <strong>{rows.length} RUNNERS</strong>
          <span>{activeCount} ACTIVE | {scratchedCount} SCRATCHED</span>
        </aside>
      </header>

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
              <th>EPI</th>
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
                        <small>{expanded ? "Hide recent starts" : "View recent starts"}</small>
                      </button>
                    </td>
                    <td>{display(runner.barrier)}</td>
                    <td>{display(runner.weight)}</td>
                    <td className="is-left">{display(runner.jockey)}</td>
                    <td className="is-left">{display(runner.trainer)}</td>
                    <td>{runner.isScratched ? "-" : display(runner.edgeiq)}</td>
                    <td>{display(runner.market, runner.isScratched ? "Scratched" : "-")}</td>
                    <td><span className="eiq-field-status-pill">{display(runner.status)}</span></td>
                  </tr>
                  {expanded ? (
                    <tr className="eiq-field-expanded-row">
                      <td colSpan={10}>
                        <div className="eiq-field-recent-panel">
                          <header>
                            <span>LAST FIVE STARTS</span>
                            <strong>{display(runner.runner)}</strong>
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
                            <div className="eiq-field-recent-empty">NO PREVIOUS STARTS</div>
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
'''

VM_CONTENT = r'''import type { FormGuideRaceDisplay, FormGuideRecentRun, FormGuideRunnerDisplay } from "./formGuideNormaliser";

export type FieldWorkspaceRow = {
  key: string;
  sourceIndex: number;
  no: string;
  silkUrl: string;
  runner: string;
  barrier: string;
  weight: string;
  jockey: string;
  trainer: string;
  edgeiq: string;
  market: string;
  status: string;
  isScratched: boolean;
  recentRuns: FormGuideRecentRun[];
};

function clean(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value).trim();
  if (!text || text === "-" || /^(none|null|undefined|nan|not available|unavailable)$/i.test(text)) return "";
  return text;
}

function firstValue(row: any, keys: string[]): any {
  for (const key of keys) {
    const value = key.split(".").reduce((acc: any, part) => acc?.[part], row);
    if (value !== undefined && value !== null && value !== "") return value;
  }
  return undefined;
}

function normaliseRunner(value: unknown): string {
  return clean(value).toUpperCase().replace(/[^A-Z0-9]/g, "");
}

function matchFormRunner(formGuide: FormGuideRaceDisplay | null | undefined, no: string, runner: string): FormGuideRunnerDisplay | null {
  if (!formGuide?.runners?.length) return null;
  const runnerKey = normaliseRunner(runner);
  return (
    formGuide.runners.find((candidate) => clean(candidate.no) === no) ??
    formGuide.runners.find((candidate) => runnerKey && normaliseRunner(candidate.horse) === runnerKey) ??
    null
  );
}

function statusForRunner(row: any, formRunner: FormGuideRunnerDisplay | null): string {
  if (formRunner?.scratched) return "Scratched";
  const raw = clean(firstValue(row, ["status", "official.status", "scratchingStatus", "official.scratchingStatus", "availability"]));
  if (raw) return raw;
  const scratched = firstValue(row, ["scratched", "official.scratched", "isScratched", "is_scratch", "is_scratched"]);
  return scratched === true || String(scratched).toUpperCase() === "TRUE" ? "Scratched" : "Active";
}

function normaliseStatus(status: string, marketValue: string): { status: string; isScratched: boolean } {
  const statusScratched = /scratch/i.test(status);
  const marketScratched = /^scratched$/i.test(clean(marketValue));
  const isScratched = statusScratched || marketScratched;
  return { status: isScratched ? "Scratched" : clean(status) || "Active", isScratched };
}

export function buildFieldWorkspaceRows(params: {
  field: any[];
  formGuide?: FormGuideRaceDisplay | null;
  weight: (value: any) => string;
  market: (value: any) => string;
}): FieldWorkspaceRow[] {
  const rows = Array.isArray(params.field) ? params.field : [];
  return rows.map((runner, index) => {
    const no = clean(firstValue(runner, ["official.number", "number", "runnerNumber", "runner_number", "saddlecloth", "no"])) || String(index + 1);
    const runnerName = clean(firstValue(runner, ["official.runner", "runner", "runnerName", "runner_name", "horse", "horseName", "name"]));
    const formRunner = matchFormRunner(params.formGuide, no, runnerName);
    const rawStatus = statusForRunner(runner, formRunner);
    const rawMarket = clean(formRunner?.marketPrice) || clean(params.market(firstValue(runner, ["official.market", "market", "live", "price", "marketPrice", "market_price", "tabPrice", "fixedOdds"]))) || "";
    const { status, isScratched } = normaliseStatus(rawStatus, rawMarket);
    const edgeiq = clean(formRunner?.epi) || clean(firstValue(runner, ["metrics.epi", "epi", "currentEpi", "current_epi", "horsePerformanceRating", "performanceRating", "rating", "official.epi"]));
    const weightValue = clean(formRunner?.weight) || clean(params.weight(firstValue(runner, [
      "official.weight",
      "official.allocatedWeight",
      "official.handicapWeight",
      "official.weightCarried",
      "weight",
      "allocated_weight",
      "allocatedWeight",
      "handicap_weight",
      "handicapWeight",
      "weight_carried",
      "weightCarried",
      "runner_weight",
      "runnerWeight",
      "weight_kg",
      "weightKg",
      "wt",
    ])));

    return {
      key: `${no}-${runnerName || formRunner?.horse || index}`,
      sourceIndex: index,
      no,
      silkUrl: formRunner?.silkUrl || clean(firstValue(runner, ["official.silkUrl", "silkUrl", "silksUrl", "silk"])),
      runner: formRunner?.horse || runnerName,
      barrier: formRunner?.barrier || clean(firstValue(runner, ["official.barrier", "barrier", "bar", "draw"])),
      weight: weightValue,
      jockey: formRunner?.jockey || clean(firstValue(runner, ["official.jockey", "jockey", "jockeyName", "jockey_name"])),
      trainer: formRunner?.trainer || clean(firstValue(runner, ["official.trainer", "trainer", "trainerName", "trainer_name"])),
      edgeiq: isScratched ? "" : edgeiq,
      market: isScratched ? "Scratched" : rawMarket,
      status,
      isScratched,
      recentRuns: (formRunner?.recentRuns ?? []).slice(0, 5),
    };
  });
}
'''

CSS_BLOCK = r'''

/* EDGEIQ FIELD WORKSPACE V1 */
.eiq-approved-shell .eiq-race-workspace--field > .eiq-context-tabs {
  display: grid;
  grid-template-columns: repeat(11, minmax(0, 1fr));
  gap: 6px;
  align-items: stretch;
}

.eiq-approved-shell .eiq-race-workspace--field > .eiq-context-tabs button {
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 0.68rem;
  letter-spacing: 0;
  padding-inline: 8px;
}

.eiq-approved-shell .eiq-race-workspace--field .eiq-approved-racefile-header__meta {
  grid-template-columns: repeat(auto-fit, minmax(116px, 1fr));
}

.eiq-approved-shell .eiq-field-workspace-v1 {
  padding: 16px;
  gap: 14px;
  background: rgba(255, 255, 255, 0.96);
}

.eiq-approved-shell .eiq-field-v1__header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  padding: 0 2px 10px;
  border-bottom: 1px solid rgba(23, 35, 58, 0.12);
}

.eiq-approved-shell .eiq-field-v1__header span {
  display: block;
  color: #426389;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.14em;
}

.eiq-approved-shell .eiq-field-v1__header strong {
  display: block;
  margin-top: 4px;
  color: #101827;
  font-size: clamp(1.08rem, 1.45vw, 1.48rem);
  line-height: 1.05;
  letter-spacing: -0.015em;
}

.eiq-approved-shell .eiq-field-v1__header p {
  margin: 4px 0 0;
  color: #607086;
  font-size: 0.8rem;
}

.eiq-approved-shell .eiq-field-v1__counts {
  min-width: 190px;
  text-align: right;
  color: #26344c;
}

.eiq-approved-shell .eiq-field-v1__counts strong {
  font-size: 0.9rem;
  letter-spacing: 0.05em;
}

.eiq-approved-shell .eiq-field-v1__counts span {
  margin-top: 4px;
  color: #65758c;
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.eiq-approved-shell .eiq-field-table-wrap-v1 {
  width: 100%;
  overflow-x: auto;
  border: 1px solid rgba(23, 35, 58, 0.12);
  border-radius: 16px;
  background: #ffffff;
}

.eiq-approved-shell .eiq-field-table-v1 {
  width: 100%;
  table-layout: fixed;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 0.78rem;
}

.eiq-approved-shell .eiq-field-table-v1 col.eiq-field-col-no { width: 4.5%; }
.eiq-approved-shell .eiq-field-table-v1 col.eiq-field-col-silk { width: 5%; }
.eiq-approved-shell .eiq-field-table-v1 col.eiq-field-col-runner { width: 18%; }
.eiq-approved-shell .eiq-field-table-v1 col.eiq-field-col-bar { width: 5%; }
.eiq-approved-shell .eiq-field-table-v1 col.eiq-field-col-wgt { width: 6.5%; }
.eiq-approved-shell .eiq-field-table-v1 col.eiq-field-col-jockey { width: 15%; }
.eiq-approved-shell .eiq-field-table-v1 col.eiq-field-col-trainer { width: 17.5%; }
.eiq-approved-shell .eiq-field-table-v1 col.eiq-field-col-epi { width: 7%; }
.eiq-approved-shell .eiq-field-table-v1 col.eiq-field-col-market { width: 8%; }
.eiq-approved-shell .eiq-field-table-v1 col.eiq-field-col-status { width: 13.5%; }

.eiq-approved-shell .eiq-field-table-v1 th,
.eiq-approved-shell .eiq-field-table-v1 td {
  padding: 11px 10px;
  border-bottom: 1px solid rgba(23, 35, 58, 0.08);
  color: #1b2738;
  text-align: center;
  vertical-align: middle;
  overflow-wrap: anywhere;
}

.eiq-approved-shell .eiq-field-table-v1 th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #f5f7fb;
  color: #53657d;
  font-size: 0.66rem;
  font-weight: 900;
  letter-spacing: 0.12em;
}

.eiq-approved-shell .eiq-field-table-v1 th.is-left,
.eiq-approved-shell .eiq-field-table-v1 td.is-left {
  text-align: left;
}

.eiq-approved-shell .eiq-field-runner-row {
  cursor: pointer;
  transition: background 150ms ease, box-shadow 150ms ease;
}

.eiq-approved-shell .eiq-field-runner-row:hover,
.eiq-approved-shell .eiq-field-runner-row:focus-visible {
  outline: none;
  background: #f8fbff;
  box-shadow: inset 4px 0 0 rgba(37, 99, 235, 0.45);
}

.eiq-approved-shell .eiq-field-runner-row.is-expanded {
  background: #f7fbff;
  box-shadow: inset 4px 0 0 #2563eb;
}

.eiq-approved-shell .eiq-field-runner-row.is-scratched {
  background: #f7f7f8;
  color: #7a8392;
}

.eiq-approved-shell .eiq-field-runner-row.is-scratched td {
  color: #7a8392;
}

.eiq-approved-shell .eiq-field-cell-no {
  font-weight: 900;
  color: #101827;
}

.eiq-approved-shell .eiq-field-table-v1__silk {
  display: inline-flex;
  width: 32px;
  height: 32px;
  object-fit: contain;
  border-radius: 50%;
  background: #eef2f7;
}

.eiq-approved-shell .eiq-field-runner-button {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 3px;
  max-width: 100%;
  border: 0;
  background: transparent;
  padding: 0;
  color: inherit;
  font: inherit;
  cursor: pointer;
  text-align: left;
}

.eiq-approved-shell .eiq-field-runner-button strong {
  color: #111827;
  font-size: 0.87rem;
  font-weight: 900;
  line-height: 1.15;
}

.eiq-approved-shell .eiq-field-runner-button small {
  color: #68788e;
  font-size: 0.66rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eiq-approved-shell .eiq-field-status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 76px;
  border: 1px solid rgba(23, 35, 58, 0.14);
  border-radius: 999px;
  padding: 5px 9px;
  background: #ffffff;
  color: #334155;
  font-size: 0.66rem;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eiq-approved-shell .eiq-field-runner-row.is-scratched .eiq-field-status-pill {
  background: #f1f3f6;
  color: #6b7280;
  border-color: rgba(107, 114, 128, 0.25);
}

.eiq-approved-shell .eiq-field-expanded-row td {
  padding: 0;
  background: #f6f9fd;
}

.eiq-approved-shell .eiq-field-recent-panel {
  margin: 0;
  padding: 14px 16px 16px 88px;
  border-top: 1px solid rgba(37, 99, 235, 0.14);
  background: linear-gradient(180deg, rgba(248, 251, 255, 0.98), rgba(241, 246, 252, 0.96));
}

.eiq-approved-shell .eiq-field-recent-panel header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.eiq-approved-shell .eiq-field-recent-panel header span {
  color: #426389;
  font-size: 0.66rem;
  font-weight: 900;
  letter-spacing: 0.14em;
}

.eiq-approved-shell .eiq-field-recent-panel header strong {
  color: #172033;
  font-size: 0.82rem;
  font-weight: 900;
}

.eiq-approved-shell .eiq-field-recent-panel table {
  width: 100%;
  border-collapse: collapse;
  background: #ffffff;
  border: 1px solid rgba(23, 35, 58, 0.08);
  border-radius: 10px;
  overflow: hidden;
}

.eiq-approved-shell .eiq-field-recent-panel th,
.eiq-approved-shell .eiq-field-recent-panel td {
  padding: 8px 9px;
  border-bottom: 1px solid rgba(23, 35, 58, 0.07);
  font-size: 0.72rem;
  text-align: left;
}

.eiq-approved-shell .eiq-field-recent-panel th {
  background: #f1f5fa;
  color: #5a6b81;
  font-size: 0.61rem;
  font-weight: 900;
  letter-spacing: 0.1em;
}

.eiq-approved-shell .eiq-field-recent-empty,
.eiq-approved-shell .eiq-field-empty-row td {
  padding: 18px;
  color: #69778c;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-align: center;
}

@media (max-width: 1440px) {
  .eiq-approved-shell .eiq-race-workspace--field > .eiq-context-tabs {
    gap: 4px;
  }

  .eiq-approved-shell .eiq-race-workspace--field > .eiq-context-tabs button {
    font-size: 0.62rem;
    padding-inline: 6px;
  }

  .eiq-approved-shell .eiq-field-table-v1 th,
  .eiq-approved-shell .eiq-field-table-v1 td {
    padding-inline: 7px;
  }
}

@media (max-width: 1366px) {
  .eiq-approved-shell .eiq-field-v1__header {
    align-items: flex-start;
  }

  .eiq-approved-shell .eiq-field-v1__header p {
    max-width: 520px;
  }

  .eiq-approved-shell .eiq-field-table-v1 {
    font-size: 0.72rem;
  }

  .eiq-approved-shell .eiq-field-table-v1__silk {
    width: 28px;
    height: 28px;
  }
}
'''

FORENSIC_CONTENT = r'''# EDGEIQ FIELD WORKSPACE V1 Forensic Report

## Status Before Remediation
FIELD was functional but not locked. Browser and source inspection showed a basic acceptances-style table rather than a governed product workspace.

## Render Path Verified
RaceFileV3.tsx mounts RaceWorkspace for race view. RaceWorkspace maps the FIELD tab to FieldWorkspace. FieldWorkspace builds display rows through buildFieldWorkspaceRows in fieldWorkspaceViewModel.ts and receives governed form data from normaliseFormGuideRace.

## Header Finding
FIELD uses RaceWorkspace's shared non-RACE header. The header was not duplicated inside FieldWorkspace, but the shared header allowed raw administrative race text to appear as user-facing TRACK or SURFACE metadata when source fields were concatenated.

## Tab Finding
The workspace tab strip is generated from RaceWorkspace's tabs array. FIELD lacked the compact tab geometry applied to the repaired RACE workspace, allowing REVIEW to wrap awkwardly at desktop widths.

## Last-Five Data Finding
Last-five data already exists in FormGuideRaceDisplay.runners[].recentRuns and FieldWorkspace already had dormant expansion logic. The interaction was incomplete because only the runner-name button opened it, the expansion included an unnecessary navigation button, and the no-history copy was internal.

## Scratched Finding
Scratching status can arrive from official/status flags, formGuide.scratched, and a presentation market value of Scratched. The FIELD view model only trusted some status flags, so rows could show market Scratched while retaining ACTIVE status.

## EDGEiQ Semantics Finding
The current FIELD edgeiq column is primarily EPI/current performance rating data, not EDGEiQ price. The visible compact column label must therefore be EPI rather than generic EDGEiQ.

## CSS Finding
Live shell scoping uses .eiq-approved-shell. Older .edgeiq-os scoped rules do not reliably affect the approved shell. FIELD needed approved-shell scoped table, header, tab and expansion rules.

## Remediation Scope
The fix is presentation/view-model only: RaceWorkspace header sanitisation, FieldWorkspace structure/interaction, FieldWorkspace view-model scratch and weight handling, and FIELD CSS. No pricing, probability, EPI calculation, V6/V7 engine, backend, FORM workspace, HOME, MEETINGS or RACE logic is changed.
'''

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Missing expected block: {label}")
    return text.replace(old, new, 1)

def patch_race_workspace():
    text = RACE_TSX.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'import { canonicalRaceTitleDisplay, canonicalTrackDisplayName } from "../../design-system/presentation";',
        'import { canonicalRaceTitleDisplay, canonicalRailDisplay, canonicalTrackDisplayName, canonicalTrackRatingDisplay, canonicalWeatherDisplay } from "../../design-system/presentation";',
        "presentation import",
    )
    old = '''  const headerValue = (value: any) => {
    const text = clean(value);
    if (!text || text === "-" || /^not supplied$/i.test(text) || /^unavailable$/i.test(text)) return "";
    if (/^race file$/i.test(text)) return "";
    return text;
  };
  const raceNumber = headerValue(official.raceNumber);
  const meetingName = canonicalTrackDisplayName(headerValue(official.meeting));
  const raceClass = headerValue(official.class) || headerValue(official.raceClass);
  const distance = headerValue(official.distance);
  const trackCondition = headerValue(official.trackCondition) || headerValue(official.condition);
  const raceDate = headerValue(official.date) || headerValue(official.raceDate);
  const raceTime = headerValue(official.time) || headerValue(official.localTime);
  const surface = headerValue(official.surface) || headerValue(official.trackType);
  const prizeMoney = headerValue(official.prizeMoney) || headerValue(official.totalPrizeMoney);
  const raceTitle = canonicalRaceTitleDisplay(headerValue(official.raceName) || headerValue(official.name));
  const showRaceFileHeader = tab !== "RACE";
  const raceHeaderMeta = [
    ["LOCATION", meetingName],
    ["DATE", raceDate],
    ["TIME", raceTime],
    ["DISTANCE", distance],
    ["SURFACE", surface],
    ["PRIZE MONEY", prizeMoney],
  ].filter((item) => item[1]);
'''
    new = '''  const headerValue = (value: any) => {
    const text = clean(value);
    if (!text || text === "-" || /^not supplied$/i.test(text) || /^unavailable$/i.test(text)) return "";
    if (/^race file$/i.test(text)) return "";
    return text;
  };
  const usefulHeaderValue = (value: any) => {
    const text = headerValue(value);
    if (!text) return "";
    if (text.length > 80) return "";
    if (/Set Weights|Apprentices|VOBIS|field limit|Track name:|Track type:|No sex restriction|No age restriction|Bonus/i.test(text)) return "";
    return text;
  };
  const firstHeaderValue = (...values: any[]) => values.map(usefulHeaderValue).find(Boolean) || "";
  const raceNumber = headerValue(official.raceNumber);
  const meetingName = canonicalTrackDisplayName(headerValue(official.meeting));
  const raceClass = firstHeaderValue(official.class, official.raceClass, official.benchmark, official.restrictions?.class);
  const distance = firstHeaderValue(official.distance);
  const trackCondition = canonicalTrackRatingDisplay(firstHeaderValue(official.trackCondition, official.condition), "");
  const rail = canonicalRailDisplay(firstHeaderValue(official.rail, official.railPosition), "");
  const weather = canonicalWeatherDisplay(firstHeaderValue(official.weather, official.weatherCondition), "");
  const raceDate = firstHeaderValue(official.date, official.raceDate);
  const raceTime = firstHeaderValue(official.time, official.localTime);
  const prizeMoney = firstHeaderValue(official.prizeMoney, official.totalPrizeMoney);
  const raceTitle = canonicalRaceTitleDisplay(headerValue(official.raceName) || headerValue(official.name));
  const showRaceFileHeader = tab !== "RACE";
  const raceHeaderMeta = [
    ["MEETING", meetingName],
    ["DATE", raceDate],
    ["TIME", raceTime],
    ["DISTANCE", distance],
    ["CLASS", raceClass],
    ["TRACK", trackCondition],
    ["RAIL", rail],
    ["WEATHER", weather],
    ["PRIZEMONEY", prizeMoney],
  ].filter((item) => item[1]);
'''
    text = replace_once(text, old, new, "header values")
    old_extra = '''            {trackCondition ? (
              <div>
                <dt>TRACK</dt>
                <dd>{trackCondition}</dd>
              </div>
            ) : null}
'''
    text = text.replace(old_extra, "", 1)
    RACE_TSX.write_text(text, encoding="utf-8")

def main():
    DOC_ROOT.mkdir(parents=True, exist_ok=True)
    FORENSIC.write_text(FORENSIC_CONTENT, encoding="utf-8")
    FIELD_TSX.write_text(FIELD_CONTENT, encoding="utf-8")
    VM_TS.write_text(VM_CONTENT, encoding="utf-8")
    patch_race_workspace()
    css = CSS.read_text(encoding="utf-8")
    marker = "/* EDGEIQ FIELD WORKSPACE V1 */"
    if marker not in css:
        CSS.write_text(css.rstrip() + CSS_BLOCK + "\n", encoding="utf-8")
    print("EDGEIQ_FIELD_WORKSPACE_V1_APPLIED")

if __name__ == "__main__":
    main()
