from pathlib import Path

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
screen = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
component = root / "src" / "components" / "workspaces" / "RaceResultsWorkspace.tsx"

component.write_text(r'''type Row = Record<string, any>;

type EnrichedRunnerLike = {
  row: Row;
  ratingsHeatmap?: Row;
  [key: string]: any;
};

type RaceResultsWorkspaceProps = {
  activeRaceRows: EnrichedRunnerLike[];
  header: Row;
  railDisplay: string;
  displayExpectedTempo: string;

  saddle: (row: Row) => number;
  horse: (row: Row) => string;
  runnerRowKey: (row: Row) => string;
  firstText: (row: Row | undefined, keys: string[], fallback?: string) => string;
  firstNum: (row: Row | undefined, keys: string[]) => number | null;
  num: (value: unknown) => number | null;
  projectionRatingValue: (item: EnrichedRunnerLike) => number | null;
  renderMetricValue: (value: number | null, digits?: number, signedMode?: boolean) => string;
  trackCondition: (row: Row) => string;
  raceClass: (row: Row) => string;
};

export function RaceResultsWorkspace(props: RaceResultsWorkspaceProps) {
  const {
    activeRaceRows,
    header,
    railDisplay,
    displayExpectedTempo,
    saddle,
    horse,
    runnerRowKey,
    firstText,
    firstNum,
    num,
    projectionRatingValue,
    renderMetricValue,
    trackCondition,
    raceClass,
  } = props;

  const empty = "-";

  const resultRows = [...activeRaceRows].sort((a, b) => saddle(a.row) - saddle(b.row));

  const resultValue = (row: Row, keys: string[], fallback = "Pending") => {
    const raw = firstText(row, keys, "");
    return raw && raw !== "-" ? raw : fallback;
  };

  const resultPosition = (item: EnrichedRunnerLike, index: number) =>
    resultValue(item.row, ["finish_position", "finishing_position", "result_position", "pos"], String(index + 1));

  const resultMargin = (row: Row) =>
    resultValue(row, ["margin", "beaten_margin", "official_margin"], "Pending");

  const resultEpi = (item: EnrichedRunnerLike) =>
    firstNum(item.ratingsHeatmap, ["runner_rating", "epi", "performance_index"]) ?? projectionRatingValue(item);

  const sectional = (row: Row, keys: string[]) => resultValue(row, keys, empty);
  const sectionalNumber = (value: string) => num(String(value).replace(/[Ll]/g, ""));

  const sectionalClass = (value: string) => {
    const parsed = sectionalNumber(value);
    return parsed !== null && parsed < 0 ? "inside-standard" : "outside-standard";
  };

  const sectionalsFor = (row: Row) => ({
    s800: sectional(row, ["last_800_vs_standard", "last_800_lengths", "last800", "sectional_800"]),
    s600: sectional(row, ["last_600_vs_standard", "last_600_lengths", "last600", "sectional_600"]),
    s400: sectional(row, ["last_400_vs_standard", "last_400_lengths", "last400", "sectional_400"]),
    s200: sectional(row, ["last_200_vs_standard", "last_200_lengths", "last200", "sectional_200"]),
    finish: sectional(row, ["finish_vs_standard", "finish_lengths", "last_finish", "sectional_finish"]),
  });

  const rankingMetrics = [
    { label: "Best Last 800m", key: "s800" as const },
    { label: "Best Last 600m", key: "s600" as const },
    { label: "Best Last 400m", key: "s400" as const },
    { label: "Best Last 200m", key: "s200" as const },
    { label: "Strongest Finish", key: "finish" as const },
  ].map((metric) => {
    const ranked = resultRows
      .map((item) => ({ item, value: sectionalsFor(item.row)[metric.key] }))
      .map((entry) => ({ ...entry, numeric: sectionalNumber(entry.value) }))
      .filter((entry): entry is typeof entry & { numeric: number } => entry.numeric !== null)
      .sort((a, b) => a.numeric - b.numeric);
    return { ...metric, winner: ranked[0] || null, runnerUp: ranked[1] || null };
  });

  const officialTime = firstText(header, ["official_time", "winning_time", "race_time_official"], "Pending");
  const last600 = firstText(header, ["race_last_600", "last_600", "overall_last_600"], "Pending");
  const raceTempo = firstText(header, ["race_tempo", "tempo", "race_shape"], displayExpectedTempo !== "-" ? displayExpectedTempo : "Pending");

  return (
    <section className="edgeiq-results-tab edgeiq-product-section edgeiq-product-v4-panel edgeiq-results-v1-lock">
      <div className="edgeiq-tab-heading edgeiq-product-v4-section-title">
        <span>RESULTS</span>
        <strong>Race Review & Intelligence</strong>
        <em>Official result and standardised sectional performance.</em>
      </div>

      <div className="edgeiq-results-v1-grid edgeiq-results-v1-top-grid">
        <section className="edgeiq-results-v1-panel">
          <div className="edgeiq-results-v1-title">Official Results</div>
          <div className="edgeiq-results-v1-table edgeiq-product-v4-table" role="table" aria-label="Official results">
            <div className="edgeiq-results-v1-row head" role="row">
              {["POS", "NO", "SILK", "RUNNER", "MARGIN (BEATEN BY)", "EPI"].map((label) => <span key={`results-official-head-${label}`}>{label}</span>)}
            </div>
            {resultRows.map((item, index) => (
              <div className="edgeiq-results-v1-row" role="row" key={`results-official-${runnerRowKey(item.row)}`}>
                <span>{resultPosition(item, index)}</span>
                <span>{saddle(item.row) === 999 ? empty : saddle(item.row)}</span>
                <span className="edgeiq-field-silk" aria-label={`${horse(item.row)} silk`}><i /></span>
                <strong>{horse(item.row)}</strong>
                <span>{resultMargin(item.row)}</span>
                <span>{resultEpi(item) === null ? empty : renderMetricValue(resultEpi(item), 1)}</span>
              </div>
            ))}
          </div>
          <div className="edgeiq-results-v1-meta">
            Official Time: <span>{officialTime}</span> <i /> Last 600m: <span>{last600}</span> <i /> Track Condition: <span>{trackCondition(header)}</span> <i /> Rail: <span>{railDisplay}</span>
          </div>
        </section>

        <section className="edgeiq-results-v1-panel">
          <div className="edgeiq-results-v1-title">Sectionals <em>(Lengths Faster Than Standard)</em></div>
          <div className="edgeiq-sectionals-v1-table edgeiq-product-v4-table" role="table" aria-label="Sectionals">
            <div className="edgeiq-sectionals-v1-row head" role="row">
              {["POS", "RUNNER", "800M", "600M", "400M", "200M", "FINISH"].map((label) => <span key={`sectionals-head-${label}`}>{label}</span>)}
            </div>
            {resultRows.map((item, index) => {
              const values = sectionalsFor(item.row);
              return (
                <div className="edgeiq-sectionals-v1-row" role="row" key={`sectionals-${runnerRowKey(item.row)}`}>
                  <span>{resultPosition(item, index)}</span>
                  <strong>{horse(item.row)}</strong>
                  {[values.s800, values.s600, values.s400, values.s200, values.finish].map((value, valueIndex) => (
                    <span key={`sectionals-${runnerRowKey(item.row)}-${valueIndex}`} className={sectionalClass(value)}>{value}</span>
                  ))}
                </div>
              );
            })}
          </div>
          <div className="edgeiq-results-v1-scale"><span>Faster than standard</span><i>{"<= -4.0L"}</i><i>-4.0L to -2.0L</i><i>-2.0L to -0.1L</i><b>0.0L Standard</b><em>Slower than standard</em><strong>+0.1L or more</strong></div>
          <p className="edgeiq-results-v1-data-label">Data is EDGEiQ Standardised Sectionals</p>
        </section>
      </div>

      <div className="edgeiq-results-v1-bottom-grid">
        <section className="edgeiq-results-v1-panel">
          <div className="edgeiq-results-v1-title">Sectional Rankings</div>
          <div className="edgeiq-results-ranking-table edgeiq-product-v4-table" role="table" aria-label="Sectional rankings">
            <div className="edgeiq-results-ranking-row head" role="row">
              {["METRIC", "WINNER", "FIGURE", "RUNNER UP", "FIGURE"].map((label) => <span key={`ranking-head-${label}`}>{label}</span>)}
            </div>
            {rankingMetrics.map((metric) => (
              <div className="edgeiq-results-ranking-row" role="row" key={`sectional-ranking-${metric.label}`}>
                <span>{metric.label}</span>
                <strong>{metric.winner ? horse(metric.winner.item.row) : empty}</strong>
                <span>{metric.winner?.value || empty}</span>
                <strong>{metric.runnerUp ? horse(metric.runnerUp.item.row) : empty}</strong>
                <span>{metric.runnerUp?.value || empty}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="edgeiq-results-v1-panel edgeiq-results-review-panel">
          <div className="edgeiq-results-v1-title">Race Review</div>
          <p>Race review is based on official finishing order, EDGEiQ performance ratings and standardised sectional context.</p>
          <p>{raceTempo !== "Pending" ? `Tempo profile: ${raceTempo}.` : "Tempo profile pending."} Faster-than-standard sectional cells are highlighted in green; slower values remain neutral.</p>
        </section>

        <section className="edgeiq-results-v1-panel edgeiq-results-info-panel">
          {[["Winning Time", officialTime], ["Last 600m", last600], ["Race Tempo", raceTempo], ["Track Condition", trackCondition(header)], ["Rail Position", railDisplay], ["Race Grade", raceClass(header)], ["Number of Runners", String(activeRaceRows.length)]].map(([label, value]) => (
            <article key={`results-info-${label}`}>
              <span>{label}</span>
              <strong>{value}</strong>
            </article>
          ))}
        </section>
      </div>
    </section>
  );
}
''', encoding="utf-8")

text = screen.read_text(encoding="utf-8")
start = text.index('{intelMode === "RESULTS" ? (() => {')
end = text.index('{intelMode === "TRACK" ? (', start)

replacement = '''{intelMode === "RESULTS" ? (
<RaceResultsWorkspace
  activeRaceRows={activeRaceRows}
  header={header}
  railDisplay={railDisplay}
  displayExpectedTempo={displayExpectedTempo}
  saddle={saddle}
  horse={horse}
  runnerRowKey={runnerRowKey}
  firstText={firstText}
  firstNum={firstNum}
  num={num}
  projectionRatingValue={projectionRatingValue}
  renderMetricValue={renderMetricValue}
  trackCondition={trackCondition}
  raceClass={raceClass}
/>
) : null}
'''

text = text[:start] + replacement + text[end:]

import_line = 'import { RaceResultsWorkspace } from "./workspaces/RaceResultsWorkspace";'
if import_line not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines) + "\n"

text = text.replace("ï»¿", "")
screen.write_text(text, encoding="utf-8")

print("[RESULTS_WORKSPACE_EXTRACT] complete")
