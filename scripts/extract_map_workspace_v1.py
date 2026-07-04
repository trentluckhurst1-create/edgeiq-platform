from pathlib import Path

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
screen = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
component = root / "src" / "components" / "workspaces" / "RaceMapWorkspace.tsx"

component.write_text(r'''type Row = Record<string, any>;

type EnrichedRunnerLike = {
  row: Row;
  mapEnrichment?: Row;
  [key: string]: any;
};

type RaceMapWorkspaceProps = {
  activeRaceRows: EnrichedRunnerLike[];
  selected: EnrichedRunnerLike | undefined;
  setSelectedKey: (value: string) => void;
  setDrawerOpen: (value: boolean) => void;

  firstText: (row: Row | undefined, keys: string[], fallback?: string) => string;
  firstNum: (row: Row | undefined, keys: string[]) => number | null;
  text: (value: unknown) => string;
  num: (value: unknown) => number | null;
  clamp: (value: number, min: number, max: number) => number;

  runnerRowKey: (row: Row) => string;
  horse: (row: Row) => string;
  shortHorseName: (value: string, maxLength?: number) => string;
  saddle: (row: Row) => number;
  barrier: (row: Row) => string;
  projectedSpdValue: (item: EnrichedRunnerLike) => number | null;
  renderMetricValue: (value: number | null, digits?: number, signedMode?: boolean) => string;
};

export function RaceMapWorkspace(props: RaceMapWorkspaceProps) {
  const {
    activeRaceRows,
    selected,
    setSelectedKey,
    setDrawerOpen,
    firstText,
    firstNum,
    clamp,
    runnerRowKey,
    horse,
    shortHorseName,
    saddle,
    barrier,
    projectedSpdValue,
    renderMetricValue,
  } = props;

  const mapSourceRow = (item: EnrichedRunnerLike): Row => ({ ...(item.row || {}), ...(item.mapEnrichment || {}) });

  const mapClean = (value: unknown, fallback = "-") => {
    const raw = String(value ?? "").trim();
    if (!raw || /^(UNKNOWN|NOT LOADED|SOURCE_MISSING|SOURCE GAP|NULL|NN|UNDEFINED|0\.0)$/i.test(raw)) return fallback;
    return raw;
  };

  const mapRowsV2 = [...activeRaceRows].map((item) => {
    const src = mapSourceRow(item);
    const x = firstNum(src, ["map_x_pct_display_v3", "map_x_pct_display", "map_x_pct"]);
    const y = firstNum(src, ["map_y_px_display_v3", "map_y_px_display", "map_y_px"]);

    return {
      item,
      key: runnerRowKey(item.row),
      horseName: horse(item.row),
      shortName: shortHorseName(horse(item.row), 13),
      saddle: mapClean(firstText(item.row, ["saddlecloth", "horse_no", "runner_no", "runner_number", "number"], saddle(item.row) === 999 ? "" : String(saddle(item.row)))),
      barrier: mapClean(firstText(item.row, ["barrier", "draw"], barrier(item.row))),
      runStyle: mapClean(firstText(src, ["run_style_display_v3", "run_style_display", "run_style", "speed_map_bucket"], "")),
      earlySpeed: mapClean(firstText(src, ["early_speed_rating_display", "projected_speed_display", "early_speed", "projected_speed"], "")),
      paceFit: mapClean(firstText(src, ["pace_fit_display", "pace_fit_band", "pace_fit"], "")),
      settling: mapClean(firstText(src, ["settling_band_display_v3", "settling_band_display", "settling_band", "settling_position"], "")),
      wideRisk: mapClean(firstText(src, ["wide_risk_display", "wide_risk"], "")),
      coverRisk: mapClean(firstText(src, ["cover_risk_display", "cover_risk"], "")),
      pressureRole: mapClean(firstText(src, ["pressure_role_display", "pressure_role"], "")),
      lateSpeed: mapClean(firstText(src, ["late_speed_display", "late_speed"], "")),
      confidence: mapClean(firstText(src, ["map_confidence_display_v3", "map_confidence_display", "map_confidence"], "")),
      speedRank: mapClean(firstText(src, ["speed_rank_v3"], "")),
      speedGap: mapClean(firstText(src, ["speed_gap_to_leader_v3"], "")),
      relativeBand: mapClean(firstText(src, ["relative_speed_band_v3"], "")),
      evidence: mapClean(firstText(src, ["map_evidence_display", "map_evidence"], "")),
      lane: mapClean(firstText(src, ["map_lane_display", "map_lane"], "")),
      zone: mapClean(firstText(src, ["map_zone_display", "map_zone"], "")),
      jockeyName: firstText(item.row, ["jockey", "jockey_name", "rider"], "-"),
      trainerName: firstText(item.row, ["trainer", "trainer_name"], "-"),
      weight: firstText(item.row, ["weight", "allocated_weight", "handicap_weight", "weight_carried", "runner_weight", "weight_kg", "wgt"], "-"),
      epiSpd: renderMetricValue(projectedSpdValue(item), 1),
      x: x !== null ? clamp(x, 4, 96) : 74,
      y: y !== null ? clamp(y, 8, 94) : 50,
      selected: !!selected && runnerRowKey(item.row) === runnerRowKey(selected.row),
    };
  }).sort((a, b) => a.x - b.x || Number(a.barrier || 99) - Number(b.barrier || 99));

  const mapTableRowsV2 = [...mapRowsV2].sort((a, b) => Number(a.saddle || 999) - Number(b.saddle || 999));

  const mapLaneRowsV1 = [...mapRowsV2].sort((a, b) => {
    const barrierValue = Number(a.barrier);
    const barrierB = Number(b.barrier);
    const valid = Number.isFinite(barrierValue) && barrierValue > 0;
    const validB = Number.isFinite(barrierB) && barrierB > 0;
    if (valid && validB) return barrierB - barrierValue;
    if (valid) return -1;
    if (validB) return 1;
    return a.x - b.x;
  });

  const mapBarrierMax = Math.max(
    ...mapLaneRowsV1.map((row) => Number(row.barrier)).filter((value) => Number.isFinite(value) && value > 0),
    activeRaceRows.length,
    1,
  );

  const mapBarrierLaneRows = Array.from({ length: mapBarrierMax }, (_, index) => {
    const barrierNo = mapBarrierMax - index;
    return {
      barrierNo,
      runners: mapRowsV2
        .filter((row) => Number(row.barrier) === barrierNo)
        .sort((a, b) => a.x - b.x || Number(a.saddle || 99) - Number(b.saddle || 99)),
    };
  });

  return (
    <section className="edgeiq-map-tab edgeiq-product-section edgeiq-product-v4-panel edgeiq-map-final-lock">
      <section className="edgeiq-map-final-visual" aria-label="Speed map and barrier stack">
        <div className="edgeiq-map-final-track">
          {mapBarrierLaneRows.map((lane) => (
            <div
              key={`map-final-lane-${lane.barrierNo}`}
              className={`edgeiq-map-final-lane ${lane.runners.some((row) => row.selected) ? "is-selected" : ""}`}
            >
              {lane.runners.map((row, runnerIndex) => {
                const xPct = clamp(row.x, 7, 76);
                const stackOffset = runnerIndex * 16;

                return (
                  <button
                    key={`map-final-runner-${row.key}`}
                    type="button"
                    className="edgeiq-map-final-runner"
                    onClick={() => { setSelectedKey(row.key); setDrawerOpen(true); }}
                    title={`${row.horseName} | B${lane.barrierNo}`}
                    style={{ ["--map-runner-x" as string]: `${xPct}%`, ["--map-runner-offset" as string]: `${stackOffset}px` }}
                  >
                    <span className="edgeiq-map-final-speed-line" />
                    <span className="edgeiq-map-final-pill">
                      <b>{row.saddle}</b>
                      <strong>{row.shortName}</strong>
                    </span>
                  </button>
                );
              })}
            </div>
          ))}
        </div>

        <div className="edgeiq-map-final-axis" aria-hidden="true">
          {Array.from({ length: mapBarrierMax }, (_, index) => mapBarrierMax - index).map((barrierNo) => (
            <span key={`map-final-axis-${barrierNo}`}>B{barrierNo}</span>
          ))}
        </div>

        <div className="edgeiq-map-final-direction">DIRECTION OF RACE</div>
      </section>

      <section className="edgeiq-map-final-table edgeiq-product-v4-table">
        <div className="edgeiq-map-runner-table-head">
          {["NO", "SILK", "RUNNER", "BARRIER", "JOCKEY", "TRAINER", "WEIGHT", "EPI SPD"].map((label) => (
            <span key={`map-v3-table-head-${label}`}>{label}</span>
          ))}
        </div>

        {mapTableRowsV2.map((row) => (
          <button
            className="edgeiq-map-runner-table-row"
            key={`map-v3-table-${row.key}`}
            type="button"
            onClick={() => { setSelectedKey(row.key); setDrawerOpen(true); }}
          >
            <strong>{row.saddle}</strong>
            <span className="edgeiq-field-silk" aria-label={`${row.horseName} silk`}><i /></span>
            <strong>{row.horseName}</strong>
            <span>{row.barrier}</span>
            <span>{row.jockeyName}</span>
            <span>{row.trainerName}</span>
            <span>{row.weight}</span>
            <span>{row.epiSpd}</span>
          </button>
        ))}
      </section>
    </section>
  );
}
''', encoding="utf-8")

text = screen.read_text(encoding="utf-8")

start = text.index('{intelMode === "MP" ? (() => {')
end = text.index('{intelMode === "FORM" ? (() => {', start)

replacement = '''{intelMode === "MP" ? (
<RaceMapWorkspace
  activeRaceRows={activeRaceRows}
  selected={selected}
  setSelectedKey={setSelectedKey}
  setDrawerOpen={setDrawerOpen}
  firstText={firstText}
  firstNum={firstNum}
  text={text}
  num={num}
  clamp={clamp}
  runnerRowKey={runnerRowKey}
  horse={horse}
  shortHorseName={shortHorseName}
  saddle={saddle}
  barrier={barrier}
  projectedSpdValue={projectedSpdValue}
  renderMetricValue={renderMetricValue}
/>
) : null}
'''

text = text[:start] + replacement + text[end:]

import_line = 'import { RaceMapWorkspace } from "./workspaces/RaceMapWorkspace";'
if import_line not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines) + "\n"

text = text.replace("ï»¿", "")
screen.write_text(text, encoding="utf-8")

print("[MAP_WORKSPACE_EXTRACT] complete")
