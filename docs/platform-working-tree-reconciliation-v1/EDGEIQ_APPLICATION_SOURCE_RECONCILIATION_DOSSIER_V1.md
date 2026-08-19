# EDGEIQ Application Source Reconciliation Dossier V1

## Status

PASS - application source changes inventoried without staging, deletion, reset, stash or commit.

- Source changed items: 163
- Candidate units detected: 10
- Unresolved source items: 50

## Tracked State

- TRACKED: 161
- UNTRACKED: 2

## Candidate Unit Distribution

- SHARED_UI_COMPONENT: 71
- SOURCE_UNIT_UNRESOLVED: 50
- APPLICATION_STYLING: 20
- RACE_WORKSPACE: 7
- MAP_WORKSPACE: 5
- FORM_WORKSPACE: 3
- FRONTEND_DATA_WIRING: 3
- SHARED_TYPES: 2
- MARKET_WORKSPACE: 1
- MEETINGS_WORKSPACE: 1

## Directory Distribution

- `src/edgeiq-os/race/components`: 4
- `src/edgeiq-os/race/services`: 2
- `src/App_BEFORE_COMMAND_FIX.tsx`: 1
- `src/App_BEFORE_CONDITION_HEADER_POLISH.tsx`: 1
- `src/App_BEFORE_EXPANDABLE_WORKSHEET.tsx`: 1
- `src/App_BEFORE_EXP_LS_FIX.tsx`: 1
- `src/App_BEFORE_FORCE_RACE_BUTTON_FIX.tsx`: 1
- `src/App_BEFORE_FORCE_TAB_ONLY_LIVE_BOARD_20260614.tsx`: 1
- `src/App_BEFORE_FORMJOIN_AND_WORKSHEET.tsx`: 1
- `src/App_BEFORE_FORMTAB_REWRITE.tsx`: 1
- `src/App_BEFORE_FULL_RACE_CLICKER_REWRITE.tsx`: 1
- `src/App_BEFORE_HARD_RACE_CLICK_FIX.tsx`: 1
- `src/App_BEFORE_LINE_BASED_CURRENT_RACE_FIX.tsx`: 1
- `src/App_BEFORE_MARKET_TAPE_TAB.tsx`: 1
- `src/App_BEFORE_ORPHAN_DEBUG_CLEANUP.tsx`: 1
- `src/App_BEFORE_RACE_SELECTION_FIX.tsx`: 1
- `src/App_BEFORE_REAL_RATINGS.tsx`: 1
- `src/App_BEFORE_SHELL_REWRITE.tsx`: 1
- `src/App_BEFORE_TICKER_WIRE.tsx`: 1
- `src/App_BEFORE_TRACKING_TAB_20260614.tsx`: 1
- `src/App_MASTER_LOCK.tsx`: 1
- `src/App_UI_LOCKED.tsx`: 1
- `src/App_before_formtab_cleanup.tsx`: 1
- `src/App_before_repair.tsx`: 1
- `src/App_before_tail_repair.tsx`: 1
- `src/DashboardAnalytics.tsx`: 1
- `src/SpeedMap.tsx`: 1
- `src/components/BettingTab.tsx`: 1
- `src/components/EdgeBookieBoard.tsx`: 1
- `src/components/EdgeRaceTicker_BEFORE_WIRE.tsx`: 1
- `src/components/FormGuide.tsx`: 1
- `src/components/FormTab_BEFORE_FORMTAB_REWRITE.tsx`: 1
- `src/components/FormTab_BEFORE_FORM_WORK.tsx`: 1
- `src/components/FormTab_BEFORE_FULL_REWRITE_FIX.tsx`: 1
- `src/components/FormTab_BEFORE_LAST5_TABLE_FIX.tsx`: 1
- `src/components/FormTab_UI_LOCKED.tsx`: 1
- `src/components/GearTab.tsx`: 1
- `src/components/HorseDetailPanel.tsx`: 1
- `src/components/LiveBetsTab.tsx`: 1
- `src/components/LiveExecutionTerminal.tsx`: 1
- `src/components/LiveMarketMovers.tsx`: 1
- `src/components/LiveRaceControl.tsx`: 1
- `src/components/MarketTapeTab.tsx`: 1
- `src/components/MarketTapeTab_BEFORE_ADAPTIVE_WIRE.tsx`: 1
- `src/components/MarketTapeTab_BEFORE_MOVEMENT_BOARD.tsx`: 1
- `src/components/MarketTapeTab_BEFORE_PRIORITY_PANEL.tsx`: 1
- `src/components/MarketTapeTab_BEFORE_REGIME_WIRE.tsx`: 1
- `src/components/MarketTapeTab_LEGACY.tsx`: 1
- `src/components/MeetingRaceSelector.tsx`: 1
- `src/components/PerformanceGraph.tsx`: 1
- `src/components/PerformanceGraph_UI_LOCKED.tsx`: 1
- `src/components/PerformanceTab.tsx`: 1
- `src/components/RaceIntelligenceScreen_BEFORE_DNA_EXPLAINABILITY_PANEL_V1.tsx`: 1
- `src/components/RaceIntelligenceScreen_BEFORE_DNA_EXPLAINABILITY_UI_WIRE_V1.tsx`: 1
- `src/components/RaceIntelligenceScreen_BEFORE_DNA_V6_2_FIELD_WIRE.tsx`: 1
- `src/components/RaceIntelligenceScreen_BEFORE_DNA_V6_2_LINE_REPLACE.tsx`: 1
- `src/components/RaceIntelligenceScreen_BEFORE_FACTOR_JOIN_KEY_FIX.tsx`: 1
- `src/components/RaceIntelligenceScreen_BEFORE_FACTOR_SCORECARD_REPAIR.tsx`: 1
- `src/components/RaceIntelligenceScreen_BEFORE_FACTOR_SCORECARD_V2_PY_PATCH.tsx`: 1
- `src/components/RaceIntelligenceScreen_BEFORE_FACTOR_SCORECARD_V2_WIRE.tsx`: 1
- `src/components/RaceIntelligenceScreen_BEFORE_RUNNER_DNA_CARD_REPLACE_EXACT_V2.tsx`: 1
- `src/components/RaceIntelligenceScreen_BEFORE_RUNNER_DNA_CARD_V1.tsx`: 1
- `src/components/RaceIntelligenceScreen_BEFORE_RUNNER_DNA_DRAWER_WIRE_V1.tsx`: 1
- `src/components/RaceIntelligenceScreen_BEFORE_RUNNER_DNA_HERO_CARD_V1.tsx`: 1
- `src/components/RaceIntelligenceScreen_BEFORE_RUNNER_DNA_INTERNAL_POLISH_V1.tsx`: 1
- `src/components/RaceIntelligenceScreen_BEFORE_RUNNER_DNA_UI_V1.tsx`: 1
- `src/components/RaceIntelligenceScreen_BEFORE_RUNNER_DNA_V2_TILE_SWAP.tsx`: 1
- `src/components/RaceMarket.tsx`: 1
- `src/components/RatedPrices.tsx`: 1
- `src/components/RatingsTab.tsx`: 1
- `src/components/RatingsTab_BEFORE_COMMAND_FIX.tsx`: 1
- `src/components/RatingsTab_BEFORE_EDGE_REWRITE.tsx`: 1
- `src/components/RatingsTab_BEFORE_ELITE_VISUALS.tsx`: 1
- `src/components/RatingsTab_BEFORE_EXP_LS_FIX.tsx`: 1
- `src/components/RatingsTab_BEFORE_HEADER_SORT.tsx`: 1
- `src/components/RatingsTab_BEFORE_PRO_UPGRADE.tsx`: 1
- `src/components/RatingsTab_BEFORE_REAL_RATINGS.tsx`: 1
- `src/components/RatingsTab_UI_LOCKED.tsx`: 1
- `src/components/RunnerDetail.tsx`: 1
- `src/components/SpeedMap.tsx`: 1
- `src/components/SpeedMapIframe.tsx`: 1
- `src/components/SpeedMapPanel.tsx`: 1
- `src/components/SpeedMap_UI_LOCKED.tsx`: 1
- `src/components/Tabs.tsx`: 1
- `src/components/Tabs_BEFORE_EDGEIQ_TERMINAL_TABS.tsx`: 1
- `src/components/UpcomingStateMeetingNavigator.tsx`: 1
- `src/components/Worksheet.tsx`: 1
- `src/components/WorksheetTable.tsx`: 1
- `src/components/Worksheet_BEFORE_COMMAND_FIX.tsx`: 1
- `src/components/Worksheet_BEFORE_EXECUTION_PRIORITY_POLISH.tsx`: 1
- `src/components/Worksheet_BEFORE_EXECUTION_TERMINAL.tsx`: 1
- `src/components/Worksheet_BEFORE_EXPANDABLE_WORKSHEET.tsx`: 1
- `src/components/Worksheet_BEFORE_FINAL_POLISH.tsx`: 1
- `src/components/Worksheet_BEFORE_FORMJOIN_AND_WORKSHEET.tsx`: 1
- `src/components/Worksheet_UI_LOCKED.tsx`: 1
- `src/components/edgeiq-bookie-board.css`: 1
- `src/components/race-intelligence-screen.css`: 1
- `src/components/shell/edgeiqOsShell.css`: 1
- `src/components/ui/badge.tsx`: 1
- `src/components/ui/button.tsx`: 1
- `src/components/ui/card.tsx`: 1
- `src/components/ui/input.tsx`: 1
- `src/components/workspaces/RaceFormWorkspace.tsx`: 1
- `src/components/workspaces/RaceMarketWorkspace.tsx`: 1
- `src/components/workspaces/RaceStatsWorkspace.tsx`: 1
- `src/config/edgeiqLiveFeeds.ts`: 1
- `src/config/edgeiqLiveFeeds_BEFORE_TODAY_ONLY_DEFAULT_20260614.ts`: 1
- `src/edgeiq-os/home/EdgeiqOsHome.tsx`: 1
- `src/edgeiq-os/race/RaceFileV2.tsx`: 1
- `src/edgeiq-os/race/RaceFileV3_STABLE_BEFORE_COMPONENT_EXTRACTION_20260709.tsx`: 1
- `src/edgeiq-os/styles/edgeiqOsV2_STABLE_BEFORE_COMPONENT_EXTRACTION_20260709.css`: 1
- `src/index.css`: 1
- `src/index_BEFORE_CONDITION_HEADER_POLISH.css`: 1
- `src/index_BEFORE_EXECUTION_PRIORITY_POLISH.css`: 1
- `src/index_BEFORE_FORM_REWRITE_FIX.css`: 1
- `src/index_BEFORE_RATINGS_ALIGNMENT_FIX.css`: 1
- `src/index_BEFORE_RATINGS_ELITE_VISUALS.css`: 1
- `src/index_BEFORE_TODAY_CELL_POLISH.css`: 1
- `src/lib/formHistory.ts`: 1
- `src/lib/normalise.ts`: 1
- `src/lib/utils.ts`: 1
- `src/services/runnerMetricsService.ts`: 1
- `src/services/selectedRunnerCoreService.ts`: 1
- `src/services/selectedRunnerProfileService.ts`: 1
- `src/styles/edgeiqBrandedHomeUiV3.css`: 1
- `src/styles/edgeiqCleanProductUiV1.css`: 1
- `src/styles/edgeiqCleanProductUiV2.css`: 1
- `src/styles/edgeiqDesignSystem.css`: 1
- `src/styles/edgeiqFinalProductHomeV1.css`: 1
- `src/styles/edgeiqHomeCompactPolishV4.css`: 1
- `src/styles/edgeiqIconsBrandV1.css`: 1
- `src/styles/edgeiqOneScreenProductHomeV1.css`: 1
- `src/styles/edgeiqProductScaleGlobalV1.css`: 1
- `src/styles/edgeiqProductTerminalV1.css`: 1
- `src/styles/terminal-primitives.css`: 1
- `src/tabs/BettingEngineTab.tsx`: 1
- `src/terminal/execution/ExecutionMatrix.tsx`: 1
- `src/terminal/form/FormCentre.tsx`: 1
- `src/terminal/intelligence/IntelligenceCentre.tsx`: 1
- `src/terminal/layout/racing-terminal-overrides.css`: 1
- `src/terminal/layout/terminalTabs.ts`: 1
- `src/terminal/marketMemory/marketMemoryEngine.ts`: 1
- `src/terminal/marketMemory/marketMemoryTest.ts`: 1
- `src/terminal/markets/MarketsCommandHeader.tsx`: 1
- `src/terminal/snapshotHistory/snapshotHistoryEngine.ts`: 1
- `src/terminal/snapshotHistory/snapshotHistoryTest.ts`: 1
- `src/terminal/speed/SpeedCentre.tsx`: 1
- `src/terminal/tabs/ExecutionTab.tsx`: 1
- `src/terminal/tabs/LearningTab.tsx`: 1
- `src/terminal/tabs/MarketTab.tsx`: 1
- `src/terminal/valuation/ValuationLabHeader.tsx`: 1
- `src/types/racing.ts`: 1
- `src/types/racing_BEFORE_EDGEIQ_TERMINAL_TABS.ts`: 1
- `src/utils/chartColours.ts`: 1
- `src/utils/csv.ts`: 1
- `src/utils/format.ts`: 1
- `src/utils/pricing.ts`: 1
- `src/utils/ratings.tsx`: 1
- `src/utils/silks.ts`: 1

