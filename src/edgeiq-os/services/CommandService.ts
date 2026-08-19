import { buildCommandViewModel } from "./command-view-model";
import { buildAgreementMatrix } from "./agreement-matrix";
import { buildConfidenceProfile } from "./confidence-profile";
import { buildIntelligenceTimeline } from "./intelligence-timeline";

export type { CommandViewModel } from "./command-view-model";
export type { AgreementMatrix, AgreementItem } from "./agreement-matrix";
export type { ConfidenceProfile, ConfidenceSignal } from "./confidence-profile";
export type { IntelligenceTimeline, TimelineEvent } from "./intelligence-timeline";

export const CommandService = {
  buildViewModel: buildCommandViewModel,
  buildAgreementMatrix,
  buildConfidenceProfile,
  buildIntelligenceTimeline,
};

export {
  buildCommandViewModel,
  buildAgreementMatrix,
  buildConfidenceProfile,
  buildIntelligenceTimeline,
};
