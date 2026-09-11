import { useEffect, useMemo, useState } from "react";
import { buildRaceIntelligenceViewModel } from "../services/raceWorkspaceViewModel";
import { findCurrentRaceIntelligenceRace, loadCurrentRaceIntelligenceFeed, type CurrentRaceIntelligenceRace } from "../services/currentRaceIntelligenceFeed";
import type { FormGuideRaceDisplay } from "../services/formGuideNormaliser";
import type { ThreeDayRace } from "../services/threeDayCatalog";
import { cleanProductText } from "../../design-system/presentation";

type Props = {
  raceBook: any;
  field: any[];
  formGuide?: FormGuideRaceDisplay | null;
  raceKey?: string | null;
  meetingRaces?: ThreeDayRace[];
  clean: (value: any) => string;
  onBackToMeeting?: () => void;
  onOpenRace?: (race: ThreeDayRace) => void;
  onOpenRunner?: (index: number) => void;
};

function text(value: unknown, fallback = ""): string { return cleanProductText(value, fallback); }
function formatTime(value: unknown): string {
  const raw = text(value, "");
  if (!raw) return "";
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return raw;
  return new Intl.DateTimeFormat("en-AU", { hour: "numeric", minute: "2-digit", hour12: true, timeZone: "Australia/Melbourne" }).format(parsed);
}
function cell(value: unknown, fallback = "-"): string { return text(value, fallback); }
function epiStatusLabel(value: unknown): string { const status = text(value, ""); return /^available$/i.test(status) ? "" : status; }
function Silk({ src, runner }: { src: string; runner: string }) {
  return src ? <img className="eiq-race-v1__silk" src={src} alt={`${runner} silks`} loading="lazy" onError={(event) => { event.currentTarget.style.display = "none"; }} /> : <span className="eiq-race-v1__silk is-empty" aria-hidden="true" />;
}

