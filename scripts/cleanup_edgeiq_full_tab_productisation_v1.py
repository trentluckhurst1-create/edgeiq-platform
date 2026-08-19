from pathlib import Path
from datetime import datetime, timezone
import csv

root = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
tsx = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
index_css = root / "src" / "index.css"
summary = root / "public" / "data" / "edgeiq_full_tab_productisation_v1_cleanup_summary.csv"
report = root / "public" / "data" / "edgeiq_full_tab_productisation_v1_cleanup_report.txt"

changes = []
text = tsx.read_text(encoding="utf-8-sig")
replacements = {
    "MODEL RANK | WIN CHANCE | FAIR PRICE | TAB PRICE | VALUE EDGE | EDGEiQ CONFIDENCE | MARKET READ": "MODEL RANK | WIN CHANCE | FAIR PRICE | TAB PRICE | SETUP GAP | EDGEiQ CONFIDENCE | MARKET READ",
    "Betting Confidence": "Evidence Confidence",
    "Market overbet": "Market caution",
    "No value edge currently identified.": "No setup advantage currently identified.",
    "No value edge currently triggered.": "No setup advantage currently triggered.",
    "value edge currently identified": "setup advantage currently identified",
    "value edge currently triggered": "setup advantage currently triggered",
}
for old, new in replacements.items():
    count = text.count(old)
    if count:
        text = text.replace(old, new)
        changes.append(("RaceIntelligenceScreen.tsx", old, new, count))
tsx.write_text(text, encoding="utf-8")

css = index_css.read_text(encoding="utf-8-sig")
css = css.replace("\ufeff", "")
lines = [line for line in css.splitlines() if line.strip()]
# Remove duplicate terminal imports and rebuild a clean import header.
non_terminal = [line for line in lines if "edgeiqProductTerminalV1.css" not in line]
if not non_terminal or non_terminal[0].strip() != "@import './styles/edgeiqProductTerminalV1.css';":
    lines_out = ["@import './styles/edgeiqProductTerminalV1.css';"] + non_terminal
else:
    lines_out = non_terminal
new_css = "\n".join(lines_out) + "\n"
if new_css != index_css.read_text(encoding="utf-8", errors="ignore"):
    index_css.write_text(new_css, encoding="utf-8")
    changes.append(("index.css", "BOM/import header", "normalised product CSS import header", 1))

rows = [
    {"metric": "status", "value": "FULL_TAB_PRODUCTISATION_V1_CLEANUP_APPLIED"},
    {"metric": "changes_applied", "value": str(sum(c[3] for c in changes))},
    {"metric": "ui_changed", "value": "YES"},
    {"metric": "backend_data_changed", "value": "NO"},
    {"metric": "pricing_changed", "value": "NO"},
    {"metric": "probability_changed", "value": "NO"},
    {"metric": "v6_1_changed", "value": "NO"},
    {"metric": "v7_2g2_changed", "value": "NO"},
    {"metric": "active_csv_schemas_changed", "value": "NO"},
    {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
]
with summary.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["metric", "value"])
    writer.writeheader()
    writer.writerows(rows)

with report.open("w", encoding="utf-8") as f:
    f.write("EDGEiQ Full Tab Productisation V1 Cleanup\n")
    f.write("Status: FULL_TAB_PRODUCTISATION_V1_CLEANUP_APPLIED\n")
    f.write("\nChanges:\n")
    for file_name, old, new, count in changes:
        f.write(f"- {file_name}: {count} replacement(s): {old} -> {new}\n")
    if not changes:
        f.write("- No cleanup changes required.\n")
    f.write("\nBackend data changed: NO\nPricing changed: NO\nProbability changed: NO\nV6.1 changed: NO\nV7.2G2 changed: NO\nActive CSV schemas changed: NO\n")

print("FULL_TAB_PRODUCTISATION_V1_CLEANUP_APPLIED")
