import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  buildPerformanceIntelligenceService,
  formatBenchmarkLevel,
  loadPerformanceIntelligenceFeed,
  type HistoricalPerformanceIntelligenceRow,
  type PerformanceIntelligenceService,
} from "../../services/performance-intelligence";

type RaceBookContext = {
  official?: {
    meeting?: any;
    raceNumber?: any;
    distance?: any;
    raceClass?: any;
    trackCondition?: any;
    rail?: any;
    fieldSize?: any;
  };
};

type ResultsWorkspaceProps = {
  run: any;
  runner?: any;
  raceKey?: string | null;
  raceBook?: RaceBookContext;
  clean: (value: any) => string;
  weight: (value: any) => string;
  market: (value: any) => string;
  esiOverall?: ReactNode;
  onBackToForm: () => void;
  onCompareSelectedRun: () => void;
  onEvidence: () => void;
};

function hasValue(value: any) {
  return value !== null && value !== undefined && value !== "" && value !== "Not available" && value !== "Not recorded";
}

function firstValue(...values: any[]) {
  return values.find(hasValue);
}

function sameText(left: any, right: any) {
  return String(left ?? "").trim().toUpperCase() === String(right ?? "").trim().toUpperCase();
}

function CertifiedRunContext({ row }: { row: HistoricalPerformanceIntelligenceRow | null }) {
  return (
    <aside className="eiq-results-workspace__summary">
      <span>Certified Performance Intelligence</span>
      {row ? (
        <>
          <strong>{formatBenchmarkLevel(row.benchmark_level)}</strong>
          <p>
            Race benchmark context from the certified performance warehouse. Runner lengths versus benchmark remain unavailable until a governed conversion exists.
          </p>
          <dl>
            <div><dt>Benchmark Sample</dt><dd>{row.benchmark_sample_size || "Unavailable"}</dd></div>
            <div><dt>Race vs Benchmark</dt><dd>{row.race_seconds_vs_benchmark || "Unavailable"}</dd></div>
            <div><dt>Pattern</dt><dd>{row.fingerprint_pattern || "Unavailable"}</dd></div>
            <div><dt>Quality</dt><dd>{row.fingerprint_quality_state || "Unavailable"}</dd></div>
          </dl>
        </>
      ) : (
        <>
          <strong>Historical benchmark context unavailable.</strong>
          <p>The selected run is not linked to the compact certified performance feed for this product race.</p>
        </>
      )}
    </aside>
  );
}

function SectionalsBoundary({ esiOverall }: { esiOverall?: ReactNode }) {
  return (
    <aside className="eiq-results-workspace__summary">
      <span>Sectionals</span>
      <strong>{hasValue(esiOverall) ? "ESI lengths available." : "Sectional lengths unavailable."}</strong>
      <p>
        EDGEiQ displays sectionals as lengths versus standard only. Raw official split times are not shown in this workspace.
      </p>
      <p>Stewards report unavailable from the current governed source.</p>
      <dl>
        <div>
          <dt>ESI Overall</dt>
          <dd>{hasValue(esiOverall) ? esiOverall : "Unavailable"}</dd>
        </div>
        <div>
          <dt>Display Rule</dt>
          <dd>Lengths vs standard</dd>
        </div>
      </dl>
    </aside>
  );
}

