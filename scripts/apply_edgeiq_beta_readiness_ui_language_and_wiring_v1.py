from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def write(rel: str, text: str) -> None:
    (ROOT / rel).write_text(text, encoding="utf-8", newline="")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Missing replacement target: {label}")
    return text.replace(old, new, 1)


def patch_map_workspace() -> None:
    path = "src/edgeiq-os/race/components/MapWorkspace.tsx"
    text = read(path)

    text = replace_once(
        text,
        """function sourceLabel(row: BETA009Row): string {
  const parts = [row.sourceConfidence, row.rowStatus].filter(Boolean);
  return parts.length ? parts.join(" | ") : "Source pending";
}
""",
        """function runnerText(row: BETA009Row, officialKey: string, sourceKeys: string[] = []): string {
  const runner = row.runner as RaceFieldRunner | null | undefined;
  if (!runner) return "";
  const official = (runner.official ?? {}) as Record<string, unknown>;
  const source = (runner.source ?? {}) as Record<string, unknown>;
  const candidates = [official[officialKey], ...sourceKeys.map((key) => source[key])];
  return firstText(...candidates);
}

function runnerJockey(row: BETA009Row): string {
  return runnerText(row, "jockey", ["jockeyName", "jockey"]);
}

function runnerTrainer(row: BETA009Row): string {
  return runnerText(row, "trainer", ["trainerName", "trainer"]);
}

function runnerWeight(row: BETA009Row): string {
  return runnerText(row, "weight", ["weight", "weightAllocated"]);
}

function runnerMarket(row: BETA009Row): string {
  return runnerText(row, "market", ["market", "fixedOdds", "price"]);
}

function mapConfidenceLabel(row: BETA009Row): string {
  if (row.run_style || row.early_speed || row.projected_position) return "Mapped";
  return "Pending";
}
""",
        "map helpers",
    )

    text = text.replace(
        """                title={sourceLabel(row)}
""",
        """                title={mapConfidenceLabel(row)}
""",
    )

    text = replace_once(
        text,
        """function MapTable({ rows }: { rows: BETA009Row[] }) {
  return (
    <section className="eiq-map-v1-panel">
      <div className="eiq-map-v1-panel__title">
        <span>Map Table</span>
        <small>NO | HORSE | BARRIER | EFFECTIVE BARRIER | RUN STYLE | EARLY SPEED | PROJECTED POSITION</small>
      </div>
      <div className="eiq-map-v1-table-scroll">
        <table className="eiq-map-v1-table">
          <thead>
            <tr>
              <th>No</th>
              <th>Horse</th>
              <th>Barrier</th>
              <th>Effective Barrier</th>
              <th>Run Style</th>
              <th>Early Speed</th>
              <th>Projected Position</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`table-${rowNumber(row)}-${rowRunnerName(row)}`}>
                <td>{rowNumber(row)}</td>
                <td><strong>{rowRunnerName(row)}</strong></td>
                <td>{rowValue(row.barrier)}</td>
                <td>{rowValue(row.effective_barrier)}</td>
                <td>{rowValue(row.run_style)}</td>
                <td>{rowValue(row.early_speed)}</td>
                <td>{rowValue(row.projected_position)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
""",
        """function MapTable({ rows }: { rows: BETA009Row[] }) {
  return (
    <section className="eiq-map-v1-panel">
      <div className="eiq-map-v1-panel__title">
        <span>Runner Map Table</span>
        <small>Current race field and expected settling read</small>
      </div>
      <div className="eiq-map-v1-table-scroll">
        <table className="eiq-map-v1-table">
          <thead>
            <tr>
              <th>No</th>
              <th>Runner</th>
              <th>Barrier</th>
              <th>Jockey</th>
              <th>Trainer</th>
              <th>Weight</th>
              <th>Market</th>
              <th>Map</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`table-${rowNumber(row)}-${rowRunnerName(row)}`}>
                <td>{rowNumber(row)}</td>
                <td><strong>{rowRunnerName(row)}</strong></td>
                <td>{rowValue(row.effective_barrier) || rowValue(row.barrier)}</td>
                <td>{runnerJockey(row)}</td>
                <td>{runnerTrainer(row)}</td>
                <td>{runnerWeight(row)}</td>
                <td>{runnerMarket(row)}</td>
                <td>{rowValue(row.projected_position) || rowValue(row.run_style)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
""",
        "map table",
    )

    text = replace_once(
        text,
        """function SourcePanel({ viewModel }: { viewModel: BETA009ViewModel }) {
  return (
    <aside className="eiq-map-v1-side">
      <section className="eiq-map-v1-panel">
        <div className="eiq-map-v1-panel__title"><span>Feed Status</span></div>
        <dl className="eiq-map-v1-facts">
          <div><dt>Status</dt><dd>{viewModel.status}</dd></div>
          <div><dt>Rows</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Matched</dt><dd>{viewModel.source.matchedRows}</dd></div>
          <div><dt>Loaded</dt><dd>{viewModel.source.loadedRows}</dd></div>
        </dl>
      </section>
      <section className="eiq-map-v1-panel" data-empty-source-state={GOVERNED_UNRESOLVED_SOURCE_STATE}>
        <div className="eiq-map-v1-panel__title"><span>Null Handling</span></div>
        <p className="eiq-map-v1-copy">
          Missing map evidence remains blank until the governed feed supplies it.
        </p>
      </section>
    </aside>
  );
}
""",
        """function MapReadPanel({ viewModel }: { viewModel: BETA009ViewModel }) {
  const mappedCount = viewModel.rows.filter((row) => row.run_style || row.early_speed || row.projected_position).length;
  const pendingCount = Math.max(0, viewModel.rows.length - mappedCount);

  return (
    <aside className="eiq-map-v1-side">
      <section className="eiq-map-v1-panel">
        <div className="eiq-map-v1-panel__title"><span>Race Shape Read</span></div>
        <dl className="eiq-map-v1-facts">
          <div><dt>Runners</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Mapped</dt><dd>{mappedCount}</dd></div>
          <div><dt>Pending</dt><dd>{pendingCount}</dd></div>
        </dl>
      </section>
      <section className="eiq-map-v1-panel" data-empty-source-state={GOVERNED_UNRESOLVED_SOURCE_STATE}>
        <div className="eiq-map-v1-panel__title"><span>Map Note</span></div>
        <p className="eiq-map-v1-copy">
          Blank map reads mean there is not enough governed evidence for that runner yet.
        </p>
      </section>
    </aside>
  );
}
""",
        "map side panel",
    )

    text = text.replace(
        """            <div><dt>Source</dt><dd>{sourceLabel(row)}</dd></div>""",
        """            <div><dt>Map Read</dt><dd>{mapConfidenceLabel(row)}</dd></div>""",
    )
    text = text.replace(
        """          <span>Runner-level barrier and early-position evidence.</span>""",
        """          <span>Runner-level barrier and expected-position read.</span>""",
    )
    text = text.replace(
        """          <span>Victorian barrier orientation. Rows are anchored to effective barrier.</span>""",
        """          <span>Victorian barrier orientation. Barrier 1 sits at the bottom.</span>""",
    )
    text = rework_hero_dl(text, "eiq-map-v1-hero")
    text = text.replace("<SourcePanel viewModel={viewModel} />", "<MapReadPanel viewModel={viewModel} />")
    write(path, text)


