
import { buildAgreementMatrix } from "./agreement-matrix";
import { buildPressureEngine } from "./pressure-engine";
import { buildTempoEngine } from "./tempo-engine";
import { buildPositionEngine } from "./position-engine";
import { buildSpeedProfile } from "./speed-profile";
import { buildTrackSignature } from "./track-signature";

export type ConfidenceSignal = {
  label: string;
  status: string;
  strength: number;
  direction: "SUPPORTING" | "WATCH" | "NEUTRAL";
};

export type ConfidenceProfile = {
  label: string;
  band: "LOW" | "DEVELOPING" | "MODERATE" | "HIGH" | "VERY HIGH";
  agreement: number;
  strongestSignal: ConfidenceSignal;
  weakestSignal: ConfidenceSignal;
  signals: ConfidenceSignal[];
  summary: string;
};

function bandFromAgreement(agreement: number): ConfidenceProfile["band"] {
  if (agreement >= 90) return "VERY HIGH";
  if (agreement >= 75) return "HIGH";
  if (agreement >= 55) return "MODERATE";
  if (agreement >= 35) return "DEVELOPING";
  return "LOW";
}

function strengthFromStatus(status: string): number {
  const value = status.toLowerCase();

  if (
    value.includes("elite") ||
    value.includes("very high") ||
    value.includes("high") ||
    value.includes("strong") ||
    value.includes("confirm") ||
    value.includes("mapped") ||
    value.includes("assessed") ||
    value.includes("active")
  ) {
    return 90;
  }

  if (
    value.includes("positive") ||
    value.includes("moderate") ||
    value.includes("normal") ||
    value.includes("on_pace") ||
    value.includes("forward")
  ) {
    return 72;
  }

  if (
    value.includes("watch") ||
    value.includes("building") ||
    value.includes("developing") ||
    value.includes("unknown")
  ) {
    return 48;
  }

  return 60;
}

function directionFromStrength(strength: number): ConfidenceSignal["direction"] {
  if (strength >= 70) return "SUPPORTING";
  if (strength >= 50) return "NEUTRAL";
  return "WATCH";
}

export function buildConfidenceProfile(): ConfidenceProfile {
  const agreement = buildAgreementMatrix();
  const pressure = buildPressureEngine();
  const tempo = buildTempoEngine();
  const position = buildPositionEngine();
  const speed = buildSpeedProfile();
  const track = buildTrackSignature();

  const rawSignals = [
    { label: "Pressure Engine", status: pressure.band },
    { label: "Tempo Engine", status: tempo.band },
    { label: "Position Engine", status: position.position },
    { label: "SpeedProfile", status: speed.confidence },
    { label: "TrackSignature", status: track.todayPattern },
    { label: "Agreement Matrix", status: `${agreement.agreement}%` },
  ];

  const signals = rawSignals.map((signal) => {
    const strength =
      signal.label === "Agreement Matrix"
        ? agreement.agreement
        : strengthFromStatus(signal.status);

    return {
      ...signal,
      strength,
      direction: directionFromStrength(strength),
    };
  });

  const sorted = [...signals].sort((a, b) => b.strength - a.strength);
  const strongestSignal = sorted[0] ?? signals[0];
  const weakestSignal = sorted[sorted.length - 1] ?? signals[0];

  const band = bandFromAgreement(agreement.agreement);

  return {
    label: "Operational Confidence",
    band,
    agreement: agreement.agreement,
    strongestSignal,
    weakestSignal,
    signals,
    summary:
      `${band.replace("_", " ")} confidence is currently driven by ${strongestSignal.label}. ` +
      `${weakestSignal.label} remains the weakest signal and should stay under observation.`,
  };
}
