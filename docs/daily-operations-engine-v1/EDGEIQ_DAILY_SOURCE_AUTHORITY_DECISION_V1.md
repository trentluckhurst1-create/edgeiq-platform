# EDGEiQ Daily Source Authority Decision V1

Use repository-supported local outputs first. Live access without a governed existing collector is EXTERNAL_ACCESS_REQUIRED, not fabricated.

## Supported Sources
- RACINGCOM_THREE_DAY_PRODUCT_CATALOG: SUPPORTED (meetings,races,declared_runners,barriers,weights,jockeys,trainers,current_conditions)
- RACINGCOM_GRAPHQL_HISTORICAL_RESULTS: SUPPORTED (historical_results,official_race_times,placings,margins,track_conditions,runners,jockeys,trainers,weights,barriers)
- RACING_AUSTRALIA_RESULTS_OUTPUTS: SUPPORTED_PARTIAL (official_results,placings,margins,conditions,metadata)
- RACINGCOM_SPEED_DATA_OUTPUTS: SUPPORTED_PARTIAL (speed_summaries,sectionals,splits,runner_speed_metrics)
- GOVERNED_TRACK_CONDITION_WEATHER_REGISTRY: SUPPORTED_PARTIAL (weather,wind,rainfall,track-condition source evidence,operator-condition candidates)

Weather may support context but must not infer official track condition. Final SP/market data is not used as a predictive feature here.
