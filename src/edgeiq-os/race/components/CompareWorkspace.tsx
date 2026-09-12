import { useEffect, useMemo, useState } from "react";
import type { ThreeDayMeeting, ThreeDayRace, ThreeDayRunner } from "../services/threeDayCatalog";
import { canonicalTrackDisplayName, cleanProductText } from "../../design-system/presentation";
import { loadRunnerDetail } from "../services/runnerDetailFeed";

type Props = {
  meeting: ThreeDayMeeting | null;
  selectedRaceKey: string | null;
  onRaceChange: (raceKey: string) => void;
};

type MetricRow = {
  label: string;
  a: unknown;
  b: unknown;
  format?: "price" | "number" | "text";
};

function display(value: unknown, fallback = "-"): string {
  return cleanProductText(value, fallback);
}

function unwrap(value: unknown): unknown {
  if (value && typeof value === "object" && !Array.isArray(value) && "value" in (value as Record<string, unknown>)) {
    return (value as Record<string, unknown>).value;
  }
  return value;
}

function sourceValue(runner: ThreeDayRunner | null, keys: string[]): unknown {
  if (!runner) return null;
  const source = runner.source ?? {};
  for (const key of keys) {
    const raw = unwrap(source[key]);
    if (raw !== null && raw !== undefined && String(raw).trim() !== "") return raw;
  }
  return null;
}

function numeric(value: unknown): number | null {
  const raw = unwrap(value);
  const parsed = Number(String(raw ?? "").replace(/[$,%+]/g, "").trim());
  return Number.isFinite(parsed) ? parsed : null;
}

function price(value: unknown): string {
  const number = numeric(value);
  return number !== null && number > 0 ? `$${number.toFixed(2)}` : display(unwrap(value));
}

function runnerNo(runner: ThreeDayRunner): string {
  return display(runner.official.no ?? runner.official.number);
}

function runnerName(runner: ThreeDayRunner): string {
  return display(runner.official.runner, "Unnamed runner");
}

function runnerKey(runner: ThreeDayRunner, index: number): string {
  return `${runnerNo(runner)}|${runnerName(runner)}|${index}`;
}

function detailPath(runner: ThreeDayRunner): string {
  const value = runner.source?.runnerDetailPath;
  return typeof value === "string" ? value : "";
}

function selectedRace(meeting: ThreeDayMeeting | null, selectedRaceKey: string | null): ThreeDayRace | null {
  if (!meeting?.races.length) return null;
  return meeting.races.find((race) => race.raceKey === selectedRaceKey) ?? meeting.races[0];
}

function valueText(value: unknown, format: MetricRow["format"]): string {
  if (format === "price") return price(value);
  if (format === "number") {
    const number = numeric(value);
    return number === null ? "-" : number.toFixed(2);
  }
  return display(unwrap(value));
}

function diffText(a: unknown, b: unknown): string {
  const left = numeric(a);
  const right = numeric(b);
  if (left === null || right === null) return "-";
  const diff = left - right;
  return `${diff > 0 ? "+" : ""}${diff.toFixed(2)}`;
}

