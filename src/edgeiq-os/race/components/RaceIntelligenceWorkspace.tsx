import { useEffect, useMemo, useState } from "react";
import { buildRaceIntelligenceViewModel } from "../services/raceWorkspaceViewModel";
import { findCurrentRaceIntelligenceRace, loadCurrentRaceIntelligenceFeed, type CurrentRaceIntelligenceRace } from "../services/currentRaceIntelligenceFeed";
import type { FormGuideRaceDisplay } from "../services/formGuideNormaliser";
import type { ThreeDayRace } from "../services/threeDayCatalog";
import { canonicalRaceTitleDisplay, canonicalRailDisplay, canonicalTrackDisplayName, canonicalTrackRatingDisplay, canonicalWeatherDisplay, cleanProductText } from "../../design-system/presentation";
import { EiqDataTable } from "../../design-system/v1";

type Props = {
  raceBook: any;
  field: any[];
  formGuide?: FormGuideRaceDisplay | null;
  raceKey?: string | null;
  meetingRaces?: ThreeDayRace[];
  clean: (value: any) => string;
  onBackToMeeting?: () => void;
  onOpenRace?: (race: ThreeDayRace) => void;
  showRaceContext?: boolean;
};

function text(value: unknown, fallback = ""): string {
  return cleanProductText(value, fallback);
}

function firstValue(source: unknown, keys: string[]): unknown {
  if (!source || typeof source !== "object") return undefined;
  for (const key of keys) {
    const value = key.split(".").reduce((acc: any, part) => acc?.[part], source as any);
    if (value !== undefined && value !== null && String(value).trim() !== "") return value;
  }
  return undefined;
}

function money(value: unknown): string {
  const raw = text(value, "").replace(/[$,]/g, "");
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? `$${parsed.toLocaleString("en-AU", { maximumFractionDigits: 0 })}` : "";
}

function formatDate(value: unknown): string {
  const raw = text(value, "");
  if (!raw) return "";
  const date = new Date(`${raw}T00:00:00`);
  return Number.isNaN(date.getTime()) ? raw : new Intl.DateTimeFormat("en-AU", { day: "2-digit", month: "short", year: "numeric" }).format(date);
}

function formatTime(value: unknown): string {
  const raw = text(value, "");
  if (!raw) return "";
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return raw;
  return new Intl.DateTimeFormat("en-AU", { hour: "numeric", minute: "2-digit", hour12: true, timeZone: "Australia/Melbourne" }).format(parsed);
}

function cell(value: unknown, fallback = "-"): string {
  const raw = String(value ?? "").replace(/\s+/g, " ").trim();
  if (/^(Unavailable|Insufficient Runs|Insufficient Evidence|No History|No Current EPR|No Early Evidence)$/i.test(raw)) return raw;
  return text(value, fallback);
}

function epiStatusLabel(value: unknown): string {
  const status = text(value, "");
  return /^available$/i.test(status) ? "" : status;
}

function cardDisplayLabel(label: string): string {
  if (label === "EPF") return "Performance";
  if (label === "TEMPO") return "Tempo";
  if (label === "KEY DETERMINANTS") return "Key Determinants";
  if (label === "HIDDEN ANGLES") return "Hidden Angles";
  return label;
}

function Silk({ src, runner }: { src: string; runner: string }) {
  return src ? <img className="eiq-race-v1__silk" src={src} alt={`${runner} silks`} loading="lazy" onError={(event) => { event.currentTarget.style.display = "none"; }} /> : <span className="eiq-race-v1__silk is-empty" aria-hidden="true" />;
}

