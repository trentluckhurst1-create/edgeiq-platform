from pathlib import Path
import csv
import re

ROOT = Path(__file__).resolve().parents[1]
TSX = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
OUT = ROOT / "public" / "data" / "edgeiq_tab_polish_audit_v1.csv"

source = TSX.read_text(encoding="utf-8", errors="replace")
checks = []

def add(check_name, passed, detail=""):
    checks.append({
        "check_name": check_name,
        "status": "PASS" if passed else "FAIL",
        "detail": detail,
    })

required_titles = [
    "Race Intelligence",
    "Race Field",
    "EDGEiQ Performance Index",
    "Form Study",
    "Race Map",
    "EDGEiQ Nexus",
    "EDGEiQ Market",
]
for title in required_titles:
    add(f"standard_title_present::{title}", title in source, title)

legacy_market_title = "EDGEiQ and market price comparison"
add("legacy_market_title_removed", legacy_market_title not in source, legacy_market_title)

heading_blocks = re.findall(r'<div\s+className="edgeiq-tab-heading"[\s\S]*?</div>', source)
spam_blocks = [block.strip().replace("\n", " ")[:240] for block in heading_blocks if "Awaiting Feed" in block]
add("no_awaiting_feed_heading_spam", len(spam_blocks) == 0, " | ".join(spam_blocks))

add("race_list_file_reference_present", 'raceList: "/data/edgeiq_vic_three_day_race_list_v1.csv"' in source, "FILES.raceList")
add("race_list_state_present", "const [raceListRows, setRaceListRows]" in source, "raceListRows state")
add("race_list_loaded", "loadCsv(FILES.raceList)" in source and "setRaceListRows(raceList)" in source, "loadCsv + setter")
add("racingcom_fallback_loop_present", "raceListRows.forEach" in source, "raceListRows.forEach")
add("fallback_is_additive_not_empty_only", "raceMap.size === 0" not in source[source.find("const productShellRaces"):source.find("const productShellMeetings")], "no raceMap.size === 0 gate inside productShellRaces")

dep_match = re.search(r'const\s+productShellRaces\s*=\s*useMemo\([\s\S]*?\},\s*\[([^\]]+)\]\);', source)
if dep_match:
    deps = dep_match.group(1)
    add("product_shell_races_depends_runner_rows", "runnerRows" in deps, deps)
    add("product_shell_races_depends_race_list_rows", "raceListRows" in deps, deps)
else:
    add("product_shell_races_usememo_found", False, "productShellRaces useMemo not found")

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["check_name", "status", "detail"])
    writer.writeheader()
    writer.writerows(checks)

failures = [row for row in checks if row["status"] != "PASS"]
print(f"EDGEiQ tab polish audit: {len(checks) - len(failures)}/{len(checks)} PASS")
if failures:
    for row in failures:
        print(f"FAIL {row['check_name']}: {row['detail']}")
    raise SystemExit(1)
