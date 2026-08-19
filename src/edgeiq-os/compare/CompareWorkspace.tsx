import { useEffect, useMemo, useState } from "react";
import {
  loadPerformanceIntelligenceFeed,
  type PerformanceIntelligenceFeed,
} from "../services/performance-intelligence";
import {
  buildCompareViewModel,
  defaultCompareSelection,
  getCompareOptions,
  type CompareEntityMode,
  type CompareMetricRow,
  type ComparePanel,
} from "./compareWorkspaceData";

type CompareWorkspaceProps = {
  raceKey?: string | null;
  runner?: any;
};

const MODES: CompareEntityMode[] = ["HORSE", "RACE"];

function clean(value: unknown): string {
  const text = String(value ?? "").trim();
  return text || "Unavailable";
}

function runnerIdentity(runner: any): string {
  return String(runner?.horse ?? runner?.runnerName ?? runner?.name ?? "").trim();
}

function Panel({ label, panel }: { label: string; panel: ComparePanel | null }) {
  if (!panel) {
    return (
      <article className="eiq-compare-final-card">
        <span>{label}</span>
        <strong>Unavailable</strong>
        <p>Choose a governed entity to compare.</p>
      </article>
    );
  }

  return (
    <article className="eiq-compare-final-card">
      <span>{label}</span>
      <strong>{panel.title}</strong>
      <p>{panel.subtitle}</p>
      <dl>
        {panel.rows.map((row) => (
          <div key={`${label}-${row.label}`}>
            <dt>{row.label}</dt>
            <dd>{row.left}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

function MetricRow({ row }: { row: CompareMetricRow }) {
  return (
    <tr>
      <th scope="row">{row.label}</th>
      <td>{row.left}</td>
      <td>{row.right}</td>
      <td>{row.scope}</td>
    </tr>
  );
}

export function CompareWorkspace({ raceKey, runner }: CompareWorkspaceProps) {
  const [feed, setFeed] = useState<PerformanceIntelligenceFeed | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "unavailable">("loading");
  const [mode, setMode] = useState<CompareEntityMode>("HORSE");
  const [leftId, setLeftId] = useState("");
  const [rightId, setRightId] = useState("");

  useEffect(() => {
    let cancelled = false;
    loadPerformanceIntelligenceFeed()
      .then((nextFeed) => {
        if (cancelled) return;
        setFeed(nextFeed);
        setLoadState("ready");
        const options = getCompareOptions(nextFeed, "HORSE", raceKey);
        const selection = defaultCompareSelection(options);
        const runnerName = runnerIdentity(runner).toUpperCase();
        const runnerOption = runnerName
          ? options.find((option) => option.label.toUpperCase() === runnerName)
          : null;
        setLeftId(runnerOption?.id ?? selection.leftId);
        setRightId(selection.rightId === runnerOption?.id ? (options[1]?.id ?? selection.rightId) : selection.rightId);
      })
      .catch((error) => {
        console.warn("EDGEiQ compare feed unavailable", error);
        if (!cancelled) {
          setFeed(null);
          setLoadState("unavailable");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [raceKey, runner]);

  const options = useMemo(() => getCompareOptions(feed, mode, raceKey), [feed, mode, raceKey]);
  const viewModel = useMemo(
    () => buildCompareViewModel(feed, mode, leftId, rightId, raceKey),
    [feed, mode, leftId, rightId, raceKey],
  );

  useEffect(() => {
    if (!options.length) {
      setLeftId("");
      setRightId("");
      return;
    }
    const selection = defaultCompareSelection(options);
    if (!options.some((option) => option.id === leftId)) setLeftId(selection.leftId);
    if (!options.some((option) => option.id === rightId)) setRightId(selection.rightId);
  }, [options, leftId, rightId]);

  return (
    <section className="eiq-compare-final" data-edgeiq-workspace-key="COMPARE" data-edgeiq-mounted-component="CompareWorkspace">
      <header className="eiq-compare-final__header">
        <div>
          <span>COMPARE</span>
          <strong>Side-by-side governed comparison</strong>
          <p>
            Compare horses or races using common certified performance fields. Values that are not present in the governed feed remain unavailable.
          </p>
        </div>
        <aside>
          <span>Feed</span>
          <strong>{loadState === "ready" ? "Loaded" : loadState === "loading" ? "Loading" : "Unavailable"}</strong>
          <small>{clean(viewModel.feedGenerated)}</small>
        </aside>
      </header>

      <div className="eiq-compare-final__controls">
        <label>
          <span>Entity</span>
          <select
            value={mode}
            onChange={(event) => {
              const nextMode = event.target.value as CompareEntityMode;
              setMode(nextMode);
              const selection = defaultCompareSelection(getCompareOptions(feed, nextMode, raceKey));
              setLeftId(selection.leftId);
              setRightId(selection.rightId);
            }}
          >
            {MODES.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </label>
        <label>
          <span>Left</span>
          <select value={leftId} onChange={(event) => setLeftId(event.target.value)} disabled={!options.length}>
            {options.map((option) => (
              <option key={option.id} value={option.id}>{option.label}</option>
            ))}
          </select>
        </label>
        <label>
          <span>Right</span>
          <select value={rightId} onChange={(event) => setRightId(event.target.value)} disabled={!options.length}>
            {options.map((option) => (
              <option key={option.id} value={option.id}>{option.label}</option>
            ))}
          </select>
        </label>
        <div className="eiq-compare-final__scope">
          <span>Scope</span>
          <strong>{mode === "HORSE" ? "Current race runners" : "Certified races"}</strong>
        </div>
      </div>

      <div className="eiq-compare-final__panels">
        <Panel label="Left" panel={viewModel.leftPanel} />
        <Panel label="Right" panel={viewModel.rightPanel} />
        <aside className="eiq-compare-final-card eiq-compare-final__boundary">
          <span>Data Boundary</span>
          <strong>Comparable fields only</strong>
          <p>{viewModel.limitationText}</p>
          <ul>
            {viewModel.unavailableModes.map((item) => (
              <li key={item.label}><b>{item.label}</b><em>{item.reason}</em></li>
            ))}
          </ul>
        </aside>
      </div>

      <section className="eiq-compare-final-table">
        <header>
          <span>Common Metrics</span>
          <strong>{mode === "HORSE" ? "Profile alignment" : "Race context alignment"}</strong>
        </header>
        <div>
          <table>
            <thead>
              <tr>
                <th>Metric</th>
                <th>Left</th>
                <th>Right</th>
                <th>Scope</th>
              </tr>
            </thead>
            <tbody>
              {viewModel.metricRows.map((row) => <MetricRow key={row.label} row={row} />)}
            </tbody>
          </table>
        </div>
      </section>

      <section className="eiq-compare-final-table">
        <header>
          <span>Historical Context</span>
          <strong>{mode === "HORSE" ? "Recent governed runs" : "Not applicable for race comparison"}</strong>
        </header>
        {mode === "HORSE" && viewModel.historicalRows.length ? (
          <div>
            <table>
              <thead>
                <tr>
                  <th>Side</th>
                  <th>Date</th>
                  <th>Race</th>
                  <th>Dist</th>
                  <th>Class</th>
                  <th>Cond</th>
                  <th>Finish</th>
                  <th>Margin</th>
                  <th>SP</th>
                  <th>Benchmark</th>
                </tr>
              </thead>
              <tbody>
                {viewModel.historicalRows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.side}</td>
                    <td>{row.date}</td>
                    <td>{row.race}</td>
                    <td>{row.distance}</td>
                    <td>{row.className}</td>
                    <td>{row.condition}</td>
                    <td>{row.finish}</td>
                    <td>{row.margin}</td>
                    <td>{row.sp}</td>
                    <td>{row.benchmark}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="eiq-compare-final__empty">
            {mode === "HORSE"
              ? "Historical governed rows are not available for this selection."
              : "Race comparison uses race-level governed fields only."}
          </p>
        )}
      </section>
    </section>
  );
}
