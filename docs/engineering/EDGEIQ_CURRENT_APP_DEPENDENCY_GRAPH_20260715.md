# EDGEiQ Current App Dependency Graph

Generated: 2026-07-15T17:47:54

Scope: current production application dependency chain for visible racing intelligence. This is documentation only and does not modify feeds or UI.

## Current Validation Context

- Coverage input: `public\data\edgeiq_data_coverage_report_v1.json`
- End-to-end input: `public\data\edgeiq_end_to_end_validation_v1.json`
- Selected E2E race: `not available`

## Visible Field Dependency Graph

| Workspace | Field | Component | Service | Builder | Generated Feed | Race Identity Key | Runner Identity Key | Matching Function | Current Coverage | Displayed | Failure Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Form Guide / Field / Market / EPI | EPI | RaceFormGuideWorkspace.tsx; EpiWorkspaceWorkspace.tsx; MarketWorkspace.tsx | formGuideEnrichedFeed.ts; formGuideNormaliser.ts; epiWorkspaceFeed.ts; marketFeed.ts | build_edgeiq_form_guide_enriched_v2.py; build_edgeiq_epi_workspace_terminal_feed_v1.py; build_edgeiq_market_terminal_feed_v1.py | edgeiq_form_guide_enriched_v2.json; edgeiq_epi_workspace_terminal_feed_v1.csv; edgeiq_market_terminal_feed_v1.csv | form enrichment uses date\|normalised track\|race number; terminal feeds use race_key exact match | runner_id, normalised runner name, no/saddlecloth fallback | findEnrichedFormGuideRace; normaliseFormGuideRace; buildEpiWorkspaceViewModel; buildMarketViewModel | 395/503 (78.53%%) PARTIAL | yes | partial coverage remains where current-date governed EPI is absent or runner identity is unmatched |
| Form Guide / Market | EDGEiQ Price | RaceFormGuideWorkspace.tsx; MarketWorkspace.tsx | formGuideEnrichedFeed.ts; formGuideNormaliser.ts; marketFeed.ts | build_edgeiq_form_guide_enriched_v2.py; build_edgeiq_market_terminal_feed_v1.py | edgeiq_form_guide_enriched_v2.json; edgeiq_market_terminal_feed_v1.csv | form enrichment uses date\|normalised track\|race number; market terminal uses race_key exact match | normalised runner name and runner number | normaliseFormGuideRace; buildMarketViewModel | 459/503 (91.25%%) PARTIAL | yes | remaining gaps are missing governed price rows, scratched runners, or unmatched current-race identity |
| Form Guide / MAP | early speed | RaceFormGuideWorkspace.tsx; MapWorkspace.tsx | formGuideNormaliser.ts; mapFeed.ts | build_edgeiq_current_early_speed_v1.py; build_edgeiq_map_terminal_feed_v1.py | edgeiq_form_guide_enriched_v2.json; edgeiq_map_terminal_feed_v1.csv | form enrichment key or race_key exact match for map terminal | normalised runner name, runner number | normaliseFormGuideRace; matchTerminalRow | 252/503 (50.10%%) PARTIAL | yes where present | map terminal exact race_key can miss when current raceKey format differs from generated terminal feed |
| Form Guide | late speed | RaceFormGuideWorkspace.tsx | formGuideNormaliser.ts | build_edgeiq_current_late_speed_v1.py; build_edgeiq_form_guide_enriched_v2.py | edgeiq_form_guide_enriched_v2.json | date\|normalised track\|race number | runner_id, strict composite, normalised runner name | findEnrichedFormGuideRace; normaliseFormGuideRace | 257/503 (51.09%%) PARTIAL | yes where present | missing where no governed late-speed value exists for current runner or enrichment join fails |
| Form Guide / Insights | suitability | RaceFormGuideWorkspace.tsx; InsightsWorkspace.tsx | formGuideNormaliser.ts; insightsFeed.ts | build_edgeiq_current_suitability_v1.py; build_edgeiq_insights_terminal_feed_v1.py | edgeiq_form_guide_enriched_v2.json; edgeiq_insights_terminal_feed_v1.csv | date\|normalised track\|race number for form; exact race_key for insights | runner_id, normalised runner name, no | normaliseFormGuideRace; buildInsightsViewModel | 385/503 (76.54%%) PARTIAL | yes where present | insights remain empty when terminal race_key has no exact selected-race match or evidence category missing |
| Form Guide / Insights | form momentum | RaceFormGuideWorkspace.tsx; InsightsWorkspace.tsx | formGuideNormaliser.ts; insightsFeed.ts | build_edgeiq_current_form_momentum_v1.py; build_edgeiq_insights_terminal_feed_v1.py | edgeiq_form_guide_enriched_v2.json; edgeiq_insights_terminal_feed_v1.csv | date\|normalised track\|race number for form; exact race_key for insights | runner_id, normalised runner name, no | normaliseFormGuideRace; buildInsightsViewModel | 389/503 (77.34%%) PARTIAL | yes where present | missing where no governed momentum exists or insights evidence is unmatched |
| Form Guide recent form / Results | ERI | RaceFormGuideWorkspace.tsx; ResultsWorkspace.tsx | formGuideNormaliser.ts; resultsFeed.ts | build_edgeiq_form_guide_enriched_v2.py; build_edgeiq_meeting_results_terminal_feed_v1.py | edgeiq_form_guide_enriched_v2.json; edgeiq_meeting_results_terminal_feed_v1.csv | date\|normalised track\|race number or meeting_key+race_key | historical runner identity from enriched full form | normaliseFormGuideRace; matchRow | None/211 (0.00%%) NOT READY | displayed as blank when absent | current report shows no governed ERI coverage in current app feeds |
| Form Guide / Market | market | RaceFormGuideWorkspace.tsx; MarketWorkspace.tsx | formGuideNormaliser.ts; marketFeed.ts | build_edgeiq_form_guide_enriched_v2.py; build_edgeiq_market_terminal_feed_v1.py | edgeiq_form_guide_enriched_v2.json; edgeiq_market_terminal_feed_v1.csv | date\|normalised track\|race number for form; exact race_key for market terminal | normalised runner name, no | normaliseFormGuideRace; matchTerminalRow | 87/503 (17.30%%) PARTIAL | yes when present; Pending Market when absent | partial because live market values are unavailable, stale, scratched, suspended, or unmatched |
| Market | market fluctuation | MarketWorkspace.tsx | marketFeed.ts | build_edgeiq_market_terminal_feed_v1.py | edgeiq_market_terminal_feed_v1.csv | exact race_key | normalised runner name, no | matchTerminalRow | 87/503 (17.30%%) PARTIAL | yes where move is supplied | not shown when move field is blank or terminal row is unmatched |
| MAP | map lane/order | MapWorkspace.tsx | mapFeed.ts | build_edgeiq_map_terminal_feed_v1.py | edgeiq_map_terminal_feed_v1.csv | exact race_key | normalised runner name, no | matchTerminalRow; raceRows | None/211 (0.00%%) NOT READY | race-context fallback displays runners; governed map evidence only when present | matched_current_map_rows can remain zero when exact race_key or governed map evidence does not align |
| MAP / Insights | runner style | MapWorkspace.tsx; InsightsWorkspace.tsx | mapFeed.ts; insightsFeed.ts | build_edgeiq_map_terminal_feed_v1.py; build_edgeiq_insights_terminal_feed_v1.py | edgeiq_map_terminal_feed_v1.csv; edgeiq_insights_terminal_feed_v1.csv | exact race_key | normalised runner name, no | matchTerminalRow; buildInsightsViewModel | None/211 (0.00%%) NOT READY | yes where run_style exists | blank/pending when no governed style row is present |
| EPI | historical EPI tiles | EpiWorkspaceWorkspace.tsx | epiWorkspaceFeed.ts | build_edgeiq_epi_workspace_terminal_feed_v1.py | edgeiq_epi_workspace_terminal_feed_v1.csv | exact race_key | horse/no within terminal row | buildEpiWorkspaceViewModel; rowFromTerminal | not separately reported | yes where tile values are supplied | current summary reports historical_tiles=0, likely missing governed historical EPI source or join |
| Insights | runner insights | InsightsWorkspace.tsx | insightsFeed.ts | build_edgeiq_insights_terminal_feed_v1.py | edgeiq_insights_terminal_feed_v1.csv | exact race_key | no/horse in terminal row | buildInsightsViewModel | not separately reported | yes where card/runner evidence rows match | matched_intelligence=0 indicates no governed evidence rows matched current selected race |
| Overview | race overview | OverviewWorkspace.tsx | overviewFeed.ts | build_edgeiq_overview_terminal_feed_v1.py | edgeiq_overview_terminal_feed_v1.csv | exact race_key | race-level only | buildOverviewViewModel | not separately reported | yes where overview rows match | overview rows are unavailable when exact selected race_key is not present in terminal feed |
| Meeting Scratchings / Form Guide | scratchings | MeetingScratchingsWorkspace.tsx; RaceFormGuideWorkspace.tsx | scratchingsFeed.ts; formGuideNormaliser.ts | current catalogue and scratchings builders | edgeiq_form_guide_enriched_v2.json; three-day catalogue | meeting/race keys from catalogue | runner_id, runner name, no | normaliseFormGuideRace | 106/211 (50.24%%) PARTIAL | yes where supplied | partial where source catalogue has no scratching status for runner |
| Field / Form Guide / MAP | barriers | RaceFormGuideWorkspace.tsx; MapWorkspace.tsx | formGuideNormaliser.ts; mapFeed.ts; threeDayCatalog.ts | three-day catalogue builders; form-guide enrichment | edgeiq_form_guide_enriched_v2.json; edgeiq_map_terminal_feed_v1.csv; three-day catalogue JSON | raceKey or date\|track\|raceNo | runner_id, no, runner name | normaliseFormGuideRace; raceRows | not separately reported | yes where source has barrier | remaining gaps usually source omissions or stale current catalogue identity |
| Field / Form Guide / MAP | weights | RaceFormGuideWorkspace.tsx; MapWorkspace.tsx | formGuideNormaliser.ts; mapFeed.ts | three-day catalogue builders; form-guide enrichment | edgeiq_form_guide_enriched_v2.json; edgeiq_map_terminal_feed_v1.csv | raceKey or date\|track\|raceNo | runner_id, no, runner name | normaliseFormGuideRace; runnerWeight | not separately reported | yes where source has weight | remaining gaps are current source omissions, not calculated in React |
| Field / Form Guide / MAP / Results | jockey | RaceFormGuideWorkspace.tsx; MapWorkspace.tsx; ResultsWorkspace.tsx | formGuideNormaliser.ts; mapFeed.ts; resultsFeed.ts | three-day catalogue builders; form-guide enrichment; results terminal builder | edgeiq_form_guide_enriched_v2.json; edgeiq_map_terminal_feed_v1.csv; edgeiq_meeting_results_terminal_feed_v1.csv | raceKey or date\|track\|raceNo | runner_id, no, runner name | normaliseFormGuideRace; runnerJockey; matchRow | not separately reported | yes where source has jockey | remaining gaps are source omissions or race-key mismatch |
| Field / Form Guide / MAP / Results | trainer | RaceFormGuideWorkspace.tsx; MapWorkspace.tsx; ResultsWorkspace.tsx | formGuideNormaliser.ts; mapFeed.ts; resultsFeed.ts | three-day catalogue builders; form-guide enrichment; results terminal builder | edgeiq_form_guide_enriched_v2.json; edgeiq_map_terminal_feed_v1.csv; edgeiq_meeting_results_terminal_feed_v1.csv | raceKey or date\|track\|raceNo | runner_id, no, runner name | normaliseFormGuideRace; runnerTrainer; matchRow | not separately reported | yes where source has trainer | remaining gaps are source omissions or race-key mismatch |
| Meeting Gear / Form Guide | gear | MeetingGearChangesWorkspace.tsx; RaceFormGuideWorkspace.tsx | gearChangesFeed.ts; formGuideNormaliser.ts | build_edgeiq_gear_terminal_feed_v1.py; build_edgeiq_form_guide_enriched_v2.py | edgeiq_gear_terminal_feed_v1.csv; edgeiq_form_guide_enriched_v2.json | race_key / date\|track\|raceNo depending feed | normalised runner name, no, runner_id where present | gearChangesFeed service; normaliseFormGuideRace | None/503 (0.00%%) NOT READY | current gear only where supplied | current terminal gear feed reports source_confidence=current_gear_not_supplied for most/all rows |
| Results / Review | race results | ResultsWorkspace.tsx; MeetingResultsWorkspace.tsx; RaceWorkspace.tsx REVIEW | resultsFeed.ts | build_edgeiq_meeting_results_terminal_feed_v1.py | edgeiq_meeting_results_terminal_feed_v1.csv | meeting_key+race_key, then date+normalised track+raceNo fallback | result runner rows when individual results exist | matchRow; buildMeetingResultsViewModel | None/None (0.00%%) NOT READY | pending/unavailable for future races | current/future races correctly withhold result rows until official result feed arrives |
| Form Guide | historical form | RaceFormGuideWorkspace.tsx | formGuideEnrichedFeed.ts; formGuideNormaliser.ts | build_edgeiq_form_guide_enriched_v2.py | edgeiq_form_guide_enriched_v2.json | date\|normalised track\|race number | runner_id, strict composite, normalised runner name | findEnrichedFormGuideRace; normaliseFormGuideRace | 503/503 (100.00%%) READY | yes | reported as ready in beta coverage |
| Form Guide | recent form | RaceFormGuideWorkspace.tsx | formGuideNormaliser.ts | build_edgeiq_form_guide_enriched_v2.py | edgeiq_form_guide_enriched_v2.json | date\|normalised track\|race number | runner_id, strict composite, normalised runner name | normaliseFormGuideRace | 503/503 (100.00%%) READY | yes | reported as ready in beta coverage |
| Form Guide / Results | sectionals | RaceFormGuideWorkspace.tsx; ResultsWorkspace.tsx | formGuideNormaliser.ts; resultsFeed.ts | build_edgeiq_form_guide_enriched_v2.py; build_edgeiq_meeting_results_terminal_feed_v1.py | edgeiq_form_guide_enriched_v2.json; edgeiq_meeting_results_terminal_feed_v1.csv | date\|normalised track\|race number | historical runner identity | normaliseFormGuideRace | 462/503 (91.85%%) PARTIAL | yes where supplied | some split segments remain blank where governed benchmark evidence is absent |

