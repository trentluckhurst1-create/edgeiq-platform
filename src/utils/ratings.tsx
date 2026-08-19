import { FormRun, RunnerInsight } from "../types/racing";

export function getRunnerInsight(runs: FormRun[], todayRating: number): RunnerInsight {
  const usable = runs
    .filter((r) => Number.isFinite(r.rating))
    .slice(0, 5);

  if (!usable.length) {
    return {
      improving: false,
      consistent: false,
      hiddenRun: false,
      mapDependent: false
    };
  }

  const ratings = usable.map((r) => r.rating);
  const avg = ratings.reduce((a, b) => a + b, 0) / ratings.length;
  const variance =
    ratings.reduce((a, b) => a + Math.pow(b - avg, 2), 0) / ratings.length;

  const improving =
    usable.length >= 3 &&
    usable[0].rating >= usable[Math.min(usable.length - 1, 2)].rating + 3;

  const consistent = variance <= 9;

  const hiddenRun = usable.some(
    (r) => r.finish >= 4 && r.margin <= 2.0 && r.rating >= todayRating - 2
  );

  const mapDependent = usable.some(
    (r) => r.barrier >= 12 && r.finish <= 3
  );

  return {
    improving,
    consistent,
    hiddenRun,
    mapDependent
  };
}

export function runRatingColor(runRating: number, todayRating: number): string {
  const diff = runRating - todayRating;
  if (diff >= 2.5) return "#4ade80";
  if (diff >= -2) return "#facc15";
  return "#f87171";
}

export function finishBadge(finish: number | string): string {
  const f = Number(finish);
  if (f === 1) return "";
  if (f === 2) return "";
  if (f === 3) return "";
  return String(finish ?? "-");
}


