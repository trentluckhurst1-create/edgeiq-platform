# EDGEiQ Racing.com Access Contract V1

| Field | Value |
| --- | --- |
| endpoint | https://graphql.rmdprod.racing.com/ |
| required_authentication | RACINGCOM_PUBLIC_WIDGET_API_KEY |
| source_of_evidence | repository adapter contract and prior 401 evidence |
| intended_access_class | SUPPORTED_CREDENTIAL_REQUIRED |
| operator_action_required | Obtain approved key and set only in PowerShell session |
| repository_configuration_required | $env:RACINGCOM_PUBLIC_WIDGET_API_KEY="<APPROVED_VALUE>" |
| validation_command | python .\scripts\validate_edgeiq_external_data_credentials_v1.py |
| safe_failure_behaviour | skip request when key absent |
| secret_storage_rule | never commit, print, log, or persist value |
| credential_rotation_considerations | operator-owned rotation |
| licence_review_status | REQUIRED |
