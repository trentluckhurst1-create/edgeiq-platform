import { useEffect, useMemo, useState } from "react";
import type { ThreeDayMeeting, ThreeDayRace, ThreeDayRunner } from "../services/threeDayCatalog";
import { canonicalTrackDisplayName, cleanProductText } from "../../design-system/presentation";
import { buildInsightsViewModel, loadInsightsTerminalFeed, type BETA012ViewModel } from "../services/insightsFeed";
import { buildMeetingResultsViewModel, loadResultsTerminalFeed, type MeetingResultsViewModel } from "../services/resultsFeed";
import { loadRunnerDetail } from "../services/runnerDetailFeed";

type RaceWorkspaceProps = {
  meeting: ThreeDayMeeting | null;
  selectedRaceKey: string | null;
  onRaceChange: (raceKey: string) => void;
};

function display(value: unknown, fallback = "-"): string {
  return cleanProductText(value, fallback);
}

function useSelectedRace(meeting: ThreeDayMeeting | null, selectedRaceKey: string | null): ThreeDayRace | null {
  return useMemo(() => {
    if (!meeting?.races.length) return null;
    return meeting.races.find((race) => race.raceKey === selectedRaceKey) ?? meeting.races[0];
  }, [meeting, selectedRaceKey]);
}

function RaceTabs({ meeting, race, onRaceChange }: { meeting: ThreeDayMeeting; race: ThreeDayRace; onRaceChange: (raceKey: string) => void }) {
  return (
    <nav className="eiq-build-v1__race-tabs" aria-label="Meeting races">
      {meeting.races.map((item) => (
        <button key={item.raceKey} type="button" className={item.raceKey === race.raceKey ? "is-active" : ""} onClick={() => onRaceChange(item.raceKey)}>
          <strong>R{item.raceNumber}</strong><span>{display(item.raceTime)}</span>
        </button>
      ))}
    </nav>
  );
}

function RaceHeader({ title, meeting, race }: { title: string; meeting: ThreeDayMeeting; race: ThreeDayRace }) {
  return (
    <header className="eiq-build-v1__header">
      <div><p>{canonicalTrackDisplayName(meeting.meeting)} · {display(meeting.date, "")}</p><h1>{title}</h1></div>
      <strong>R{race.raceNumber}</strong>
    </header>
  );
}

function EmptyCell() { return <span className="eiq-build-v1__dash">-</span>; }

function unwrap(value: unknown): unknown {
  if (value && typeof value === "object" && !Array.isArray(value) && "value" in (value as Record<string, unknown>)) {
    return (value as Record<string, unknown>).value;
  }
  return value;
}

function numberValue(value: unknown): number | null {
  const raw = unwrap(value);
  const parsed = Number(String(raw ?? "").replace(/[$,%+]/g, "").trim());
  return Number.isFinite(parsed) ? parsed : null;
}

function sourceValue(runner: ThreeDayRunner, keys: string[]): unknown {
  const source = runner.source ?? {};
  for (const key of keys) {
    const value = source[key];
    const unwrapped = unwrap(value);
    if (unwrapped !== null && unwrapped !== undefined && String(unwrapped).trim() !== "") return unwrapped;
  }
  return null;
}

function runnerNumber(runner: ThreeDayRunner): string {
  return display(runner.official.no ?? runner.official.number);
}

function runnerName(runner: ThreeDayRunner): string {
  return display(runner.official.runner, "Unnamed runner");
}

function runnerDetailPath(runner: ThreeDayRunner): string {
  const value = runner.source?.runnerDetailPath;
  return typeof value === "string" ? value : "";
}

function priceText(value: unknown): string {
  const raw = unwrap(value);
  const numeric = Number(String(raw ?? "").replace("$", "").trim());
  return Number.isFinite(numeric) && numeric > 0 ? `$${numeric.toFixed(2)}` : display(raw);
}