def rework_hero_dl(text: str, class_name: str) -> str:
    return text.replace(
        """        <dl>
          <div><dt>Workspace</dt><dd>{viewModel.workspaceId}</dd></div>
          <div><dt>Status</dt><dd>{viewModel.status}</dd></div>
          <div><dt>Rows</dt><dd>{viewModel.rows.length}</dd></div>
        </dl>""",
        """        <dl>
          <div><dt>Runners</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Race Read</dt><dd>{viewModel.status === "current" ? "Available" : "Pending"}</dd></div>
        </dl>""",
    )


def patch_market_workspace() -> None:
    path = "src/edgeiq-os/race/components/MarketWorkspace.tsx"
    text = read(path)
    text = replace_once(
        text,
        """function SourcePanel({ viewModel }: { viewModel: BETA010ViewModel }) {
  return (
    <aside className="eiq-market-v1-side">
      <section className="eiq-market-v1-panel">
        <div className="eiq-market-v1-panel__title"><span>Feed Status</span></div>
        <dl className="eiq-market-v1-facts">
          <div><dt>Status</dt><dd>{viewModel.status}</dd></div>
          <div><dt>Rows</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Matched</dt><dd>{viewModel.source.matchedRows}</dd></div>
          <div><dt>Loaded</dt><dd>{viewModel.source.loadedRows}</dd></div>
        </dl>
      </section>
      <section className="eiq-market-v1-panel">
        <div className="eiq-market-v1-panel__title"><span>Null Handling</span></div>
        <p className="eiq-market-v1-copy">
          Missing market evidence stays blank or pending until governed price feeds supply it.
        </p>
      </section>
    </aside>
  );
}
""",
        """function MarketReadPanel({ viewModel }: { viewModel: BETA010ViewModel }) {
  const pricedCount = viewModel.rows.filter((row) => row.market || row.edgeiq_price).length;
  const pendingCount = Math.max(0, viewModel.rows.length - pricedCount);

  return (
    <aside className="eiq-market-v1-side">
      <section className="eiq-market-v1-panel">
        <div className="eiq-market-v1-panel__title"><span>Market Read</span></div>
        <dl className="eiq-market-v1-facts">
          <div><dt>Runners</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Priced</dt><dd>{pricedCount}</dd></div>
          <div><dt>Pending</dt><dd>{pendingCount}</dd></div>
        </dl>
      </section>
      <section className="eiq-market-v1-panel">
        <div className="eiq-market-v1-panel__title"><span>Market Note</span></div>
        <p className="eiq-market-v1-copy">
          Pending Market means current prices are not available for that runner yet.
        </p>
      </section>
    </aside>
  );
}
""",
        "market side panel",
    )
    text = text.replace(
        """        <small>NO | HORSE | EPI | MARKET | OPEN | HIGH | LOW | MOVE | EDGEiQ PRICE | EDGE | STATUS</small>""",
        """        <small>Current prices and EDGEiQ assessed price context</small>""",
    )
    text = text.replace("              <th>Status</th>\n", "")
    text = text.replace("                <td>{value(row.status)}</td>\n", "")
    text = text.replace(
        """          <span>Governed market movement and assessed price alignment for this race.</span>""",
        """          <span>Current market and EDGEiQ assessed price alignment for this race.</span>""",
    )
    text = rework_hero_dl(text, "eiq-market-v1-hero")
    text = text.replace("<SourcePanel viewModel={viewModel} />", "<MarketReadPanel viewModel={viewModel} />")
    write(path, text)


