
import { buildAgreementMatrix } from "./agreement-matrix";
import { buildPressureEngine } from "./pressure-engine";
import { buildTempoEngine } from "./tempo-engine";
import { buildTrackSignature } from "./track-signature";

export type TimelineEvent = {
  time: string;
  title: string;
  impact: "HIGH" | "MEDIUM" | "LOW";
  narrative: string;
};

export type IntelligenceTimeline = {
  overallAgreement: number;
  events: TimelineEvent[];
};

export function buildIntelligenceTimeline(): IntelligenceTimeline {

  const agreement = buildAgreementMatrix();
  const pressure = buildPressureEngine();
  const tempo = buildTempoEngine();
  const track = buildTrackSignature();

  return {

    overallAgreement: agreement.agreement,

    events: [

      {
        time: "08:30",
        title: "TrackSignature Updated",
        impact: "MEDIUM",
        narrative: track.assessment,
      },

      {
        time: "08:47",
        title: "Pressure Engine",
        impact: pressure.band === "HIGH" ? "HIGH" : "MEDIUM",
        narrative: pressure.summary,
      },

      {
        time: "09:05",
        title: "Tempo Engine",
        impact: "MEDIUM",
        narrative: tempo.raceRead,
      },

      {
        time: "09:24",
        title: "RaceFlow Revised",
        impact: "HIGH",
        narrative: pressure.tacticalRead,
      },

      {
        time: "09:41",
        title: "Operational Assessment",
        impact: "HIGH",
        narrative:
          "EDGEiQ intelligence engines have reached operational agreement.",
      },

    ],
  };

}