## Files by Candidate Unit

### APPLICATION_STYLING

- `??` `+4617 -0` `src/edgeiq-os/styles/edgeiqOsV2_STABLE_BEFORE_COMPONENT_EXTRACTION_20260709.css`
- ` M` `+1 -1` `src/index.css`
- ` M` `+1 -1` `src/index_BEFORE_CONDITION_HEADER_POLISH.css`
- ` M` `+1 -1` `src/index_BEFORE_EXECUTION_PRIORITY_POLISH.css`
- ` M` `+1 -1` `src/index_BEFORE_FORM_REWRITE_FIX.css`
- ` M` `+1 -1` `src/index_BEFORE_RATINGS_ALIGNMENT_FIX.css`
- ` M` `+1 -1` `src/index_BEFORE_RATINGS_ELITE_VISUALS.css`
- ` M` `+1 -1` `src/index_BEFORE_TODAY_CELL_POLISH.css`
- ` M` `+1 -1` `src/styles/edgeiqBrandedHomeUiV3.css`
- ` M` `+1 -1` `src/styles/edgeiqCleanProductUiV1.css`
- ` M` `+1 -1` `src/styles/edgeiqCleanProductUiV2.css`
- ` M` `+14 -13` `src/styles/edgeiqDesignSystem.css`
- ` M` `+1 -1` `src/styles/edgeiqFinalProductHomeV1.css`
- ` M` `+1 -1` `src/styles/edgeiqHomeCompactPolishV4.css`
- ` M` `+1 -1` `src/styles/edgeiqIconsBrandV1.css`
- ` M` `+1 -1` `src/styles/edgeiqOneScreenProductHomeV1.css`
- ` M` `+1 -1` `src/styles/edgeiqProductScaleGlobalV1.css`
- ` M` `+1 -1` `src/styles/edgeiqProductTerminalV1.css`
- ` M` `+1 -1` `src/styles/terminal-primitives.css`
- ` M` `+31 -31` `src/terminal/layout/racing-terminal-overrides.css`

