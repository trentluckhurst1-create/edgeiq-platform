from pathlib import Path

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
screen = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
component = root / "src" / "components" / "workspaces" / "RaceRunnersWorkspace.tsx"

component.write_text(r'''type Row = Record<string, any>;
type EnrichedRunnerLike = {
  row: Row;
  bet?: Row;
  ratingsHeatmap?: Row;
  [key: string]: any;
};

type RaceRunnersWorkspaceProps = {
  activeRaceRows: EnrichedRunnerLike[];
  setSelectedKey: (value: string) => void;
  setIntelMode: (value: any) => void;
  runnerRowKey: (row: Row) => string;
  saddle: (row: Row) => number;
  horse: (row: Row) => string;
  barrier: (row: Row) => string;
  firstText: (row: Row | undefined, keys: string[], fallback?: string) => string;
  marketMoney: (value: number | null) => string;
  livePrice: (row: Row, bet?: Row) => number | null;
  projectionRatingValue: (item: EnrichedRunnerLike) => number | null;
  renderMetricValue: (value: number | null, digits?: number, signedMode?: boolean) => string;
  isScratched: (item: EnrichedRunnerLike) => boolean;
};

export function RaceRunnersWorkspace(props: RaceRunnersWorkspaceProps) {
  const {
    activeRaceRows,
    setSelectedKey,
    setIntelMode,
    runnerRowKey,
    saddle,
    horse,
    barrier,
    firstText,
    marketMoney,
    livePrice,
    projectionRatingValue,
    renderMetricValue,
    isScratched,
  } = props;

  const fieldRows = [...activeRaceRows].sort((a, b) => saddle(a.row) - saddle(b.row));

  const cleanMarket = (item: EnrichedRunnerLike) => {
    return marketMoney(livePrice(item.row, item.bet));
  };

  const cleanWeight = (row: Row) =>
    firstText(row, ["weight", "allocated_weight", "handicap_weight", "weight_carried", "runner_weight", "weight_kg", "wgt"], "-");

  const runnerEpiValue = (item: EnrichedRunnerLike) =>
    projectionRatingValue(item);

  const openRunnerForm = (item: EnrichedRunnerLike) => {
    setSelectedKey(runnerRowKey(item.row));
    setIntelMode("FORM");
  };

  return (
    <section className="edgeiq-field-tab edgeiq-product-section edgeiq-product-v4-panel edgeiq-field-lock-v1">
      <div className="edgeiq-field-guide-table edgeiq-product-v4-table" role="table" aria-label="EDGEiQ Race Field">
        <div className="edgeiq-field-guide-row head" role="row">
          {["NO", "SILK", "RUNNER", "BAR", "WGT", "JOCKEY", "TRAINER", "EDGEiQ", "MARKET", "STATUS"].map((label) => (
            <span key={`field-head-${label}`}>{label}</span>
          ))}
        </div>

        {fieldRows.map((item) => {
          const row = item.row;
          const rowKey = runnerRowKey(row);
          const epi = runnerEpiValue(item);
          const status = isScratched(item) ? "SCRATCHED" : "ACTIVE";

          return (
            <button
              key={`field-row-wrap-${rowKey}`}
              type="button"
              className={`edgeiq-field-guide-row ${isScratched(item) ? "is-scratched" : ""}`}
              onClick={() => openRunnerForm(item)}
              role="row"
              aria-label={`Open ${horse(row)} form profile`}
            >
              <span>{saddle(row) === 999 ? "-" : saddle(row)}</span>
              <span className="edgeiq-field-silk" aria-label={`${horse(row)} silk`}><i /></span>
              <strong>{horse(row)}</strong>
              <span>{barrier(row)}</span>
              <span>{cleanWeight(row)}</span>
              <span>{firstText(row, ["jockey", "jockey_name", "rider"], "-")}</span>
              <span>{firstText(row, ["trainer", "trainer_name"], "-")}</span>
              <span>{epi === null ? "-" : renderMetricValue(epi, 1)}</span>
              <span>{cleanMarket(item)}</span>
              <span className="edgeiq-field-status-text">{status}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
''', encoding="utf-8")

text = screen.read_text(encoding="utf-8")
start = text.index('{intelMode === "RUNNERS" ? (() => {')
end = text.index('{intelMode === "PERFORMANCE" ? (() => {', start)

replacement = '''{intelMode === "RUNNERS" ? (
<RaceRunnersWorkspace
  activeRaceRows={activeRaceRows}
  setSelectedKey={setSelectedKey}
  setIntelMode={setIntelMode}
  runnerRowKey={runnerRowKey}
  saddle={saddle}
  horse={horse}
  barrier={barrier}
  firstText={firstText}
  marketMoney={marketMoney}
  livePrice={livePrice}
  projectionRatingValue={projectionRatingValue}
  renderMetricValue={renderMetricValue}
  isScratched={isScratched}
/>
) : null}
'''

text = text[:start] + replacement + text[end:]

import_line = 'import { RaceRunnersWorkspace } from "./workspaces/RaceRunnersWorkspace";'
if import_line not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines) + "\n"

text = text.replace("ï»¿", "")
screen.write_text(text, encoding="utf-8")

print("[RUNNERS_WORKSPACE_EXTRACT] complete")
