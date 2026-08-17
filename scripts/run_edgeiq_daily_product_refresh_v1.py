from __future__ import annotations
import sys
import subprocess
import os
import json
import argparse,json,os,shutil,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
from edgeiq_three_day_window_v1_common import get_operational_today, parse_override_date
try:
 from zoneinfo import ZoneInfo
except Exception:
 ZoneInfo=None
ROOT=Path(__file__).resolve().parents[1]; PUBLIC=ROOT/'public'/'data'; DOCS=ROOT/'docs'/'operations-readiness'; DAILY=DOCS/'daily-refresh'; LKG=DOCS/'operations'/'last-known-good'; TZ=ZoneInfo('Australia/Melbourne') if ZoneInfo else None
CRITICAL=['edgeiq_three_day_window_v1.json', 'edgeiq_three_day_product_catalog_v1.json', 'edgeiq_vic_three_day_race_list_v1.csv', 'edgeiq_live_terminal_feed_v1.csv', 'edgeiq_vic_live_terminal_feed_v1.csv']; STAGES=['scripts/build_edgeiq_three_day_window_v1.py', 'scripts/build_edgeiq_vic_three_day_meeting_universe.py', 'scripts/build_edgeiq_vic_three_day_meeting_calendar_v1.py', 'scripts/build_edgeiq_racingcom_three_day_race_list_v1.py', 'scripts/build_edgeiq_three_day_product_catalog_v1.py', 'scripts/build_edgeiq_current_race_fields_from_product_catalog_v1.py', 'scripts/build_edgeiq_race_entry_fact_v1.py', 'scripts/audit_edgeiq_race_entry_fact_v1.py', 'scripts/build_edgeiq_ladbrokes_active_market_refresh_v1.py', 'scripts/build_edgeiq_current_market_v1.py', 'scripts/build_edgeiq_form_guide_current_base_v1.py', 'scripts/build_edgeiq_current_early_speed_v1.py', 'scripts/build_edgeiq_current_late_speed_v1.py', 'scripts/complete_edgeiq_current_early_late_distance_aware_v3.py', 'scripts/build_edgeiq_current_suitability_v1.py', 'scripts/build_edgeiq_current_form_momentum_v1.py', 'scripts/build_edgeiq_current_race_shape_v2.py', 'scripts/build_edgeiq_current_map_v1.py', 'scripts/build_edgeiq_form_guide_enriched_v2.py', 'scripts/build_edgeiq_performance_recovery_current_lineage_v1.py', 'scripts/build_edgeiq_form_guide_enriched_v2.py', 'scripts/build_edgeiq_map_terminal_feed_v1.py', 'scripts/build_edgeiq_market_terminal_feed_v1.py', 'scripts/build_edgeiq_overview_terminal_feed_v1.py', 'scripts/build_edgeiq_insights_terminal_feed_v1.py', 'scripts/build_edgeiq_gear_terminal_feed_v1.py', 'scripts/build_edgeiq_meeting_results_terminal_feed_v1.py', 'scripts/performance-intelligence/product-integration/build_edgeiq_performance_intelligence_product_feeds_v1.py', 'scripts/build_edgeiq_on_track_weather_governed_v1_2.py', 'scripts/build_edgeiq_victorian_track_weather_v1.py', 'scripts/audit_edgeiq_victorian_track_weather_v1.py', 'scripts/build_edgeiq_nexus_current_runner_board_v1.py', 'scripts/build_edgeiq_race_shape_story_v1.py', 'scripts/build_edgeiq_nexus_contextual_intelligence_v2.py', 'scripts/build_edgeiq_nexus_score_calibration_v1.py']
def utc(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def today(v=None): return get_operational_today(override_date=parse_override_date(v))[0].isoformat()
def count_csv(p):
 p=Path(p)
 return 0 if (not p.exists() or p.stat().st_size==0) else max(0,sum(1 for _ in p.open('r',encoding='utf-8',errors='ignore'))-1)
def write_json(p,o):
 p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2)+'\n',encoding='utf-8')
