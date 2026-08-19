
from __future__ import annotations
import subprocess
from edgeiq_racing_com_public_common_v1 import *

def git(cmd):
    try: return subprocess.check_output(['git']+cmd,cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
    except Exception: return ''

def main():
    ensure(); status=git(['status','--short']); head=git(['rev-parse','--short','HEAD'])
    local_speed=read_csv(PUB/'edgeiq_racingcom_runner_speed_fact_v1.csv'); local_split=read_csv(PUB/'edgeiq_racingcom_runner_split_fact_v1.csv')
    external=read_csv(PUB/'edgeiq_external_source_access_health_fact_v1.csv')
    base={'base_commit':head,'dirty_file_count':len([x for x in status.splitlines() if x.strip()]),'external_data_status_rows':len(external),'racingcom_runner_speed_rows':len(local_speed),'racingcom_runner_split_rows':len(local_split),'credential_handling':'No credentials/cookies/tokens imported. GraphQL direct runner-sectional replay skipped unless governed credential exists.','local_speed_coverage':'retained getRaceForm payload evidence through existing speed facts'}
    write_json(DOC/'RACING_COM_PUBLIC_DATA_V1_BASELINE.json',base)
    write_text(DOC/'RACING_COM_PUBLIC_DATA_V1_BASELINE.md','# Racing.com Public Data V1 Baseline\n\n- Base commit: `{}`\n- Dirty worktree entries observed: {}\n- Existing Racing.com speed rows: {}\n- Existing Racing.com split rows: {}\n- Credential handling: no browser session material, cookies, tokens or API keys are imported.\n- Local sectional source: retained `getRaceForm` payloads and existing speed/split facts.\n'.format(head,base['dirty_file_count'],len(local_speed),len(local_split)))
    contract={'allowed_raw_inputs':['meeting metadata','race metadata','runner identity','official result fields','race time','runner race time','raw SectionalTimes','raw SplitTimes','download metadata when public'],'ignored_racingcom_derived_metrics':['standardTimeDifference','standardTimeId','rankings/colour classifications','speed ratings','derived comments','proprietary standard figures'],'edgeiq_calculates':['Standard Times','Race Time Delta','sectional deltas','Lengths v Standard','Performance Base','normalisation','ratings','EPI'],'canonical_admission':'NO until public access and unit semantics are governed'}
    write_json(DOC/'RACING_COM_PUBLIC_DATA_CONTRACT_V1.json',contract)
    write_text(DOC/'RACING_COM_PUBLIC_DATA_CONTRACT_V1.md','# Racing.com Public Data Contract V1\n\nEDGEiQ may ingest raw Racing.com meeting, race, result, timing and sectional observations when legitimately accessible. EDGEiQ deliberately ignores Racing.com proprietary standard-time-derived metrics and rankings. EDGEiQ calculates its own Standard Times, Race Time Delta, sectional deltas, Lengths v Standard, Performance Base, normalisation, ratings and EPI.\n')
    docs={
    'RACING_COM_HAR_CAPTURE_GUIDE.md':'# Racing.com HAR Capture Guide\n\nOptional. Capture a logged-out public browser HAR only. Remove cookies/auth/session material before analysis. The analyser stores sanitised inventories only.\n',
    'RACING_COM_PUBLIC_DATA_V1_MASTER_REPORT.md':'# Racing.com Public Data V1 Master Report\n\nOutcome: code complete with access boundary. Public appv2 meeting catalogue is accessible. Runner-level sectionals are identified in retained `getRaceForm` payloads but direct anonymous GraphQL replay is not confirmed.\n',
    'RACING_COM_PUBLIC_DATA_V1_OPERATOR_GUIDE.md':'# Operator Guide\n\nRun the acceptance script in OFFLINE, LIVE_PUBLIC, and FULL_DRY_RUN modes. Do not provide credentials unless a governed access agreement exists.\n',
    'RACING_COM_PUBLIC_DATA_V1_SOURCE_MAP.md':'# Source Map\n\n- Public meeting catalogue: `www.racing.com/services/appv2/GetMeetsByMonth`.\n- Runner sectionals evidence: retained `getRaceForm` payloads under `outputs/sectionals/raw/VIC/racingcom_full_payloads`.\n- Processed facts: `data/processed/racing-com-public-v1`.\n',
    'RACING_COM_PUBLIC_DATA_V1_FIELD_DICTIONARY.md':'# Field Dictionary\n\nSee `sectionals/sectional_field_dictionary.csv` and processed fact schemas. Raw timing fields are retained as observations only.\n',
    'RACING_COM_PUBLIC_DATA_V1_ACCESS_MATRIX.md':'# Access Matrix\n\nPublic appv2 meeting catalogue: public anonymous confirmed. Direct GraphQL runner sectionals: credential required/not publicly replay-confirmed. Retained local payload evidence: governed local evidence, not a fresh public proof.\n',
    'RACING_COM_PUBLIC_DATA_V1_ACCEPTANCE.md':'# Acceptance\n\nExpected governed status is `CODE_COMPLETE_ACCESS_REQUIRED` unless live public runner sectionals are proven anonymously.\n',
    'RACING_COM_PUBLIC_DATA_V1_LIMITATIONS.md':'# Limitations\n\nRunner-level sectional source is identified from retained payloads, but direct logged-out reproducibility is not confirmed. No canonical timing warehouse admission occurs in this program.\n'}
    for k,v in docs.items(): write_text(DOC/k,v)
if __name__=='__main__': main()
