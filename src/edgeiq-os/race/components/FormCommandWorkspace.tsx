import { useMemo } from "react";
import type { FormGuideRaceDisplay, FormGuideRunnerDisplay } from "../services/formGuideNormaliser";

type Props = {
  formGuide: FormGuideRaceDisplay | null;
  onOpenRunner: (index: number) => void;
};

function value(value: unknown, fallback = "-"): string {
  const text = String(value ?? "").trim();
  return text && !/^(none|null|undefined|nan|not available|unavailable)$/i.test(text) ? text : fallback;
}

function numeric(value: unknown): number | null {
  const text = String(value ?? "").replace(/[$,%+,]/g, "").trim();
  if (!text) return null;
  const parsed = Number(text);
  return Number.isFinite(parsed) ? parsed : null;
}

function priceDelta(runner: FormGuideRunnerDisplay): string {
  const market = numeric(runner.marketPrice);
  const fair = numeric(runner.edgeiqPrice);
  if (market === null || fair === null || fair <= 0) return "-";
  const edge = ((market - fair) / fair) * 100;
  return `${edge > 0 ? "+" : ""}${edge.toFixed(1)}%`;
}

function momentumLabel(runner: FormGuideRunnerDisplay): string {
  if (runner.formMomentumDirection === "up") return "Rising";
  if (runner.formMomentumDirection === "down") return "Easing";
  const text = value(runner.formMomentum, "Stable").toLowerCase();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function lastRunText(runner: FormGuideRunnerDisplay): string {
  const run = runner.recentRuns[0];
  if (!run) return "No previous start";
  const parts = [run.track, run.distance, run.position ? `${run.position}/${run.fieldSize || "-"}` : "", run.epi ? `EPI ${run.epi}` : ""].filter(Boolean);
  return parts.join(" · ");
}

function bestFit(runner: FormGuideRunnerDisplay): string {
  const matches = [
    ...runner.careerProfile,
    ...runner.conditionProfile,
    ...runner.classProfile,
    ...runner.jockeyProfile,
    ...runner.raceDayPattern,
  ].filter((line) => line.matchesToday && line.record);
  return matches.slice(0, 2).map((line) => `${line.label} ${line.record}`).join(" · ") || value(runner.suitabilityLabel, "No governed fit signal");
}

function sortedRunners(runners: FormGuideRunnerDisplay[]): FormGuideRunnerDisplay[] {
  return [...runners].sort((a, b) => {
    if (a.scratched !== b.scratched) return a.scratched ? 1 : -1;
    const aEpi = numeric(a.epi) ?? -Infinity;
    const bEpi = numeric(b.epi) ?? -Infinity;
    if (aEpi !== bEpi) return bEpi - aEpi;
    return a.sortNo - b.sortNo;
  });
}

export function FormCommandWorkspace({ formGuide, onOpenRunner }: Props) {
  const runners = useMemo(() => sortedRunners(formGuide?.runners ?? []), [formGuide]);
  const active = runners.filter((runner) => !runner.scratched);
  const topEpi = active.find((runner) => numeric(runner.epi) !== null) ?? null;
  const rising = active.filter((runner) => runner.formMomentumDirection === "up").length;
  const priced = active.filter((runner) => numeric(runner.edgeiqPrice) !== null).length;
  const strongFit = active.filter((runner) => {
    const score = numeric(runner.suitabilityScore);
    return score !== null && score >= 70;
  }).length;

  return (
    <section className="eiq-form-command" aria-label="Professional form workspace">
      <header className="eiq-form-command__header">
        <div>
          <span>FORM</span>
          <strong>Professional runner analysis</strong>
          <p>Compare current ratings, trajectory, suitability and price. Open a runner for the full historical dossier.</p>
        </div>
        <aside><strong>{active.length}</strong><span>ACTIVE RUNNERS</span></aside>
      </header>

      <section className="eiq-form-command__snapshot" aria-label="Form snapshot">
        <article><span>TOP EPI</span><strong>{topEpi ? `${topEpi.no}. ${topEpi.horse}` : "-"}</strong><small>{topEpi && numeric(topEpi.epi) !== null ? `EPI ${topEpi.epi}` : "Insufficient evidence"}</small></article>
        <article><span>RISING FORM</span><strong>{rising}</strong><small>Runners with positive governed momentum</small></article>
        <article><span>STRONG SUITABILITY</span><strong>{strongFit}</strong><small>Suitability score 70+</small></article>
        <article><span>FAIR PRICES</span><strong>{priced}/{active.length || 0}</strong><small>Active runners with EDGEiQ price</small></article>
      </section>

      <div className="eiq-form-command__table-wrap">
        <table className="eiq-form-command__table">
          <thead><tr><th>NO</th><th className="is-left">HORSE</th><th>LAST 5</th><th>EPI</th><th>ERI</th><th>EARLY</th><th>LATE</th><th>SUITABILITY</th><th>TRAJECTORY</th><th className="is-left">TODAY FIT</th><th>FAIR</th><th>MARKET</th><th>EDGE</th><th /></tr></thead>
          <tbody>
            {runners.map((runner) => (
              <tr key={runner.id} className={runner.scratched ? "is-scratched" : ""}>
                <td>{value(runner.no)}</td>
                <td className="is-left"><strong>{value(runner.horse)}</strong><small>{value(runner.trainer)} · {value(runner.jockey)}</small></td>
                <td>{runner.lastFive.length ? runner.lastFive.slice(0, 5).join("-") : "-"}</td>
                <td><strong>{runner.scratched ? "-" : value(runner.epi)}</strong></td>
                <td>{runner.scratched ? "-" : value(runner.rating)}</td>
                <td>{runner.scratched ? "-" : value(runner.earlySpeed)}</td>
                <td>{runner.scratched ? "-" : value(runner.late)}</td>
                <td><strong>{runner.scratched ? "-" : value(runner.suitabilityScore)}</strong><small>{runner.scratched ? "" : value(runner.suitabilityLabel, "")}</small></td>
                <td><span className={`eiq-form-command__momentum is-${runner.formMomentumDirection || "flat"}`}>{runner.scratched ? "-" : momentumLabel(runner)}</span></td>
                <td className="is-left"><span>{runner.scratched ? "Scratched" : bestFit(runner)}</span><small>{runner.scratched ? "" : lastRunText(runner)}</small></td>
                <td>{runner.scratched ? "-" : value(runner.edgeiqPrice)}</td>
                <td>{runner.scratched ? "Scratched" : value(runner.marketPrice)}</td>
                <td><strong>{runner.scratched ? "-" : priceDelta(runner)}</strong></td>
                <td><button type="button" disabled={runner.scratched} onClick={() => onOpenRunner(runner.sourceIndex)}>Open</button></td>
              </tr>
            ))}
            {!runners.length ? <tr><td colSpan={14}>Form data is not published for this race.</td></tr> : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
