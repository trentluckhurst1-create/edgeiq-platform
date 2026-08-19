import { RaceFileService } from "./RaceFileService";

function clean(value: unknown): string {
  return String(value ?? "").trim();
}

function scoreTextMatch(a: unknown, b: unknown, weight: number): number {
  const left = clean(a).toUpperCase();
  const right = clean(b).toUpperCase();
  if (!left || !right) return weight * 0.45;
  if (left === right) return weight;
  if (left.includes(right) || right.includes(left)) return weight * 0.8;
  return weight * 0.35;
}

function scoreDistance(a: unknown, b: unknown, weight: number): number {
  const n1 = Number(clean(a).replace(/[^\d.]/g, ""));
  const n2 = Number(clean(b).replace(/[^\d.]/g, ""));
  if (!Number.isFinite(n1) || !Number.isFinite(n2)) return weight * 0.45;
  const diff = Math.abs(n1 - n2);
  if (diff <= 50) return weight;
  if (diff <= 100) return weight * 0.85;
  if (diff <= 200) return weight * 0.65;
  return weight * 0.35;
}

function verdict(score: number): string {
  if (score >= 90) return "ELITE RACE SUITABILITY";
  if (score >= 82) return "STRONG RACE SUITABILITY";
  if (score >= 72) return "USEFUL HISTORICAL REFERENCE";
  if (score >= 60) return "QUERY WITH SOME UPSIDE";
  return "LOW CONFIDENCE";
}

export function buildAssignmentComparison(today: any, historical: any) {
  const components = [
    { label: "Distance", score: scoreDistance(today.distance, historical?.distance, 18) },
    { label: "Class", score: scoreTextMatch(today.className, historical?.raceClass, 12) },
    { label: "Track condition", score: scoreTextMatch(today.condition, historical?.condition, 12) },
    { label: "Pressure", score: scoreTextMatch(today.pressure, historical?.pressureRating, 16) },
    { label: "Tempo", score: scoreTextMatch(today.tempo, historical?.tempoRating, 16) },
    { label: "TrackSignature", score: scoreTextMatch(today.trackSignature, historical?.trackSignatureMatch, 12) },
    { label: "SpeedProfile", score: scoreTextMatch(today.speedProfile, historical?.raceFlowMatch, 8) },
    { label: "Barrier", score: historical?.barrier ? 4 : 2 },
    { label: "Weight", score: historical?.weight ? 2 : 1 },
  ];

  const score = Math.round(components.reduce((sum, item) => sum + item.score, 0));
  const strengths = components.filter((item) => item.score >= 0.75 * Math.max(item.score, 1)).slice(0, 5);

  return {
    score,
    verdict: verdict(score),
    reasons: components
      .filter((item) => item.score >= 7)
      .map((item) => item.label),
    watch: components
      .filter((item) => item.score < 7)
      .map((item) => item.label),
    components: components.map((item) => ({
      label: item.label,
      score: Number(item.score.toFixed(1)),
    })),
    evidenceConfidence:
      score >= 84 ? "HIGH" : score >= 70 ? "MEDIUM" : "LOW",
    assessment:
      score >= 84
        ? "This past run lines up strongly with today's race."
        : score >= 70
          ? "This past run is useful, with a few differences to respect."
          : "This past run is background form rather than a key reference.",
    strengths: strengths.map((item) => item.label),
  };
}

export function buildCompareModel() {
  const file = RaceFileService.buildRaceBook();
  const runner = file.field[0];
  const historical = runner?.historicalRuns?.[0];

  const today = {
    race: `${file.raceBook.official.meeting} R${file.raceBook.official.raceNumber}`,
    distance: file.raceBook.official.distance,
    className: file.raceBook.official.raceClass,
    condition: file.raceBook.official.trackCondition,
    rail: file.raceBook.official.rail,
    pressure: file.raceBook.intelligence.pressure,
    tempo: file.raceBook.intelligence.tempo,
    trackSignature: file.raceBook.intelligence.trackSignature,
    speedProfile: file.raceBook.intelligence.speedProfile,
  };

  return {
    today,
    historical: historical
      ? {
          race: `${historical.track} · ${historical.distance} · ${historical.raceClass}`,
          condition: historical.condition,
          barrier: historical.barrier,
          weight: historical.weight,
          jockey: historical.jockey,
          officialTime: historical.officialRaceTime,
          raceStrength: historical.edgeiqRaceStrength,
          runRating: historical.edgeiqRunRating,
          pressure: historical.pressureRating,
          tempo: historical.tempoRating,
          trackSignature: historical.trackSignatureMatch,
          raceFlow: historical.raceFlowMatch,
          speedProfile: historical.speedProfile,
          positionInRunning: historical.positionInRunning,
        }
      : null,
    similarity: historical
      ? buildAssignmentComparison(today, historical)
      : {
          score: 0,
          verdict: "NO HISTORICAL MATCH",
          reasons: [],
          watch: ["No comparable historical run available"],
          components: [],
          evidenceConfidence: "LOW",
          assessment: "No historical assignment comparison is available.",
          strengths: [],
        },
  };
}

export const CompareService = {
  build: buildCompareModel,
  buildAssignmentComparison,
};