export function RaceIntelligenceWorkspace({
  raceBook,
  field,
  formGuide,
  raceKey,
  meetingRaces = [],
  clean,
  onBackToMeeting,
  onOpenRace,
  showRaceContext = true,
}: Props) {
  const [intelligenceRace, setIntelligenceRace] = useState<CurrentRaceIntelligenceRace | null>(null);

  useEffect(() => {
    let cancelled = false;
    loadCurrentRaceIntelligenceFeed()
      .then((payload) => {
        if (!cancelled) setIntelligenceRace(findCurrentRaceIntelligenceRace(payload, raceKey));
      })
      .catch((error) => {
        if (!cancelled) {
          console.warn("Current race intelligence feed not loaded", error);
          setIntelligenceRace(null);
        }
      });
    return () => { cancelled = true; };
  }, [raceKey]);

  const model = useMemo(() => buildRaceIntelligenceViewModel({ raceBook, field, formGuide, intelligenceRace }), [raceBook, field, formGuide, intelligenceRace]);
  const official = raceBook?.official ?? {};
  const source = raceBook?.source ?? {};
  const meeting = canonicalTrackDisplayName(clean(official.meeting));
  const raceNo = clean(official.raceNumber);
  const raceName = canonicalRaceTitleDisplay(clean(official.raceName) || clean(firstValue(source, ["raceName", "name"])) || `Race ${raceNo}`);
  const raceClass = clean(official.raceClass) || clean(firstValue(source, ["raceClass", "class"]));
  const distance = clean(official.distance) || clean(firstValue(source, ["distance"]));
  const track = canonicalTrackRatingDisplay(official.trackCondition || firstValue(source, ["trackCondition", "condition", "conditions"]), "Track Rating Awaiting");
  const rail = canonicalRailDisplay(official.rail || firstValue(source, ["rail", "railPosition"]), "Rail Not Supplied");
  const time = formatTime(official.raceTime || official.officialRaceTime || firstValue(source, ["raceTime", "time"])) || "Time Not Published";
  const date = formatDate(official.date || official.meetingDate || firstValue(source, ["date", "raceDate"])) || "Date Not Published";
  const prize = money(firstValue(source, ["prizeMoney", "prizemoney", "totalPrizeMoney"]) ?? official.prizeMoney) || "Prizemoney Not Published";
  const weather = canonicalWeatherDisplay(firstValue(source, ["weather", "weatherCondition", "forecast"]), "Weather Awaiting Feed");
  const status = clean(firstValue(official, ["status"]) ?? firstValue(source, ["status"])) || "Active";
  const selectedRaceKey = text(raceKey, "");
  const races = [...meetingRaces].sort((a, b) => Number(a.raceNumber) - Number(b.raceNumber));
  const visibleWhatMatters = model.whatMatters.slice(0, 5);
  const hasSpeedMapEvidence = model.speedMap.some((zone) => zone.runners.length);
  const metadata = [["MEETING", meeting || "Meeting Not Published"], ["DATE", date], ["TIME", time], ["DISTANCE", distance || "Distance Not Published"], ["TRACK", track], ["RAIL", rail], ["WEATHER", weather], ["PRIZEMONEY", prize]];

  return (
    <section className={showRaceContext ? "eiq-race-v1" : "eiq-race-v1 eiq-race-v1--framed"} aria-label="Race overview" data-edgeiq-race-workspace-v1="repair-v1">
      <div className="eiq-race-v1__breadcrumb" aria-label="Race breadcrumb">
        <button type="button" onClick={onBackToMeeting}>MEETINGS</button><span aria-hidden="true">&gt;</span><strong>{meeting || "MEETING"}</strong><span aria-hidden="true">&gt;</span><strong>RACE {raceNo || "-"}</strong><span aria-hidden="true">&gt;</span><strong>RACE</strong>
      </div>
      <header className="eiq-race-v1__identity">
        <div><h1><span>Race {raceNo || "-"}</span> {raceName}</h1>{raceClass ? <span className="eiq-race-v1__class-badge">{raceClass}</span> : null}</div>
        <button type="button" className="eiq-approved-button" onClick={onBackToMeeting}>Back to Races</button>
      </header>
      <dl className="eiq-race-v1__metadata" aria-label="Race metadata">{metadata.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
      {races.length ? <section className="eiq-race-v1__selector" aria-label="Races at this meeting"><span>RACES AT THIS MEETING</span><div>{races.map((race) => {
        const isSelected = String(race.raceKey) === selectedRaceKey;
        return <button key={race.raceKey} type="button" className={isSelected ? "is-active" : ""} aria-current={isSelected ? "true" : undefined} onClick={() => onOpenRace?.(race)}><strong>R{race.raceNumber}</strong><small>{formatTime(race.raceTime) || "Time Not Published"}</small></button>;
      })}</div></section> : null}
      <section className="eiq-race-v1__summary" aria-label="Race intelligence summary">{model.cards.map((card) => <article key={card.label} className="eiq-race-v1__summary-card"><span>{cardDisplayLabel(card.label)}</span><strong>{card.value}</strong><p>{card.detail}</p></article>)}</section>
      <section className="eiq-race-v1__matters" aria-label="What matters today"><header><h2>What Matters Today</h2><span>{`${visibleWhatMatters.length} active`}</span></header><div>{visibleWhatMatters.length ? visibleWhatMatters.map((item, index) => <p key={`${item}-${index}`}><span aria-hidden="true" />{item}</p>) : <p><span aria-hidden="true" />Insufficient governed race statements for this race.</p>}</div></section>
      <section className="eiq-race-v1__midrow">
        <article className={`eiq-race-v1__speed ${hasSpeedMapEvidence ? "is-populated" : "is-empty-state"}`} aria-label="Speed map preview"><header><h2>Speed Map Preview</h2><span>Travel Right to Left</span></header>{hasSpeedMapEvidence ? <div className="eiq-race-v1__speed-grid">{model.speedMap.map((zone) => <div key={zone.zone} className="eiq-race-v1__speed-zone"><strong>{zone.zone}</strong><div>{zone.runners.length ? zone.runners.slice(0, 5).map((runner) => <span key={`${zone.zone}-${runner.no}-${runner.runner}`}><b>{runner.no}</b>{runner.runner}{runner.earlySpeed ? <em>{runner.earlySpeed}</em> : null}</span>) : <small>Awaiting Speed Evidence</small>}</div></div>)}</div> : <div className="eiq-race-v1__empty">Awaiting Speed Evidence</div>}</article>
      <article className="eiq-race-v1__epi" aria-label="EPR top 3"><header><h2>EPR Top 3</h2><span>{model.topEpi.length ? "Governed EPR" : "Insufficient Evidence"}</span></header><div>{[0, 1, 2].map((index) => {
          const row = model.topEpi[index];
          const statusLabel = row ? epiStatusLabel(row.status) : "";
          return row ? <div key={`${row.no}-${row.runner}`} className={`eiq-race-v1__epi-row ${statusLabel ? "has-status" : "is-normal"}`}><b>{index + 1}</b><span>{row.no}</span><strong>{row.runner}</strong><em>{row.value}</em><small>{statusLabel}</small></div> : <div key={`empty-epi-${index}`} className="eiq-race-v1__epi-row is-empty"><b>{index + 1}</b><span>-</span><strong>Insufficient Evidence</strong><em>-</em><small>Awaiting EPR</small></div>;
        })}</div></article>
      </section>
      <section className="eiq-race-v1__board" aria-label="Runner board"><header><h2>Runner Board</h2><span>{model.runnerBoard.length ? `${model.runnerBoard.length} runners` : "Field Not Published"}</span></header><EiqDataTable density="compact" className="eiq-race-v1__table" wrapperProps={{ className: "eiq-race-v1__table-wrap" }}><colgroup><col className="col-no" /><col className="col-silk" /><col className="col-runner" /><col className="col-bar" /><col className="col-wgt" /><col className="col-jockey" /><col className="col-trainer" /><col className="col-epi" /><col className="col-speed" /><col className="col-edgeiq" /><col className="col-market" /><col className="col-status" /></colgroup><thead><tr><th>NO</th><th>SILK</th><th className="is-left">RUNNER</th><th>BAR</th><th>WGT</th><th className="is-left">JOCKEY</th><th className="is-left">TRAINER</th><th>EPR</th><th>SPD</th><th>EDGEiQ PRICE</th><th>MARKET</th><th>STATUS</th></tr></thead><tbody>{model.runnerBoard.length ? model.runnerBoard.map((runner) => <tr key={`${runner.no}-${runner.runner}`} className={runner.scratched ? "is-scratched" : ""}><td>{cell(runner.no)}</td><td><Silk src={runner.silkUrl} runner={runner.runner} /></td><td className="is-left"><strong>{cell(runner.runner)}</strong></td><td>{cell(runner.barrier)}</td><td>{cell(runner.weight)}</td><td className="is-left">{cell(runner.jockey)}</td><td className="is-left">{cell(runner.trainer)}</td><td>{runner.scratched ? "-" : cell(runner.epi)}</td><td>{runner.scratched ? "-" : cell(runner.earlySpeed)}</td><td>{runner.scratched ? "-" : cell(runner.edgeiqPrice)}</td><td>{runner.scratched ? "Scratched" : cell(runner.market, "Awaiting Market")}</td><td><span className="eiq-race-v1__status">{runner.status}</span></td></tr>) : <tr><td colSpan={12}>Field Not Published</td></tr>}</tbody></EiqDataTable></section>
    </section>
  );
}