## Generated Feed Inventory

| Feed | Exists | Rows | Available Columns / Shape |
| --- | --- | --- | --- |
| edgeiq_form_guide_enriched_v2.json | yes | 40 | json:races, json:runners=503 |
| edgeiq_epi_workspace_terminal_feed_v1.csv | yes | 211 | workspace_id, meeting_key, race_key, generated_at, race_date, track, race_no, no, horse, current_epi, rank, field_avg, diff, start_10, start_9, start_8 |
| edgeiq_market_terminal_feed_v1.csv | yes | 211 | workspace_id, meeting_key, race_key, generated_at, race_date, track, race_no, no, horse, epi, market, open, high, low, move, edgeiq_price |
| edgeiq_map_terminal_feed_v1.csv | yes | 211 | workspace_id, meeting_key, race_key, generated_at, race_date, track, race_no, no, horse, barrier, effective_barrier, run_style, early_speed, projected_position, source, source_timestamp |
| edgeiq_insights_terminal_feed_v1.csv | yes | 291 | workspace_id, meeting_key, race_key, generated_at, race_date, track, race_no, row_kind, card_type, card_title, card_value, card_detail, no, horse, key_insight, edge |
| edgeiq_meeting_results_terminal_feed_v1.csv | yes | 15 | meeting_key, race_key, race_date, track, race_no, time, winner, jockey, trainer, sp_tab, margin, official_time, track_condition, status, open, source |
| edgeiq_overview_terminal_feed_v1.csv | yes | 96 | workspace_id, meeting_key, race_key, generated_at, race_date, track, race_no, section, evidence, source, status, open, source_timestamp, source_confidence, row_status |
| three-day catalogue | no | 0 |  |
| three-day catalogue JSON | no | 0 |  |
| edgeiq_gear_terminal_feed_v1.csv | yes | 211 | race_date, track, race_no, race_key, runner, normalized_runner, gear_current, gear_changes, gear_added, gear_removed, first_time_gear, gear_change_flag, source_confidence |

