from edgeiq_external_data_common_v1 import credential_status,now
import json
print(json.dumps({'checked_at':now(),'credentials':credential_status(),'values_printed':'NO'},indent=2,sort_keys=True))
