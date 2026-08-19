# Racing.com Browser Network Capture V1

Built UTC: 2026-07-22T09:23:56+00:00

## Status

`RACINGCOM_NETWORK_CAPTURE_V1_PASS`

## Counts

- Fixtures: 15
- Request rows: 1910
- Response rows: 1935
- Candidate payload rows: 366
- Strong candidate rows: 0
- Recent visible fixtures with strong candidates: 0
- Negative controls with strong candidates: 0
- Response class counts: `{"ADVERTISING": 30, "ANALYTICS": 190, "CSV_FILE": 8, "GRAPHQL_RESPONSE": 114, "HTML_DOCUMENT": 57, "IMAGE_OR_FONT": 471, "JAVASCRIPT_ASSET": 873, "JSON_API": 20, "STRUCTURED_PAYLOAD": 40, "UNRELATED": 132}`
- Capture errors/warnings: 121

## Findings

Browser capture confirms the speed-data page loads dynamic first-party Racing.com/sectionals traffic. Candidate payload rows are not yet admitted sources; they move to the source-candidate validation unit for race identity, runner identity, schema and unit checks.