## Service Loader And Matching Inventory

| Service | Loaded URL | View Builder | Matching / Normalisation Functions |
| --- | --- | --- | --- |
| epiWorkspaceFeed.ts | /data/edgeiq_epi_workspace_terminal_feed_v1.csv | buildEpiWorkspaceViewModel |  |
| formGuideEnrichedFeed.ts | /data/edgeiq_form_guide_enriched_v2.json | findEnrichedFormGuideRace | normaliseTrack, raceKeyFromParts |
| formGuideEnrichedFeed_CHECKPOINT_BEFORE_ALL_RUNNER_V1_20260711_075326.ts | /data/edgeiq_form_guide_enriched_v1.json | findEnrichedFormGuideRace | normaliseTrack, raceKeyFromParts |
| formGuideEnrichedFeed_CHECKPOINT_BEFORE_ENGINE_WIRING_V3_4_20260711_114946.ts | /data/edgeiq_form_guide_enriched_v1.json | findEnrichedFormGuideRace | normaliseTrack, raceKeyFromParts |
| formGuideEnrichedFeed_CHECKPOINT_BEFORE_FORM_GUIDE_V3_20260711_063656.ts | /data/edgeiq_form_guide_enriched_v1.json | findEnrichedFormGuideRace | normaliseTrack, raceKeyFromParts |
| formGuideEnrichedFeed_CHECKPOINT_BEFORE_FORM_GUIDE_V3_3_20260711_095927.ts | /data/edgeiq_form_guide_enriched_v1.json | findEnrichedFormGuideRace | normaliseTrack, raceKeyFromParts |
| formGuideNormaliser.ts |  | normaliseFormGuideRace | normaliseRunnerName, runnerName, runnerNo |
| formGuideNormaliser_CHECKPOINT_BEFORE_ALL_RUNNER_V1_20260711_075326.ts |  | normaliseFormGuideRace | normaliseRunnerName, runnerName, runnerNo |
| formGuideNormaliser_CHECKPOINT_BEFORE_ENGINE_WIRING_V3_4_20260711_114946.ts |  | normaliseFormGuideRace | normaliseRunnerName, runnerName, runnerNo |
| formGuideNormaliser_CHECKPOINT_BEFORE_FORM_GUIDE_V2_20260710_152416.ts |  | normaliseFormGuideRace | runnerName, runnerNo |
| formGuideNormaliser_CHECKPOINT_BEFORE_FORM_GUIDE_V3_20260711_063656.ts |  | normaliseFormGuideRace | normaliseRunnerName, runnerName, runnerNo |
| formGuideNormaliser_CHECKPOINT_BEFORE_FORM_GUIDE_V3_3_20260711_095927.ts |  | normaliseFormGuideRace | normaliseRunnerName, runnerName, runnerNo |
| gearChangesFeed.ts | /data/edgeiq_gear_terminal_feed_v1.csv | buildMeetingGearChangesViewModel | normaliseTrack, runnerName |
| insightsFeed.ts | /data/edgeiq_insights_terminal_feed_v1.csv | buildInsightsViewModel |  |
| mapFeed.ts | /data/edgeiq_map_terminal_feed_v1.csv | buildMapViewModel | matchTerminalRow, runnerName, runnerNo |
| marketFeed.ts | /data/edgeiq_market_terminal_feed_v1.csv | buildMarketViewModel | matchTerminalRow, runnerName, runnerNo |
| meetingDetailFeed.ts |  | buildMeetingDetailViewModel |  |
| overviewFeed.ts | /data/edgeiq_overview_terminal_feed_v1.csv | buildOverviewViewModel |  |
| resultsFeed.ts | /data/edgeiq_meeting_results_terminal_feed_v1.csv | buildIndividualRaceResultViewModel, buildMeetingResultsViewModel | matchRow, normaliseTrack, runnerName |
| runnerProfileStats.ts |  |  | normaliseRunnerName |
| runnerProfileStats_CHECKPOINT_BEFORE_CAREER_PROFILE_GRID_V2_20260710_080314.ts |  |  | normaliseRunnerName |
| runnerProfileStats_CHECKPOINT_BEFORE_FINAL_RUNNER_PROFILE_LAYOUT_20260710_091357.ts |  |  | normaliseRunnerName |
| runnerProfileStats_CHECKPOINT_BEFORE_PRO_PUNTER_LANGUAGE_20260710_060812.ts |  |  | normaliseRunnerName |
| runnerProfileStats_CHECKPOINT_BEFORE_PROFILE_MATCH_AUDIT_20260710_050735.ts |  |  | normaliseRunnerName |
| runnerProfileStats_CHECKPOINT_BEFORE_PROFILE_STATS_DISPLAY_FIX_20260710_053620.ts |  |  | normaliseRunnerName |
| runnerProfileStats_CHECKPOINT_BEFORE_RACING_RECORD_FORMAT_20260710_082623.ts |  |  | normaliseRunnerName |
| scratchingsFeed.ts |  | buildMeetingScratchingsViewModel | runnerName |
| threeDayCatalog.ts | /data/edgeiq_three_day_product_catalog_v1.json |  |  |
| threeDayCatalog_CHECKPOINT_BEFORE_THREE_DAY_ROUTING_FINAL_20260710_130642.ts | /data/edgeiq_three_day_product_catalog_v1.json |  |  |
| trackFeed.ts |  | buildMeetingTrackViewModel | normaliseTrack |
| trackMapAssets.ts |  |  | normaliseTrack |
| weatherFeed.ts |  | buildMeetingWeatherViewModel |  |

## Main Dependency Findings

- Form Guide enrichment uses `findEnrichedFormGuideRace`, which compares `raceDate|normalised track|raceNumber`.
- MAP, Market, Overview, Insights and EPI terminal services primarily use exact `race_key` matching.
- The most likely zero-match class is exact `race_key` mismatch between selected current race keys and generated terminal feeds, not React calculation failure.
- Race context fallback is present in MAP and Market so listed runners can render without fabricating governed values.
- React fetch guards reject oversized CSV feeds over 10,000 rows in the terminal services inspected here.
- Missing governed values should continue to display blank, pending or unavailable states rather than synthetic defaults.

## Required Field Coverage

Covered fields: EPI, EDGEiQ Price, early speed, late speed, suitability, form momentum, ERI, market, market fluctuation, map lane/order, runner style, historical EPI tiles, runner insights, scratchings, barriers, weights, jockey, trainer, gear, race results, historical form, recent form, sectionals.
