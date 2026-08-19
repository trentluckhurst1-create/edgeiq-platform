import { useEffect, useMemo, useState } from "react";
import {
  loadPerformanceIntelligenceFeed,
  type PerformanceIntelligenceFeed,
} from "../../services/performance-intelligence";
import {
  buildLabQueryModel,
  executeLabResearchQuery,
  type LabEntity,
  type LabGroupBy,
  type LabMetricKey,
  type LabQuery,
  type LabSortDirection,
  type LabUniverse,
} from "../services/labResearch";

function display(value: unknown, fallback = "Unavailable"): string {
  const text = String(value ?? "").trim();
  return text && text !== "-" ? text : fallback;
}

function initialQuery(): LabQuery {
  return {
    universe: "TODAY",
    track: "ALL",
    scope: "ALL_RACES",
    entity: "HORSE",
    metric: "PERFORMANCE_COUNT",
    search: "",
    groupBy: "NONE",
    sort: "DESC",
    limit: 25,
  };
}

function metricForEntity(entity: LabEntity): LabMetricKey {
  if (entity === "RACE") return "RUNNER_COUNT";
  if (entity === "BENCHMARK") return "BENCHMARK_SAMPLE";
  return "PERFORMANCE_COUNT";
}

function LabSelect<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string; disabled?: boolean; note?: string }[];
  onChange: (value: T) => void;
}) {
  return (
    <label className="eiq-lab-final-field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value as T)}>
        {options.map((option) => (
          <option key={option.value} value={option.value} disabled={option.disabled}>
            {option.label}{option.disabled && option.note ? ` - ${option.note}` : ""}
          </option>
        ))}
      </select>
    </label>
  );
}

