from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT = ROOT / "docs" / "full-product-implementation" / "checkpoints" / f"FINAL_PIXEL_SPEC_PHASE1_{STAMP}"
FILES = [
    "src/edgeiq-os/home/EdgeiqOsHome.tsx",
    "src/edgeiq-os/race/RaceFileV3.tsx",
    "src/edgeiq-os/race/components/PerformanceWorkspace.tsx",
    "src/edgeiq-os/race/components/OverviewWorkspace.tsx",
    "src/edgeiq-os/race/services/performanceWorkspaceViewModel.ts",
    "src/edgeiq-os/styles/edgeiqOsV2.css",
]


def checkpoint() -> None:
    CHECKPOINT.mkdir(parents=True, exist_ok=True)
    for rel in FILES:
        src = ROOT / rel
        if src.exists():
            dst = CHECKPOINT / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel: str, text: str) -> None:
    (ROOT / rel).write_text(text.replace("\n", "\r\n"), encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Patch anchor not found: {label}")
    return text.replace(old, new, 1)


def patch_home() -> None:
    write("src/edgeiq-os/home/EdgeiqOsHome.tsx", r'''import { useEffect, useMemo, useState } from "react";
import { buildMissionControlModel } from "../services/mission-control";
import { loadMeetingsWorkspaceViewModel, type MeetingsWorkspaceViewModel } from "../race/services/meetingsFeed";

type HomeWorkspaceSection = "meetings" | "race" | "field" | "formGuide" | "performance" | "epi" | "map" | "market" | "overview" | "insights" | "results" | "lab";

type EdgeiqOsHomeProps = {
  onOpenMeetings?: () => void;
  onOpenWorkspace?: (section: HomeWorkspaceSection) => void;
};

const WORKSPACE_STATE_STORAGE_KEY = "edgeiq-os-racefile-v3-state";
const mission = buildMissionControlModel();

const coreWorkspaces: Array<{ label: string; section: HomeWorkspaceSection; detail: string }> = [
  { label: "Form Guide", section: "formGuide", detail: "Field, profile, gear, market and recent form." },
  { label: "Race", section: "race", detail: "Tempo, EPF, determinants and runner board." },
  { label: "Performance", section: "performance", detail: "EPI matrix and governed historical cells." },
  { label: "Map", section: "map", detail: "Expected race shape and settling positions." },
  { label: "Market", section: "market", detail: "Live prices and governed assessed prices." },
  { label: "Lab", section: "lab", detail: "Governed research queries and comparisons." },
];

function clean(value: unknown): string {
  const text = String(value ?? "").replace(/\s+/g, " ").trim();
  if (!text || text === "-" || ["null", "undefined", "none"].includes(text.toLowerCase())) return "";
  return text;
}

function display(value: unknown, fallback = "Unavailable"): string {
  return clean(value) || fallback;
}

function readPersistedContext(model: MeetingsWorkspaceViewModel | null) {
  if (typeof window === "undefined" || !model) return null;
  try {
    const parsed = JSON.parse(window.localStorage.getItem(WORKSPACE_STATE_STORAGE_KEY) ?? "{}");
    const meetingKey = clean(parsed.selectedMeetingKey);
    const raceKey = clean(parsed.selectedRaceKey);
    if (!meetingKey && !raceKey) return null;
    for (const day of model.days) {
      for (const meeting of day.meetings) {
        if (meeting.meetingKey !== meetingKey && !meeting.raceSummaries.some((race) => race.raceKey === raceKey)) continue;
        const race = meeting.raceSummaries.find((item) => item.raceKey === raceKey) ?? meeting.raceSummaries[0];
        return {
          meeting: meeting.meeting,
          race: race?.label ?? "Race",
          meta: [meeting.track, meeting.rail, race?.distance, race?.raceClass].map(clean).filter(Boolean).join(" | "),
        };
      }
    }
  } catch {
    return null;
  }
  return null;
}

export function EdgeiqOsHome({ onOpenMeetings, onOpenWorkspace }: EdgeiqOsHomeProps) {
  const [model, setModel] = useState<MeetingsWorkspaceViewModel | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    loadMeetingsWorkspaceViewModel()
      .then((loaded) => {
        if (!cancelled) {
          setModel(loaded);
          setLoadError(null);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setModel(null);
          setLoadError(error instanceof Error ? error.message : "Meeting workspace feed unavailable");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const today = model?.days.find((day) => day.key === "TODAY") ?? model?.days[0] ?? null;
  const meetings = useMemo(() => (today?.meetings ?? []).slice(0, 6), [today]);
  const persisted = useMemo(() => readPersistedContext(model), [model]);
  const stats = [
    { label: "Meetings", value: String(today?.totals.meetings ?? mission.meetingCount), detail: "Today window" },
    { label: "Races", value: String(today?.totals.races ?? mission.raceCount), detail: "Loaded race contexts" },
    { label: "Runners", value: String(today?.totals.declared ?? mission.runnerCount), detail: "Declared runners" },
    { label: "Weather", value: mission.weatherWatch.label || "Unavailable", detail: mission.weatherWatch.value || "No governed weather watch" },
  ];

  return (
    <section className="eiq-home-final eiq-home-pixel-v1">
      <section className="eiq-home-pixel-v1__grid">
        <article className="eiq-home-pixel-v1__hero">
          <span>EDGEIQ OS</span>
          <h2>Today's Racing Intelligence</h2>
          <p>Governed meetings, race workspaces, runner evidence and research tools in one professional operating system.</p>
          <div className="eiq-home-pixel-v1__stats">
            {stats.map((item) => (
              <div key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </div>
            ))}
          </div>
        </article>
        <article className="eiq-home-pixel-v1__continue">
          <span>Continue Analysis</span>
          {persisted ? (
            <>
              <strong>{persisted.meeting} {persisted.race}</strong>
              <p>{persisted.meta || "Persisted race context"}</p>
              <button type="button" onClick={() => onOpenWorkspace?.("race")}>Open Race Workspace</button>
            </>
          ) : (
            <>
              <strong>No active race context</strong>
              <p>Open a meeting to begin a governed race workspace.</p>
              <button type="button" onClick={onOpenMeetings}>Open Meetings</button>
            </>
          )}
        </article>
      </section>

      <section className="eiq-home-pixel-v1__panel">
        <header>
          <div><span>Today's Meetings</span><strong>{today?.displayDate ?? "Current racing window"}</strong></div>
          <button type="button" onClick={onOpenMeetings}>View Meetings</button>
        </header>
        {loadError ? <p className="eiq-home-pixel-v1__empty">{loadError}</p> : null}
        <div className="eiq-home-pixel-v1__table-wrap">
          <table className="eiq-home-pixel-v1__table">
            <thead><tr><th>Meeting</th><th>State</th><th>Track</th><th>Weather</th><th>Races</th><th>Declared</th><th>Scratchings</th><th>Select</th></tr></thead>
            <tbody>
              {meetings.map((meeting) => (
                <tr key={meeting.meetingKey}>
                  <td><strong>{display(meeting.meeting)}</strong><small>{display(meeting.first)} first | {display(meeting.last)} last</small></td>
                  <td>{display(meeting.state)}</td>
                  <td>{display(meeting.track)}<small>{display(meeting.rail)}</small></td>
                  <td>{display(meeting.weather)}<small>{display(meeting.wind)}</small></td>
                  <td>{meeting.races}</td>
                  <td>{meeting.declared}</td>
                  <td>{meeting.scratchings}</td>
                  <td><button type="button" onClick={onOpenMeetings}>Open</button></td>
                </tr>
              ))}
              {!meetings.length && !loadError ? <tr><td colSpan={8}>Today's meeting feed is not available.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="eiq-home-pixel-v1__lower">
        <article className="eiq-home-pixel-v1__panel">
          <header><div><span>Core Workspaces</span><strong>Race analysis flow</strong></div></header>
          <div className="eiq-home-pixel-v1__workspace-grid">
            {coreWorkspaces.map((item) => (
              <button key={item.label} type="button" onClick={() => onOpenWorkspace?.(item.section)}>
                <strong>{item.label}</strong>
                <small>{item.detail}</small>
              </button>
            ))}
          </div>
        </article>
        <article className="eiq-home-pixel-v1__panel">
          <header><div><span>Current Availability</span><strong>Governed feed status</strong></div></header>
          <dl className="eiq-home-pixel-v1__availability">
            <div><dt>Generated</dt><dd>{display(model?.generatedAtDisplay)}</dd></div>
            <div><dt>Window</dt><dd>{model ? `${model.days.length} days` : "Unavailable"}</dd></div>
            <div><dt>Meetings</dt><dd>{today?.totals.meetings ?? "Unavailable"}</dd></div>
            <div><dt>Weather Watch</dt><dd>{display(mission.weatherWatch.label)}</dd></div>
          </dl>
        </article>
      </section>
    </section>
  );
}
''')


def patch_race_file() -> None:
    rel = "src/edgeiq-os/race/RaceFileV3.tsx"
    text = read(rel)
    text = replace_once(
        text,
        "<EdgeiqOsHome />",
        '<EdgeiqOsHome onOpenMeetings={() => openSection("meetings")} onOpenWorkspace={openSection} />',
        "home props",
    )
    write(rel, text)


def patch_performance_vm() -> None:
    rel = "src/edgeiq-os/race/services/performanceWorkspaceViewModel.ts"
    text = read(rel)
    text = replace_once(text, "  runner: string;\n  current: string;", "  runner: string;\n  silkUrl: string;\n  epi: string;\n  avg: string;\n  last: string;\n  current: string;", "row type")
    text = replace_once(text, "    const cells = row.starts.filter((start) => clean(start.value) || start.context).slice(-5).map(cellFromStart);\n    return {", "    const cells = row.starts.filter((start) => clean(start.value) || start.context).slice(-5).map(cellFromStart);\n    const last = [...cells].reverse().find((cell) => clean(cell.value))?.value ?? \"\";\n    return {", "last cell")
    text = replace_once(text, "      runner: clean(row.horse),\n      current: clean(row.current_epi),", "      runner: clean(row.horse),\n      silkUrl: \"\",\n      epi: clean(row.current_epi),\n      avg: clean(row.average_last_10),\n      last,\n      current: clean(row.current_epi),", "row fields")
    write(rel, text)


def patch_performance_component() -> None:
    rel = "src/edgeiq-os/race/components/PerformanceWorkspace.tsx"
    text = read(rel)
    text = replace_once(text, "};\n\nfunction value", "};\n\nconst HISTORY_COLUMNS = [\"L5\", \"L4\", \"L3\", \"L2\", \"L1\"];\n\nfunction value", "history columns")
    old_head = """<tr>
                  <th>No</th>
                  <th>Runner</th>
                  <th>Current</th>
                  <th>Peak</th>
                  <th>Average</th>
                  <th>Runs</th>
                  <th>L5</th>
                  <th>L4</th>
                  <th>L3</th>
                  <th>L2</th>
                  <th>L1</th>
                </tr>"""
    new_head = """<tr>
                  <th>NO</th>
                  <th>SILK</th>
                  <th>HORSE</th>
                  <th>EPI</th>
                  <th>AVG</th>
                  <th>LAST</th>
                  {HISTORY_COLUMNS.map((column) => <th key={column}>{column}</th>)}
                </tr>"""
    text = replace_once(text, old_head, new_head, "performance header")
    old_cells = """<td>{row.no}</td>
                    <td><strong>{row.runner}</strong></td>
                    <td>{value(row.current) || "-"}</td>
                    <td>{value(row.peak) || "-"}</td>
                    <td>{value(row.average) || "-"}</td>
                    <td>{row.validStarts}</td>
                    {Array.from({ length: 5 }).map((_, index) => {
                      const cell = row.cells[index];
                      return (
                        <td key={`${row.key}-cell-${index}`}>"""
    new_cells = """<td>{row.no}</td>
                    <td><span className="eiq-performance-v2-silk is-empty" aria-hidden="true" /></td>
                    <td><strong>{row.runner}</strong></td>
                    <td className="eiq-performance-v2-epi">{value(row.epi) || "-"}</td>
                    <td>{value(row.avg) || "-"}</td>
                    <td>{value(row.last) || "-"}</td>
                    {HISTORY_COLUMNS.map((column, index) => {
                      const cell = row.cells[index];
                      return (
                        <td key={`${row.key}-${column}`}>"""
    text = replace_once(text, old_cells, new_cells, "performance row cells")
    text = replace_once(text, "<span>Performance Heat Map</span>\n            <small>Historical rating cells only; empty cells remain unavailable.</small>", "<span>Performance Matrix</span>\n            <small>NO / SILK / HORSE / EPI / AVG / LAST / historical runs</small>", "performance title")
    write(rel, text)


def patch_overview() -> None:
    rel = "src/edgeiq-os/race/components/OverviewWorkspace.tsx"
    text = read(rel)
    text = replace_once(text, 'const SUMMARY_SECTIONS = ["Race Environment", "MAP / Race Shape", "Field Intelligence", "Operational / Data State"] as const;', 'const SUMMARY_SECTIONS = ["Race Environment", "MAP / Race Shape", "Field Intelligence"] as const;', "summary sections")
    for label in ["EPI Snapshot", "Speed Map Preview", "Race Evidence"]:
        start = text.find(f'      <article className="eiq-overview-v3-card">\\n        <span>{label}</span>')
        if start >= 0:
            end = text.find("      </article>", start)
            text = text[:start] + text[end + len("      </article>\n"):]
    text = replace_once(text, "<thead><tr><th>No</th><th>Runner</th><th>EPI</th><th>Early Speed</th><th>Map</th><th>Status</th></tr></thead>", "<thead><tr><th>NO</th><th>RUNNER</th><th>BAR</th><th>JOCKEY</th><th>EPI</th><th>MARKET</th><th>STATUS</th></tr></thead>", "overview board head")
    old = """<td>{display(row.no, "")}</td>
                    <td><strong>{display(row.horse)}</strong></td>
                    <td>{display(row.current_epi)}</td>
                    <td>{display(mapRow?.early_speed)}</td>
                    <td>{display(mapRow?.run_style || mapRow?.projected_position)}</td>
                    <td className={statusClass(row.rowStatus || mapRow?.row_status)}>{display(row.rowStatus || mapRow?.row_status, "Unavailable").replace(/_/g, " ")}</td>"""
    new = """<td>{display(row.no, "")}</td>
                    <td><strong>{display(row.horse)}</strong></td>
                    <td>{display(mapRow?.barrier)}</td>
                    <td>Unavailable</td>
                    <td>{display(row.current_epi)}</td>
                    <td>Unavailable</td>
                    <td className={statusClass(row.rowStatus || mapRow?.row_status)}>{display(row.rowStatus || mapRow?.row_status, "Unavailable").replace(/_/g, " ")}</td>"""
    text = replace_once(text, old, new, "overview board cells")
    text = replace_once(text, """<div className="eiq-overview-v3-layout">
        <main>
          <WhatMattersToday rows={viewModel.rows} />
          <div className="eiq-overview-v3-two-up">
            <SpeedMapPreview rows={selectedMapRows} onOpenTab={onOpenTab} />
            <EpiSnapshot rows={epiViewModel.rows} context={performanceContext} onOpenTab={onOpenTab} />
          </div>
          <RunnerBoard epiRows={epiViewModel.rows} mapRows={selectedMapRows} />
        </main>
        <aside>
          <section className="eiq-overview-v1-panel">
            <div className="eiq-overview-v1-panel__title">
              <span>Race Reference</span>
              <small>Certified performance context</small>
            </div>
            <dl className="eiq-overview-v1-facts">
              <div><dt>Benchmark</dt><dd>{performanceContext?.race ? formatBenchmarkLevel(performanceContext.race.selected_benchmark_level) : "Unavailable"}</dd></div>
              <div><dt>Sample</dt><dd>{display(performanceContext?.race?.selected_benchmark_sample_size)}</dd></div>
              <div><dt>History Rows</dt><dd>{performanceContext?.historical.length ?? 0}</dd></div>
              <div><dt>Profiles</dt><dd>{performanceContext?.horses.length ?? 0}</dd></div>
            </dl>
            <p className="eiq-overview-v1-copy">{display(performanceContext?.race?.fallback_path, "Performance reference is unavailable for this race.")}</p>
          </section>
          <DataGaps rows={viewModel.rows} epiRows={epiViewModel.rows} mapRows={selectedMapRows} />
          <section className="eiq-overview-v1-panel eiq-overview-v3-actions">
            <div className="eiq-overview-v1-panel__title"><span>Open Workspace</span></div>
            {["FORM GUIDE", "MAP", "EPI", "MARKET", "INSIGHTS"].map((label) => (
              <button key={label} type="button" onClick={() => onOpenTab?.(OPEN_TAB_MAP[label])}>{label}</button>
            ))}
          </section>
        </aside>
      </div>""", """<div className="eiq-overview-v3-layout eiq-overview-pixel-v1__layout">
        <main>
          <div className="eiq-overview-v3-two-up">
            <SpeedMapPreview rows={selectedMapRows} onOpenTab={onOpenTab} />
            <EpiSnapshot rows={epiViewModel.rows} context={performanceContext} onOpenTab={onOpenTab} />
          </div>
          <RunnerBoard epiRows={epiViewModel.rows} mapRows={selectedMapRows} />
        </main>
      </div>""", "overview layout")
    write(rel, text)


def patch_css() -> None:
    rel = "src/edgeiq-os/styles/edgeiqOsV2.css"
    text = read(rel)
    marker = "/* EDGEIQ FINAL PIXEL SPEC PHASE 1 LOCK */"
    if marker in text:
        write(rel, text)
        return
    text = text.rstrip() + r'''

/* EDGEIQ FINAL PIXEL SPEC PHASE 1 LOCK */
:root {
  --edgeiq-bg: #ffffff;
  --edgeiq-page-bg: #f7f9fc;
  --edgeiq-surface: #ffffff;
  --edgeiq-surface-raised: #ffffff;
  --edgeiq-surface-subtle: #f7f9fc;
  --edgeiq-muted-surface: #f2f5f9;
  --edgeiq-primary: #1261a6;
  --edgeiq-primary-strong: #084c87;
  --edgeiq-primary-dark: #073b68;
  --edgeiq-primary-soft: #eaf3fa;
  --edgeiq-primary-hover: #ddecf7;
  --edgeiq-text-primary: #17212b;
  --edgeiq-text-secondary: #52606d;
  --edgeiq-text-muted: #788592;
  --edgeiq-border: #dce3ea;
  --edgeiq-border-strong: #c8d2dc;
  --edgeiq-border-soft: #e7ecf1;
}

html, body, #root {
  background: #ffffff !important;
  color: var(--edgeiq-text-primary) !important;
  color-scheme: light !important;
  font-family: Inter, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

.eiq-home-pixel-v1, .eiq-performance-pixel-v1, .eiq-overview-pixel-v1, .eiq-race-intel-v1 {
  color: var(--edgeiq-text-primary);
}

.eiq-home-pixel-v1 { display: grid; gap: 14px; width: 100%; }
.eiq-home-pixel-v1__grid, .eiq-home-pixel-v1__lower { display: grid; grid-template-columns: minmax(0, 8fr) minmax(320px, 4fr); gap: 14px; }
.eiq-home-pixel-v1__hero, .eiq-home-pixel-v1__continue, .eiq-home-pixel-v1__panel, .eiq-performance-pixel-v1__panel, .eiq-overview-pixel-v1 .eiq-overview-v1-panel, .eiq-overview-pixel-v1__summary > article {
  background: #ffffff; border: 1px solid var(--edgeiq-border); border-radius: 5px; box-shadow: none; padding: 12px;
}
.eiq-home-pixel-v1 h2 { margin: 5px 0 6px; font-size: 28px; line-height: 1.15; color: var(--edgeiq-text-primary); }
.eiq-home-pixel-v1 span, .eiq-home-pixel-v1__panel header span, .eiq-performance-pixel-v1 .eiq-epi-v1-panel__title span, .eiq-overview-pixel-v1 .eiq-overview-v1-panel__title span {
  color: var(--edgeiq-primary); font-size: 11px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase;
}
.eiq-home-pixel-v1 p, .eiq-home-pixel-v1 small, .eiq-performance-pixel-v1 small, .eiq-overview-pixel-v1 small { color: var(--edgeiq-text-secondary); }
.eiq-home-pixel-v1__stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-top: 14px; }
.eiq-home-pixel-v1__stats > div, .eiq-home-pixel-v1__workspace-grid button, .eiq-home-pixel-v1__availability div { border: 1px solid var(--edgeiq-border); border-radius: 4px; background: var(--edgeiq-surface-subtle); padding: 10px; }
.eiq-home-pixel-v1__stats strong, .eiq-home-pixel-v1__continue strong, .eiq-home-pixel-v1__panel header strong { display: block; color: var(--edgeiq-text-primary); font-size: 18px; line-height: 1.2; }
.eiq-home-pixel-v1 button, .eiq-overview-pixel-v1 button { min-height: 34px; border: 1px solid var(--edgeiq-primary); border-radius: 4px; background: var(--edgeiq-primary-soft); color: var(--edgeiq-primary-dark); font-weight: 800; cursor: pointer; }
.eiq-home-pixel-v1__panel > header { display: flex; justify-content: space-between; gap: 14px; align-items: center; margin-bottom: 10px; }
.eiq-home-pixel-v1__table-wrap, .eiq-epi-v1-table-scroll, .eiq-overview-v1-table-scroll { border: 1px solid var(--edgeiq-border); border-radius: 4px; overflow: auto; }
.eiq-home-pixel-v1__table, .eiq-epi-v1-table, .eiq-overview-v1-table { width: 100%; border-collapse: collapse; background: #fff; color: var(--edgeiq-text-primary); }
.eiq-home-pixel-v1__table th, .eiq-epi-v1-table th, .eiq-overview-v1-table th { height: 36px; padding: 0 10px; border-bottom: 1px solid var(--edgeiq-border); background: var(--edgeiq-surface-subtle); color: var(--edgeiq-text-secondary); font-size: 11px; font-weight: 800; letter-spacing: .05em; text-align: left; text-transform: uppercase; white-space: nowrap; }
.eiq-home-pixel-v1__table td, .eiq-epi-v1-table td, .eiq-overview-v1-table td { height: 38px; padding: 0 10px; border-bottom: 1px solid var(--edgeiq-border-soft); color: var(--edgeiq-text-primary); vertical-align: middle; }
.eiq-home-pixel-v1__table td small { display: block; margin-top: 2px; }
.eiq-home-pixel-v1__workspace-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.eiq-home-pixel-v1__workspace-grid button { text-align: left; background: #fff; color: var(--edgeiq-text-primary); }
.eiq-home-pixel-v1__workspace-grid strong, .eiq-home-pixel-v1__workspace-grid small { display: block; }
.eiq-home-pixel-v1__availability { display: grid; gap: 8px; margin: 0; }
.eiq-home-pixel-v1__availability div { display: flex; justify-content: space-between; gap: 12px; }
.eiq-home-pixel-v1__availability dt, .eiq-home-pixel-v1__availability dd { margin: 0; }
.eiq-home-pixel-v1__availability dd { font-weight: 800; }
.eiq-performance-pixel-v1, .eiq-overview-pixel-v1, .eiq-race-intel-v1 { gap: 12px; }
.eiq-performance-pixel-v1__hero, .eiq-overview-pixel-v1__hero, .eiq-race-intel-v1 .eiq-epi-v1-hero { min-height: 64px; padding: 14px 0 12px; border-bottom: 1px solid var(--edgeiq-border); background: transparent; }
.eiq-performance-pixel-v1__hero h3, .eiq-overview-pixel-v1__hero h3, .eiq-race-intel-v1 .eiq-epi-v1-hero h3 { font-size: 24px; color: var(--edgeiq-text-primary); }
.eiq-performance-v2-table th:nth-child(3), .eiq-performance-v2-table td:nth-child(3) { min-width: 210px; }
.eiq-performance-v2-silk { width: 28px; height: 28px; display: inline-block; border-radius: 4px; border: 1px solid var(--edgeiq-border); background: var(--edgeiq-muted-surface); }
.eiq-performance-v2-epi { color: var(--edgeiq-primary-dark); font-weight: 900; }
.eiq-epi-v1-tile { min-width: 52px; min-height: 28px; border-radius: 4px; border: 1px solid var(--edgeiq-border); font-weight: 800; }
.eiq-epi-v1-tile.is-positive { background: #d8eaf7 !important; color: #073b68 !important; border-color: #a9cde5 !important; }
.eiq-epi-v1-tile.is-neutral { background: #eaf3fa !important; color: #084c87 !important; border-color: #c5dceb !important; }
.eiq-epi-v1-tile.is-negative { background: #f2f5f9 !important; color: #52606d !important; border-color: #dce3ea !important; }
.eiq-epi-v1-tile.is-missing { background: #ffffff !important; color: #788592 !important; }
.eiq-overview-pixel-v1__summary { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.eiq-overview-pixel-v1__layout { grid-template-columns: 1fr; }
.eiq-overview-pixel-v1__layout > main { display: grid; gap: 12px; }
.eiq-overview-pixel-v1__layout > aside { display: none; }
.eiq-overview-v3-two-up { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 12px; }
.eiq-overview-v3-map-preview, .eiq-overview-v3-epi { min-height: 210px; }
.eiq-overview-pixel-v1__runner-board .eiq-overview-v1-table th, .eiq-overview-pixel-v1__runner-board .eiq-overview-v1-table td { height: 34px; }
@media (max-width: 1100px) {
  .eiq-home-pixel-v1__grid, .eiq-home-pixel-v1__lower, .eiq-home-pixel-v1__stats, .eiq-home-pixel-v1__workspace-grid, .eiq-overview-pixel-v1__summary, .eiq-overview-v3-two-up { grid-template-columns: 1fr; }
}
'''
    write(rel, text)


def main() -> None:
    checkpoint()
    patch_home()
    patch_race_file()
    patch_performance_vm()
    patch_performance_component()
    patch_overview()
    patch_css()
    print(f"checkpoint={CHECKPOINT}")
    for rel in FILES:
        print(f"touched={rel}")


if __name__ == "__main__":
    main()