def patch_overview_workspace() -> None:
    path = "src/edgeiq-os/race/components/OverviewWorkspace.tsx"
    text = read(path)
    text = text.replace('"Operational / Data State",', '"Race Readiness",')
    text = text.replace("Mission Control Evidence", "Race Intelligence")
    text = text.replace("SECTION | EVIDENCE | SOURCE | STATUS | OPEN", "Section | Evidence | Open")
    text = text.replace("              <th>Source</th>\n              <th>Status</th>\n", "")
    text = text.replace("                  <td>{value(row.source)}</td>\n                  <td><b className={statusClass(row)}>{value(row.status)}</b></td>\n", "")
    text = replace_once(
        text,
        """function SourcePanel({ viewModel }: { viewModel: BETA011ViewModel }) {
  return (
    <aside className="eiq-overview-v1-side">
      <section className="eiq-overview-v1-panel">
        <div className="eiq-overview-v1-panel__title"><span>Operational State</span></div>
        <dl className="eiq-overview-v1-facts">
          <div><dt>Status</dt><dd>{viewModel.status}</dd></div>
          <div><dt>Rows</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Matched</dt><dd>{viewModel.source.matchedRows}</dd></div>
          <div><dt>Loaded</dt><dd>{viewModel.source.loadedRows}</dd></div>
        </dl>
      </section>
      <section className="eiq-overview-v1-panel">
        <div className="eiq-overview-v1-panel__title"><span>Null Handling</span></div>
        <p className="eiq-overview-v1-copy">
          Missing evidence remains pending or unavailable until governed feeds supply it.
        </p>
      </section>
    </aside>
  );
}
""",
        """function RaceReadPanel({ viewModel }: { viewModel: BETA011ViewModel }) {
  const populated = viewModel.rows.filter((row) => value(row.evidence)).length;
  const pending = Math.max(0, viewModel.rows.length - populated);

  return (
    <aside className="eiq-overview-v1-side">
      <section className="eiq-overview-v1-panel">
        <div className="eiq-overview-v1-panel__title"><span>Race Read</span></div>
        <dl className="eiq-overview-v1-facts">
          <div><dt>Sections</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Available</dt><dd>{populated}</dd></div>
          <div><dt>Pending</dt><dd>{pending}</dd></div>
        </dl>
      </section>
      <section className="eiq-overview-v1-panel">
        <div className="eiq-overview-v1-panel__title"><span>Coverage Note</span></div>
        <p className="eiq-overview-v1-copy">
          Pending sections remain blank until the governed race read is available.
        </p>
      </section>
    </aside>
  );
}
""",
        "overview side panel",
    )
    text = text.replace(
        "What to know before analysing this race: environment, map, field intelligence and data readiness.",
        "What to know before analysing this race: environment, map and field intelligence.",
    )
    text = rework_hero_dl(text, "eiq-overview-v1-hero")
    text = text.replace("<SourcePanel viewModel={viewModel} />", "<RaceReadPanel viewModel={viewModel} />")
    write(path, text)


