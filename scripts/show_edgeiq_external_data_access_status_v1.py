from edgeiq_external_data_common_v1 import credential_status
for name,status in credential_status().items(): print(f'{name}: {status}')