export function InsightsWorkspace({ meeting, selectedRaceKey, onRaceChange }: RaceWorkspaceProps) {
  const race = useSelectedRace(meeting, selectedRaceKey);
  const [model, setModel] = useState<BETA012ViewModel | null>(null);

  useEffect(() => {
    let active = true;
    if (!meeting || !race) { setModel(null); return () => { active = false; }; }
    loadInsightsTerminalFeed()
      .then((rows) => { if (active) setModel(buildInsightsViewModel(race.raceKey, rows, meeting.meetingKey)); })
      .catch(() => { if (active) setModel(null); });
    return () => { active = false; };
  }, [meeting, race]);

  if (!meeting || !race) return null;
  const cards = model?.cards ?? [];
  const rows = model?.rows ?? [];
  return (
    <section className="eiq-build-v1" data-edgeiq-workspace-key="INSIGHTS">
      <RaceHeader title="Insights" meeting={meeting} race={race} />
      <RaceTabs meeting={meeting} race={race} onRaceChange={onRaceChange} />
      <div className="eiq-build-v1__grid eiq-build-v1__grid--2">
        {(cards.length ? cards.slice(0, 4) : [null, null, null, null]).map((card, index) => (
          <article className="eiq-build-v1__card" key={card?.cardType ?? index}>
            <h2>{card?.title ?? ["Key Angles", "Race Shape", "Price & Edge", "Risk Flags"][index]}</h2>
            {card?.value ? <strong>{card.value}</strong> : <EmptyCell />}
            {card?.detail ? <small>{card.detail}</small> : null}
          </article>
        ))}
      </div>
      <section className="eiq-build-v1__card eiq-build-v1__table-card">
        <header><h2>{display(race.raceName, `Race ${race.raceNumber}`)}</h2></header>
        <table><thead><tr><th>NO.</th><th>RUNNER</th><th>INSIGHT</th><th>EDGE</th><th>CONF.</th><th>COVERAGE</th></tr></thead>
          <tbody>{rows.length ? rows.map((row, index) => <tr key={`${row.no}-${row.horse}-${index}`}><td>{display(row.no)}</td><td><strong>{display(row.horse)}</strong></td><td>{display(row.key_insight)}</td><td>{display(row.edge)}</td><td>{display(row.confidence)}</td><td>{display(row.coverage)}</td></tr>) : <tr><td colSpan={6} className="eiq-build-v1__empty">-</td></tr>}</tbody>
        </table>
      </section>
    </section>
  );
}

export function ResultsWorkspace({ meeting, selectedRaceKey, onRaceChange }: RaceWorkspaceProps) {
  const race = useSelectedRace(meeting, selectedRaceKey);
  const [model, setModel] = useState<MeetingResultsViewModel | null>(null);

  useEffect(() => {
    let active = true;
    if (!meeting) { setModel(null); return () => { active = false; }; }
    loadResultsTerminalFeed()
      .then((rows) => { if (active) setModel(buildMeetingResultsViewModel(meeting, rows)); })
      .catch(() => { if (active) setModel(null); });
    return () => { active = false; };
  }, [meeting]);

  if (!meeting || !race) return null;
  const result = model?.rows.find((row) => row.raceKey === race.raceKey) ?? null;
  return (
    <section className="eiq-build-v1" data-edgeiq-workspace-key="RESULTS">
      <RaceHeader title="Results" meeting={meeting} race={race} />
      <RaceTabs meeting={meeting} race={race} onRaceChange={onRaceChange} />
      <section className="eiq-build-v1__card eiq-build-v1__table-card"><header><h2>{display(race.raceName, `Race ${race.raceNumber}`)}</h2><strong>{display(result?.status)}</strong></header>
        <table><thead><tr><th>POS.</th><th>RUNNER</th><th>JOCKEY</th><th>TRAINER</th><th>SP</th><th>MARGIN</th><th>TIME</th></tr></thead>
          <tbody>{result?.winner ? <tr><td>1</td><td><strong>{display(result.winner)}</strong></td><td>{display(result.jockey)}</td><td>{display(result.trainer)}</td><td>{display(result.spTab)}</td><td>{display(result.margin)}</td><td>{display(result.time)}</td></tr> : <tr><td colSpan={7} className="eiq-build-v1__empty">-</td></tr>}</tbody>
        </table>
      </section>
    </section>
  );
}

