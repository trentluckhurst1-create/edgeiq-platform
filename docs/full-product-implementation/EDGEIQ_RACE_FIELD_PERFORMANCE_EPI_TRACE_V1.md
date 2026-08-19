# EDGEIQ RACE/FIELD/PERFORMANCE/EPI Trace V1

Generated: 2026-07-18T18:57:24

## Source Flow

| Field | Canonical display source | Current columns / keys |
| --- | --- | --- |
| Runner identity | RaceBook field + FormGuide normaliser | official.number, runnerNumber, saddlecloth, no, runner/horse/name |
| Saddlecloth | RaceBook field + FormGuide normaliser | number, runnerNumber, saddlecloth; rendered as text plus silk image only |
| Silks | RaceBook field + FormGuide normaliser | official.silkUrl, silkUrl, silksUrl, silk |
| Barrier | RaceBook field + FormGuide normaliser | official.barrier, barrier, bar, draw |
| Weight | RaceBook field + FormGuide normaliser | official.weight, weight, wt |
| Jockey | RaceBook field + FormGuide normaliser | official.jockey, jockey |
| Trainer | RaceBook field + FormGuide normaliser | official.trainer, trainer |
| Market | Current race intelligence + FormGuide + field | market.value, marketPrice, official.market, price |
| EDGEiQ price | Current race intelligence + FormGuide | edgeiqPrice.value, edgeiqPrice |
| EPI | EPI workspace terminal + current race intelligence + FormGuide | current_epi, epi.value, epi |
| EPI speed | Current race intelligence + FormGuide | earlySpeed.value, earlySpeed |
| Status | RaceBook field + current race intelligence | scratched/status fields |
| Historical runs | FormGuide enriched feed | recentRuns/fullForm/lastFive |
| Historical performance rating | EPI terminal start cells with performance-intelligence run context | start_10..start_1 + *_context |

## Feed Coverage Snapshot

- edgeiq_current_race_intelligence_v1.json races: 40; keys sampled: class, distance, fieldSummary, mapCoverage, meeting, overview, pressure, raceDate, raceKey, raceName, raceNumber, rail, runners, tempo, trackCondition, weather
- edgeiq_form_guide_enriched_v2.json races: 40; keys sampled: benchmarkContext, meeting, pressure, raceDate, raceKey, raceNumber, rail, runners, tempo, trackCondition, weather
- edgeiq_epi_workspace_terminal_feed_v1.csv columns sampled: workspace_id, meeting_key, race_key, generated_at, race_date, track, race_no, no, horse, current_epi, rank, field_avg, diff, start_10, start_9, start_8, start_7, start_6, start_5, start_4, start_3, start_2, start_1, peak_last_10, average_last_10, governed_trend, source, source_timestamp, source_confidence, row_status, start_10_class, start_9_class
- performance-intelligence product feed object count: 1; keys sampled: benchmark_explanation_index, historical_performance_intelligence_index, horse_intelligence_index, manifest, race_intelligence_index

## Component Flow

- RaceFileV3 maps global RACE to RaceWorkspace tab RACE.
- RaceWorkspace orchestrates RaceIntelligenceWorkspace, FieldWorkspace, PerformanceWorkspace and EpiWorkspaceWorkspace.
- RaceIntelligenceWorkspace renders a service-built model from raceBook, formGuide and current race intelligence.
- FieldWorkspace renders a service-built field model with optional governed recent form expansion.
- PerformanceWorkspace renders historical performance heat map rows; run metadata is supplied by the performance-intelligence service and historical rating cells by the governed EPI terminal feed.
- EpiWorkspaceWorkspace remains the dedicated current EDGEIQ Performance Index workspace.

## Mock / Demo Risk Trace

- No product-facing rows are generated from demo, sample, mock, or synthetic arrays by this tranche.
- Unavailable governed values render as unavailable/pending states rather than invented metrics.
