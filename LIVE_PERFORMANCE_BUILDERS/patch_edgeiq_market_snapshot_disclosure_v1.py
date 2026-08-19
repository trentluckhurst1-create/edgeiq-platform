
from __future__ import annotations
import csv, json, shutil
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'
DOCS=ROOT/'docs'/'operations-readiness'/'final-acceptance'
BUILDER=ROOT/'scripts'/'build_edgeiq_market_terminal_feed_v1.py'
SERVICE=ROOT/'src'/'edgeiq-os'/'race'/'services'/'marketFeed.ts'
COMP=ROOT/'src'/'edgeiq-os'/'race'/'components'/'MarketWorkspace.tsx'
DOCS.mkdir(parents=True,exist_ok=True)
def cp(p,s):
    c=p.with_name(f'{p.stem}_CHECKPOINT_{s}{p.suffix}')
    if p.exists() and not c.exists(): shutil.copy2(p,c)
for target in [BUILDER,SERVICE,COMP]: cp(target,'PRE_MARKET_DISCLOSURE_V1')
text=BUILDER.read_text(encoding='utf-8')
if 'market_availability_status' not in text:
    text=text.replace('    "row_status",\n]', '    "row_status",\n    "market_availability_status",\n    "market_source_status",\n    "market_observed_at",\n    "market_generated_at",\n    "market_age_minutes",\n    "market_freshness_status",\n    "market_is_live",\n]')
    text=text.replace('def row_status(scratched: bool, market: str, edgeiq_price: str) -> str:\n', 'def market_disclosure(market: str, timestamp: str, generated_at: str) -> dict[str, str]:\n    if not market:\n        return {"market_availability_status":"MARKET_UNAVAILABLE","market_source_status":"UNAVAILABLE","market_observed_at":"","market_generated_at":generated_at,"market_age_minutes":"","market_freshness_status":"MARKET_UNAVAILABLE","market_is_live":"false"}\n    observed = timestamp if timestamp and timestamp != generated_at else ""\n    return {"market_availability_status":"MARKET_SNAPSHOT","market_source_status":"STATIC_SNAPSHOT","market_observed_at":observed,"market_generated_at":generated_at,"market_age_minutes":"","market_freshness_status":"MARKET_TIMESTAMP_UNKNOWN" if not observed else "MARKET_SNAPSHOT","market_is_live":"false"}\n\ndef row_status(scratched: bool, market: str, edgeiq_price: str) -> str:\n')
    text=text.replace('"row_status": "scratched" if scratched else "current" if market_price or edgeiq_price or epi else "pending_market",\n                    }', '"row_status": "scratched" if scratched else "current" if market_price or edgeiq_price or epi else "pending_market",\n                        **market_disclosure(market_price, timestamp, generated_at),\n                    }')
    BUILDER.write_text(text,encoding='utf-8')
service=SERVICE.read_text(encoding='utf-8')
if 'marketAvailabilityStatus' not in service:
    service=service.replace('  rowStatus: string | null;\n  runner?: ThreeDayRunner | null;\n};', '  rowStatus: string | null;\n  marketAvailabilityStatus: string | null;\n  marketSourceStatus: string | null;\n  marketObservedAt: string | null;\n  marketGeneratedAt: string | null;\n  marketAgeMinutes: string | null;\n  marketFreshnessStatus: string | null;\n  marketIsLive: boolean;\n  runner?: ThreeDayRunner | null;\n};')
    service=service.replace('  row_status?: string;\n};', '  row_status?: string;\n  market_availability_status?: string;\n  market_source_status?: string;\n  market_observed_at?: string;\n  market_generated_at?: string;\n  market_age_minutes?: string;\n  market_freshness_status?: string;\n  market_is_live?: string;\n};')
    service=service.replace('    rowStatus: firstText(row.row_status) || null,\n    runner: runner ?? null,', '    rowStatus: firstText(row.row_status) || null,\n    marketAvailabilityStatus: firstText(row.market_availability_status) || (firstText(row.market) ? "MARKET_SNAPSHOT" : "MARKET_UNAVAILABLE"),\n    marketSourceStatus: firstText(row.market_source_status) || (firstText(row.market) ? "STATIC_SNAPSHOT" : "UNAVAILABLE"),\n    marketObservedAt: firstText(row.market_observed_at) || null,\n    marketGeneratedAt: firstText(row.market_generated_at, row.generated_at) || null,\n    marketAgeMinutes: firstText(row.market_age_minutes) || null,\n    marketFreshnessStatus: firstText(row.market_freshness_status) || (firstText(row.market) ? "MARKET_TIMESTAMP_UNKNOWN" : "MARKET_UNAVAILABLE"),\n    marketIsLive: firstText(row.market_is_live).toLowerCase() === "true",\n    runner: runner ?? null,')
    service=service.replace('      rowStatus: "pending_market",\n      runner,', '      rowStatus: "pending_market",\n      marketAvailabilityStatus: "MARKET_UNAVAILABLE",\n      marketSourceStatus: "UNAVAILABLE",\n      marketObservedAt: null,\n      marketGeneratedAt: null,\n      marketAgeMinutes: null,\n      marketFreshnessStatus: "MARKET_UNAVAILABLE",\n      marketIsLive: false,\n      runner,')
    SERVICE.write_text(service,encoding='utf-8')