### FORM_WORKSPACE

- ` M` `+1 -1` `src/components/FormGuide.tsx`
- ` M` `+1 -1` `src/components/workspaces/RaceFormWorkspace.tsx`
- ` M` `+1 -1` `src/terminal/form/FormCentre.tsx`

### FRONTEND_DATA_WIRING

- ` M` `+1 -1` `src/services/runnerMetricsService.ts`
- ` M` `+1 -1` `src/services/selectedRunnerCoreService.ts`
- ` M` `+1 -1` `src/services/selectedRunnerProfileService.ts`

### MAP_WORKSPACE

- ` M` `+1 -1` `src/SpeedMap.tsx`
- ` M` `+1 -1` `src/components/SpeedMap.tsx`
- ` M` `+1 -1` `src/components/SpeedMapIframe.tsx`
- ` M` `+1 -1` `src/components/SpeedMapPanel.tsx`
- ` M` `+1 -1` `src/components/SpeedMap_UI_LOCKED.tsx`

### MARKET_WORKSPACE

- ` M` `+1 -1` `src/components/workspaces/RaceMarketWorkspace.tsx`

### MEETINGS_WORKSPACE

- ` M` `+1 -0` `src/edgeiq-os/race/components/MeetingWorkspace.tsx`

### RACE_WORKSPACE

