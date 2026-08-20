import { edgeiqDataPath } from "./edgeiqDataOrigin";

export const EDGEIQ_REFRESH_MS = 15000;

export const EDGEIQ_LIVE_FILES = {
  formGuideEnriched: edgeiqDataPath("/data/edgeiq_form_guide_enriched_v2.json"),
  currentRaceIntelligence: edgeiqDataPath("/data/edgeiq_current_race_intelligence_v1.json"),
  threeDayWindow: edgeiqDataPath("/data/edgeiq_three_day_window_v1.json"),
  threeDayProductCatalog: edgeiqDataPath("/data/edgeiq_three_day_product_catalog_v1.json"),
  liveRunnerBoard: edgeiqDataPath("/data/edgeiq_live_runner_board_v1.csv"),
  trainerJockeyFactors: edgeiqDataPath("/data/edgeiq_live_trainer_jockey_factor_feed_v3.csv"),
  terminalFeed: edgeiqDataPath("/data/edgeiq_vic_live_terminal_feed_v1.csv"),
  raceReliability: edgeiqDataPath("/data/edgeiq_live_race_reliability_v1_feed.csv"),
  executionQuality: edgeiqDataPath("/data/edgeiq_execution_quality_v2.csv"),
  contextualProbability: edgeiqDataPath("/data/edgeiq_probability_engine_v4_1.csv"),
  contextualProbabilityV5: edgeiqDataPath("/data/edgeiq_contextual_probability_engine_v5.csv"),
  raceShape: edgeiqDataPath("/data/edgeiq_race_shape_engine_v2.csv"),
  energyProfile: edgeiqDataPath("/data/edgeiq_horse_energy_profile_v1.csv"),
  proxyEnergy: edgeiqDataPath("/data/edgeiq_horse_energy_proxy_v1.csv"),
  capitalAllocation: edgeiqDataPath("/data/edgeiq_capital_allocation_v1.csv"),
  portfolioThrottle: edgeiqDataPath("/data/edgeiq_portfolio_throttle_v1.csv"),
  portfolioRisk: edgeiqDataPath("/data/edgeiq_portfolio_risk_v1.csv"),
  universalIdentity: edgeiqDataPath("/data/edgeiq_universal_race_identity_v2.csv"),
  orchestratorStatus: edgeiqDataPath("/data/edgeiq_truth_loop_orchestrator_v1_status.csv"),
  systemState: edgeiqDataPath("/data/edgeiq_system_state_v1.csv"),
  modelTracking: edgeiqDataPath("/data/edgeiq_model_tracking_dashboard_v1.csv"),
};
