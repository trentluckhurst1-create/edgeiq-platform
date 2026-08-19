from pathlib import Path
from datetime import datetime
import shutil

repo = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
target = repo / "scripts" / "probe_racingcom_speed_data_network_v1.py"

if not target.exists():
    raise SystemExit(f"TARGET_NOT_FOUND: {target}")

original = target.read_text(encoding="utf-8")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = target.with_name(
    f"{target.stem}.before_getraceform_patch_{timestamp}{target.suffix}"
)
shutil.copy2(target, backup)

old_root = '''APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA = APP_ROOT / "public" / "data"
'''

new_root = '''APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = APP_ROOT
DATA = APP_ROOT / "public" / "data"
'''

if old_root not in original:
    raise SystemExit("EXPECTED_PROJECT_ROOT_BLOCK_NOT_FOUND")

patched = original.replace(old_root, new_root, 1)

old_operations = '''RELEVANT_OPERATIONS = {
    "getRaceEntriesForField_CD",
    "getRaceResults_CD",
    "getRaceNumberList_CD",
    "getMeeting_CD",
}
'''

new_operations = '''RELEVANT_OPERATIONS = {
    "getRaceEntriesForField_CD",
    "getRaceResults_CD",
    "getRaceNumberList_CD",
    "getMeeting_CD",
    "getRaceForm",
}
'''

if old_operations not in patched:
    raise SystemExit("EXPECTED_RELEVANT_OPERATIONS_BLOCK_NOT_FOUND")

patched = patched.replace(old_operations, new_operations, 1)

old_function = '''def operation_from_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if query.get("operationName"):
        return clean(query["operationName"][0])
    graphql_query = unquote(query.get("query", [""])[0])
    match = re.search(r"\\bquery\\s+([A-Za-z0-9_]+)", graphql_query)
    return match.group(1) if match else ""
'''

new_function = '''def operation_from_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    if query.get("operationName"):
        return clean(query["operationName"][0])

    graphql_query = unquote(query.get("query", [""])[0])

    named_query_match = re.search(
        r"\\bquery\\s+([A-Za-z_][A-Za-z0-9_]*)",
        graphql_query,
    )
    if named_query_match:
        return named_query_match.group(1)

    known_operations = (
        "getRaceForm",
        "getRaceResults_CD",
        "getRaceNumberList_CD",
        "getRaceEntriesForField_CD",
        "getMeeting_CD",
        "getRacesForMeet",
    )

    for operation in known_operations:
        if re.search(
            rf"\\b{re.escape(operation)}\\s*\\(",
            graphql_query,
            flags=re.IGNORECASE,
        ):
            return operation

    alias_match = re.search(
        r"\\b([A-Za-z_][A-Za-z0-9_]*)\\s*:\\s*"
        r"([A-Za-z_][A-Za-z0-9_]*)\\s*\\(",
        graphql_query,
    )
    if alias_match:
        return alias_match.group(2)

    return ""
'''

if old_function not in patched:
    raise SystemExit("EXPECTED_OPERATION_FUNCTION_NOT_FOUND")

patched = patched.replace(old_function, new_function, 1)

target.write_text(patched, encoding="utf-8")

print(f"PATCHED: {target}")
print(f"BACKUP:  {backup}")
print("PROJECT_ROOT_FIXED: YES")
print("GETRACEFORM_DETECTION_ADDED: YES")
print("GETRACEFORM_RELEVANT_OPERATION_ADDED: YES")
