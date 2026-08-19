# Racing.com Static Source Forensics V1

Built UTC: 2026-07-22T09:19:04+00:00

## Status

`RACINGCOM_STATIC_SOURCE_FORENSICS_V1_PASS`

## Counts

- Fixtures consumed: 15
- Responses captured: 15
- Response metadata ledger rows: 15
- HTML speed pages: 7
- Historical CSV/octet-stream documents: 8
- Candidate string/asset rows: 78
- Embedded payload rows: 0
- Script/requested-document rows: 43
- Sectionals iframe candidates: 0
- Errors: 0

## Findings

Static HTML did not prove a direct fresh CSV source. Recent Racing.com speed-data pages expose a `dxp-static.racing.com/sectionals/index.html` iframe candidate with `meetCode` and `raceNumber` parameters. This is only a candidate from static source forensics; browser network capture is required to identify the widget's actual data delivery mechanism.

Historical direct CSV fixtures remain available through their retained CloudFront CSV URLs.
