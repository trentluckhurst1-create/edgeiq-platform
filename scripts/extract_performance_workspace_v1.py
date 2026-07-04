from pathlib import Path

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
screen = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
component = root / "src" / "components" / "workspaces" / "RacePerformanceWorkspace.tsx"

component.write_text(r'''type Row = Record<string, any>;

type EnrichedRunnerLike = {
  row: Row;
  runnerHistory?: Row[];
  runnerForm?: Row;
  ratingsHeatmap?: Row;
  [key: string]: any;
};

type RatingHoverCardLike = {
  title: string;
  metrics: { label: string; value: string; tone?: string }[];
  footer: string;
};

type RacePerformanceWorkspaceProps = {
  activeRaceRows: EnrichedRunnerLike[];
  header: Row;
  setSelectedKey: (value: string) => void;
  setSelectedHistoricalRun: (value: Row | null) => void;
  setIntelMode: (value: any) => void;
  clearRatingHover: () => void;
  placeRatingHoverCard: (event: any, card: RatingHoverCardLike) => void;

  firstText: (row: Row | undefined, keys: string[], fallback?: string) => string;
  firstNum: (row: Row | undefined, keys: string[]) => number | null;
  runnerRowKey: (row: Row) => string;
  saddle: (row: Row) => number;
  horse: (row: Row) => string;
  projectionRatingValue: (item: EnrichedRunnerLike) => number | null;
  renderMetricValue: (value: number | null, digits?: number, signedMode?: boolean) => string;
  ratedHistoryRows: (rows: Row[]) => Row[];
  historyRatingValue: (row: Row | undefined) => number | null;
  historyFinishText: (row: Row | undefined) => string;
  formatHistoryDate: (value: string) => string;
  historyDateText: (row: Row | undefined) => string;
  historyTrackText: (row: Row | undefined) => string;
  historyRaceNoText: (row: Row | undefined) => string;
  historyDistanceText: (row: Row | undefined) => string;
  historyClassText: (row: Row | undefined) => string;
  historyGoingText: (row: Row | undefined) => string;
  historyBarrierText: (row: Row | undefined) => string;
  historyJockeyText: (row: Row | undefined) => string;
  historySpText: (row: Row | undefined) => string;
};

export function RacePerformanceWorkspace(props: RacePerformanceWorkspaceProps) {
  const {
    activeRaceRows,
    header,
    setSelectedKey,
    setSelectedHistoricalRun,
    setIntelMode,
    clearRatingHover,
    placeRatingHoverCard,
    firstText,
    firstNum,
    runnerRowKey,
    saddle,
    horse,
    projectionRatingValue,
    renderMetricValue,
    ratedHistoryRows,
    historyRatingValue,
    historyFinishText,
    formatHistoryDate,
    historyDateText,
    historyTrackText,
    historyRaceNoText,
    historyDistanceText,
    historyClassText,
    historyGoingText,
    historyBarrierText,
    historyJockeyText,
    historySpText,
  } = props;

  const empty = "-";
  const heatRows = activeRaceRows.map((item) => ({ item, heat: item.ratingsHeatmap || {} }));
  const heatRowsWithRatings = heatRows.filter((entry) => (firstNum(entry.heat, ["runner_rating", "epi", "performance_index"]) ?? projectionRatingValue(entry.item)) !== null);
  const expectedRaceRating = heatRows.map((entry) => firstNum(entry.heat, ["expected_rating"])).find((value) => value !== null) ?? null;
  const currentFigureFor = (item: EnrichedRunnerLike, heat: Row) => firstNum(heat, ["runner_rating", "epi", "performance_index"]) ?? projectionRatingValue(item);
  const runnerPerformance = heatRows.map((entry) => currentFigureFor(entry.item, entry.heat)).filter((value): value is number => value !== null).sort((a, b) => a - b);
  const averageFigure = runnerPerformance.length ? runnerPerformance.reduce((sum, value) => sum + value, 0) / runnerPerformance.length : null;
  const performanceSpread = runnerPerformance.length ? Math.max(...runnerPerformance) - Math.min(...runnerPerformance) : null;

  const topFigureEntry = heatRows.reduce<{ item: EnrichedRunnerLike; value: number } | null>((best, entry) => {
    const value = currentFigureFor(entry.item, entry.heat);
    if (value === null) return best;
    if (!best || value > best.value) return { item: entry.item, value };
    return best;
  }, null);

  const epiHeatClass = (value: number | null) => {
    if (value === null) return "edgeiq-epi-cell is-missing";
    if (value >= 105) return "edgeiq-epi-cell is-elite";
    if (value >= 100) return "edgeiq-epi-cell is-strong";
    if (value >= 95) return "edgeiq-epi-cell is-positive";
    if (value >= 90) return "edgeiq-epi-cell is-warning";
    return "edgeiq-epi-cell is-risk";
  };

  const staticFigureText = (value: number | null) => value === null ? empty : renderMetricValue(value, 1);
  const historyResultAvailable = (run: Row | undefined) => !!run && historyFinishText(run) !== "-";

  const buildPerformanceRunCard = (runnerName: string, label: string, run: Row | undefined, figure: number | null): RatingHoverCardLike | null => {
    if (!run) return null;
    return {
      title: `${runnerName} - ${label} Figure: ${staticFigureText(figure)}`,
      metrics: [
        { label: "Date", value: formatHistoryDate(historyDateText(run)) },
        { label: "Track", value: historyTrackText(run) },
        { label: "Race", value: historyRaceNoText(run) },
        { label: "Distance", value: historyDistanceText(run) },
        { label: "Class", value: historyClassText(run) },
        { label: "Going", value: historyGoingText(run) },
        { label: "Barrier", value: historyBarrierText(run) },
        { label: "Jockey", value: historyJockeyText(run) },
        { label: "Trainer", value: firstText(run, ["trainer", "trainer_name"], firstText(header, ["trainer", "trainer_name"], "-")) },
        { label: "Position", value: historyFinishText(run) },
        { label: "Margin", value: firstText(run, ["margin", "beaten_margin"], "-") },
        { label: "SP", value: historySpText(run) },
        { label: "EPI Figure", value: staticFigureText(figure), tone: figure !== null && figure >= 100 ? "#43efc6" : "#f4f8f8" },
      ],
      footer: historyResultAvailable(run) ? "Click to open this historical result in RESULTS." : "Result detail unavailable for this historical race.",
    };
  };

  const openHistoricalResult = (item: EnrichedRunnerLike, run: Row | undefined) => {
    if (!historyResultAvailable(run)) return;
    clearRatingHover();
    setSelectedKey(runnerRowKey(item.row));
    setSelectedHistoricalRun(run || null);
    setIntelMode("RESULTS");
  };

  if (!heatRowsWithRatings.length) {
    return (
      <section className="edgeiq-ratings-tab edgeiq-performance-tab edgeiq-product-section edgeiq-product-v4-panel edgeiq-performance-rebuild-v2">
        <div className="edgeiq-performance-panel-head"><strong>PERFORMANCE INDEX TABLE</strong></div>
        <div className="edgeiq-product-empty">Performance Index pending for this race.</div>
      </section>
    );
  }

  const performanceCards = [
    { label: "Race Standard", value: staticFigureText(expectedRaceRating), detail: "Expected Figure", visual: "spark" },
    { label: "Top Figure", value: staticFigureText(topFigureEntry?.value ?? null), detail: topFigureEntry ? horse(topFigureEntry.item.row) : "Peak EPI in Field", visual: "trophy" },
    { label: "Average Figure", value: staticFigureText(averageFigure), detail: "Average EPI in Field", visual: "bars" },
    { label: "Field Spread", value: staticFigureText(performanceSpread), detail: "EPI Points", visual: "range" },
  ];

  return (
    <section className="edgeiq-ratings-tab edgeiq-performance-tab edgeiq-product-section edgeiq-performance-rebuild-v2">
      <div className="edgeiq-performance-summary-grid">
        {performanceCards.map((card) => (
          <article key={`performance-card-${card.label}`} className={`edgeiq-performance-summary-card visual-${card.visual}`}>
            <span>{card.label}</span>
            <strong>{card.value}</strong>
            <em>{card.detail}</em>
            <i aria-hidden="true" />
          </article>
        ))}
      </div>

      <div className="edgeiq-performance-index-panel edgeiq-product-v4-panel">
        <div className="edgeiq-performance-panel-head"><strong>PERFORMANCE INDEX TABLE</strong></div>
        <div className="edgeiq-performance-index-table edgeiq-product-v4-table" role="table" aria-label="EDGEiQ Performance Index">
          <div className="edgeiq-performance-index-row head" role="row">
            {["NO", "SILK", "HORSE", "EPI", "CURRENT", "PEAK", "AVG", "LAST", "L5", "L4", "L3", "L2", "L1"].map((label) => (
              <span key={`performance-v2-head-${label}`}>{label}</span>
            ))}
          </div>

          {heatRows.map(({ item, heat }) => {
            const current = currentFigureFor(item, heat);
            const rated = ratedHistoryRows(item.runnerHistory || []);
            const recent = rated.slice(0, 5);
            const l5ToL1Runs = Array.from({ length: 5 }, (_, index) => recent[4 - index]);
            const peak = rated.length ? Math.max(...rated.map((run) => historyRatingValue(run) ?? Number.NEGATIVE_INFINITY).filter((value) => Number.isFinite(value))) : null;
            const avg = recent.length ? recent.reduce((sum, run) => sum + (historyRatingValue(run) ?? 0), 0) / recent.length : null;
            const last = recent.length ? historyRatingValue(recent[0]) : firstNum(item.runnerForm, ["form_last_start_rating", "last_start_rating", "rating_1"]);

            return (
              <div className="edgeiq-performance-index-row" role="row" key={`performance-tab-${runnerRowKey(item.row)}`}>
                <span>{saddle(item.row) === 999 ? empty : saddle(item.row)}</span>
                <span className="edgeiq-field-silk" aria-label={`${horse(item.row)} silk`}><i /></span>
                <strong>{horse(item.row)}</strong>
                <span className="edgeiq-performance-epi">{staticFigureText(current)}</span>
                <span>{staticFigureText(current)}</span>
                <span>{staticFigureText(peak)}</span>
                <span>{staticFigureText(avg)}</span>
                <span>{staticFigureText(last)}</span>
                {l5ToL1Runs.map((run, index) => {
                  const label = `L${5 - index}`;
                  const rating = historyRatingValue(run);
                  const card = buildPerformanceRunCard(horse(item.row), label, run, rating);
                  const canOpen = historyResultAvailable(run);
                  return (
                    <button
                      key={`epi-${label.toLowerCase()}-${runnerRowKey(item.row)}`}
                      type="button"
                      className={epiHeatClass(rating)}
                      disabled={!canOpen}
                      onMouseEnter={(event) => { if (card) placeRatingHoverCard(event, card); }}
                      onMouseMove={(event) => { if (card) placeRatingHoverCard(event, card); }}
                      onMouseLeave={clearRatingHover}
                      onClick={() => openHistoricalResult(item, run)}
                    >
                      {staticFigureText(rating)}
                    </button>
                  );
                })}
              </div>
            );
          })}
        </div>

        <div className="edgeiq-performance-table-footer">
          <div className="edgeiq-performance-scale">
            <span>EPI SCALE</span>
            <i className="is-risk">&lt; 90</i>
            <i className="is-warning">90 - 94</i>
            <i className="is-positive">95 - 99</i>
            <i className="is-strong">100 - 104</i>
            <i className="is-elite">105+</i>
          </div>
          <span>Click or hover a rating for race details</span>
          <button type="button" onClick={() => setIntelMode("PERFORMANCE")}>View full performance report →</button>
        </div>
      </div>
    </section>
  );
}
''', encoding="utf-8")