export function ResultsWorkspace({
  run,
  runner,
  raceKey,
  raceBook,
  clean,
  weight,
  market,
  esiOverall,
  onBackToForm,
  onCompareSelectedRun,
  onEvidence,
}: ResultsWorkspaceProps) {
  const [performanceService, setPerformanceService] = useState<PerformanceIntelligenceService | null>(null);
  const official = run?.professionalForm?.official ?? {};
  const evidence = run?.professionalForm?.evidence ?? {};
  const raceNumber = firstValue(official.race, raceBook?.official?.raceNumber);
  const headerItems = [
    ["Track", official.track],
    ["Race", raceNumber ? `R${clean(raceNumber)}` : null],
    ["Date", official.date],
    ["Distance", official.distance],
    ["Class", official.raceClass],
    ["Condition", official.condition],
    ["Rail", firstValue(official.rail, raceBook?.official?.rail)],
    ["Field", firstValue(official.fieldSize, raceBook?.official?.fieldSize)],
    ["ERI", evidence.raceStrength?.overall ?? run?.edgeiqRaceStrength],
  ].filter(([, value]) => hasValue(value));

  const row = {
    finish: official.finish,
    runner: run?.runner ?? run?.horse ?? run?.runnerName,
    barrier: official.barrier,
    weight: official.weight,
    jockey: official.jockey,
    trainer: official.trainer ?? run?.trainer,
    sp: official.sp,
    margin: official.margin,
    epi: evidence.runRating?.overall ?? run?.edgeiqRunRating,
    esi: esiOverall,
    stewards: official.stewardsReportNotes ?? official.stewardsNotes ?? run?.stewardsReportNotes ?? run?.stewardsReport ?? run?.stewardsNotes,
  };

  const columns = [
    ["Finish", row.finish, (value: any) => clean(value)],
    ["Runner", row.runner, (value: any) => clean(value)],
    ["Barrier", row.barrier, (value: any) => clean(value)],
    ["Weight", row.weight, (value: any) => weight(value)],
    ["Jockey", row.jockey, (value: any) => clean(value)],
    ["Trainer", row.trainer, (value: any) => clean(value)],
    ["SP", row.sp, (value: any) => market(value)],
    ["Margin", row.margin, (value: any) => clean(value)],
    ["EPI", row.epi, (value: any) => clean(value)],
    ["ESI", row.esi, (value: any) => value],
    ["Stewards", row.stewards, (value: any) => clean(value)],
  ].filter(([, value]) => hasValue(value));

  const hasFullRaceResults = Array.isArray(run?.raceResultRows) && run.raceResultRows.length > 1;
  const certifiedRunContext = useMemo(() => {
    const rows = performanceService?.getHistoricalForRunner(
      raceKey,
      runner?.saddlecloth ?? runner?.number ?? runner?.no,
      runner?.horse ?? runner?.runnerName,
    ) ?? [];
    return (
      rows.find((row) => sameText(row.race_date, official.date) && sameText(row.track, official.track)) ??
      rows.find((row) => sameText(row.race_context_key, official.raceContextKey)) ??
      rows[0] ??
      null
    );
  }, [official.date, official.raceContextKey, official.track, performanceService, raceKey, runner]);

  useEffect(() => {
    let cancelled = false;
    loadPerformanceIntelligenceFeed()
      .then((feed) => {
        if (!cancelled) setPerformanceService(buildPerformanceIntelligenceService(feed));
      })
      .catch((error) => {
        console.warn("Performance intelligence feed unavailable", error);
        if (!cancelled) setPerformanceService(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="eiq-results-workspace">
      <header className="eiq-results-workspace__header">
        <div>
          <span>RESULTS</span>
          <strong>What happened in that historical race?</strong>
          <p>{hasFullRaceResults ? "Historical race result connected." : "Results data not yet connected for this historical race."}</p>
        </div>
        <dl>
          {headerItems.map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{clean(value)}</dd>
            </div>
          ))}
        </dl>
      </header>

      <div className="eiq-results-workspace__body">
        <section className="eiq-results-workspace__panel">
          <div className="eiq-results-workspace__title">
            <span>Runner Performance</span>
            <em>Historical race context</em>
          </div>

          {hasFullRaceResults ? (
            <table>
              <thead>
                <tr>
                  {columns.map(([label]) => <th key={label}>{label}</th>)}
                </tr>
              </thead>
              <tbody>
                <tr>
                  {columns.map(([label, value, formatter]) => <td key={label}>{formatter(value)}</td>)}
                </tr>
              </tbody>
            </table>
          ) : (
            <div className="eiq-results-workspace__empty">
              <strong>Results data not yet connected for this historical race.</strong>
              <p>EDGEiQ has the selected runner's historical run context, but not the full race result field for this race yet.</p>
            </div>
          )}
        </section>

        <div className="eiq-results-workspace__stack">
          <CertifiedRunContext row={certifiedRunContext} />
          <SectionalsBoundary esiOverall={esiOverall} />
        </div>
      </div>

      <footer className="eiq-results-workspace__actions">
        <button type="button" onClick={onBackToForm}>Back to Form</button>
        <button type="button" onClick={onCompareSelectedRun}>Compare Selected Run</button>
        <button type="button" onClick={onEvidence}>Evidence</button>
      </footer>
    </section>
  );
}
