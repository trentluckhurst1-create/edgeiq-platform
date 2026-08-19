import json
from pathlib import Path
from collections import Counter

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
source = root / "public" / "data" / "edgeiq_form_guide_enriched_v2.json"
output = root / "docs" / "full-product-implementation" / "FORM_GUIDE_ENRICHED_V2_STRUCTURE_INSPECTION.txt"

with source.open("r", encoding="utf-8-sig") as handle:
    payload = json.load(handle)

def describe(value, path="$", depth=0, lines=None, keys=None):
    if lines is None:
        lines = []
    if keys is None:
        keys = Counter()

    if depth > 6:
        return lines, keys

    if isinstance(value, dict):
        lines.append(f"{path}: object keys={len(value)}")
        for key, child in value.items():
            keys[key] += 1
            child_path = f"{path}.{key}"
            if isinstance(child, (dict, list)):
                describe(child, child_path, depth + 1, lines, keys)
            else:
                preview = repr(child)
                if len(preview) > 160:
                    preview = preview[:157] + "..."
                lines.append(f"{child_path}: {type(child).__name__} = {preview}")
    elif isinstance(value, list):
        lines.append(f"{path}: array count={len(value)}")
        for index, child in enumerate(value[:3]):
            describe(child, f"{path}[{index}]", depth + 1, lines, keys)
    else:
        lines.append(f"{path}: {type(value).__name__} = {value!r}")

    return lines, keys

lines, keys = describe(payload)

important = [
    "meeting_id", "race_id", "runner_id", "horse_id", "horse",
    "runner", "runners", "recentRuns", "recent_runs", "history",
    "careerProfile", "career_profile", "epi", "eri",
    "positionInRunning", "position_in_running",
    "esi800600", "esi600400", "esi400200", "esi200F",
    "sectionals", "todaysMatch", "today_match", "insights"
]

report = []
report.append("EDGEIQ FORM GUIDE ENRICHED V2 STRUCTURE INSPECTION")
report.append("=" * 58)
report.extend(lines)
report.append("")
report.append("IMPORTANT KEY COUNTS")
report.append("-" * 58)

for key in important:
    report.append(f"{key}: {keys.get(key, 0)}")

output.parent.mkdir(parents=True, exist_ok=True)
output.write_text("\n".join(report) + "\n", encoding="utf-8")

print(f"WROTE={output}")
print(f"ROOT_TYPE={type(payload).__name__}")
print(f"IMPORTANT_KEYS_FOUND={sum(1 for key in important if keys.get(key, 0) > 0)}")
print("EDGEIQ_FORM_GUIDE_STRUCTURE_INSPECTION_PASS")
