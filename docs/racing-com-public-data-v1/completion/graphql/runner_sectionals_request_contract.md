# Runner Sectionals Request Contract

Endpoint: `https://graphql.rmdprod.racing.com/`

Method: `GET`

Operation: `sectionaltimes_callback: getRaceForm(meetCode, raceNumber)`

Sample variables: `meetCode=5191101`, `raceNumber=1`.

Approved credential delivery: environment variable `RACINGCOM_CHAMPION_DATA_ENDPOINT_KEY` mapped to request header `x-api-key`. The value is never stored or printed.

Cookie requirement from browser recapture: `ABSENT`.
