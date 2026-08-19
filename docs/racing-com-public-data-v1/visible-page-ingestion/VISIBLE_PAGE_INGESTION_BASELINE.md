# Racing.com Visible Page Ingestion Baseline V1

Created: 2026-07-29T04:52:57Z

This pipeline opens ordinary public Racing.com pages in Chromium and extracts only visibly rendered page evidence.

## Security Boundary

- No protected GraphQL access
- No x-api-key capture or reuse
- No cookies, browser storage or hidden credentials read
- No network credential interception
- Only rendered DOM text, visible table cells, screenshots and sanitised HTML retained

## Operational Command

```powershell
python .\scripts\run_edgeiq_racing_com_visible_sectionals_pipeline_v1.py --date TODAY --state VIC --promote
```

## Evidence Roots

- Raw visible evidence: `data\raw\racing-com-visible-v1`
- Operational files: `data\operational\racing-com-visible-v1`
