import type { EvidenceModule } from "../EvidenceTypes";

export function buildGenericEvidenceModule(name: string): EvidenceModule {
  return {
    id: name.toLowerCase().replace(/\s+/g, "-"),
    title: name,
    currentInterpretation:
      "This evidence module is ready to connect to the EDGEiQ intelligence layer.",
    confidenceBand: "Current",
  };
}