def patch_insights_workspace() -> None:
    path = "src/edgeiq-os/race/components/InsightsWorkspace.tsx"
    text = read(path)
    text = text.replace("          <small>{value(card.source)}</small>\n", "")
    text = replace_once(
        text,
        """function QualityPanel({ viewModel }: { viewModel: BETA012ViewModel }) {
  const populated = viewModel.rows.filter((row) => value(row.key_insight) || value(row.edge)).length;
  return (
    <aside className="eiq-insights-v1-side">
      <section className="eiq-insights-v1-panel">
        <div className="eiq-insights-v1-panel__title"><span>Insight Confidence / Evidence Quality</span></div>
        <dl className="eiq-insights-v1-facts">
          <div><dt>Status</dt><dd>{viewModel.status}</dd></div>
          <div><dt>Runner Rows</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Populated</dt><dd>{populated}</dd></div>
          <div><dt>Feed Rows</dt><dd>{viewModel.source.loadedRows}</dd></div>
        </dl>
      </section>
      <section className="eiq-insights-v1-panel">
        <div className="eiq-insights-v1-panel__title"><span>Model Information</span></div>
        <p className="eiq-insights-v1-copy">
          Confidence describes evidence quality and source coverage. It is not winning chance.
        </p>
      </section>
      <section className="eiq-insights-v1-panel">
        <div className="eiq-insights-v1-panel__title"><span>How To Use These Insights</span></div>
        <p className="eiq-insights-v1-copy">
          Use this workspace as an evidence index, then open Form, MAP or Market for the supporting detail.
        </p>
      </section>
    </aside>
  );
}
""",
        """function QualityPanel({ viewModel }: { viewModel: BETA012ViewModel }) {
  const populated = viewModel.rows.filter((row) => value(row.key_insight) || value(row.edge)).length;
  const pending = Math.max(0, viewModel.rows.length - populated);

  return (
    <aside className="eiq-insights-v1-side">
      <section className="eiq-insights-v1-panel">
        <div className="eiq-insights-v1-panel__title"><span>Insight Quality</span></div>
        <dl className="eiq-insights-v1-facts">
          <div><dt>Runners</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Insights</dt><dd>{populated}</dd></div>
          <div><dt>Pending</dt><dd>{pending}</dd></div>
        </dl>
      </section>
      <section className="eiq-insights-v1-panel">
        <div className="eiq-insights-v1-panel__title"><span>How To Use These Insights</span></div>
        <p className="eiq-insights-v1-copy">
          Use this as a race intelligence index, then open Form, MAP or Market for the supporting detail.
        </p>
      </section>
    </aside>
  );
}
""",
        "insights side panel",
    )
    text = text.replace("Governed analyst intelligence across angles, patterns, pressure points, watch factors and evidence confidence.", "Race intelligence across angles, patterns, pressure points and watch factors.")
    text = text.replace("Insights are generated only from governed current-race intelligence, market context and source coverage.", "Insights use current-race intelligence and market context where available.")
    text = rework_hero_dl(text, "eiq-insights-v1-hero")
    write(path, text)


