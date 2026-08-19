from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS_WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "ResultsWorkspace.tsx"
MEETING_RESULTS = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingResultsWorkspace.tsx"
GLOBAL_RESULTS = ROOT / "src" / "edgeiq-os" / "race" / "components" / "GlobalResultsWorkspace.tsx"
RESULTS_FEED = ROOT / "src" / "edgeiq-os" / "race" / "services" / "resultsFeed.ts"
MEETING_WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
RACE_FILE = ROOT / "src" / "edgeiq-os" / "race" / "RaceFileV3.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
TRACE = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_RESULTS_TRACE_V1.md"


RESULTS_WORKSPACE_SOURCE = r'''import { useEffect, useMemo, useState, type ReactNode } from "react";
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
            <span>Runner Result</span>
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

        <CertifiedRunContext row={certifiedRunContext} />
      </div>

      <footer className="eiq-results-workspace__actions">
        <button type="button" onClick={onBackToForm}>Back to Form</button>
        <button type="button" onClick={onCompareSelectedRun}>Compare Selected Run</button>
        <button type="button" onClick={onEvidence}>Evidence</button>
      </footer>
    </section>
  );
}
'''


GLOBAL_RESULTS_SOURCE = r'''import type { ThreeDayMeeting } from "../services/threeDayCatalog";
import { MeetingResultsWorkspace } from "./MeetingResultsWorkspace";

type GlobalResultsWorkspaceProps = {
  meeting?: ThreeDayMeeting | null;
};

export function GlobalResultsWorkspace({ meeting = null }: GlobalResultsWorkspaceProps) {
  if (!meeting) {
    return (
      <section className="eiq-global-results-workspace">
        <section className="eiq-workspace-panel">
          <span>RESULTS</span>
          <strong>Select a meeting to review results.</strong>
          <p>Meeting and race results are shown once a governed meeting context is available.</p>
        </section>
      </section>
    );
  }

  return (
    <section className="eiq-global-results-workspace">
      <MeetingResultsWorkspace meeting={meeting} />
    </section>
  );
}
'''