export function RaceIntelligenceWorkspace({ raceBook, field, formGuide, raceKey, meetingRaces = [], onOpenRace, onOpenRunner }: Props) {
  const [intelligenceRace, setIntelligenceRace] = useState<CurrentRaceIntelligenceRace | null>(null);

  useEffect(() => {
    let cancelled = false;
    loadCurrentRaceIntelligenceFeed()
      .then((payload) => { if (!cancelled) setIntelligenceRace(findCurrentRaceIntelligenceRace(payload, raceKey)); })
      .catch((error) => {
        if (!cancelled) {
          console.warn("Current race intelligence feed not loaded", error);
          setIntelligenceRace(null);
        }
      });
    return () => { cancelled = true; };
  }, [raceKey]);

  const model = useMemo(
    () => buildRaceIntelligenceViewModel({ raceBook, field, formGuide, intelligenceRace }),
    [raceBook, field, formGuide, intelligenceRace],
  );
  const selectedRaceKey = text(raceKey, "");
  const races = [...meetingRaces].sort((a, b) => Number(a.raceNumber) - Number(b.raceNumber));
  const visibleWhatMatters = model.whatMatters.slice(0, 5);
  const hasSpeedMapEvidence = model.speedMap.some((zone) => zone.runners.length);

  return (
    <section className="eiq-race-v1" aria-label="Race command" data-edgeiq-race-workspace-v1="command-v3">
      {races.length ? (
        <section className="eiq-race-v1__selector" aria-label="Races at this meeting">
          <span>Races at this meeting</span>
          <div>
            {races.map((race) => {
              const isSelected = String(race.raceKey) === selectedRaceKey;
              return (
                <button key={race.raceKey} type="button" className={isSelected ? "is-active" : ""} aria-current={isSelected ? "true" : undefined} onClick={() => onOpenRace?.(race)}>
                  <strong>R{race.raceNumber}</strong>
                  <small>{formatTime(race.raceTime) || "Time Not Published"}</small>
                </button>
              );
            })}
          </div>
        </section>
      ) : null}

      <section className="eiq-race-v1__summary" aria-label="Race intelligence summary">
        {model.cards.map((card) => (
          <article key={card.label} className="eiq-race-v1__summary-card">
            <span>{card.label}</span>
            <strong>{card.value}</strong>
            <p>{card.detail}</p>
          </article>
        ))}
      </section>

      <section className="eiq-race-v1__matters" aria-label="Decision snapshot">
        <header><h2>Decision Snapshot</h2><span>Pre-race command view</span></header>
        <div>{model.marketSnapshot.map((item) => <p key={item.label}><span aria-hidden="true" /><strong>{item.label}:</strong> {item.value}</p>)}</div>
      </section>

      <section className="eiq-race-v1__matters" aria-label="What matters today">
        <header><h2>What Matters Today</h2><span>{`${visibleWhatMatters.length} active`}</span></header>
        <div>
          {visibleWhatMatters.length
            ? visibleWhatMatters.map((item, index) => <p key={`${item}-${index}`}><span aria-hidden="true" />{item}</p>)
            : <p><span aria-hidden="true" />Insufficient governed race statements for this race.</p>}
        </div>
      </section>

      <section className="eiq-race-v1__midrow">
        <article className={`eiq-race-v1__speed ${hasSpeedMapEvidence ? "is-populated" : "is-empty-state"}`} aria-label="Speed map preview">
          <header><h2>Speed Map Preview</h2><span>{hasSpeedMapEvidence ? "Governed current early speed" : "Current early-speed evidence not supplied"}</span></header>
          {hasSpeedMapEvidence ? (
            <div className="eiq-race-v1__speed-grid">
              {model.speedMap.map((zone) => (
                <div key={zone.zone} className="eiq-race-v1__speed-zone">
                  <strong>{zone.zone}</strong>
                  <div>{zone.runners.slice(0, 5).map((runner) => <span key={`${zone.zone}-${runner.no}-${runner.runner}`}><b>{runner.no}</b>{runner.runner}{runner.earlySpeed ? <em>{runner.earlySpeed}</em> : null}</span>)}</div>
                </div>
              ))}
            </div>
          ) : <div className="eiq-race-v1__empty">Current early-speed evidence not supplied</div>}
        </article>

        <article className="eiq-race-v1__epi" aria-label="EPI top 3">
          <header><h2>EPI Top 3</h2><span>{model.topEpr.length ? "Governed EPI" : "Insufficient Evidence"}</span></header>
          <div>
            {[0, 1, 2].map((index) => {
              const row = model.topEpr[index];
              const statusLabel = row ? epiStatusLabel(row.status) : "";
              return row ? (
                <div key={`${row.no}-${row.runner}`} className={`eiq-race-v1__epi-row ${statusLabel ? "has-status" : "is-normal"}`}>
                  <b>{index + 1}</b><span>{row.no}</span><strong>{row.runner}</strong><em>{row.value}</em><small>{statusLabel}</small>
                </div>
              ) : (
                <div key={`empty-epi-${index}`} className="eiq-race-v1__epi-row is-empty">
                  <b>{index + 1}</b><span>-</span><strong>Insufficient Evidence</strong><em>-</em><small>Awaiting EPI</small>
                </div>
              );
            })}
          </div>
        </article>
      </section>

      <section className="eiq-race-v1__board" aria-label="Runner board">
        <header><h2>Runner Board</h2><span>{model.runnerBoard.length ? `${model.runnerBoard.length} runners · select a runner for deep form` : "Field Not Published"}</span></header>
        <div className="eiq-race-v1__table-wrap">
          <table className="eiq-race-v1__table">
            <colgroup><col className="col-no" /><col className="col-silk" /><col className="col-runner" /><col className="col-bar" /><col className="col-wgt" /><col className="col-jockey" /><col className="col-trainer" /><col className="col-epi" /><col className="col-speed" /><col className="col-edgeiq" /><col className="col-market" /><col className="col-status" /></colgroup>
            <thead><tr><th>NO</th><th>SILK</th><th className="is-left">RUNNER</th><th>BAR</th><th>WGT</th><th className="is-left">JOCKEY</th><th className="is-left">TRAINER</th><th>EPI</th><th>SPD</th><th>EDGEiQ PRICE</th><th>MARKET</th><th>STATUS</th></tr></thead>
            <tbody>
              {model.runnerBoard.length ? model.runnerBoard.map((runner, index) => (
                <tr key={`${runner.no}-${runner.runner}`} className={runner.scratched ? "is-scratched" : ""} role={runner.scratched ? undefined : "button"} tabIndex={runner.scratched ? undefined : 0} aria-label={runner.scratched ? undefined : `Open ${runner.runner} runner profile`} onClick={() => { if (!runner.scratched) onOpenRunner?.(index); }} onKeyDown={(event) => { if (!runner.scratched && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); onOpenRunner?.(index); } }}>
                  <td>{cell(runner.no)}</td><td><Silk src={runner.silkUrl} runner={runner.runner} /></td><td className="is-left"><strong>{cell(runner.runner)}</strong></td><td>{cell(runner.barrier)}</td><td>{cell(runner.weight)}</td><td className="is-left">{cell(runner.jockey)}</td><td className="is-left">{cell(runner.trainer)}</td><td>{runner.scratched ? "-" : cell(runner.epr)}</td><td>{runner.scratched ? "-" : cell(runner.earlySpeed)}</td><td>{runner.scratched ? "-" : cell(runner.edgeiqPrice)}</td><td>{runner.scratched ? "Scratched" : cell(runner.market)}</td><td><span className="eiq-race-v1__status">{runner.status}</span></td>
                </tr>
              )) : <tr><td colSpan={12}>Field Not Published</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
