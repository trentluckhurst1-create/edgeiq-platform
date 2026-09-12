import { useEffect, useMemo, useState } from "react";
import { loadPerformanceIntelligenceFeed, type PerformanceIntelligenceFeed } from "../../services/performance-intelligence";
import {
  buildLabQueryModel,
  executeLabResearchQuery,
  type LabEntity,
  type LabMetricKey,
  type LabQuery,
} from "../services/labResearch";

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

export function ResearchLabWorkspace() {
  const [feed, setFeed] = useState<PerformanceIntelligenceFeed | null>(null);
  const [query, setQuery] = useState<LabQuery>(() => initialQuery());

  useEffect(() => {
    let active = true;
    loadPerformanceIntelligenceFeed()
      .then((next) => { if (active) setFeed(next); })
      .catch(() => { if (active) setFeed(null); });
    return () => { active = false; };
  }, []);

  const model = useMemo(() => feed ? buildLabQueryModel(feed) : null, [feed]);
  const result = useMemo(() => feed ? executeLabResearchQuery(feed, query) : null, [feed, query]);

  const metrics = model?.metricsByEntity[query.entity] ?? [];

  return (
    <section className="eiq-build-v1" data-edgeiq-workspace-key="RESEARCH-LAB">
      <header className="eiq-build-v1__header"><div><p>EDGEiQ / RACING</p><h1>Research Lab</h1></div></header>

      <div className="eiq-build-v1__grid eiq-build-v1__grid--3">
        <article className="eiq-build-v1__card"><h2>Races</h2><strong>{model?.summary.races ?? "-"}</strong></article>
        <article className="eiq-build-v1__card"><h2>Horses</h2><strong>{model?.summary.horses ?? "-"}</strong></article>
        <article className="eiq-build-v1__card"><h2>Benchmarks</h2><strong>{model?.summary.benchmarks ?? "-"}</strong></article>
      </div>

      <section className="eiq-build-v1__card">
        <div className="eiq-build-v1__grid eiq-build-v1__grid--3">
          <label><span>Track</span><select value={query.track} onChange={(event) => setQuery((current) => ({ ...current, track: event.target.value }))}>{(model?.tracks ?? [{ value: "ALL", label: "All Tracks" }]).map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
          <label><span>Entity</span><select value={query.entity} onChange={(event) => { const entity = event.target.value as LabEntity; setQuery((current) => ({ ...current, entity, metric: metricForEntity(entity), groupBy: "NONE" })); }}>{(model?.entities ?? []).filter((option) => !option.disabled).map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
          <label><span>Metric</span><select value={query.metric} onChange={(event) => setQuery((current) => ({ ...current, metric: event.target.value as LabMetricKey }))}>{metrics.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
          <label><span>Sort</span><select value={query.sort} onChange={(event) => setQuery((current) => ({ ...current, sort: event.target.value as LabQuery["sort"] }))}>{(model?.sortOptions ?? []).map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
          <label><span>Limit</span><select value={query.limit} onChange={(event) => setQuery((current) => ({ ...current, limit: Number(event.target.value) }))}>{(model?.limits ?? [10,25,50]).map((limit) => <option key={limit} value={limit}>{limit}</option>)}</select></label>
          <label><span>Filter</span><input value={query.search} onChange={(event) => setQuery((current) => ({ ...current, search: event.target.value }))} /></label>
        </div>
      </section>

      <section className="eiq-build-v1__card eiq-build-v1__table-card">
        <header><h2>{result?.title ?? "Research"}</h2><strong>{result?.rows.length ?? 0}</strong></header>
        <table>
          <thead><tr>{(result?.columns ?? ["-"]).map((column) => <th key={column}>{column}</th>)}</tr></thead>
          <tbody>
            {result?.rows.length ? result.rows.map((row) => <tr key={row.id}>{result.columns.map((column) => <td key={`${row.id}-${column}`}>{row.values[column] || "-"}</td>)}</tr>) : <tr><td colSpan={Math.max(1, result?.columns.length ?? 1)} className="eiq-build-v1__empty">-</td></tr>}
          </tbody>
        </table>
      </section>
    </section>
  );
}
