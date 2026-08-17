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
import {
  EiqBadge,
  EiqCard,
  EiqDataTable,
  EiqEmptyState,
  EiqMetric,
  EiqPanel,
  EiqSectionHeader,
  EiqSidePanel,
  EiqStatusBadge,
  PageFrame,
  PageHeader,
} from "../design-system/v1";

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
      <EiqCard className="eiq-compare-v2-card eiq-compare-final-card">
        <EiqSectionHeader eyebrow={label} title="Unavailable" />
        <EiqEmptyState title="Choose a governed entity to compare." />
      </EiqCard>
    );
  }

  return (
    <EiqCard className="eiq-compare-v2-card eiq-compare-final-card">
      <EiqSectionHeader eyebrow={label} title={panel.title} meta={<EiqBadge>{panel.subtitle}</EiqBadge>} />
      <dl className="eiq-compare-v2-facts eiq-v1-side-facts">
        {panel.rows.map((row) => (
          <div key={`${label}-${row.label}`}>
            <dt>{row.label}</dt>
            <dd>{row.left}</dd>
          </div>
        ))}
      </dl>
    </EiqCard>
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
    <PageFrame className="eiq-compare-v2 eiq-compare-final" data-edgeiq-workspace-key="COMPARE" data-edgeiq-mounted-component="CompareWorkspace">
      <PageHeader
        eyebrow="COMPARE"
        title="Side-by-side governed comparison"
        description="Compare horses or races using common certified performance fields. Values that are not present in the governed feed remain unavailable."
        actions={
          <div className="eiq-compare-v2-feed">
            <EiqMetric
              label="Feed"
              value={<EiqStatusBadge status={loadState === "ready" ? "Loaded" : loadState === "loading" ? "Loading" : "Unavailable"} />}
              detail={clean(viewModel.feedGenerated)}
            />
          </div>
        }
      />

      <EiqPanel className="eiq-compare-v2-controls eiq-compare-final__controls">
        <label className="eiq-v2-field">
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
        <label className="eiq-v2-field">
          <span>Left</span>
          <select value={leftId} onChange={(event) => setLeftId(event.target.value)} disabled={!options.length}>
            {options.map((option) => (
              <option key={option.id} value={option.id}>{option.label}</option>
            ))}
          </select>
        </label>
        <label className="eiq-v2-field">
          <span>Right</span>
          <select value={rightId} onChange={(event) => setRightId(event.target.value)} disabled={!options.length}>
            {options.map((option) => (
              <option key={option.id} value={option.id}>{option.label}</option>
            ))}
          </select>
        </label>
        <div className="eiq-compare-final__scope">
          <EiqMetric label="Scope" value={mode === "HORSE" ? "Current race runners" : "Certified races"} />
        </div>
      </EiqPanel>

      <div className="eiq-compare-final__panels">
        <Panel label="Left" panel={viewModel.leftPanel} />
        <Panel label="Right" panel={viewModel.rightPanel} />
        <EiqSidePanel className="eiq-compare-final-card eiq-compare-final__boundary">
          <section className="eiq-v1-side-panel-section">
            <EiqSectionHeader eyebrow="Data Boundary" title="Comparable fields only" />
            <p className="eiq-v1-analytical-copy">{viewModel.limitationText}</p>
          </section>
          <section className="eiq-v1-side-panel-section">
            <ul className="eiq-v1-standard-list">
            {viewModel.unavailableModes.map((item) => (
              <li key={item.label}><b>{item.label}</b><em>{item.reason}</em></li>
            ))}
            </ul>
          </section>
        </EiqSidePanel>
      </div>

      <EiqPanel className="eiq-compare-final-table">
        <EiqSectionHeader eyebrow="Common Metrics" title={mode === "HORSE" ? "Profile alignment" : "Race context alignment"} />
        <EiqDataTable
          density="compact"
          className="eiq-compare-v2-table"
          wrapperProps={{ className: "eiq-v1-standard-table-scroll" }}
        >
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
        </EiqDataTable>
      </EiqPanel>

      <EiqPanel className="eiq-compare-final-table">
        <EiqSectionHeader eyebrow="Historical Context" title={mode === "HORSE" ? "Recent governed runs" : "Not applicable for race comparison"} />
        {mode === "HORSE" && viewModel.historicalRows.length ? (
          <EiqDataTable
            density="compact"
            className="eiq-compare-v2-table eiq-compare-v2-table--historical"
            wrapperProps={{ className: "eiq-v1-standard-table-scroll" }}
          >
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
          </EiqDataTable>
        ) : (
          <EiqEmptyState
            title={mode === "HORSE"
              ? "Historical governed rows are not available for this selection."
              : "Race comparison uses race-level governed fields only."}
          />
        )}
      </EiqPanel>
    </PageFrame>
  );
}