def replace_between(text: str, start: str, end: str, replacement: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[:start_index] + replacement + text[end_index:]


def patch_meeting_results(text: str) -> str:
    text = text.replace("type MeetingResultsWorkspaceProps = {\n  meeting: ThreeDayMeeting;\n  fixtureMode?: boolean;\n};", "type MeetingResultsWorkspaceProps = {\n  meeting: ThreeDayMeeting;\n};")
    text = text.replace('    ["Completed", model.summary.racesCompleted],\n    ["Official", model.summary.officialResults],', '    ["Completed", model.summary.racesCompleted],\n    ["Resulted", model.summary.officialResults],')
    text = text.replace('              <th>Official Time</th>\n              <th>Track</th>', '              <th>Track</th>')
    text = text.replace('                  <td>{valueOrDash(row.officialTime)}</td>\n                  <td>{valueOrDash(row.track)}</td>', '                  <td>{valueOrDash(row.track)}</td>')
    text = text.replace('          <strong>{result.raceLabel} official result</strong>', '          <strong>{result.raceLabel} result</strong>')
    text = text.replace('          <strong>Benchmark sectionals</strong>\n          <p>Benchmark values are EDGEiQ lengths versus standard. Negative is inside standard; positive is outside standard.</p>', '          <strong>Runner performance</strong>\n          <p>Sectional values are EDGEiQ lengths versus standard. Negative is inside standard; positive is outside standard.</p>')
    text = text.replace('  fixtureMode,\n  onClose,', '  onClose,')
    text = text.replace('  fixtureMode: boolean;\n  onClose: () => void;', '  onClose: () => void;')
    text = text.replace('        { fixtureMode },', '')
    text = text.replace('    [fixtureMode, meeting, raceRow],', '    [meeting, raceRow],')
    text = text.replace('        aria-label={`${result.raceLabel} Official Results`}', '        aria-label={`${result.raceLabel} Results`}')
    text = text.replace('            <span>Official Results</span>', '            <span>Results</span>')
    text = text.replace('            aria-label="Close Official Results"', '            aria-label="Close Results"')
    text = text.replace('export function MeetingResultsWorkspace({ meeting, fixtureMode = false }: MeetingResultsWorkspaceProps) {', 'export function MeetingResultsWorkspace({ meeting }: MeetingResultsWorkspaceProps) {')
    text = text.replace('    () => buildMeetingResultsViewModel(meeting, rows, { fixtureMode, sourceError }),\n    [fixtureMode, meeting, rows, sourceError],', '    () => buildMeetingResultsViewModel(meeting, rows, { sourceError }),\n    [meeting, rows, sourceError],')
    text = text.replace('          fixtureMode={fixtureMode}\n', '')
    text = text.replace('>Official Results<', '>Results<')
    text = text.replace('? "Official Results"\n                          : "Result pending"', '? "Results"\n                          : "Result pending"')
    text = text.replace('aria-label={`Open official results for race ${row.raceNumber}`}', 'aria-label={`Open results for race ${row.raceNumber}`}')
    text = text.replace('          <strong>Official Results</strong>', '          <strong>Race Results</strong>')
    return text


def patch_results_feed(text: str) -> str:
    start = "function buildFixtureMeeting(meeting: ThreeDayMeeting): ThreeDayMeeting {"
    end = "export function buildMeetingResultsViewModel("
    if start in text:
        text = replace_between(text, start, end, "")
    text = text.replace("  officialTime: string | null;\n", "")
    text = text.replace("    officialTime: valueOrNull(row?.official_time),\n", "")
    text = text.replace("    sectional800: valueOrNull(runner.source?.std_800_len, runner.source?.sectional_800),", "    sectional800: valueOrNull(runner.source?.std_800_len),")
    text = text.replace("    sectional600: valueOrNull(runner.source?.std_600_len, runner.source?.sectional_600),", "    sectional600: valueOrNull(runner.source?.std_600_len),")
    text = text.replace("    sectional400: valueOrNull(runner.source?.std_400_len, runner.source?.sectional_400, runner.source?.standardTimeDifference),", "    sectional400: valueOrNull(runner.source?.std_400_len),")
    text = text.replace("    sectional200: valueOrNull(runner.source?.std_200_len, runner.source?.sectional_200),", "    sectional200: valueOrNull(runner.source?.std_200_len),")
    text = text.replace("    sectionalFinish: valueOrNull(runner.source?.std_finish_len, runner.source?.sectional_finish),", "    sectionalFinish: valueOrNull(runner.source?.std_finish_len),")
    text = text.replace("  options: { fixtureMode?: boolean; sourceError?: string | null } = {},", "  options: { sourceError?: string | null } = {},")
    text = text.replace("  const meeting = options.fixtureMode ? buildFixtureMeeting(sourceMeeting) : sourceMeeting;\n", "  const meeting = sourceMeeting;\n")
    text = text.replace('      feed: "edgeiq_meeting_results_terminal_feed_v1.csv",', '      feed: "edgeiq_meeting_results_terminal_feed_v1.csv",')
    text = text.replace("  options: { fixtureMode?: boolean } = {},\n", "")
    text = text.replace("  const workingMeeting = options.fixtureMode ? buildFixtureMeeting(meeting) : meeting;", "  const workingMeeting = meeting;")
    text = text.replace('      { label: "Official Race Time", value: valueOrNull(row.officialTime, race.source?.official_time) },\n', "")
    text = text.replace('      { label: "Result Source", value: valueOrNull(row.source) },\n', "")
    text = text.replace('      { label: "Source Timestamp", value: valueOrNull(row.sourceTimestamp) },\n', "")
    return text


def patch_meeting_workspace(text: str) -> str:
    text = text.replace('  const resultsFixtureMode =\n    typeof window !== "undefined" && new URLSearchParams(window.location.search).get("edgeiqResultsFixture") === "1";\n\n', "")
    text = text.replace('            <MeetingResultsWorkspace meeting={meeting} fixtureMode={resultsFixtureMode} />', '            <MeetingResultsWorkspace meeting={meeting} />')
    return text


def patch_race_file(text: str) -> str:
    return text.replace("<GlobalResultsWorkspace />", "<GlobalResultsWorkspace meeting={selectedMeeting} />")


CSS_APPEND = r'''

/* EDGEIQ RESULTS FINAL SPEC V1 */
.eiq-results-v1-sectional.is-positive {
  background: #f2f4f7 !important;
  color: #475467 !important;
}

.eiq-results-v1-sectional.is-neutral {
  background: #f8fafc !important;
  color: #475467 !important;
}

.eiq-results-workspace__header,
.eiq-results-workspace__panel,
.eiq-results-workspace__summary {
  background: var(--edgeiq-surface, #ffffff) !important;
  border-color: var(--edgeiq-border, #e5e8ee) !important;
}

.eiq-results-workspace__header p,
.eiq-results-workspace__empty p,
.eiq-results-workspace__summary p,
.eiq-results-workspace__title em,
.eiq-results-workspace__header dt,
.eiq-results-workspace th,
.eiq-results-workspace td {
  color: var(--edgeiq-text-secondary, #5c6675) !important;
}
'''


TRACE_TEXT = """# EDGEiQ Results Trace V1

Workspace: RESULTS

Primary product path:
- Meeting-level Results workspace using public/data/edgeiq_meeting_results_terminal_feed_v1.csv.
- Race-level expansion uses current meeting race runner rows and governed standardised length fields only.

Frontend load guard:
- React does not load public/data/edgeiq_results_terminal_feed_v1.csv.
- The meeting results service rejects feeds over 10,000 rows.

Rules applied:
- Fixture/demo result generation removed from Results path.
- Official elapsed race-time display removed from product tables/snapshots.
- Sectional display is EDGEiQ lengths versus standard only.
- Positive sectional values render neutral; negative values retain inside-standard emphasis.
- Stewards actions remain disabled unless a governed internal report path exists.
- Global Results nav reuses the selected meeting context instead of an unconnected search shell.
"""


def main() -> None:
    RESULTS_WORKSPACE.write_text(RESULTS_WORKSPACE_SOURCE, encoding="utf-8")
    GLOBAL_RESULTS.write_text(GLOBAL_RESULTS_SOURCE, encoding="utf-8")
    MEETING_RESULTS.write_text(patch_meeting_results(MEETING_RESULTS.read_text(encoding="utf-8")), encoding="utf-8")
    RESULTS_FEED.write_text(patch_results_feed(RESULTS_FEED.read_text(encoding="utf-8")), encoding="utf-8")
    MEETING_WORKSPACE.write_text(patch_meeting_workspace(MEETING_WORKSPACE.read_text(encoding="utf-8")), encoding="utf-8")
    RACE_FILE.write_text(patch_race_file(RACE_FILE.read_text(encoding="utf-8")), encoding="utf-8")
    css_text = CSS.read_text(encoding="utf-8")
    if "/* EDGEIQ RESULTS FINAL SPEC V1 */" not in css_text:
        CSS.write_text(css_text.rstrip() + "\n" + CSS_APPEND.lstrip(), encoding="utf-8")
    TRACE.parent.mkdir(parents=True, exist_ok=True)
    TRACE.write_text(TRACE_TEXT, encoding="utf-8")
    print("EDGEIQ_RESULTS_FINAL_SPEC_APPLIED")


if __name__ == "__main__":
    main()
