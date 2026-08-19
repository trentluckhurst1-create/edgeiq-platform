# Runner Sectionals Access Decision

Decision: `CREDENTIAL_REQUIRED`

Clean Python replay uses no cookies or retained browser state. Approved credential mode uses `RACINGCOM_CHAMPION_DATA_ENDPOINT_KEY` only when supplied by environment.

```json
[
  {
    "mode": "ANONYMOUS_MINIMAL",
    "endpoint": "https://graphql.rmdprod.racing.com/",
    "method": "GET",
    "query_variables": "{\"meetCode\": \"5191101\", \"raceNumber\": \"1\"}",
    "status_code": 401,
    "response_content_type": "application/json; charset=UTF-8",
    "response_schema_match": "NO",
    "contains_sectionaltimes_callback": "NO",
    "horse_count": 0,
    "sectional_time_count": 0,
    "split_time_count": 0,
    "credential_state": "ABSENT",
    "cookie_state": "ABSENT",
    "access_classification": "CREDENTIAL_REQUIRED",
    "response_hash": "a24c315d94de0c2b9f62b27710bb7fab9aa26b44642284daf010e14d1fd88804",
    "raw_response_path": "",
    "error": ""
  },
  {
    "mode": "ANONYMOUS_BROWSER_HEADERS",
    "endpoint": "https://graphql.rmdprod.racing.com/",
    "method": "GET",
    "query_variables": "{\"meetCode\": \"5191101\", \"raceNumber\": \"1\"}",
    "status_code": 401,
    "response_content_type": "application/json; charset=UTF-8",
    "response_schema_match": "NO",
    "contains_sectionaltimes_callback": "NO",
    "horse_count": 0,
    "sectional_time_count": 0,
    "split_time_count": 0,
    "credential_state": "ABSENT",
    "cookie_state": "ABSENT",
    "access_classification": "CREDENTIAL_REQUIRED",
    "response_hash": "a24c315d94de0c2b9f62b27710bb7fab9aa26b44642284daf010e14d1fd88804",
    "raw_response_path": "",
    "error": ""
  },
  {
    "mode": "APPROVED_CREDENTIAL",
    "endpoint": "https://graphql.rmdprod.racing.com/",
    "method": "GET",
    "query_variables": "{\"meetCode\": \"5191101\", \"raceNumber\": \"1\"}",
    "status_code": 401,
    "response_content_type": "application/json; charset=UTF-8",
    "response_schema_match": "NO",
    "contains_sectionaltimes_callback": "NO",
    "horse_count": 0,
    "sectional_time_count": 0,
    "split_time_count": 0,
    "credential_state": "ABSENT",
    "cookie_state": "ABSENT",
    "access_classification": "CREDENTIAL_REQUIRED",
    "response_hash": "a24c315d94de0c2b9f62b27710bb7fab9aa26b44642284daf010e14d1fd88804",
    "raw_response_path": "",
    "error": ""
  }
]
```