export function LabWorkspace() {
  const [feed, setFeed] = useState<PerformanceIntelligenceFeed | null>(null);
  const [pendingQuery, setPendingQuery] = useState<LabQuery>(() => initialQuery());
  const [activeQuery, setActiveQuery] = useState<LabQuery>(() => initialQuery());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    loadPerformanceIntelligenceFeed()
      .then((nextFeed) => {
        if (cancelled) return;
        setFeed(nextFeed);
        setError(null);
      })
      .catch((loadError) => {
        if (cancelled) return;
        setFeed(null);
        setError(loadError instanceof Error ? loadError.message : "LAB research data failed to load");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const model = useMemo(() => (feed ? buildLabQueryModel(feed) : null), [feed]);
  const result = useMemo(() => (feed ? executeLabResearchQuery(feed, activeQuery) : null), [activeQuery, feed]);

  if (loading) {
    return (
      <section className="eiq-lab-workspace eiq-lab-final" data-edgeiq-workspace-key="LAB" data-edgeiq-mounted-component="LabWorkspace">
        <div className="eiq-lab-empty">Loading LAB research data.</div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="eiq-lab-workspace eiq-lab-final" data-edgeiq-workspace-key="LAB" data-edgeiq-mounted-component="LabWorkspace">
        <div className="eiq-lab-empty">{error}</div>
      </section>
    );
  }

  if (!feed || !model || !result) {
    return (
      <section className="eiq-lab-workspace eiq-lab-final" data-edgeiq-workspace-key="LAB" data-edgeiq-mounted-component="LabWorkspace">
        <div className="eiq-lab-empty">LAB research data is unavailable.</div>
      </section>
    );
  }

  const entityMetrics = model.metricsByEntity[pendingQuery.entity];
  const groupOptions = model.groupByOptions.filter((option) => {
    if (option.value === "RACE" && pendingQuery.entity === "BENCHMARK") return false;
    if (option.value === "CONDITION" && pendingQuery.entity === "HORSE") return true;
    return true;
  });

  return (
    <section className="eiq-lab-workspace eiq-lab-final" data-edgeiq-workspace-key="LAB" data-edgeiq-mounted-component="LabWorkspace" aria-label="LAB workspace">
      <header className="eiq-lab-final-hero">
        <div>
          <span>LAB</span>
          <h3>Stats Engine & Query Builder</h3>
          <p>Build browser-safe racing queries across the approved product intelligence set.</p>
        </div>
        <dl>
          <div><dt>Races</dt><dd>{model.summary.races}</dd></div>
          <div><dt>Horses</dt><dd>{model.summary.horses}</dd></div>
          <div><dt>Benchmarks</dt><dd>{model.summary.benchmarks}</dd></div>
          <div><dt>Historical Rows</dt><dd>{model.summary.historical}</dd></div>
        </dl>
      </header>

      <section className="eiq-lab-final-builder" aria-label="Research query builder">
        <div className="eiq-lab-final-builder-grid">
          <LabSelect<LabUniverse> label="Universe" value={pendingQuery.universe} options={model.universes} onChange={(universe) => setPendingQuery((query) => ({ ...query, universe }))} />
          <LabSelect<string> label="Track" value={pendingQuery.track} options={model.tracks} onChange={(track) => setPendingQuery((query) => ({ ...query, track }))} />
          <LabSelect<string> label="Scope" value={pendingQuery.scope} options={model.scopes} onChange={(scope) => setPendingQuery((query) => ({ ...query, scope }))} />
          <LabSelect<LabEntity>
            label="Entity"
            value={pendingQuery.entity}
            options={model.entities}
            onChange={(entity) =>
              setPendingQuery((query) => ({
                ...query,
                entity,
                metric: metricForEntity(entity),
                groupBy: "NONE",
              }))
            }
          />
          <LabSelect<LabMetricKey> label="Metric" value={pendingQuery.metric} options={entityMetrics} onChange={(metric) => setPendingQuery((query) => ({ ...query, metric }))} />
          <LabSelect<LabGroupBy> label="Group By" value={pendingQuery.groupBy} options={groupOptions} onChange={(groupBy) => setPendingQuery((query) => ({ ...query, groupBy }))} />
          <LabSelect<LabSortDirection> label="Sort" value={pendingQuery.sort} options={model.sortOptions} onChange={(sort) => setPendingQuery((query) => ({ ...query, sort }))} />
          <label className="eiq-lab-final-field">
            <span>Result Limit</span>
            <select value={pendingQuery.limit} onChange={(event) => setPendingQuery((query) => ({ ...query, limit: Number(event.target.value) }))}>
              {model.limits.map((limit) => (
                <option key={limit} value={limit}>{limit}</option>
              ))}
            </select>
          </label>
        </div>
        <div className="eiq-lab-final-filterbar">
          <label>
            <span>Filter</span>
            <input
              value={pendingQuery.search}
              onChange={(event) => setPendingQuery((query) => ({ ...query, search: event.target.value }))}
              placeholder="Horse, track, race, class or condition"
            />
          </label>
          <button type="button" onClick={() => setActiveQuery(pendingQuery)}>Run Query</button>
        </div>
      </section>

      <div className="eiq-lab-final-layout">
        <main className="eiq-lab-final-results">
          <section className="eiq-lab-panel eiq-lab-panel--wide">
            <header>
              <span>{result.title}</span>
              <small>{result.subtitle}</small>
            </header>
            {result.unavailableReason ? (
              <div className="eiq-lab-empty">{result.unavailableReason}</div>
            ) : result.rows.length ? (
              <div className="eiq-lab-final-table-scroll">
                <table className="eiq-lab-table">
                  <thead>
                    <tr>{result.columns.map((column) => <th key={column}>{column}</th>)}</tr>
                  </thead>
                  <tbody>
                    {result.rows.map((row) => (
                      <tr key={row.id}>
                        {result.columns.map((column) => (
                          <td key={`${row.id}-${column}`}>{display(row.values[column])}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="eiq-lab-empty">No rows match the selected governed query.</div>
            )}
          </section>
        </main>
        <aside className="eiq-lab-final-side">
          <section className="eiq-lab-panel">
            <header><span>Research Boundary</span></header>
            <p className="eiq-lab-copy">LAB exposes only approved product metrics. Jockey and trainer modules remain inactive until a validated research dataset is available.</p>
          </section>
          <section className="eiq-lab-panel">
            <header><span>Query Scope</span></header>
            <dl className="eiq-lab-final-scope">
              <div><dt>Universe</dt><dd>{activeQuery.universe}</dd></div>
              <div><dt>Track</dt><dd>{activeQuery.track === "ALL" ? "All Tracks" : activeQuery.track}</dd></div>
              <div><dt>Entity</dt><dd>{activeQuery.entity}</dd></div>
              <div><dt>Metric</dt><dd>{model.metricsByEntity[activeQuery.entity].find((item) => item.value === activeQuery.metric)?.label ?? activeQuery.metric}</dd></div>
              <div><dt>Generated</dt><dd>{model.summary.generated}</dd></div>
            </dl>
          </section>
          {model.limitations.length ? (
            <section className="eiq-lab-panel">
              <header><span>Data Limits</span></header>
              <ul className="eiq-lab-final-list">
                {model.limitations.slice(0, 4).map((item) => <li key={item}>{item}</li>)}
              </ul>
            </section>
          ) : null}
        </aside>
      </div>
    </section>
  );
}
