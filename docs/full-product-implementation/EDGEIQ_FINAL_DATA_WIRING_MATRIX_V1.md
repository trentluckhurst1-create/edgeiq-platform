# EDGEiQ Final Data Wiring Matrix V1

| Workspace | Display label(s) | Component | View model/service | Feed/API | Canonical field(s) | Unavailable behavior | Current/Historical | Transformation/freshness |
|---|---|---|---|---|---|---|---|---|
| Meetings | meeting/date/state/rail/track/weather/races/declared/scratchings | MeetingsWorkspace | meetingsFeed | public/data/edgeiq_three_day_product_catalog_v1.csv | meeting/race/scratchings fields | compact unavailable | current | builder freshness |
| Meeting Detail | race list and meeting context | MeetingWorkspace | meetingDetailFeed | public/data/edgeiq_three_day_product_catalog_v1.csv | meeting/race fields | compact unavailable | current | builder freshness |
| Scratchings | scratched runner status | MeetingScratchingsWorkspace | scratchingsFeed | public/data/edgeiq_scratchings_terminal_feed_v1.csv | runner/scratching/status | no governed scratchings state | current | builder freshness |
| Gear Changes | current gear/changes | MeetingGearChangesWorkspace | gearChangesFeed | public/data/edgeiq_gear_terminal_feed_v1.csv | gear_current/gear_changes/first_time_gear | honest unavailable/no-change | current | builder freshness |
| Track | track condition/rail/map/history | MeetingTrackWorkspace | trackFeed/trackMapAssets | public/data track feeds + public/track-maps | track/rail/condition/map asset | compact unavailable | current + historical comparison | service transforms display |
| Weather | live/current weather | MeetingWeatherWorkspace | weatherFeed | governed live-weather v1.2 outputs | temperature/rain/wind/source state | available/stale/unavailable | current | builder-owned freshness |
| Race | tempo/EPF/determinants/runner board | RaceIntelligenceWorkspace | raceWorkspaceViewModel/currentRaceIntelligenceFeed | current race intelligence feeds | tempo/epf/runner board fields | compact unavailable | current | service/view-model |
| Field | runner identity and market/status | FieldWorkspace | fieldWorkspaceViewModel | three-day catalog/live runner board | runner/barrier/weight/jockey/trainer/edgeiq/market/status | dash or status | current | view-model |
| Form Guide | EPI/early/late/suitability/momentum/price/profile/recent form | RaceFormGuideWorkspace | formGuideNormaliser/formGuideEnrichedFeed/formGuideWorkspaceViewModel | edgeiq_form_guide_enriched_v2.csv and governed terminal feeds | approved form columns and dossier fields | empty strings/dash/unavailable copy | current + historical | normaliser/view-model |
| Performance | historical performance figures | PerformanceWorkspace | performanceWorkspaceViewModel | certified performance feed | historical rating fields | empty cells | historical | view-model |
| EPI | canonical EPI | EpiWorkspaceWorkspace | epiWorkspaceFeed | epi terminal feed | EPI fields | unavailable evidence | current | service |
| Map | speed map/run style | MapWorkspace | mapFeed | map terminal feed | barrier/run_style/speed/market | limited evidence/unavailable | current | service |
| Market | market/edge/fair/fluc | MarketWorkspace | marketFeed | market terminal feed | market_price/edgeiq_price/edge/fluc | stale/unavailable | current | service |
| Overview | summary/map/EPI/runner board | OverviewWorkspace | overviewFeed | overview terminal feed | summary fields | compact unavailable | current | service |
| Insights | stable/prep/heavy/campaign insights | InsightsWorkspace | insightsFeed | insights terminal feed | insight_category/text/source | no insight inputs | current | service |
| Results | runner performance/sectionals/stewards | ResultsWorkspace | resultsFeed | results terminal feed | position/runner/EPI/ERI/ESI/stewards | preliminary/official/unavailable | historical/result | service |
| LAB | query engine/result table | LabWorkspace | labResearch/performanceIntelligenceFeed | certified performance feed | query model/results | disabled/unavailable metrics | research | service/query boundary |
| Compare | side-by-side common metrics | CompareWorkspace | compareWorkspaceData/performanceIntelligenceFeed | certified performance feed | common metric rows | unavailable values distinguished | research/current/historical | service/view-model |
| Review | review persistence boundary | ReviewWorkspace | reviewWorkspaceData | local/session persistence if supplied | reviewable items | honest no saved review record | session/review | service |
| Settings | display/governance state | SettingsWorkspace | none/model-free | application state | display/data/weather/review states | static state where controls absent | application | component state only |
