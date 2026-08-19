export type RunRatingBand =
  | "ELITE"
  | "STRONG"
  | "POSITIVE"
  | "NEUTRAL"
  | "NEGATIVE"
  | "POOR";

export type RunRatingBreakdown = {
  overall: number;
  early: number;
  mid: number;
  late: number;
  efficiency: number;
  pressureResponse: number;
  band: RunRatingBand;
  narrative: string;
  supportingEvidence: string[];
};

function toNumber(value: unknown, fallback = 0): number {
  const n = Number(String(value ?? "").replace(/[^\d.-]/g, ""));
  return Number.isFinite(n) ? n : fallback;
}

function clamp(value: number, min = 0, max = 100): number {
  return Math.max(min, Math.min(max, value));
}

function bandFor(score: number): RunRatingBand {
  if (score >= 90) return "ELITE";
  if (score >= 84) return "STRONG";
  if (score >= 76) return "POSITIVE";
  if (score >= 66) return "NEUTRAL";
  if (score >= 55) return "NEGATIVE";
  return "POOR";
}

export function buildRunRatingBreakdown(run?: any): RunRatingBreakdown {
  const rawRating = toNumber(run?.edgeiqRunRating ?? run?.runRating ?? run?.rating, 72);
  const pressure = String(run?.pressureRating ?? run?.pressure ?? "").toUpperCase();
  const tempo = String(run?.tempoRating ?? run?.tempo ?? "").toUpperCase();
  const relative = toNumber(run?.relativePerformance, 0);

  const early = clamp(rawRating - 4 + (tempo.includes("FAST") ? 4 : 0));
  const mid = clamp(rawRating - 2 + (pressure.includes("HIGH") ? 3 : 0));
  const late = clamp(rawRating + Math.max(relative, 0) * 2);
  const efficiency = clamp(rawRating + (relative >= 0 ? 3 : -3));
  const pressureResponse = clamp(rawRating + (pressure.includes("HIGH") ? 4 : pressure.includes("LOW") ? -1 : 1));

  const overall = clamp(
    rawRating * 0.5 +
      early * 0.1 +
      mid * 0.12 +
      late * 0.14 +
      efficiency * 0.07 +
      pressureResponse * 0.07
  );

  const band = bandFor(overall);
  const supportingEvidence = [
    overall >= 84 ? "High-grade performance figure" : "Performance figure requires context",
    late >= 84 ? "Late-speed profile supports the run" : "Late-speed profile not dominant",
    pressureResponse >= 84 ? "Handled pressure profile" : "Pressure response mixed",
    efficiency >= 80 ? "Efficient against EDGEIQ standard" : "Efficiency below peak range",
  ];

  return {
    overall: Number(overall.toFixed(1)),
    early: Number(early.toFixed(1)),
    mid: Number(mid.toFixed(1)),
    late: Number(late.toFixed(1)),
    efficiency: Number(efficiency.toFixed(1)),
    pressureResponse: Number(pressureResponse.toFixed(1)),
    band,
    narrative:
      band === "ELITE"
        ? "Elite historical performance."
        : band === "STRONG"
          ? "Strong professional-grade run."
          : band === "POSITIVE"
            ? "Positive run with usable evidence."
            : "Run requires supporting context.",
    supportingEvidence,
  };
}
