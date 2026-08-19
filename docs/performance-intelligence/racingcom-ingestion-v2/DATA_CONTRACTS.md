# Data Contracts

Key contracts:

- `edgeiq_racingcom_meeting_discovery_v2.csv`: canonical meetings only. No race-level URLs.
- `edgeiq_racingcom_race_discovery_v2.csv`: evidence-backed race identities.
- `edgeiq_racingcom_csv_admission_contract_v2.csv`: admission decisions and reasons.
- `edgeiq_racingcom_acquisition_queue_v2.csv`: executable acquisition/page-discovery queue.
- `edgeiq_racingcom_csv_acquisition_v2.csv`: explicit acquired CSV evidence.
- `edgeiq_racingcom_parser_output_v2.csv`: parsed runner-level speed/sectional rows.
- `edgeiq_racingcom_performance_warehouse_v2.csv`: versioned canonical warehouse.

The warehouse is appendable/versioned research data. It is not a production overwrite.