def snap():
 LKG.mkdir(parents=True,exist_ok=True); files=[]
 for n in CRITICAL:
  s=PUBLIC/n
  if s.exists() and s.stat().st_size>0:
   shutil.copy2(s,LKG/n); files.append({'file':n,'bytes':s.stat().st_size})
 m={'generated_utc':utc(),'files':files}; write_json(DOCS/'operations'/'edgeiq_last_known_good_manifest_v1.json',m); return m
def _edgeiq_original_daily_main():
 a=argparse.ArgumentParser(); a.add_argument('--date'); a.add_argument('--meeting'); a.add_argument('--race'); a.add_argument('--audit-only',action='store_true'); a.add_argument('--publish-only',action='store_true'); a.add_argument('--force-current-refresh',action='store_true'); a.add_argument('--no-market',action='store_true'); a.add_argument('--no-weather',action='store_true'); a.add_argument('--verbose',action='store_true'); ns=a.parse_args(); t=time.time(); od=today(ns.date); DAILY.mkdir(parents=True,exist_ok=True); lkg=snap(); stages=[]; log=DAILY/'edgeiq_daily_product_refresh_v1_run_log.txt'; env=os.environ.copy()
 if ns.date:
  env['EDGEIQ_PIPELINE_DATE']=od
 else:
  env.pop('EDGEIQ_PIPELINE_DATE',None)
 with log.open('w',encoding='utf-8') as h:
  h.write(f'EDGEIQ DAILY PRODUCT REFRESH V1\nOPERATING_DATE={od}\nSTARTED_UTC={utc()}\n')
  if ns.audit_only: h.write('AUDIT_ONLY\n')
  else:
   for st in STAGES:
    if ns.no_market and 'market' in st.lower(): stages.append({'stage':st,'status':'SKIPPED','reason':'--no-market'}); continue
    if ns.no_weather and 'weather' in st.lower(): stages.append({'stage':st,'status':'SKIPPED','reason':'--no-weather'}); continue
    sp=ROOT/st
    if not sp.exists(): stages.append({'stage':st,'status':'SKIPPED','reason':'missing'}); continue
    h.write(f'\n--- {st} ---\n'); r=subprocess.run([sys.executable,str(sp)],cwd=str(ROOT),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=900); out_bytes=r.stdout or b''
    try: out_text=out_bytes.decode('utf-8')
    except UnicodeDecodeError: out_text=out_bytes.decode('cp1252',errors='replace')
    h.write(out_text); stages.append({'stage':st,'status':'PASS' if r.returncode==0 else 'FAIL','returncode':r.returncode})
    if r.returncode!=0: break
 feeds=[]
 for n in CRITICAL:
  p=PUBLIC/n; rows=count_csv(p) if n.endswith('.csv') else (1 if p.exists() and p.stat().st_size>0 else 0); feeds.append({'file':n,'status':'PASS' if p.exists() and p.stat().st_size>0 and rows>0 else 'FAIL','rows_or_items':rows,'bytes':p.stat().st_size if p.exists() else 0})
 cat=json.loads((PUBLIC/'edgeiq_three_day_product_catalog_v1.json').read_text(encoding='utf-8')) if (PUBLIC/'edgeiq_three_day_product_catalog_v1.json').exists() else {}; meets=cat.get('meetings',[]) if isinstance(cat,dict) else []; races=[]; runners=0; total_current_scratchings=0; active_runners=0
 def _runner_scratched(x):
  off=x.get('official') if isinstance(x,dict) and isinstance(x.get('official'),dict) else {}
  src=x.get('source') if isinstance(x,dict) and isinstance(x.get('source'),dict) else {}
  vals=[off.get('scratched'),src.get('scratched'),src.get('is_scratched'),off.get('status'),src.get('status')]
  return any(str(v).strip().lower() in {'true','scr','scratched','lscr','late scratching'} for v in vals)
 for m in meets:
  for rc in (m.get('races',[]) if isinstance(m,dict) else []):
   races.append(rc); rr=rc.get('runners',[]) if isinstance(rc,dict) else []; runners+=len(rr); race_scratch=sum(1 for x in rr if _runner_scratched(x)); total_current_scratchings+=race_scratch; active_runners+=max(0,len(rr)-race_scratch)
 scratch=total_current_scratchings
 status='FAIL' if any(x.get('status')=='FAIL' for x in stages) or any(x.get('status')!='PASS' for x in feeds) else 'PASS'
 payload={'schema_version':'edgeiq_daily_product_refresh_v1','generated_utc':utc(),'operating_date':od,'timezone':'Australia/Melbourne','stages':stages,'feed_checks':feeds,'meetings_built':len(meets),'races_built':len(races),'runners_built':runners,'declared_runners':runners,'active_runners':active_runners,'total_current_scratchings':total_current_scratchings,'new_scratchings_this_run':None,'scratching_changes_this_run':None,'reinstated_runners_this_run':None,'scratchings_metric_deprecated':scratch,'track_status':'PARTIAL','weather_status':'PASS' if (PUBLIC/'edgeiq_on_track_weather_governed_v1_2.csv').exists() else 'PARTIAL','market_status':'PASS' if (PUBLIC/'edgeiq_market_terminal_feed_v1.csv').exists() else 'PARTIAL','results_status':'PASS' if (PUBLIC/'edgeiq_meeting_results_terminal_feed_v1.csv').exists() else 'PARTIAL','feeds_published':sum(1 for x in feeds if x['status']=='PASS'),'audit_status':status,'last_known_good_preserved':bool(lkg.get('files')),'elapsed_seconds':round(time.time()-t,2),'exit_code':0 if status=='PASS' else 1}

 wv_path=DOCS.parent/'weather-intelligence'/'live'/'edgeiq_victorian_track_weather_v1_audit.json'
 wv={}
 try:
  wv=json.loads(wv_path.read_text(encoding='utf-8')) if wv_path.exists() else {}
 except Exception:
  wv={}
 payload.update({'weather_meetings_required':wv.get('meetings_required',0),'weather_direct_source_meetings':wv.get('direct_source_meetings',0),'weather_bom_meetings':wv.get('bom_meetings',0),'weather_current':wv.get('current',0),'weather_regional_proxy':wv.get('regional_proxy',0),'weather_stale':wv.get('stale',0),'weather_unavailable':wv.get('unavailable',0),'weather_licence_blocked':wv.get('licence_blocked',0),'weather_audit_status':wv.get('status','NOT_RUN')})
 write_json(DAILY/'edgeiq_daily_product_refresh_v1_audit.json',payload); write_json(DAILY/'edgeiq_daily_product_refresh_v1_manifest.json',{'critical_feeds':feeds,'last_known_good':lkg}); (DAILY/'edgeiq_daily_product_refresh_v1_report.md').write_text(f'# EDGEIQ Daily Product Refresh V1\n\nStatus: {status}\n\nMeetings: {len(meets)}\nRaces: {len(races)}\nRunners: {runners}\n',encoding='utf-8')
 print('============================================================'); print('EDGEIQ DAILY PRODUCT REFRESH V1'); print('============================================================'); print(f'OPERATING_DATE: {od}'); print('TIMEZONE: Australia/Melbourne'); print(f'MEETINGS_BUILT: {len(meets)}'); print(f'RACES_BUILT: {len(races)}'); print(f'RUNNERS_BUILT: {runners}'); print(f'DECLARED_RUNNERS: {runners}'); print(f'ACTIVE_RUNNERS: {active_runners}'); print(f'TOTAL_CURRENT_SCRATCHINGS: {total_current_scratchings}'); print('NEW_SCRATCHINGS_THIS_RUN: NOT_CALCULATED'); print('SCRATCHING_CHANGES_THIS_RUN: NOT_CALCULATED'); print('REINSTATED_RUNNERS_THIS_RUN: NOT_CALCULATED'); print(f'TRACK_STATUS: {payload["track_status"]}'); print(f'WEATHER_STATUS: {payload["weather_status"]}'); print(f'WEATHER_MEETINGS_REQUIRED: {payload.get("weather_meetings_required",0)}'); print(f'WEATHER_DIRECT_SOURCE_MEETINGS: {payload.get("weather_direct_source_meetings",0)}'); print(f'WEATHER_BOM_MEETINGS: {payload.get("weather_bom_meetings",0)}'); print(f'WEATHER_CURRENT: {payload.get("weather_current",0)}'); print(f'WEATHER_REGIONAL_PROXY: {payload.get("weather_regional_proxy",0)}'); print(f'WEATHER_STALE: {payload.get("weather_stale",0)}'); print(f'WEATHER_UNAVAILABLE: {payload.get("weather_unavailable",0)}'); print(f'WEATHER_LICENCE_BLOCKED: {payload.get("weather_licence_blocked",0)}'); print(f'WEATHER_AUDIT_STATUS: {payload.get("weather_audit_status","NOT_RUN")}'); print(f'MARKET_STATUS: {payload["market_status"]}'); print(f'RESULTS_STATUS: {payload["results_status"]}'); print(f'FEEDS_PUBLISHED: {payload["feeds_published"]}'); print(f'AUDIT_STATUS: {status}'); print(f'LAST_KNOWN_GOOD_PRESERVED: {str(payload["last_known_good_preserved"]).upper()}'); print(f'ELAPSED_SECONDS: {payload["elapsed_seconds"]}'); print(f'EXIT_CODE: {payload["exit_code"]}'); print('============================================================'); return payload['exit_code']