def patch_epi_workspace() -> None:
    path = "src/edgeiq-os/race/components/EpiWorkspaceWorkspace.tsx"
    text = read(path)
    text = text.replace('  "SOURCE",\n  "VERSION / TIMESTAMP",\n', "")
    text = text.replace("GOVERNED TREND", "TREND")
    text = text.replace("EPI Matrix", "Performance Matrix")
    text = text.replace("NO | HORSE | CURRENT EPI | RANK | FIELD AVG | DIFF | START 10 ... START 1", "Current EPI and recent-start ratings")
    text = replace_once(
        text,
        """      <section className="eiq-epi-v1-panel">
        <div className="eiq-epi-v1-panel__title"><span>Data State</span></div>
        <dl className="eiq-epi-v1-facts">
          <div><dt>Status</dt><dd>{viewModel.status}</dd></div>
          <div><dt>Runner Rows</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Matched Rows</dt><dd>{viewModel.source.matchedRows}</dd></div>
          <div><dt>Feed Rows</dt><dd>{viewModel.source.loadedRows}</dd></div>
        </dl>
      </section>
      <section className="eiq-epi-v1-panel">
        <div className="eiq-epi-v1-panel__title"><span>Model Information</span></div>
        <p className="eiq-epi-v1-copy">
          Tile colour is supplied by the EPI workspace builder from historical race and ERI context. Missing starts remain blank.
        </p>
      </section>
""",
        """      <section className="eiq-epi-v1-panel">
        <div className="eiq-epi-v1-panel__title"><span>Performance Read</span></div>
        <dl className="eiq-epi-v1-facts">
          <div><dt>Runners</dt><dd>{viewModel.rows.length}</dd></div>
          <div><dt>Available</dt><dd>{viewModel.rows.filter((row) => row.current_epi || row.starts.some((start) => start.value)).length}</dd></div>
        </dl>
      </section>
      <section className="eiq-epi-v1-panel">
        <div className="eiq-epi-v1-panel__title"><span>Rating Note</span></div>
        <p className="eiq-epi-v1-copy">
          Missing starts remain blank.
        </p>
      </section>
""",
        "epi side panel",
    )
    text = text.replace("EPI WORKSPACE", "PERFORMANCE")
    text = text.replace("Previous 10 official starts in historical race-strength context.", "Previous 10 official starts in race-strength context.")
    text = rework_hero_dl(text, "eiq-epi-v1-hero")
    write(path, text)


def main() -> None:
    patch_map_workspace()
    patch_market_workspace()
    patch_overview_workspace()
    patch_insights_workspace()
    patch_epi_workspace()
    print("Applied EDGEiQ beta readiness UI language and existing-data wiring changes.")


if __name__ == "__main__":
    main()
