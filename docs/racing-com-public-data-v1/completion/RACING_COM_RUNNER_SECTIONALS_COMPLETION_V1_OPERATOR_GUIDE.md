# Operator Guide

To test approved credential mode, set environment variable `RACINGCOM_CHAMPION_DATA_ENDPOINT_KEY` and run:

`python scripts/replay_racing_com_runner_sectionals_v1.py --mode APPROVED_CREDENTIAL`

To use the official import fallback, provide an official Racing.com JSON or CSV export and run:

`python scripts/import_racing_com_runner_sectionals_official_file_v1.py --input-file <approved-export>`

No credential values should be committed or printed.
