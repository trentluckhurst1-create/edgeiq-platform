from pathlib import Path

path = Path(
    r".\scripts\build_edgeiq_benchmark_observation_fact_v1.py"
)

text = path.read_text(encoding="utf-8")

start_marker = "def canonical_audit_passes(payload: Any) -> bool:\n"
end_marker = "\n\ndef runner_race_key"

start = text.find(start_marker)
end = text.find(end_marker, start)

if start == -1:
    raise RuntimeError(
        "Could not find canonical_audit_passes() in builder."
    )

if end == -1:
    raise RuntimeError(
        "Could not find the end of canonical_audit_passes()."
    )

replacement = r'''def canonical_audit_passes(payload: Any) -> bool:
    """
    Accept the governed V2.1 audit across supported audit schemas.

    PASS may be represented by:
    - status / audit_status / overall_status / result = PASS
    - pass / passed / audit_pass = true
    - a PASS marker stored anywhere in the JSON
    - zero failed checks combined with positive governed checks

    Merely containing a field name with the word FAIL must not cause failure.
    """

    pass_markers = {
        "EDGEIQ_RACINGCOM_CANONICAL_SPEED_WAREHOUSE_V2_1_AUDIT_PASS",
        "RACINGCOM_CANONICAL_SPEED_WAREHOUSE_V2_1_AUDIT_PASS",
        "CANONICAL_SPEED_WAREHOUSE_V2_1_AUDIT_PASS",
    }

    status_keys = {
        "status",
        "audit_status",
        "overall_status",
        "result",
    }

    boolean_pass_keys = {
        "pass",
        "passed",
        "audit_pass",
        "is_pass",
        "is_valid",
    }

    failed_count_keys = {
        "failed_checks",
        "failure_count",
        "failed_check_count",
        "errors",
        "error_count",
    }

    explicit_pass = False
    explicit_fail = False
    pass_marker_found = False
    failed_checks_present = False

    def walk(value: Any, parent_key: str = "") -> None:
        nonlocal explicit_pass
        nonlocal explicit_fail
        nonlocal pass_marker_found
        nonlocal failed_checks_present

        if isinstance(value, dict):
            for raw_key, child in value.items():
                key = str(raw_key).strip().lower()

                if key in status_keys:
                    status = clean(child).upper()
                    if status in {
                        "PASS",
                        "PASSED",
                        "SUCCESS",
                        "VALID",
                        "COMPLETE",
                    }:
                        explicit_pass = True
                    elif status in {
                        "FAIL",
                        "FAILED",
                        "ERROR",
                        "INVALID",
                    }:
                        explicit_fail = True

                elif key in boolean_pass_keys:
                    if child is True:
                        explicit_pass = True
                    elif child is False:
                        explicit_fail = True
                    else:
                        status = clean(child).upper()
                        if status in {
                            "TRUE",
                            "PASS",
                            "PASSED",
                            "YES",
                            "1",
                        }:
                            explicit_pass = True
                        elif status in {
                            "FALSE",
                            "FAIL",
                            "FAILED",
                            "NO",
                            "0",
                        }:
                            explicit_fail = True

                elif key in failed_count_keys:
                    if isinstance(child, list):
                        if len(child) > 0:
                            failed_checks_present = True
                    elif isinstance(child, dict):
                        if len(child) > 0:
                            failed_checks_present = True
                    elif isinstance(child, (int, float)):
                        if child != 0:
                            failed_checks_present = True
                    else:
                        text_value = clean(child)
                        if text_value not in {"", "0", "NONE", "[]", "{}"}:
                            failed_checks_present = True

                walk(child, key)

        elif isinstance(value, list):
            for child in value:
                walk(child, parent_key)

        elif isinstance(value, str):
            upper_value = value.strip().upper()

            if upper_value in pass_markers:
                pass_marker_found = True

            if any(marker in upper_value for marker in pass_markers):
                pass_marker_found = True

    walk(payload)

    if explicit_fail or failed_checks_present:
        return False

    if explicit_pass or pass_marker_found:
        return True

    return False
'''

patched = (
    text[:start]
    + replacement
    + text[end:]
)

path.write_text(patched, encoding="utf-8")

print(
    "Patched canonical V2.1 audit PASS detection in:",
    path,
)
