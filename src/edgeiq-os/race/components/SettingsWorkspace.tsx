import { useEffect, useMemo, useState } from "react";

type RuntimeIndex = Record<string, unknown>;

type RuntimeState = {
  meetings: RuntimeIndex | null;
  races: RuntimeIndex | null;
  runners: RuntimeIndex | null;
  error: string | null;
  loading: boolean;
};

const initialState: RuntimeState = {
  meetings: null,
  races: null,
  runners: null,
  error: null,
  loading: true,
};

function basePath(path: string): string {
  const base = import.meta.env.BASE_URL || "/";
  return `${base.replace(/\/$/, "")}${path.startsWith("/") ? path : `/${path}`}`;
}

async function loadJson(path: string): Promise<RuntimeIndex> {
  const response = await fetch(`${basePath(path)}?t=${Date.now()}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`${path} ${response.status}`);
  const payload = await response.json();
  return payload && typeof payload === "object" && !Array.isArray(payload) ? payload as RuntimeIndex : {};
}

function arrayCount(value: unknown): number {
  return Array.isArray(value) ? value.length : 0;
}

function numberValue(value: unknown): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function text(value: unknown): string {
  const output = String(value ?? "").trim();
  return output || "-";
}

function pct(value: number, total: number): string {
  if (!total) return "-";
  return `${((value / total) * 100).toFixed(1)}%`;
}

export function SettingsWorkspace() {
  const [state, setState] = useState<RuntimeState>(initialState);

  useEffect(() => {
    let active = true;
    setState(initialState);
    Promise.all([
      loadJson("/data/meetings/index.json"),
      loadJson("/data/races/index.json"),
      loadJson("/data/runners/index.json"),
    ])
      .then(([meetings, races, runners]) => {
        if (!active) return;
        setState({ meetings, races, runners, error: null, loading: false });
      })
      .catch((error) => {
        if (!active) return;
        setState({ meetings: null, races: null, runners: null, error: error instanceof Error ? error.message : "Runtime feed unavailable", loading: false });
      });
    return () => { active = false; };
  }, []);

  const metrics = useMemo(() => {
    const meetingCount = arrayCount(state.meetings?.meetings);
    const raceCount = arrayCount(state.races?.races);
    const runnerCount = arrayCount(state.runners?.runners);
    const enriched = numberValue(state.runners?.enrichedFormMatches);
    const map = numberValue(state.runners?.mapMatches);
    const market = numberValue(state.runners?.marketMatches);
    return { meetingCount, raceCount, runnerCount, enriched, map, market };
  }, [state.meetings, state.races, state.runners]);

  const generatedAt = text(state.runners?.generatedAt ?? state.races?.generatedAt ?? state.meetings?.generatedAt);
  const status = state.loading ? "LOADING" : state.error ? "UNAVAILABLE" : "READY";

  return (
    <section className="eiq-build-v1" data-edgeiq-workspace-key="SETTINGS">
      <header className="eiq-build-v1__header">
        <div><p>EDGEiQ / RACING</p><h1>Settings</h1></div>
        <strong>{status}</strong>
      </header>

      <div className="eiq-build-v1__grid eiq-build-v1__grid--3">
        <article className="eiq-build-v1__card"><h2>Meetings</h2><strong>{state.loading ? "-" : metrics.meetingCount}</strong></article>
        <article className="eiq-build-v1__card"><h2>Races</h2><strong>{state.loading ? "-" : metrics.raceCount}</strong></article>
        <article className="eiq-build-v1__card"><h2>Runners</h2><strong>{state.loading ? "-" : metrics.runnerCount}</strong></article>
      </div>

      <section className="eiq-build-v1__card eiq-build-v1__table-card">
        <header><h2>Runtime Data</h2><strong>{generatedAt}</strong></header>
        <table>
          <thead><tr><th>FEED</th><th>STATUS</th><th>ROWS</th><th>SCHEMA</th></tr></thead>
          <tbody>
            <tr><td>Meeting Detail</td><td>{state.meetings ? "READY" : state.loading ? "-" : "UNAVAILABLE"}</td><td>{state.meetings ? metrics.meetingCount : "-"}</td><td>{text(state.meetings?.schemaVersion)}</td></tr>
            <tr><td>Race Detail</td><td>{state.races ? "READY" : state.loading ? "-" : "UNAVAILABLE"}</td><td>{state.races ? metrics.raceCount : "-"}</td><td>{text(state.races?.schemaVersion)}</td></tr>
            <tr><td>Runner Detail</td><td>{state.runners ? "READY" : state.loading ? "-" : "UNAVAILABLE"}</td><td>{state.runners ? metrics.runnerCount : "-"}</td><td>{text(state.runners?.schemaVersion)}</td></tr>
          </tbody>
        </table>
      </section>

      <section className="eiq-build-v1__card eiq-build-v1__table-card">
        <header><h2>Runner Intelligence Coverage</h2></header>
        <table>
          <thead><tr><th>DATASET</th><th>MATCHED RUNNERS</th><th>COVERAGE</th></tr></thead>
          <tbody>
            <tr><td>EDGEiQ Enriched Form</td><td>{state.runners ? metrics.enriched : "-"}</td><td>{state.runners ? pct(metrics.enriched, metrics.runnerCount) : "-"}</td></tr>
            <tr><td>EDGEiQ Speed Map</td><td>{state.runners ? metrics.map : "-"}</td><td>{state.runners ? pct(metrics.map, metrics.runnerCount) : "-"}</td></tr>
            <tr><td>EDGEiQ Market</td><td>{state.runners ? metrics.market : "-"}</td><td>{state.runners ? pct(metrics.market, metrics.runnerCount) : "-"}</td></tr>
          </tbody>
        </table>
      </section>

      {state.error ? <section className="eiq-build-v1__card"><strong>{state.error}</strong></section> : null}
    </section>
  );
}