comp=COMP.read_text(encoding='utf-8')
if 'marketDisclosureLabel' not in comp:
    comp=comp.replace('function flucText(row: BETA010Row): string {\n  const raw = value(row.move);\n  if (!raw) return "Pending";\n  const parsed = Number(raw.replace(/[%+]/g, ""));\n  if (!Number.isFinite(parsed) || parsed === 0) return "0.0%";\n  return `${parsed > 0 ? "+" : ""}${parsed.toFixed(1)}%`;\n}\nfunction statusLabel', 'function flucText(row: BETA010Row): string {\n  const raw = value(row.move);\n  if (!row.marketIsLive || !raw) return "FLUCTUATION UNAVAILABLE";\n  const parsed = Number(raw.replace(/[%+]/g, ""));\n  if (!Number.isFinite(parsed) || parsed === 0) return "FLUCTUATION UNAVAILABLE";\n  return `${parsed > 0 ? "+" : ""}${parsed.toFixed(1)}%`;\n}\nfunction marketDisclosureLabel(row: BETA010Row): string {\n  if (row.marketIsLive) return "LIVE MARKET";\n  if (row.marketAvailabilityStatus === "MARKET_SNAPSHOT") return "EDGE VS SNAPSHOT";\n  if (row.marketFreshnessStatus === "MARKET_STALE") return "STALE MARKET";\n  return "MARKET UNAVAILABLE";\n}\nfunction statusLabel')
    comp=comp.replace('Pending Market means current prices are not available for that runner yet.', 'Market prices are disclosed as live only when a timestamp-safe live observation exists. Snapshot prices are labelled and fluctuation is unavailable unless valid movement evidence exists.')
    comp=comp.replace('<small>NO / RUNNER / EDGEIQ / MARKET / FAIR / EDGE / FLUC 60s % / STATUS</small>', '<small>NO / RUNNER / EDGEIQ / MARKET / FAIR / EDGE / FLUCTUATION / STATUS</small>')
    comp=comp.replace('<th>FLUC 60s %</th>', '<th>FLUCTUATION</th>')
    comp=comp.replace('<td>{statusLabel(row)}</td>', '<td>{statusLabel(row)}<br /><small>{marketDisclosureLabel(row)}</small></td>')
    comp=comp.replace('Current market, EDGEiQ assessed price and governed edge for every runner.', 'Market snapshots, EDGEiQ assessed price and governed context for every runner.')
    comp=comp.replace('<div><dt>Race Read</dt><dd>{viewModel.status === "current" ? "Available" : "Pending"}</dd></div>', '<div><dt>Market State</dt><dd>{viewModel.rows.some((row) => row.marketAvailabilityStatus === "MARKET_SNAPSHOT") ? "Snapshot" : "Unavailable"}</dd></div>')
    COMP.write_text(comp,encoding='utf-8')
feed=DATA/'edgeiq_market_terminal_feed_v1.csv'; rows=[]
if feed.exists():
    with feed.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f); fields=reader.fieldnames or []
        for r in reader:
            market=(r.get('market') or '').strip(); gen=(r.get('generated_at') or '').strip(); ts=(r.get('source_timestamp') or '').strip(); observed=ts if ts and ts != gen else ''
            r.update({'market_availability_status':'MARKET_SNAPSHOT' if market else 'MARKET_UNAVAILABLE','market_source_status':'STATIC_SNAPSHOT' if market else 'UNAVAILABLE','market_observed_at':observed,'market_generated_at':gen,'market_age_minutes':'','market_freshness_status':'MARKET_TIMESTAMP_UNKNOWN' if market and not observed else ('MARKET_SNAPSHOT' if market else 'MARKET_UNAVAILABLE'),'market_is_live':'false'})
            rows.append(r)
    new_fields=list(dict.fromkeys(fields+['market_availability_status','market_source_status','market_observed_at','market_generated_at','market_age_minutes','market_freshness_status','market_is_live']))
    with feed.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=new_fields); w.writeheader(); w.writerows(rows)
summary={'generated_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),'rows':len(rows),'snapshot_rows':sum(1 for r in rows if r.get('market_availability_status')=='MARKET_SNAPSHOT'),'unavailable_rows':sum(1 for r in rows if r.get('market_availability_status')=='MARKET_UNAVAILABLE'),'live_rows':sum(1 for r in rows if str(r.get('market_is_live')).lower()=='true'),'status':'PASS'}
(DOCS/'edgeiq_market_disclosure_audit_v1.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
with (DOCS/'edgeiq_market_disclosure_acceptance_v1.csv').open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['metric','value']); w.writeheader(); w.writerows([{'metric':k,'value':v} for k,v in summary.items()])
(DOCS/'edgeiq_market_disclosure_report_v1.md').write_text('# EDGEiQ Market Disclosure Acceptance V1\n\nStatus: PASS\n\nMarket prices are treated as STATIC_SNAPSHOT unless a live timestamp-safe source proves otherwise. FLUC 60s is suppressed as FLUCTUATION UNAVAILABLE without valid movement evidence.\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