type ReviewRunner = { runner: ThreeDayRunner; epi: number | null; market: number | null; fair: number | null };

export function ReviewWorkspace({ meeting, selectedRaceKey, onRaceChange }: RaceWorkspaceProps) {
  const race = useSelectedRace(meeting, selectedRaceKey);
  const [rows, setRows] = useState<ReviewRunner[]>([]);
  const [results, setResults] = useState<MeetingResultsViewModel | null>(null);

  useEffect(() => {
    let active = true;
    if (!race) { setRows([]); return () => { active = false; }; }
    Promise.all(race.runners.map(async (runner) => {
      let full = runner;
      const path = runnerDetailPath(runner);
      if (path) { try { full = await loadRunnerDetail(path); } catch { full = runner; } }
      return {
        runner: full,
        epi: numberValue(sourceValue(full, ["epi", "EPI", "epi_rating", "epiRating"])),
        market: numberValue(full.official.market ?? sourceValue(full, ["market", "marketPrice", "price"])),
        fair: numberValue(sourceValue(full, ["edgeiqPrice", "edgeiq_price", "fairPrice", "fair_price"])),
      } satisfies ReviewRunner;
    })).then((next) => { if (active) setRows(next); });
    return () => { active = false; };
  }, [race]);

  useEffect(() => {
    let active = true;
    if (!meeting) { setResults(null); return () => { active = false; }; }
    loadResultsTerminalFeed().then((feed) => { if (active) setResults(buildMeetingResultsViewModel(meeting, feed)); }).catch(() => { if (active) setResults(null); });
    return () => { active = false; };
  }, [meeting]);

  if (!meeting || !race) return null;
  const result = results?.rows.find((row) => row.raceKey === race.raceKey) ?? null;
  const epiLeader = rows.filter((row) => row.epi !== null).sort((a, b) => (b.epi ?? -Infinity) - (a.epi ?? -Infinity))[0];
  const favourite = rows.filter((row) => row.market !== null && (row.market ?? 0) > 0).sort((a, b) => (a.market ?? Infinity) - (b.market ?? Infinity))[0];
  const fairLeader = rows.filter((row) => row.fair !== null && (row.fair ?? 0) > 0).sort((a, b) => (a.fair ?? Infinity) - (b.fair ?? Infinity))[0];

  return (
    <section className="eiq-build-v1" data-edgeiq-workspace-key="REVIEW">
      <RaceHeader title="Review" meeting={meeting} race={race} />
      <RaceTabs meeting={meeting} race={race} onRaceChange={onRaceChange} />
      <div className="eiq-build-v1__grid eiq-build-v1__grid--2">
        <article className="eiq-build-v1__card"><h2>Winner</h2>{result?.winner ? <strong>{result.winner}</strong> : <EmptyCell />}</article>
        <article className="eiq-build-v1__card"><h2>EPI Leader</h2>{epiLeader ? <strong>{runnerName(epiLeader.runner)} · {epiLeader.epi?.toFixed(2)}</strong> : <EmptyCell />}</article>
        <article className="eiq-build-v1__card"><h2>Market Favourite</h2>{favourite ? <strong>{runnerName(favourite.runner)} · {priceText(favourite.market)}</strong> : <EmptyCell />}</article>
        <article className="eiq-build-v1__card"><h2>EDGEiQ Favourite</h2>{fairLeader ? <strong>{runnerName(fairLeader.runner)} · {priceText(fairLeader.fair)}</strong> : <EmptyCell />}</article>
      </div>
      <section className="eiq-build-v1__card eiq-build-v1__table-card"><header><h2>{display(race.raceName, `Race ${race.raceNumber}`)}</h2></header>
        <table><thead><tr><th>NO.</th><th>RUNNER</th><th>EPI</th><th>MARKET</th><th>FAIR</th><th>EARLY</th><th>LATE</th><th>SUIT.</th><th>MOMENTUM</th></tr></thead>
          <tbody>{rows.length ? rows.map((row, index) => <tr key={`${runnerNumber(row.runner)}-${runnerName(row.runner)}-${index}`}><td>{runnerNumber(row.runner)}</td><td><strong>{runnerName(row.runner)}</strong></td><td>{row.epi === null ? "-" : row.epi.toFixed(2)}</td><td>{row.market === null ? "-" : priceText(row.market)}</td><td>{row.fair === null ? "-" : priceText(row.fair)}</td><td>{display(sourceValue(row.runner,["earlySpeed","early_speed"]))}</td><td>{display(sourceValue(row.runner,["lateSpeed","late_speed"]))}</td><td>{display(sourceValue(row.runner,["suitability"]))}</td><td>{display(sourceValue(row.runner,["formMomentum","form_momentum"]))}</td></tr>) : <tr><td colSpan={9} className="eiq-build-v1__empty">-</td></tr>}</tbody>
        </table>
      </section>
    </section>
  );
}