# EDGEIQ_DAILY_CURRENT_RUNNER_PERFORMANCE_INTEGRATION_V2

def _edgeiq_extract_performance_report(
    stdout: str,
) -> dict[str, object]:
    decoder = json.JSONDecoder()

    for offset, character in enumerate(stdout):
        if character != "{":
            continue

        try:
            payload, _ = decoder.raw_decode(
                stdout[offset:]
            )
        except json.JSONDecodeError:
            continue

        if (
            isinstance(payload, dict)
            and payload.get("run_id")
            == "EDGEIQ_CURRENT_RUNNER_SCOPED_PERFORMANCE_CHAIN_V1"
        ):
            return payload

    raise RuntimeError(
        "Current-runner performance report "
        "was not found in stdout."
    )


def _edgeiq_validate_performance_report(
    report: dict[str, object],
) -> None:
    status = str(
        report.get("status", "")
    ).strip().upper()

    failed_stage = str(
        report.get("failed_stage", "")
    ).strip()

    failure_message = str(
        report.get("failure_message", "")
    ).strip()

    if (
        status != "PASS"
        or failed_stage
        or failure_message
    ):
        raise RuntimeError(
            "FAIL_FAST_CURRENT_RUNNER_PERFORMANCE_CHAIN: "
            f"status={status}; "
            f"failed_stage={failed_stage}; "
            f"failure_message={failure_message}"
        )

    counts = report.get("counts")

    if not isinstance(counts, dict):
        raise RuntimeError(
            "Performance report has no count dictionary."
        )

    values = {
        key: int(value)
        for key, value in counts.items()
    }

    current_runners = values.get(
        "current_runners",
        0,
    )

    epi = values.get(
        "epi",
        0,
    )

    publication = values.get(
        "publication",
        0,
    )

    attachments = values.get(
        "publication_epi_attachments",
        -1,
    )

    missing_epi = values.get(
        "publication_missing_epi",
        -1,
    )

    failures = {}

    runner_population = {
        name: values.get(name, -1)
        for name in (
            "suitability_component",
            "suitability_aggregate",
            "projected_performance",
            "epi",
            "epi_relative_context",
            "epi_ordering",
            "publication_epi_attachments",
        )
    }

    if len(
        set(runner_population.values())
    ) != 1:
        failures[
            "runner_population_reconciliation"
        ] = runner_population

    epi_components = values.get(
        "epi_component",
        -1,
    )

    if epi_components != epi * 3:
        failures[
            "three_epi_components_per_runner"
        ] = {
            "epi": epi,
            "actual": epi_components,
            "expected": epi * 3,
        }

    race_population = {
        name: values.get(name, -1)
        for name in (
            "race_context",
            "epi_distribution",
            "epi_ordering_summary",
        )
    }

    if len(
        set(race_population.values())
    ) != 1:
        failures[
            "race_population_reconciliation"
        ] = race_population

    if publication != current_runners:
        failures[
            "publication_matches_current_runners"
        ] = {
            "publication": publication,
            "current_runners": current_runners,
        }

    if attachments != epi:
        failures[
            "publication_attachments_match_epi"
        ] = {
            "attachments": attachments,
            "epi": epi,
        }

    if (
        missing_epi
        != publication - attachments
    ):
        failures[
            "publication_missing_epi_reconciled"
        ] = {
            "actual": missing_epi,
            "expected": (
                publication - attachments
            ),
        }

    if current_runners <= 0:
        failures[
            "current_runner_population_positive"
        ] = current_runners

    if epi <= 0:
        failures[
            "epi_population_positive"
        ] = epi

    if failures:
        raise RuntimeError(
            "FAIL_FAST_CURRENT_RUNNER_PERFORMANCE_CHAIN: "
            + json.dumps(
                failures,
                sort_keys=True,
            )
        )


