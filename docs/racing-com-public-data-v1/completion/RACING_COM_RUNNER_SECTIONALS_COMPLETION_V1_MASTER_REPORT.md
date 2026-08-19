# Racing.com Runner Sectionals Completion V1 Master Report

Status: `CODE_COMPLETE_ACCESS_REQUIRED`

Endpoint: `https://graphql.rmdprod.racing.com/`

Operation: `sectionaltimes_callback: getRaceForm(meetCode, raceNumber)`

Sample variables: `meetCode=5191101`, `raceNumber=1`.

Required headers: ordinary JSON/browser headers plus `x-api-key` only for approved credential mode.

Cookie requirement: `ABSENT`.

Credential requirement: `RACINGCOM_CHAMPION_DATA_ENDPOINT_KEY` is required for automated live runner-sectionals access unless Racing.com provides another approved official export.

CloudFront role: no governed CSV/PDF fallback discovered.

Timing units: split labels are metres-from-finish ranges and split times are seconds.

Live clean automated horses received: 0.

Live clean automated split rows received: 0.

Retained governed local sectional rows remain available for evidence only: 2682.

Canonical rows promoted: 0.

Official import fallback status: `PASS_OFFICIAL_IMPORT_READY`.
