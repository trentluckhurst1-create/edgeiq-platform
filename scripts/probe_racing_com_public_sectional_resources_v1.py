
from __future__ import annotations
from edgeiq_racing_com_public_common_v1 import *
def main():
    ensure(); split=read_csv(PUB/'edgeiq_racingcom_runner_split_fact_v1.csv'); speed=read_csv(PUB/'edgeiq_racingcom_runner_speed_fact_v1.csv')
    reg=[]
    if split:
        reg.append({'resource_type':'runner_sectional_split_payload','source':'getRaceForm retained local payload','field_path':'data.sectionaltimes_callback.Horses[].SplitTimes','rows_observed':len(split),'access_classification':'LOCAL_GOVERNED_EVIDENCE_DIRECT_PUBLIC_NOT_CONFIRMED','public_probe_status':'NOT_PROBED_NO_PUBLIC_RESOURCE_URL'})
    if speed:
        reg.append({'resource_type':'speed_data_page','source':'source_page_url','field_path':'public/data/edgeiq_racingcom_runner_speed_fact_v1.csv.source_page_url','rows_observed':len(speed),'access_classification':'PUBLIC_PAGE_URL_KNOWN','public_probe_status':'PAGE_FETCHED_BY_FRONTEND_FORENSICS'})
    fields=[]
    for c in ['FullName','SaddleNumber','FinalPosition','SectionalTimes.Distance','SectionalTimes.Time','SectionalTimes.Position','SplitTimes.Distance','SplitTimes.Time','SplitTimes.Position','RaceTime','SixHundredMetresTime','TwoHundredMetresTime','Early','Mid','Late','OverallPeakSpeed']:
        fields.append({'field':c,'meaning':'Racing.com raw timing/speed payload field','edgeiq_use':'raw input only; no Racing.com proprietary standard figures admitted'})
    schema={'runner_sectional_source':'getRaceForm data.sectionaltimes_callback.Horses[].SplitTimes','unit_semantics':'metres from finish labels parsed into start/end metres','public_anonymous_replay':'NOT_CONFIRMED'}
    write_csv(SECT/'sectional_resource_registry.csv',reg); write_json(SECT/'sectional_resource_registry.json',reg)
    write_json(SECT/'sectional_schema.json',schema); write_csv(SECT/'sectional_field_dictionary.csv',fields)
    write_text(SECT/'sectional_resource_report.md','# Racing.com Sectional Resource Discovery V1\n\nRunner-level sectional source is identified in retained getRaceForm payloads as `data.sectionaltimes_callback.Horses[].SectionalTimes` and `SplitTimes`. Direct public anonymous replay is not confirmed; canonical admission remains blocked until access is governed.\n')
if __name__=='__main__': main()
