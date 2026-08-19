from pathlib import Path
root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

def read(rel):
    return (root / rel).read_text(encoding="utf-8")

def write(rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")

rel = "src/edgeiq-os/race/components/OverviewWorkspace.tsx"
text = read(rel)
for old, new in [
    ("Evidence pending trusted feed.", "Awaiting governed race evidence."),
    ("CertifiedBenchmarkPanel", "PerformanceHistoryPanel"),
    ("Certified Performance Intelligence", "Performance History"),
    ("Certified benchmark context is available.", "Benchmark race context is available."),
    ("Certified benchmark context is not available for this race.", "Benchmark race context is not available for this race."),
    ("Race Read", "Race Command Centre"),
    ("Coverage Note", "Availability"),
    ("Pending sections remain blank until the governed race read is available.", "Unavailable sections remain blank until governed source evidence is supplied."),
    ("<p>OVERVIEW</p>\n          <h3>{raceLabel || \"Mission Control\"}</h3>\n          <span>What to know before analysing this race: environment, map and field intelligence.</span>", "<p>OVERVIEW</p>\n          <h3>{raceLabel || \"Race Analysis Centre\"}</h3>\n          <span>Race environment, map pressure, field profile and governed evidence in one scan.</span>"),
    ("<div><dt>Race Read</dt><dd>{viewModel.status === \"current\" ? \"Available\" : \"Pending\"}</dd></div>", "<div><dt>Evidence</dt><dd>{viewModel.status === \"current\" ? \"Available\" : \"Pending\"}</dd></div>"),
]:
    text = text.replace(old, new)
write(rel, text)

rel = "src/edgeiq-os/race/components/EpiWorkspaceWorkspace.tsx"
text = read(rel)
for old, new in [
    ("<span>Runner Summary</span>", "<span>Selected Runner</span>"),
    ("Performance Matrix", "Performance Intelligence"),
    ("Current EPI and recent-start ratings", "Current field rating and recent official-start context"),
    ("Certified Race Benchmark", "Race Benchmark"),
    ("Certified benchmark context is not available for this race.", "Race benchmark context is not available for this race."),
    ("<p>PERFORMANCE</p>\n          <h3>{raceLabel || \"EPI matrix\"}</h3>\n          <span>Previous 10 official starts in race-strength context.</span>", "<p>PERFORMANCE</p>\n          <h3>{raceLabel || \"Performance Intelligence\"}</h3>\n          <span>EPI field ranking, recent official-start context and benchmark race strength.</span>"),
    ("Focus or select a populated EPI tile to inspect the historical race context.", "Select a populated EPI tile to inspect the historical race context."),
    ("Rating Note", "Availability"),
]:
    text = text.replace(old, new)
write(rel, text)

lab = r'''import { useEffect, useMemo, useState } from "react";
import {
  loadPerformanceIntelligenceFeed,
  type BenchmarkExplanationIndexRow,
  type HorseIntelligenceIndexRow,
  type PerformanceIntelligenceFeed,
  type RaceIntelligenceIndexRow,
} from "../../services/performance-intelligence";

const labTabs = ["JOCKEYS", "TRAINERS", "HORSES", "TRACKS", "MARKETS", "QUERY BUILDER", "BENCHMARKS"] as const;
type LabTab = (typeof labTabs)[number];

function clean(value: unknown): string {
  const text = String(value ?? "").trim();
  if (!text || text === "-" || text.toLowerCase() === "none" || text.toLowerCase() === "null") return "";
  return text;
}

function display(value: unknown, fallback = "Unavailable"): string {
  return clean(value) || fallback;
}

function compactRows<T>(rows: T[], limit = 24): T[] {
  return rows.slice(0, limit);
}

function sortByNumber<T>(rows: T[], getter: (row: T) => unknown): T[] {
  return [...rows].sort((left, right) => Number(clean(getter(right)) || 0) - Number(clean(getter(left)) || 0));
}

function MetricCard({ label, value, note }: { label: string; value: string | number; note?: string }) {
  return (
    <div className="eiq-lab-metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      {note ? <small>{note}</small> : null}
    </div>
  );
}

function HorsesTable({ rows }: { rows: HorseIntelligenceIndexRow[] }) {
  const ordered = compactRows(sortByNumber(rows, (row) => row.performance_count), 30);
  return (
    <section className="eiq-lab-panel eiq-lab-panel--wide">
      <header><span>Horse Intelligence Index</span><small>Governed compact feed</small></header>
      <table className="eiq-lab-table">
        <thead><tr><th>No</th><th>Horse</th><th>Profile</th><th>Performances</th><th>Eligible</th><th>Date Range</th></tr></thead>
        <tbody>
          {ordered.map((row) => (
            <tr key={`${row.race_context_key}-${row.runner_number}-${row.horse_name}`}>
              <td>{display(row.runner_number, "")}</td>
              <td><strong>{display(row.horse_name)}</strong></td>
              <td>{display(row.profile_quality_state).replace(/_/g, " ")}</td>
              <td>{display(row.performance_count, "0")}</td>
              <td>{display(row.eligible_performance_count, "0")}</td>
              <td>{display(row.date_range)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function BenchmarksTable({ rows }: { rows: BenchmarkExplanationIndexRow[] }) {
  const ordered = compactRows(sortByNumber(rows, (row) => row.sample_size), 28);
  return (
    <section className="eiq-lab-panel eiq-lab-panel--wide">
      <header><span>Benchmark Library</span><small>Standard-time evidence</small></header>
      <table className="eiq-lab-table">
        <thead><tr><th>Track</th><th>Distance</th><th>Class</th><th>Going</th><th>Sample</th><th>Confidence</th><th>Median</th></tr></thead>
        <tbody>
          {ordered.map((row) => (
            <tr key={row.benchmark_id}>
              <td>{display(row.track)}</td>
              <td>{display(row.distance_metres)}m</td>
              <td>{display(row.race_class_canonical)}</td>
              <td>{display(row.going_canonical)}</td>
              <td>{display(row.sample_size)}</td>
              <td>{display(row.confidence_state).replace(/_/g, " ")}</td>
              <td>{display(row.median_time_seconds)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function RacesTable({ rows }: { rows: RaceIntelligenceIndexRow[] }) {
  const ordered = compactRows(rows, 28);
  return (
    <section className="eiq-lab-panel eiq-lab-panel--wide">
      <header><span>Race Intelligence Index</span><small>Race context rows</small></header>
      <table className="eiq-lab-table">
        <thead><tr><th>Date</th><th>Track</th><th>Race</th><th>Distance</th><th>Class</th><th>Condition</th><th>Benchmark</th><th>Quality</th></tr></thead>
        <tbody>
          {ordered.map((row) => (
            <tr key={row.race_context_key}>
              <td>{display(row.race_date)}</td>
              <td>{display(row.track)}</td>
              <td>{display(row.race_number)}</td>
              <td>{display(row.distance_metres)}m</td>
              <td>{display(row.race_class)}</td>
              <td>{display(row.track_condition)}</td>
              <td>{display(row.selected_benchmark_confidence).replace(/_/g, " ")}</td>
              <td>{display(row.race_quality_state).replace(/_/g, " ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function UnavailableResearch({ tab }: { tab: LabTab }) {
  return (
    <section className="eiq-lab-panel eiq-lab-panel--wide">
      <header><span>{tab}</span><small>Governed feed required</small></header>
      <p className="eiq-lab-copy">
        This research module is waiting on a compact governed {tab.toLowerCase()} feed. Warehouse-scale source files are not loaded in the browser.
      </p>
    </section>
  );
}

export function LabWorkspace() {
  const [tab, setTab] = useState<LabTab>("HORSES");
  const [feed, setFeed] = useState<PerformanceIntelligenceFeed | null>(null);
  const [query, setQuery] = useState("");
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
        setError(loadError instanceof Error ? loadError.message : "LAB feed failed");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const filteredBenchmarks = useMemo(() => {
    const text = query.trim().toUpperCase();
    const rows = feed?.benchmark_explanation_index ?? [];
    if (!text) return rows;
    return rows.filter((row) => [row.track, row.race_class_canonical, row.going_canonical, row.distance_metres].some((value) => clean(value).toUpperCase().includes(text)));
  }, [feed, query]);

  if (loading) return <section className="eiq-lab-workspace"><div className="eiq-lab-empty">Loading LAB research feeds.</div></section>;
  if (error) return <section className="eiq-lab-workspace"><div className="eiq-lab-empty">{error}</div></section>;
  if (!feed) return <section className="eiq-lab-workspace"><div className="eiq-lab-empty">LAB research feeds are unavailable.</div></section>;

  const counts = feed.manifest?.row_counts ?? {};
  const content = tab === "HORSES"
    ? <HorsesTable rows={feed.horse_intelligence_index} />
    : tab === "TRACKS" || tab === "BENCHMARKS"
      ? <BenchmarksTable rows={filteredBenchmarks} />
      : tab === "QUERY BUILDER"
        ? <BenchmarksTable rows={filteredBenchmarks} />
        : tab === "MARKETS"
          ? <RacesTable rows={feed.race_intelligence_index} />
          : <UnavailableResearch tab={tab} />;

  return (
    <section className="eiq-lab-workspace">
      <div className="eiq-lab-hero">
        <div>
          <p>LAB</p>
          <h3>Research Laboratory</h3>
          <span>Governed compact research feeds for race analysis, benchmark checks and source coverage.</span>
        </div>
        <dl>
          <div><dt>Races</dt><dd>{counts.race_intelligence_index ?? feed.race_intelligence_index.length}</dd></div>
          <div><dt>Horses</dt><dd>{counts.horse_intelligence_index ?? feed.horse_intelligence_index.length}</dd></div>
          <div><dt>Benchmarks</dt><dd>{counts.benchmark_explanation_index ?? feed.benchmark_explanation_index.length}</dd></div>
        </dl>
      </div>

      <nav className="eiq-context-tabs" aria-label="LAB modules">
        {labTabs.map((item) => (
          <button key={item} type="button" className={tab === item ? "is-active" : ""} onClick={() => setTab(item)}>
            {item}
          </button>
        ))}
      </nav>

      {tab === "QUERY BUILDER" || tab === "TRACKS" || tab === "BENCHMARKS" ? (
        <section className="eiq-lab-querybar">
          <label>
            <span>Filter benchmark library</span>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Track, distance, class or condition" />
          </label>
        </section>
      ) : null}

      <div className="eiq-lab-layout">
        <main>{content}</main>
        <aside>
          <section className="eiq-lab-panel">
            <header><span>EDGEiQ Insight</span><small>Feed authority</small></header>
            <p className="eiq-lab-copy">LAB only displays governed compact feeds. Missing modules stay pending until the builder supplies a browser-safe research feed.</p>
          </section>
          <section className="eiq-lab-metric-stack">
            <MetricCard label="Feed Version" value={display(feed.manifest?.feed_version, "v1")} />
            <MetricCard label="Generated" value={display(feed.manifest?.generated_timestamp)} />
            <MetricCard label="Limit" value="Compact feeds only" note="No warehouse-scale browser loads" />
          </section>
        </aside>
      </div>
    </section>
  );
}
'''
write("src/edgeiq-os/race/components/LabWorkspace.tsx", lab)

css_rel = "src/edgeiq-os/styles/edgeiqOsV2.css"
css = read(css_rel)
css_add = r'''

/* EDGEIQ product unification pass: MAP-standard typography and compact research surfaces. */
.eiq-race-form-guide,
.eiq-overview-v1,
.eiq-epi-v1,
.eiq-lab-workspace {
  font-size: 13px;
  line-height: 1.45;
}
.eiq-race-form-guide h2,
.eiq-overview-v1 h3,
.eiq-epi-v1 h3,
.eiq-lab-workspace h3 {
  letter-spacing: 0;
  font-weight: 750;
}
.eiq-performance-profile-list {
  display: grid;
  gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.eiq-performance-profile-list li {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid rgba(120, 150, 160, 0.12);
  padding: 2px 0;
}
.eiq-performance-profile-list span { color: var(--os-text-muted); }
.eiq-performance-profile-list b { color: var(--os-text); font-weight: 650; }
.eiq-lab-workspace { display: grid; gap: 14px; }
.eiq-lab-hero,
.eiq-lab-panel,
.eiq-lab-querybar,
.eiq-lab-metric-card,
.eiq-lab-empty {
  border: 1px solid var(--os-border);
  background: var(--os-panel);
  border-radius: 14px;
  box-shadow: var(--os-shadow-soft);
}
.eiq-lab-hero {
  display: flex;
  justify-content: space-between;
  align-items: stretch;
  gap: 20px;
  padding: 18px;
}
.eiq-lab-hero p,
.eiq-lab-panel header span,
.eiq-lab-querybar span {
  margin: 0 0 6px;
  color: var(--os-accent);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.eiq-lab-hero h3 { margin: 0 0 8px; font-size: 24px; }
.eiq-lab-hero span,
.eiq-lab-copy,
.eiq-lab-panel header small,
.eiq-lab-metric-card small { color: var(--os-text-muted); }
.eiq-lab-hero dl {
  display: grid;
  grid-template-columns: repeat(3, minmax(88px, 1fr));
  gap: 8px;
  margin: 0;
  min-width: 320px;
}
.eiq-lab-hero dl div,
.eiq-lab-metric-card {
  padding: 12px;
  border: 1px solid var(--os-border-subtle);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
}
.eiq-lab-hero dt,
.eiq-lab-metric-card span {
  color: var(--os-text-muted);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.eiq-lab-hero dd,
.eiq-lab-metric-card strong {
  margin: 4px 0 0;
  color: var(--os-text);
  font-size: 18px;
  font-weight: 750;
}
.eiq-lab-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 14px;
}
.eiq-lab-layout main,
.eiq-lab-layout aside,
.eiq-lab-metric-stack { display: grid; gap: 12px; align-content: start; }
.eiq-lab-panel { padding: 14px; overflow: hidden; }
.eiq-lab-panel header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 10px;
}
.eiq-lab-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.eiq-lab-table th,
.eiq-lab-table td {
  border-bottom: 1px solid rgba(120, 150, 160, 0.12);
  padding: 7px 8px;
  text-align: left;
  vertical-align: middle;
}
.eiq-lab-table th {
  color: var(--os-text-muted);
  font-size: 10px;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  background: rgba(255, 255, 255, 0.03);
}
.eiq-lab-querybar { padding: 12px 14px; }
.eiq-lab-querybar label { display: grid; gap: 6px; }
.eiq-lab-querybar input {
  width: 100%;
  border: 1px solid var(--os-border);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
  color: var(--os-text);
  padding: 10px 12px;
}
.eiq-lab-empty { padding: 22px; color: var(--os-text-muted); }
@media (max-width: 980px) {
  .eiq-lab-hero,
  .eiq-lab-layout { grid-template-columns: 1fr; display: grid; }
  .eiq-lab-hero dl { min-width: 0; }
}
'''
if "EDGEIQ product unification pass" not in css:
    css += css_add
write(css_rel, css)
print("patched overview epi lab css")
