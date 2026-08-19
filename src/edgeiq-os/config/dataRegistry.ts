export const EDGEIQ_DATA_REGISTRY = {
  liveRunnerBoard: "/data/edgeiq_live_runner_board_v7_1_current_day_candidate.csv",
  runnerDNA: "/data/edgeiq_runner_dna_v6_2.csv",
  sourceMode: "canonical-registry-v1",
} as const;

export type EdgeiqDatasetKey = keyof typeof EDGEIQ_DATA_REGISTRY;
