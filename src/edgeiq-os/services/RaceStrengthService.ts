export type RaceStrengthBand =
  | "ELITE"
  | "STRONG"
  | "ABOVE_AVERAGE"
  | "AVERAGE"
  | "WEAK";

export type RaceStrengthBreakdown = {
  overall: number;
  speedQuality: number;
  pressureQuality: number;
  depth: number;
  finishStrength: number;
  historicalPercentile: number;
  band: RaceStrengthBand;
  narrative: string;
};

function toNumber(value: unknown, fallback = 0): number {
  const n = Number(String(value ?? "").replace(/[^\d.-]/g, ""));
  return Number.isFinite(n) ? n : fallback;
}

function clamp(value: number, min = 0, max = 100): number {
  return Math.max(min, Math.min(max, value));
}

function bandFor(score: number): RaceStrengthBand {
  if (score >= 88) return "ELITE";
  if (score >= 80) return "STRONG";
  if (score >= 72) return "ABOVE_AVERAGE";
  if (score >= 62) return "AVERAGE";
  return "WEAK";
}

export function buildRaceStrengthBreakdown(run?: any): RaceStrengthBreakdown {
  const base = toNumber(run?.edgeiqRaceStrength ?? run?.raceStrength, 68);
  const pressure = String(run?.pressureRating ?? run?.pressure ?? "").toUpperCase();
  const tempo = String(run?.tempoRating ?? run?.tempo ?? "").toUpperCase();
  const fieldSize = toNumber(run?.fieldSize, 10);

  const speedQuality = clamp(base + (tempo.includes("FAST") ? 5 : tempo.includes("SLOW") ? -4 : 1));
  const pressureQuality = clamp(base + (pressure.includes("HIGH") ? 5 : pressure.includes("LOW") ? -3 : 1));
  const depth = clamp(base + Math.min(fieldSize, 16) * 0.6);
  const finishStrength = clamp(base + (speedQuality >= 82 ? 3 : 0));
  const historicalPercentile = clamp(base);

  const overall = clamp(
    speedQuality * 0.25 +
      pressureQuality * 0.22 +
      depth * 0.2 +
      finishStrength * 0.18 +
      historicalPercentile * 0.15
  );

  const band = bandFor(overall);

  return {
    overall: Number(overall.toFixed(1)),
    speedQuality: Number(speedQuality.toFixed(1)),
    pressureQuality: Number(pressureQuality.toFixed(1)),
    depth: Number(depth.toFixed(1)),
    finishStrength: Number(finishStrength.toFixed(1)),
    historicalPercentile: Number(historicalPercentile.toFixed(1)),
    band,
    narrative:
      band === "ELITE"
        ? "Elite-strength historical race."
        : band === "STRONG"
          ? "Strong race with reliable form merit."
          : band === "ABOVE_AVERAGE"
            ? "Above-average race strength."
            : band === "AVERAGE"
              ? "Standard race strength."
              : "Weak race strength; upgrade evidence cautiously.",
  };
}
