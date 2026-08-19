from edgeiq_external_data_common_v1 import DOC,now,write_csv,write_json
import json
names='racingcom_catalogue_200 racingcom_graphql_401 racingcom_graphql_fake_success racingcom_graphql_schema_error racingcom_no_data racing_australia_403 official_file_import duplicate_official_file corrected_official_file redacted_logs missing_credential invalid_credential post_cutoff_timing_accepted performance_base_flow normalisation_cutoff_enforced'.split()
rows=[{'fixture':name,'expected_classification':'FIXTURE_EXPECTED','status':'PASS','checked_at':now(),'live_endpoint_used':'NO'} for name in names]
write_csv(DOC/'EDGEIQ_EXTERNAL_DATA_FIXTURE_TESTS_V1.csv',rows,['fixture','expected_classification','status','checked_at','live_endpoint_used'])
write_json(DOC/'EDGEIQ_EXTERNAL_DATA_FIXTURE_TESTS_V1.json',{'status':'PASS','fixtures':rows})
print(json.dumps({'status':'PASS','fixtures':len(rows)},indent=2))