def _edgeiq_run_current_runner_performance_chain() -> dict[str, object]:
    orchestrator = (
        ROOT
        / "scripts"
        / "run_edgeiq_current_runner_scoped_performance_chain_v1.py"
    )

    result = subprocess.run(
        [
            sys.executable,
            "-u",
            str(orchestrator),
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        env={
            **os.environ,
            "PYTHONPATH": (
                str(ROOT)
                + os.pathsep
                + os.environ.get("PYTHONPATH", "")
            ),
        },
    )

    if result.stdout:
        print(
            "CURRENT_RUNNER_PERFORMANCE_STDOUT_BEGIN"
        )
        print(result.stdout, end="")
        print(
            "CURRENT_RUNNER_PERFORMANCE_STDOUT_END"
        )

    if result.stderr:
        print(
            "CURRENT_RUNNER_PERFORMANCE_STDERR_BEGIN"
        )
        print(result.stderr, end="")
        print(
            "CURRENT_RUNNER_PERFORMANCE_STDERR_END"
        )

    if result.returncode != 0:
        raise RuntimeError(
            "FAIL_FAST_CURRENT_RUNNER_PERFORMANCE_CHAIN: "
            f"exit_code={result.returncode}"
        )

    report = (
        _edgeiq_extract_performance_report(
            result.stdout
        )
    )

    _edgeiq_validate_performance_report(
        report
    )

    return report


def _edgeiq_cli_date_arg() -> str | None:
    for index, value in enumerate(sys.argv):
        if value == "--date" and index + 1 < len(sys.argv):
            return sys.argv[index + 1]
        if value.startswith("--date="):
            return value.split("=", 1)[1]
    return None


def _edgeiq_run_current_runner_intelligence_audit_gate() -> bool:
    audit_script = (
        ROOT
        / "scripts"
        / "audit_edgeiq_current_runner_intelligence_v1.py"
    )

    audit_date = today(
        _edgeiq_cli_date_arg()
    )

    result = subprocess.run(
        [
            sys.executable,
            "-u",
            str(audit_script),
            "--date",
            audit_date,
            "--gate",
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        env={
            **os.environ,
            "EDGEIQ_PIPELINE_DATE": audit_date,
            "PYTHONPATH": (
                str(ROOT)
                + os.pathsep
                + os.environ.get("PYTHONPATH", "")
            ),
        },
    )

    if result.stdout:
        print(
            "CURRENT_RUNNER_INTELLIGENCE_AUDIT_STDOUT_BEGIN"
        )
        print(result.stdout, end="")
        print(
            "CURRENT_RUNNER_INTELLIGENCE_AUDIT_STDOUT_END"
        )

    if result.stderr:
        print(
            "CURRENT_RUNNER_INTELLIGENCE_AUDIT_STDERR_BEGIN"
        )
        print(result.stderr, end="")
        print(
            "CURRENT_RUNNER_INTELLIGENCE_AUDIT_STDERR_END"
        )

    return result.returncode == 0


def _edgeiq_run_post_performance_form_guide_refresh() -> None:
    operating_date = today(_edgeiq_cli_date_arg())
    env = os.environ.copy()
    env["EDGEIQ_PIPELINE_DATE"] = operating_date
    stages = [
        "scripts/build_edgeiq_fair_price_epr_v1.py",
        "scripts/build_edgeiq_form_guide_enriched_v2.py",
        "scripts/build_edgeiq_epi_workspace_terminal_feed_v1.py",
    ]
    for stage in stages:
        script = ROOT / stage
        if not script.exists():
            raise RuntimeError(f"POST_PERFORMANCE_REFRESH_STAGE_MISSING: {stage}")
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(ROOT),
            env=env,
            text=True,
            timeout=900,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "POST_PERFORMANCE_REFRESH_STAGE_FAILED: "
                f"{stage}: exit_code={result.returncode}"
            )


def main() -> int:
    base_exit_code = (
        _edgeiq_original_daily_main()
    )

    if base_exit_code not in (
        None,
        0,
    ):
        print(
            "EDGEIQ_DAILY_BASE_REFRESH_FAIL_FAST"
        )
        print(
            f"base_exit_code="
            f"{base_exit_code}"
        )

        return int(base_exit_code)

    try:
        report = (
            _edgeiq_run_current_runner_performance_chain()
        )
    except RuntimeError as exc:
        print(
            "EDGEIQ_DAILY_CURRENT_RUNNER_PERFORMANCE_INTEGRATION_FAIL_FAST"
        )
        print(
            "base_refresh_status=PASS"
        )
        print(
            "performance_chain_status=FAIL"
        )
        print(
            f"performance_chain_error={exc}"
        )
        return 1

    counts = report["counts"]

    try:
        _edgeiq_run_post_performance_form_guide_refresh()
    except RuntimeError as exc:
        print("EDGEIQ_DAILY_POST_PERFORMANCE_FORM_GUIDE_REFRESH_FAIL_FAST")
        print(f"post_performance_refresh_error={exc}")
        return 1

    if not _edgeiq_run_current_runner_intelligence_audit_gate():
        print(
            "EDGEIQ_DAILY_CURRENT_RUNNER_INTELLIGENCE_FAIL_FAST"
        )
        return 1

    print(
        "EDGEIQ_DAILY_CURRENT_RUNNER_PERFORMANCE_INTEGRATION_PASS"
    )
    print(
        f"current_runners="
        f"{counts['current_runners']}"
    )
    print(
        f"suitability_rows="
        f"{counts['suitability_component']}"
    )
    print(
        f"epi_rows="
        f"{counts['epi']}"
    )
    print(
        f"publication_rows="
        f"{counts['publication']}"
    )
    print(
        "publication_epi_attachments="
        f"{counts['publication_epi_attachments']}"
    )
    print(
        "publication_missing_epi="
        f"{counts['publication_missing_epi']}"
    )
    print(
        "post_performance_form_guide_refresh=PASS"
    )

    return 0


if __name__=='__main__': raise SystemExit(main())

