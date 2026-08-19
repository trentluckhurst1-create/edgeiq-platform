export type EdgeiqNarrative = {
  currentView: string;
  whyItMatters: string;
  watch: string;
  recommendedAction?: string;
};

export function buildBasicNarrative(input: {
  title: string;
  summary: string;
  status?: string;
  confidence?: number;
}): EdgeiqNarrative {
  return {
    currentView: input.summary,
    whyItMatters: `${input.title} is contributing to the current assessment.`,
    watch: input.status === "READY"
      ? "Continue monitoring for any material change."
      : "This area is still developing and should not be treated as final.",
  };
}
