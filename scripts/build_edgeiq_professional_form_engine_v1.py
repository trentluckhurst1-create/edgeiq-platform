from pathlib import Path
from datetime import datetime

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

files = [
    "src/edgeiq-os/race/RaceFileV3.tsx",
    "src/edgeiq-os/services/RaceFileService.ts",
    "src/edgeiq-os/services/RunRatingService.ts",
    "src/edgeiq-os/services/RaceStrengthService.ts",
    "src/edgeiq-os/services/CompareService.ts",
    "src/edgeiq-os/styles/edgeiqOsV2.css",
]

for file in files:
    p = Path(file)
    if p.exists():
        backup = p.with_name(p.stem + f"_CHECKPOINT_BEFORE_PRO_FORM_ENGINE_{stamp}" + p.suffix)
        backup.write_text(p.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")

Path("src/edgeiq-os/services/RunRatingService.ts").write_text(r'''export type RunRatingBand =
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
''', encoding="utf-8")

Path("src/edgeiq-os/services/RaceStrengthService.ts").write_text(r'''export type RaceStrengthBand =
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
''', encoding="utf-8")

Path("src/edgeiq-os/services/CompareService.ts").write_text(r'''import { RaceFileService } from "./RaceFileService";

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
  if (score >= 90) return "ELITE ASSIGNMENT MATCH";
  if (score >= 82) return "HIGH ASSIGNMENT MATCH";
  if (score >= 72) return "USABLE HISTORICAL MATCH";
  if (score >= 60) return "PARTIAL MATCH";
  return "LOW RELEVANCE";
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
        ? "This historical run is highly relevant to today's assignment."
        : score >= 70
          ? "This historical run provides usable evidence with some differences."
          : "This historical run should be treated as background form rather than primary evidence.",
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
''', encoding="utf-8")

Path("src/edgeiq-os/services/RaceFileService.ts").write_text(r'''import { buildRaceFileV2 } from "./race-file-v2";
import { buildRaceStrengthBreakdown } from "./RaceStrengthService";
import { buildRunRatingBreakdown } from "./RunRatingService";
import { buildAssignmentComparison } from "./CompareService";

export type {
  RaceFileModelV1,
  RaceFileRunnerProfile,
  HistoricalRun,
  OfficialRaceData,
  OfficialRunnerData,
  EdgeiqSpeedProfileSplit,
} from "./race-file-model";

function buildRunNarrative(run: any, runRating: any, raceStrength: any, assignment: any): string {
  if (assignment.score >= 88 && runRating.overall >= 86 && raceStrength.overall >= 80) {
    return "Strong historical evidence for today's assignment.";
  }

  if (runRating.overall >= 88 && String(run?.finish ?? "").toUpperCase() !== "1ST") {
    return "Strong in defeat. The performance rated better than the finishing position suggests.";
  }

  if (assignment.score >= 80) {
    return "Relevant historical assignment with usable evidence for today.";
  }

  if (raceStrength.overall < 62) {
    return "Form line requires caution due to weaker race strength.";
  }

  return "Background form. Useful context, but not a primary match for today.";
}

export function buildProfessionalRaceBook() {
  const file = buildRaceFileV2();

  const today = {
    race: `${file.officialRace.meeting} R${file.officialRace.raceNumber}`,
    distance: file.officialRace.distance,
    className: file.officialRace.raceClass,
    condition: file.officialRace.trackCondition,
    rail: file.officialRace.rail,
    pressure: file.raceRead.pressure,
    tempo: file.raceRead.tempo,
    trackSignature: file.raceRead.trackSignature,
    speedProfile: file.raceRead.speedProfile,
  };

  const field = file.field.map((runner: any) => {
    const historicalRuns = (runner.historicalRuns ?? []).map((run: any) => {
      const runRating = buildRunRatingBreakdown(run);
      const raceStrength = buildRaceStrengthBreakdown(run);
      const assignment = buildAssignmentComparison(today, run);

      return {
        ...run,
        professionalForm: {
          official: {
            date: run.date,
            track: run.track,
            race: run.race,
            distance: run.distance,
            raceClass: run.raceClass,
            condition: run.condition,
            rail: run.rail ?? "Not recorded",
            barrier: run.barrier,
            weight: run.weight,
            jockey: run.jockey,
            sp: run.sp,
            finish: run.finish,
            margin: run.margin,
            officialRaceTime: run.officialRaceTime,
            winnerTime: run.winnerTime ?? "Not recorded",
            fieldSize: run.fieldSize ?? "Not recorded",
          },
          evidence: {
            runRating,
            raceStrength,
            speedProfile: run.speedProfile,
            pressure: run.pressureRating,
            tempo: run.tempoRating,
            trackSignature: run.trackSignatureMatch,
            raceFlow: run.raceFlowMatch,
            runnerDNA: runner.runnerDNA,
            narrative: buildRunNarrative(run, runRating, raceStrength, assignment),
          },
          assignment,
        },
      };
    });

    return {
      ...runner,
      historicalRuns,
      evidenceRuns: [...historicalRuns].sort(
        (a: any, b: any) =>
          (b.professionalForm?.assignment?.score ?? 0) -
          (a.professionalForm?.assignment?.score ?? 0)
      ),
    };
  });

  return {
    ...file,
    field,
    raceBook: {
      official: {
        meeting: file.officialRace.meeting,
        raceNumber: file.officialRace.raceNumber,
        raceName: file.officialRace.raceName,
        distance: file.officialRace.distance,
        raceClass: file.officialRace.raceClass,
        trackCondition: file.officialRace.trackCondition,
        rail: file.officialRace.rail,
        officialRaceTime: file.officialRace.officialRaceTime ?? "Pending",
        prizeMoney: file.officialRace.prizeMoney ?? "Pending",
        fieldSize: file.field.length,
      },
      intelligence: {
        raceFlow: file.raceRead.raceFlow,
        pressure: file.raceRead.pressure,
        tempo: file.raceRead.tempo,
        trackSignature: file.raceRead.trackSignature,
        speedProfile: file.raceRead.speedProfile,
        confidence: file.raceRead.confidence,
        raceStrength: buildRaceStrengthBreakdown(),
        runRating: buildRunRatingBreakdown(),
      },
    },
  };
}

export const RaceFileService = {
  build: buildRaceFileV2,
  buildRaceBook: buildProfessionalRaceBook,
};

export { buildRaceFileV2, buildRaceFileV2 as buildRaceFile };
''', encoding="utf-8")

Path("src/edgeiq-os/race/RaceFileV3.tsx").write_text(r'''import { useMemo, useState } from "react";
import { RaceFileService } from "../services/RaceFileService";
import { CompareWorkspace } from "../compare/CompareWorkspace";

const file = RaceFileService.buildRaceBook();
const primary = file.field[0];

type FormMode = "form" | "evidence";

function verdict(run: any): string {
  return run?.professionalForm?.assignment?.verdict ?? "NEEDS CONTEXT";
}

function assessment(run: any): string {
  return run?.professionalForm?.evidence?.narrative ?? "Background form. Useful context, but not a primary match for today.";
}

function Pill({ label }: { label: string }) {
  return <span className="eiq-pro-form-pill">{label}</span>;
}

function Metric({ label, value }: { label: string; value: any }) {
  return (
    <article>
      <span>{label}</span>
      <strong>{value ?? "—"}</strong>
    </article>
  );
}

function HistoricalRunCard({ run }: { run: any }) {
  const form = run.professionalForm;
  const official = form?.official ?? {};
  const evidence = form?.evidence ?? {};
  const assignment = form?.assignment ?? {};

  return (
    <article className="eiq-pro-form-card">
      <header className="eiq-pro-form-card__header">
        <div>
          <span>Official Form</span>
          <strong>{official.date} · {official.track} · {official.distance}</strong>
          <p>{official.raceClass} · {official.condition} · Rail {official.rail}</p>
        </div>

        <aside>
          <span>Today's Assignment</span>
          <strong>{assignment.score ?? 0}%</strong>
          <p>{verdict(run)}</p>
        </aside>
      </header>

      <section className="eiq-pro-form-block">
        <header>
          <span>Official Form Guide</span>
          <strong>What happened</strong>
        </header>

        <div className="eiq-pro-form-grid">
          <Metric label="Race" value={official.race} />
          <Metric label="Barrier" value={official.barrier} />
          <Metric label="Weight" value={official.weight} />
          <Metric label="Jockey" value={official.jockey} />
          <Metric label="SP" value={official.sp} />
          <Metric label="Finish" value={official.finish} />
          <Metric label="Margin" value={official.margin} />
          <Metric label="Official Time" value={official.officialRaceTime} />
          <Metric label="Winner Time" value={official.winnerTime} />
          <Metric label="Field Size" value={official.fieldSize} />
        </div>
      </section>

      <section className="eiq-pro-form-block">
        <header>
          <span>EDGEIQ Evidence</span>
          <strong>Why it happened</strong>
        </header>

        <div className="eiq-pro-form-grid">
          <Metric label="Run Rating™" value={`${evidence.runRating?.overall ?? run.edgeiqRunRating} · ${evidence.runRating?.band ?? ""}`} />
          <Metric label="Race Strength™" value={`${evidence.raceStrength?.overall ?? run.edgeiqRaceStrength} · ${evidence.raceStrength?.band ?? ""}`} />
          <Metric label="Pressure" value={evidence.pressure} />
          <Metric label="Tempo" value={evidence.tempo} />
          <Metric label="TrackSignature™" value={evidence.trackSignature} />
          <Metric label="RaceFlow™" value={evidence.raceFlow} />
          <Metric label="RunnerDNA™" value={evidence.runnerDNA} />
        </div>

        <p className="eiq-pro-form-narrative">{assessment(run)}</p>
      </section>

      <section className="eiq-pro-form-block">
        <header>
          <span>Today's Relevance</span>
          <strong>How this run maps to today</strong>
        </header>

        <div className="eiq-assignment-row">
          {(assignment.components ?? []).map((item: any) => (
            <article key={item.label}>
              <span>{item.label}</span>
              <strong>{item.score}</strong>
            </article>
          ))}
        </div>

        <div className="eiq-pro-form-summary">
          <div>
            <span>Evidence Confidence</span>
            <strong>{assignment.evidenceConfidence ?? "LOW"}</strong>
          </div>
          <p>{assignment.assessment}</p>
        </div>

        <div className="eiq-pro-form-pills">
          {(assignment.reasons ?? []).map((reason: string) => <Pill key={reason} label={`✓ ${reason}`} />)}
          {(assignment.watch ?? []).map((reason: string) => <Pill key={reason} label={`△ ${reason}`} />)}
        </div>
      </section>

      <section className="eiq-pro-form-block">
        <header>
          <span>Position & EDGEIQ Standard</span>
          <strong>How the run unfolded</strong>
        </header>

        <div className="eiq-pro-form-position">
          <strong>
            Jump {run.positionInRunning?.jump ?? "—"} · 800 {run.positionInRunning?.m800 ?? "—"} · 600 {run.positionInRunning?.m600 ?? "—"} · 400 {run.positionInRunning?.m400 ?? "—"} · 200 {run.positionInRunning?.m200 ?? "—"} · Finish {run.positionInRunning?.finish ?? "—"}
          </strong>
        </div>

        <div className="eiq-pro-form-speed">
          {(run.speedProfile ?? []).map((split: any) => (
            <article key={split.marker}>
              <span>{split.marker}</span>
              <strong>{split.lengthsVsStandard}</strong>
              <small>{split.position}</small>
            </article>
          ))}
        </div>
      </section>

      <button className="eiq-pro-form-open" type="button">
        Open Historical Race Book →
      </button>
    </article>
  );
}

export function RaceFileV3() {
  const [mode, setMode] = useState<FormMode>("form");

  const displayedRuns = useMemo(() => {
    if (!primary) return [];
    return mode === "evidence" ? (primary as any).evidenceRuns ?? primary.historicalRuns : primary.historicalRuns;
  }, [mode]);

  return (
    <section className="eiq-race-book-pro">
      <header className="eiq-race-book-pro__hero">
        <span>EDGEIQ Race Book</span>
        <strong>{file.raceBook.official.meeting} R{file.raceBook.official.raceNumber}</strong>
        <p>
          {file.raceBook.official.raceName} · {file.raceBook.official.distance} · {file.raceBook.official.raceClass} · {file.raceBook.official.trackCondition} · {file.raceBook.official.rail}
        </p>
      </header>

      <section className="eiq-race-book-pro__grid">
        <article>
          <span>Official Race</span>
          <strong>{file.raceBook.official.distance}</strong>
          <p>{file.raceBook.official.raceClass} · Field {file.raceBook.official.fieldSize}</p>
        </article>
        <article>
          <span>RaceFlow™</span>
          <strong>{file.raceBook.intelligence.raceFlow}</strong>
          <p>Expected tactical shape.</p>
        </article>
        <article>
          <span>Pressure</span>
          <strong>{file.raceBook.intelligence.pressure}</strong>
          <p>Projected pressure read.</p>
        </article>
        <article>
          <span>Tempo</span>
          <strong>{file.raceBook.intelligence.tempo}</strong>
          <p>Expected race speed.</p>
        </article>
        <article>
          <span>TrackSignature™</span>
          <strong>{file.raceBook.intelligence.trackSignature}</strong>
          <p>Track pattern and suitability.</p>
        </article>
        <article>
          <span>SpeedProfile™</span>
          <strong>{file.raceBook.intelligence.speedProfile}</strong>
          <p>Measured against EDGEIQ standards.</p>
        </article>
      </section>

      <section className="eiq-race-book-pro__section">
        <header>
          <span>Field Intelligence</span>
          <strong>Runner-by-runner assessment</strong>
        </header>

        <div className="eiq-race-book-pro__table-wrap">
          <table>
            <thead>
              <tr>
                <th>No</th>
                <th>Runner</th>
                <th>Bar</th>
                <th>Weight</th>
                <th>Jockey</th>
                <th>Trainer</th>
                <th>Market</th>
                <th>EDGE Rating™</th>
                <th>RunnerDNA™</th>
                <th>SpeedProfile™</th>
                <th>TrackSignature™</th>
                <th>RaceFlow™</th>
                <th>Assessment</th>
              </tr>
            </thead>
            <tbody>
              {file.field.map((runner) => (
                <tr key={runner.official.no}>
                  <td>{runner.official.no}</td>
                  <td><strong>{runner.official.runner}</strong></td>
                  <td>{runner.official.barrier}</td>
                  <td>{runner.official.weight}</td>
                  <td>{runner.official.jockey}</td>
                  <td>{runner.official.trainer}</td>
                  <td>{runner.official.market}</td>
                  <td>{runner.edgeRating}</td>
                  <td>{runner.runnerDNA}</td>
                  <td>{runner.speedProfile}</td>
                  <td>{runner.trackSignature}</td>
                  <td>{runner.raceFlow}</td>
                  <td>{runner.assessment}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {primary ? (
        <section className="eiq-race-book-pro__section">
          <header>
            <span>Runner Dossier</span>
            <strong>{primary.official.runner}</strong>
            <p>{primary.assessment}</p>
          </header>

          <div className="eiq-race-book-pro__runner-snapshot">
            <article><span>Trainer</span><strong>{primary.official.trainer}</strong></article>
            <article><span>Jockey</span><strong>{primary.official.jockey}</strong></article>
            <article><span>Barrier</span><strong>{primary.official.barrier}</strong></article>
            <article><span>Weight</span><strong>{primary.official.weight}</strong></article>
            <article><span>Market</span><strong>{primary.official.market}</strong></article>
          </div>

          <div className="eiq-pro-form-toolbar">
            <div>
              <span>Professional Form Guide</span>
              <strong>Official form + EDGEIQ evidence + today's relevance</strong>
            </div>
            <nav>
              <button type="button" className={mode === "form" ? "is-active" : ""} onClick={() => setMode("form")}>
                Form View
              </button>
              <button type="button" className={mode === "evidence" ? "is-active" : ""} onClick={() => setMode("evidence")}>
                Evidence View
              </button>
            </nav>
          </div>

          <div className="eiq-race-book-pro__runs">
            {displayedRuns.map((run: any) => (
              <HistoricalRunCard key={`${run.date}-${run.track}-${run.race}`} run={run} />
            ))}
          </div>
        </section>
      ) : null}

      <CompareWorkspace />
    </section>
  );
}
''', encoding="utf-8")

css_path = Path("src/edgeiq-os/styles/edgeiqOsV2.css")
css = css_path.read_text(encoding="utf-8", errors="ignore")
css += r'''

/* Sprint 10.1 — Professional Historical Form Engine */
.eiq-pro-form-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
  padding: 16px;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 18px;
  background: rgba(255,255,255,0.035);
  margin: 18px 0;
}

.eiq-pro-form-toolbar span,
.eiq-pro-form-card span,
.eiq-pro-form-block span,
.eiq-pro-form-summary span {
  display: block;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  opacity: 0.62;
}

.eiq-pro-form-toolbar strong {
  display: block;
  margin-top: 4px;
  font-size: 14px;
}

.eiq-pro-form-toolbar nav {
  display: flex;
  gap: 8px;
}

.eiq-pro-form-toolbar button,
.eiq-pro-form-open {
  border: 1px solid rgba(255,255,255,0.14);
  background: rgba(255,255,255,0.045);
  color: inherit;
  border-radius: 999px;
  padding: 9px 13px;
  cursor: pointer;
}

.eiq-pro-form-toolbar button.is-active {
  background: rgba(255,255,255,0.14);
  border-color: rgba(255,255,255,0.26);
}

.eiq-pro-form-card {
  border: 1px solid rgba(255,255,255,0.11);
  border-radius: 22px;
  padding: 18px;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.055), rgba(255,255,255,0.025));
  margin-bottom: 18px;
}

.eiq-pro-form-card__header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(255,255,255,0.09);
}

.eiq-pro-form-card__header strong {
  display: block;
  margin-top: 5px;
  font-size: 18px;
}

.eiq-pro-form-card__header p {
  margin: 5px 0 0;
  opacity: 0.72;
}

.eiq-pro-form-card__header aside {
  min-width: 210px;
  text-align: right;
}

.eiq-pro-form-card__header aside strong {
  font-size: 28px;
}

.eiq-pro-form-block {
  margin-top: 16px;
  padding: 14px;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  background: rgba(0,0,0,0.16);
}

.eiq-pro-form-block header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.eiq-pro-form-block header strong {
  font-size: 13px;
  opacity: 0.86;
}

.eiq-pro-form-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}

.eiq-pro-form-grid article,
.eiq-assignment-row article,
.eiq-pro-form-speed article {
  border: 1px solid rgba(255,255,255,0.075);
  border-radius: 13px;
  padding: 10px;
  background: rgba(255,255,255,0.035);
}

.eiq-pro-form-grid article strong,
.eiq-assignment-row article strong,
.eiq-pro-form-speed article strong {
  display: block;
  margin-top: 5px;
  font-size: 13px;
}

.eiq-pro-form-narrative {
  margin: 13px 0 0;
  opacity: 0.82;
  line-height: 1.55;
}

.eiq-assignment-row,
.eiq-pro-form-speed {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
}

.eiq-pro-form-summary {
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: 14px;
  align-items: start;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255,255,255,0.075);
}

.eiq-pro-form-summary strong {
  display: block;
  margin-top: 5px;
  font-size: 18px;
}

.eiq-pro-form-summary p {
  margin: 0;
  opacity: 0.82;
  line-height: 1.5;
}

.eiq-pro-form-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.eiq-pro-form-pill {
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 999px;
  padding: 7px 10px;
  background: rgba(255,255,255,0.045);
  font-size: 11px;
  letter-spacing: 0.06em;
}

.eiq-pro-form-position {
  padding: 11px 12px;
  border-radius: 13px;
  background: rgba(255,255,255,0.035);
  border: 1px solid rgba(255,255,255,0.075);
  margin-bottom: 10px;
}

.eiq-pro-form-open {
  margin-top: 14px;
  width: 100%;
  border-radius: 14px;
  text-align: left;
  padding: 13px 14px;
}

@media (max-width: 1100px) {
  .eiq-pro-form-grid,
  .eiq-assignment-row,
  .eiq-pro-form-speed {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .eiq-pro-form-card__header,
  .eiq-pro-form-toolbar,
  .eiq-pro-form-summary {
    grid-template-columns: 1fr;
    flex-direction: column;
  }

  .eiq-pro-form-card__header aside {
    text-align: left;
  }
}
'''
css_path.write_text(css, encoding="utf-8")

print("[EDGEIQ] Sprint 10.1 Professional Historical Form Engine applied")
