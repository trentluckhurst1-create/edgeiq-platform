import { buildPressureEngine } from "./pressure-engine";
import { buildTempoEngine } from "./tempo-engine";
import { buildPositionEngine } from "./position-engine";
import { buildSpeedProfile } from "./speed-profile";
import { buildTrackSignature } from "./track-signature";

export type AgreementItem = {
  engine: string;
  status: "CONFIRM" | "WATCH" | "NEUTRAL";
};

export type AgreementMatrix = {
  agreement: number;
  items: AgreementItem[];
};

function confirm(value: unknown): "CONFIRM" | "WATCH" {
  const text = String(value).toUpperCase();

  if (
    text.includes("HIGH") ||
    text.includes("VERY") ||
    text.includes("STRONG") ||
    text.includes("ELITE") ||
    text.includes("POSITIVE") ||
    text.includes("ACTIVE") ||
    text.includes("FAST") ||
    text.includes("ON_PACE") ||
    text.includes("FORWARD") ||
    text.includes("MAPPED") ||
    text.includes("ASSESSED")
  ) {
    return "CONFIRM";
  }

  return "WATCH";
}

export function buildAgreementMatrix(): AgreementMatrix {
  const pressure = buildPressureEngine();
  const tempo = buildTempoEngine();
  const position = buildPositionEngine();
  const speed = buildSpeedProfile();
  const track = buildTrackSignature();

  const items: AgreementItem[] = [
    {
      engine: "Pressure Engine",
      status: confirm(pressure.band),
    },
    {
      engine: "Tempo Engine",
      status: confirm(tempo.band),
    },
    {
      engine: "Position Engine",
      status: confirm(position.position),
    },
    {
      engine: "SpeedProfile",
      status: confirm(speed.confidence),
    },
    {
      engine: "TrackSignature",
      status: confirm(track.todayPattern),
    },
  ];

  const confirms = items.filter((x) => x.status === "CONFIRM").length;

  return {
    agreement: Math.round((confirms / items.length) * 100),
    items,
  };
}