- ` M` `+2 -2` `src/edgeiq-os/race/RaceFileV2.tsx`
- `??` `+636 -0` `src/edgeiq-os/race/RaceFileV3_STABLE_BEFORE_COMPONENT_EXTRACTION_20260709.tsx`
- ` M` `+3 -2` `src/edgeiq-os/race/components/MapWorkspace.tsx`
- ` M` `+13 -12` `src/edgeiq-os/race/components/MarketWorkspace.tsx`
- ` M` `+397 -112` `src/edgeiq-os/race/components/RaceFormGuideWorkspace.tsx`
- ` M` `+151 -1` `src/edgeiq-os/race/services/epiWorkspaceFeed.ts`
- ` M` `+3 -1` `src/edgeiq-os/race/services/threeDayCatalog.ts`

### SHARED_TYPES

- ` M` `+1 -1` `src/types/racing.ts`
- ` M` `+1 -1` `src/types/racing_BEFORE_EDGEIQ_TERMINAL_TABS.ts`

### SHARED_UI_COMPONENT

- ` M` `+1 -1` `src/components/BettingTab.tsx`
- ` M` `+1 -1` `src/components/EdgeBookieBoard.tsx`
- ` M` `+1 -1` `src/components/EdgeRaceTicker_BEFORE_WIRE.tsx`
- ` M` `+1 -1` `src/components/FormTab_BEFORE_FORMTAB_REWRITE.tsx`
- ` M` `+1 -1` `src/components/FormTab_BEFORE_FORM_WORK.tsx`
- ` M` `+1 -1` `src/components/FormTab_BEFORE_FULL_REWRITE_FIX.tsx`
- ` M` `+1 -1` `src/components/FormTab_BEFORE_LAST5_TABLE_FIX.tsx`
- ` M` `+1 -1` `src/components/FormTab_UI_LOCKED.tsx`
- ` M` `+1 -1` `src/components/GearTab.tsx`
- ` M` `+1 -1` `src/components/HorseDetailPanel.tsx`
- ` M` `+1 -1` `src/components/LiveBetsTab.tsx`
- ` M` `+1 -1` `src/components/LiveExecutionTerminal.tsx`
- ` M` `+1 -1` `src/components/LiveMarketMovers.tsx`
- ` M` `+1 -1` `src/components/LiveRaceControl.tsx`
- ` M` `+1 -1` `src/components/MarketTapeTab.tsx`
- ` M` `+1 -1` `src/components/MarketTapeTab_BEFORE_ADAPTIVE_WIRE.tsx`
- ` M` `+1 -1` `src/components/MarketTapeTab_BEFORE_MOVEMENT_BOARD.tsx`
- ` M` `+1 -1` `src/components/MarketTapeTab_BEFORE_PRIORITY_PANEL.tsx`
- ` M` `+1 -1` `src/components/MarketTapeTab_BEFORE_REGIME_WIRE.tsx`
- ` M` `+1 -1` `src/components/MarketTapeTab_LEGACY.tsx`
- ` M` `+1 -1` `src/components/MeetingRaceSelector.tsx`
- ` M` `+1 -1` `src/components/PerformanceGraph.tsx`
- ` M` `+1 -1` `src/components/PerformanceGraph_UI_LOCKED.tsx`
- ` M` `+1 -1` `src/components/PerformanceTab.tsx`
- ` M` `+1 -1` `src/components/RaceIntelligenceScreen_BEFORE_DNA_EXPLAINABILITY_PANEL_V1.tsx`
- ` M` `+1 -1` `src/components/RaceIntelligenceScreen_BEFORE_DNA_EXPLAINABILITY_UI_WIRE_V1.tsx`
- ` M` `+1 -1` `src/components/RaceIntelligenceScreen_BEFORE_DNA_V6_2_FIELD_WIRE.tsx`
- ` M` `+1 -1` `src/components/RaceIntelligenceScreen_BEFORE_DNA_V6_2_LINE_REPLACE.tsx`
- ` M` `+1 -1` `src/components/RaceIntelligenceScreen_BEFORE_FACTOR_JOIN_KEY_FIX.tsx`
- ` M` `+1 -1` `src/components/RaceIntelligenceScreen_BEFORE_FACTOR_SCORECARD_REPAIR.tsx`
- ` M` `+1 -1` `src/components/RaceIntelligenceScreen_BEFORE_FACTOR_SCORECARD_V2_PY_PATCH.tsx`
- ` M` `+1 -1` `src/components/RaceIntelligenceScreen_BEFORE_FACTOR_SCORECARD_V2_WIRE.tsx`
- ` M` `+1 -1` `src/components/RaceIntelligenceScreen_BEFORE_RUNNER_DNA_CARD_REPLACE_EXACT_V2.tsx`
- ` M` `+1 -1` `src/components/RaceIntelligenceScreen_BEFORE_RUNNER_DNA_CARD_V1.tsx`
- ` M` `+1 -1` `src/components/RaceIntelligenceScreen_BEFORE_RUNNER_DNA_DRAWER_WIRE_V1.tsx`
- ` M` `+1 -1` `src/components/RaceIntelligenceScreen_BEFORE_RUNNER_DNA_HERO_CARD_V1.tsx`
- ` M` `+1 -1` `src/components/RaceIntelligenceScreen_BEFORE_RUNNER_DNA_INTERNAL_POLISH_V1.tsx`
- ` M` `+1 -1` `src/components/RaceIntelligenceScreen_BEFORE_RUNNER_DNA_UI_V1.tsx`
- ` M` `+1 -1` `src/components/RaceIntelligenceScreen_BEFORE_RUNNER_DNA_V2_TILE_SWAP.tsx`
- ` M` `+1 -1` `src/components/RaceMarket.tsx`
- ` M` `+1 -1` `src/components/RatedPrices.tsx`
- ` M` `+1 -1` `src/components/RatingsTab.tsx`
- ` M` `+1 -1` `src/components/RatingsTab_BEFORE_COMMAND_FIX.tsx`
- ` M` `+1 -1` `src/components/RatingsTab_BEFORE_EDGE_REWRITE.tsx`
- ` M` `+1 -1` `src/components/RatingsTab_BEFORE_ELITE_VISUALS.tsx`
- ` M` `+1 -1` `src/components/RatingsTab_BEFORE_EXP_LS_FIX.tsx`
- ` M` `+1 -1` `src/components/RatingsTab_BEFORE_HEADER_SORT.tsx`
- ` M` `+1 -1` `src/components/RatingsTab_BEFORE_PRO_UPGRADE.tsx`
- ` M` `+1 -1` `src/components/RatingsTab_BEFORE_REAL_RATINGS.tsx`
- ` M` `+1 -1` `src/components/RatingsTab_UI_LOCKED.tsx`
- ` M` `+1 -1` `src/components/RunnerDetail.tsx`
- ` M` `+1 -1` `src/components/Tabs.tsx`
- ` M` `+1 -1` `src/components/Tabs_BEFORE_EDGEIQ_TERMINAL_TABS.tsx`
- ` M` `+1 -1` `src/components/UpcomingStateMeetingNavigator.tsx`
- ` M` `+1 -1` `src/components/Worksheet.tsx`
- ` M` `+1 -1` `src/components/WorksheetTable.tsx`
- ` M` `+1 -1` `src/components/Worksheet_BEFORE_COMMAND_FIX.tsx`
- ` M` `+1 -1` `src/components/Worksheet_BEFORE_EXECUTION_PRIORITY_POLISH.tsx`
- ` M` `+1 -1` `src/components/Worksheet_BEFORE_EXECUTION_TERMINAL.tsx`
- ` M` `+1 -1` `src/components/Worksheet_BEFORE_EXPANDABLE_WORKSHEET.tsx`
- ` M` `+1 -1` `src/components/Worksheet_BEFORE_FINAL_POLISH.tsx`
- ` M` `+1 -1` `src/components/Worksheet_BEFORE_FORMJOIN_AND_WORKSHEET.tsx`
- ` M` `+1 -1` `src/components/Worksheet_UI_LOCKED.tsx`
- ` M` `+1 -1` `src/components/edgeiq-bookie-board.css`
- ` M` `+1 -1` `src/components/race-intelligence-screen.css`
- ` M` `+69 -0` `src/components/shell/edgeiqOsShell.css`
- ` M` `+1 -1` `src/components/ui/badge.tsx`
- ` M` `+1 -1` `src/components/ui/button.tsx`
- ` M` `+1 -1` `src/components/ui/card.tsx`
- ` M` `+1 -1` `src/components/ui/input.tsx`
- ` M` `+1 -1` `src/components/workspaces/RaceStatsWorkspace.tsx`