text = screen.read_text(encoding="utf-8")
start = text.index('{intelMode === "PERFORMANCE" ? (() => {')
end = text.index('{intelMode === "NEXUS" ? (() => {', start)

replacement = '''{intelMode === "PERFORMANCE" ? (
<RacePerformanceWorkspace
  activeRaceRows={activeRaceRows}
  header={header}
  setSelectedKey={setSelectedKey}
  setSelectedHistoricalRun={setSelectedHistoricalRun}
  setIntelMode={setIntelMode}
  clearRatingHover={clearRatingHover}
  placeRatingHoverCard={placeRatingHoverCard}
  firstText={firstText}
  firstNum={firstNum}
  runnerRowKey={runnerRowKey}
  saddle={saddle}
  horse={horse}
  projectionRatingValue={projectionRatingValue}
  renderMetricValue={renderMetricValue}
  ratedHistoryRows={ratedHistoryRows}
  historyRatingValue={historyRatingValue}
  historyFinishText={historyFinishText}
  formatHistoryDate={formatHistoryDate}
  historyDateText={historyDateText}
  historyTrackText={historyTrackText}
  historyRaceNoText={historyRaceNoText}
  historyDistanceText={historyDistanceText}
  historyClassText={historyClassText}
  historyGoingText={historyGoingText}
  historyBarrierText={historyBarrierText}
  historyJockeyText={historyJockeyText}
  historySpText={historySpText}
/>
) : null}
'''

text = text[:start] + replacement + text[end:]

import_line = 'import { RacePerformanceWorkspace } from "./workspaces/RacePerformanceWorkspace";'
if import_line not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines) + "\n"

text = text.replace("ï»¿", "")
screen.write_text(text, encoding="utf-8")

print("[PERFORMANCE_WORKSPACE_EXTRACT] complete")