export function ResearchLabWorkspace() {
  return (
    <section className="eiq-build-v1" data-edgeiq-workspace-key="RESEARCH-LAB">
      <header className="eiq-build-v1__header"><div><p>EDGEiQ / RACING</p><h1>Research Lab</h1></div></header>
      <div className="eiq-build-v1__grid eiq-build-v1__grid--3">
        {["Dataset","Experiment","Model"].map((title) => <article className="eiq-build-v1__card" key={title}><h2>{title}</h2><EmptyCell /></article>)}
      </div>
      <section className="eiq-build-v1__card eiq-build-v1__table-card"><header><h2>Experiment Queue</h2></header><table><thead><tr><th>ID</th><th>EXPERIMENT</th><th>SCOPE</th><th>STATUS</th><th>RESULT</th></tr></thead><tbody><tr><td colSpan={5} className="eiq-build-v1__empty">-</td></tr></tbody></table></section>
    </section>
  );
}

export function CompareWorkspace() {
  return (
    <section className="eiq-build-v1" data-edgeiq-workspace-key="COMPARE">
      <header className="eiq-build-v1__header"><div><p>EDGEiQ / RACING</p><h1>Compare</h1></div></header>
      <div className="eiq-build-v1__grid eiq-build-v1__grid--2"><article className="eiq-build-v1__card"><h2>Selection A</h2><EmptyCell /></article><article className="eiq-build-v1__card"><h2>Selection B</h2><EmptyCell /></article></div>
      <section className="eiq-build-v1__card eiq-build-v1__table-card"><header><h2>Comparison Matrix</h2></header><table><thead><tr><th>METRIC</th><th>SELECTION A</th><th>SELECTION B</th><th>DIFF.</th></tr></thead><tbody><tr><td colSpan={4} className="eiq-build-v1__empty">-</td></tr></tbody></table></section>
    </section>
  );
}

export function SettingsWorkspace() {
  return (
    <section className="eiq-build-v1" data-edgeiq-workspace-key="SETTINGS">
      <header className="eiq-build-v1__header"><div><p>EDGEiQ / RACING</p><h1>Settings</h1></div></header>
      <div className="eiq-build-v1__grid eiq-build-v1__grid--2">
        {["Data Feeds","Display","Race Defaults","Workspace"].map((title) => <article className="eiq-build-v1__card eiq-build-v1__settings-card" key={title}><h2>{title}</h2><dl><div><dt>Status</dt><dd>-</dd></div><div><dt>Default</dt><dd>-</dd></div></dl></article>)}
      </div>
    </section>
  );
}
