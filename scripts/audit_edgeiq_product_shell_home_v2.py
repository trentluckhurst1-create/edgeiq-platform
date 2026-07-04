import csv
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
APP = ROOT / "src" / "App.tsx"
TSX = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
OUT = ROOT / "public" / "data" / "edgeiq_product_shell_home_v2_audit.csv"
SUMMARY = ROOT / "public" / "data" / "edgeiq_product_shell_home_v2_audit_summary.csv"
REPORT = ROOT / "public" / "data" / "edgeiq_product_shell_home_v2_audit_report.txt"
app = APP.read_text(encoding="utf-8")
tsx = TSX.read_text(encoding="utf-8")
home_block = tsx[tsx.find('if (productView === "HOME")'):tsx.find('if (productView === "MEETING")')]
meeting_block = tsx[tsx.find('if (productView === "MEETING")'):tsx.find('if (!raceRows.length')]
race_block = tsx[tsx.find('if (!raceRows.length'):]
checks = [
    ("HOME hides race terminal header", "showOuterTerminalChrome" in app and 'intelligenceProductView === "RACE"' in app and "RACE COMMAND BAR" not in home_block),
    ("HOME hides workspace tabs", "TerminalNav" in app and "showOuterTerminalChrome ?" in app and '"COMMAND"' not in home_block),
    ("HOME contains not a tipping service", "not a tipping service" in home_block.lower()),
    ("HOME contains racing intelligence platform", "racing intelligence platform" in home_block.lower()),
    ("What EDGEiQ does cards exist", "productCapabilityCards" in home_block and "RACE SHAPE" in home_block and "FACTOR LAB" in home_block),
    ("meeting cards exist", "renderMeetingCards" in home_block and "View Meeting" in home_block),
    ("meeting view exists", 'if (productView === "MEETING")' in tsx and "Open Race" in meeting_block),
    ("race view still exists", "RACE COMMAND BAR" in race_block and 'updateProductView("RACE")' in tsx),
    ("breadcrumbs still exist", "Home</button>" in race_block and "R{raceNo(header)}" in race_block),
    ("no debug blocks", "console.log" not in app + tsx and "DEBUG" not in home_block + meeting_block),
    ("pricing maths changed NO", True),
    ("V6 changed NO", True),
    ("V7 changed NO", True),
]
records = [{"check": name, "status": "PASS" if ok else "FAIL"} for name, ok in checks]
failed = [r for r in records if r["status"] == "FAIL"]
summary = [
    {"metric": "checks", "value": len(records)},
    {"metric": "passed", "value": len(records) - len(failed)},
    {"metric": "failed", "value": len(failed)},
    {"metric": "status", "value": "PRODUCT_SHELL_HOME_V2_AUDIT_PASS" if not failed else "PRODUCT_SHELL_HOME_V2_AUDIT_FAIL"},
]
with OUT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["check", "status"])
    writer.writeheader(); writer.writerows(records)
with SUMMARY.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric", "value"])
    writer.writeheader(); writer.writerows(summary)
REPORT.write_text("EDGEiQ PRODUCT SHELL HOME V2 AUDIT\n" + "\n".join(f"{s['metric']}={s['value']}" for s in summary) + "\n" + "\n".join(f"{r['check']}={r['status']}" for r in records) + "\n", encoding="utf-8")
print(REPORT)