export function CompareWorkspace({ meeting, selectedRaceKey, onRaceChange }: Props) {
  const race = useMemo(() => selectedRace(meeting, selectedRaceKey), [meeting, selectedRaceKey]);
  const [selectionA, setSelectionA] = useState(0);
  const [selectionB, setSelectionB] = useState(1);
  const [runnerA, setRunnerA] = useState<ThreeDayRunner | null>(null);
  const [runnerB, setRunnerB] = useState<ThreeDayRunner | null>(null);

  useEffect(() => {
    setSelectionA(0);
    setSelectionB(race && race.runners.length > 1 ? 1 : 0);
  }, [race?.raceKey]);

  useEffect(() => {
    let active = true;
    const base = race?.runners[selectionA] ?? null;
    if (!base) { setRunnerA(null); return () => { active = false; }; }
    const path = detailPath(base);
    if (!path) { setRunnerA(base); return () => { active = false; }; }
    loadRunnerDetail(path).then((full) => { if (active) setRunnerA(full); }).catch(() => { if (active) setRunnerA(base); });
    return () => { active = false; };
  }, [race, selectionA]);

  useEffect(() => {
    let active = true;
    const base = race?.runners[selectionB] ?? null;
    if (!base) { setRunnerB(null); return () => { active = false; }; }
    const path = detailPath(base);
    if (!path) { setRunnerB(base); return () => { active = false; }; }
    loadRunnerDetail(path).then((full) => { if (active) setRunnerB(full); }).catch(() => { if (active) setRunnerB(base); });
    return () => { active = false; };
  }, [race, selectionB]);

  if (!meeting || !race) return null;

  const metrics: MetricRow[] = [
    { label: "Barrier", a: runnerA?.official.barrier ?? sourceValue(runnerA, ["barrier"]), b: runnerB?.official.barrier ?? sourceValue(runnerB, ["barrier"]), format: "text" },
    { label: "Weight", a: runnerA?.official.weight ?? sourceValue(runnerA, ["weight"]), b: runnerB?.official.weight ?? sourceValue(runnerB, ["weight"]), format: "text" },
    { label: "EPI", a: sourceValue(runnerA, ["epi", "EPI", "epi_rating", "epiRating"]), b: sourceValue(runnerB, ["epi", "EPI", "epi_rating", "epiRating"]), format: "number" },
    { label: "Market", a: runnerA?.official.market ?? sourceValue(runnerA, ["market", "marketPrice", "price"]), b: runnerB?.official.market ?? sourceValue(runnerB, ["market", "marketPrice", "price"]), format: "price" },
    { label: "EDGEiQ Price", a: sourceValue(runnerA, ["edgeiqPrice", "edgeiq_price", "fairPrice", "fair_price"]), b: sourceValue(runnerB, ["edgeiqPrice", "edgeiq_price", "fairPrice", "fair_price"]), format: "price" },
    { label: "Early Speed", a: sourceValue(runnerA, ["earlySpeed", "early_speed"]), b: sourceValue(runnerB, ["earlySpeed", "early_speed"]), format: "number" },
    { label: "Late Speed", a: sourceValue(runnerA, ["lateSpeed", "late_speed"]), b: sourceValue(runnerB, ["lateSpeed", "late_speed"]), format: "number" },
    { label: "Suitability", a: sourceValue(runnerA, ["suitability"]), b: sourceValue(runnerB, ["suitability"]), format: "number" },
    { label: "Form Momentum", a: sourceValue(runnerA, ["formMomentum", "form_momentum"]), b: sourceValue(runnerB, ["formMomentum", "form_momentum"]), format: "number" },
  ];

  return (
    <section className="eiq-build-v1" data-edgeiq-workspace-key="COMPARE">
      <header className="eiq-build-v1__header"><div><p>{canonicalTrackDisplayName(meeting.meeting)} · {display(meeting.date, "")}</p><h1>Compare</h1></div><strong>R{race.raceNumber}</strong></header>
      <nav className="eiq-build-v1__race-tabs" aria-label="Meeting races">
        {meeting.races.map((item) => <button key={item.raceKey} type="button" className={item.raceKey === race.raceKey ? "is-active" : ""} onClick={() => onRaceChange(item.raceKey)}><strong>R{item.raceNumber}</strong><span>{display(item.raceTime)}</span></button>)}
      </nav>
      <div className="eiq-build-v1__grid eiq-build-v1__grid--2">
        <article className="eiq-build-v1__card"><h2>Selection A</h2><select value={selectionA} onChange={(event) => setSelectionA(Number(event.target.value))}>{race.runners.map((runner, index) => <option key={runnerKey(runner,index)} value={index}>{runnerNo(runner)}. {runnerName(runner)}</option>)}</select>{runnerA ? <strong>{runnerName(runnerA)}</strong> : <span className="eiq-build-v1__dash">-</span>}</article>
        <article className="eiq-build-v1__card"><h2>Selection B</h2><select value={selectionB} onChange={(event) => setSelectionB(Number(event.target.value))}>{race.runners.map((runner, index) => <option key={runnerKey(runner,index)} value={index}>{runnerNo(runner)}. {runnerName(runner)}</option>)}</select>{runnerB ? <strong>{runnerName(runnerB)}</strong> : <span className="eiq-build-v1__dash">-</span>}</article>
      </div>
      <section className="eiq-build-v1__card eiq-build-v1__table-card"><header><h2>{display(race.raceName, `Race ${race.raceNumber}`)}</h2></header><table><thead><tr><th>METRIC</th><th>{runnerA ? runnerName(runnerA) : "SELECTION A"}</th><th>{runnerB ? runnerName(runnerB) : "SELECTION B"}</th><th>DIFF.</th></tr></thead><tbody>{metrics.map((metric) => <tr key={metric.label}><td><strong>{metric.label}</strong></td><td>{valueText(metric.a, metric.format)}</td><td>{valueText(metric.b, metric.format)}</td><td>{metric.format === "text" ? "-" : diffText(metric.a, metric.b)}</td></tr>)}</tbody></table></section>
    </section>
  );
}