### SOURCE_UNIT_UNRESOLVED

- ` M` `+1 -1` `src/App_BEFORE_COMMAND_FIX.tsx`
- ` M` `+2 -2` `src/App_BEFORE_CONDITION_HEADER_POLISH.tsx`
- ` M` `+1 -1` `src/App_BEFORE_EXPANDABLE_WORKSHEET.tsx`
- ` M` `+1 -1` `src/App_BEFORE_EXP_LS_FIX.tsx`
- ` M` `+2 -2` `src/App_BEFORE_FORCE_RACE_BUTTON_FIX.tsx`
- ` M` `+2 -2` `src/App_BEFORE_FORCE_TAB_ONLY_LIVE_BOARD_20260614.tsx`
- ` M` `+1 -1` `src/App_BEFORE_FORMJOIN_AND_WORKSHEET.tsx`
- ` M` `+1 -1` `src/App_BEFORE_FORMTAB_REWRITE.tsx`
- ` M` `+2 -2` `src/App_BEFORE_FULL_RACE_CLICKER_REWRITE.tsx`
- ` M` `+2 -2` `src/App_BEFORE_HARD_RACE_CLICK_FIX.tsx`
- ` M` `+2 -2` `src/App_BEFORE_LINE_BASED_CURRENT_RACE_FIX.tsx`
- ` M` `+2 -2` `src/App_BEFORE_MARKET_TAPE_TAB.tsx`
- ` M` `+2 -2` `src/App_BEFORE_ORPHAN_DEBUG_CLEANUP.tsx`
- ` M` `+2 -2` `src/App_BEFORE_RACE_SELECTION_FIX.tsx`
- ` M` `+1 -1` `src/App_BEFORE_REAL_RATINGS.tsx`
- ` M` `+1 -1` `src/App_BEFORE_SHELL_REWRITE.tsx`
- ` M` `+2 -2` `src/App_BEFORE_TICKER_WIRE.tsx`
- ` M` `+2 -2` `src/App_BEFORE_TRACKING_TAB_20260614.tsx`
- ` M` `+1 -1` `src/App_MASTER_LOCK.tsx`
- ` M` `+1 -1` `src/App_UI_LOCKED.tsx`
- ` M` `+1 -1` `src/App_before_formtab_cleanup.tsx`
- ` M` `+1 -1` `src/App_before_repair.tsx`
- ` M` `+1 -1` `src/App_before_tail_repair.tsx`
- ` M` `+1 -1` `src/DashboardAnalytics.tsx`
- ` M` `+1 -1` `src/config/edgeiqLiveFeeds.ts`
- ` M` `+1 -1` `src/config/edgeiqLiveFeeds_BEFORE_TODAY_ONLY_DEFAULT_20260614.ts`
- ` M` `+215 -157` `src/edgeiq-os/home/EdgeiqOsHome.tsx`
- ` M` `+1 -1` `src/lib/formHistory.ts`
- ` M` `+1 -1` `src/lib/normalise.ts`
- ` M` `+1 -1` `src/lib/utils.ts`
- ` M` `+1 -1` `src/tabs/BettingEngineTab.tsx`
- ` M` `+1 -1` `src/terminal/execution/ExecutionMatrix.tsx`
- ` M` `+1 -1` `src/terminal/intelligence/IntelligenceCentre.tsx`
- ` M` `+1 -1` `src/terminal/layout/terminalTabs.ts`
- ` M` `+1 -1` `src/terminal/marketMemory/marketMemoryEngine.ts`
- ` M` `+1 -1` `src/terminal/marketMemory/marketMemoryTest.ts`
- ` M` `+1 -1` `src/terminal/markets/MarketsCommandHeader.tsx`
- ` M` `+1 -1` `src/terminal/snapshotHistory/snapshotHistoryEngine.ts`
- ` M` `+1 -1` `src/terminal/snapshotHistory/snapshotHistoryTest.ts`
- ` M` `+1 -1` `src/terminal/speed/SpeedCentre.tsx`
- ` M` `+1 -1` `src/terminal/tabs/ExecutionTab.tsx`
- ` M` `+1 -1` `src/terminal/tabs/LearningTab.tsx`
- ` M` `+1 -1` `src/terminal/tabs/MarketTab.tsx`
- ` M` `+1 -1` `src/terminal/valuation/ValuationLabHeader.tsx`
- ` M` `+1 -1` `src/utils/chartColours.ts`
- ` M` `+1 -1` `src/utils/csv.ts`
- ` M` `+1 -1` `src/utils/format.ts`
- ` M` `+1 -1` `src/utils/pricing.ts`
- ` M` `+1 -1` `src/utils/ratings.tsx`
- ` M` `+1 -1` `src/utils/silks.ts`

## Governance Decision

Candidate-unit assignment is forensic classification only. It does not authorise staging or committing.
Each source group must be matched against its builder, audit, evidence and acceptance artefacts before becoming a governed commit unit.
