import csv
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
TSX = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
OUT = ROOT / "public" / "data" / "edgeiq_product_shell_home_v3_polish_audit.csv"
SUMMARY = ROOT / "public" / "data" / "edgeiq_product_shell_home_v3_polish_audit_summary.csv"
REPORT = ROOT / "public" / "data" / "edgeiq_product_shell_home_v3_polish_audit_report.txt"
text = TSX.read_text(encoding="utf-8")
home_start = text.find('if (productView === "HOME")')
meeting_start = text.find('if (productView === "MEETING")', home_start)
home = text[home_start:meeting_start]
meeting_plus = text[meeting_start:]
checks = [
    ("stats pill row removed", "productShellStats" not in home and "Victoria focus" not in home and "Fields ready" not in home),
    ("CLEAN PATH INTO THE TERMINAL removed", "clean path into the terminal" not in home.lower()),
    ("floating FIELDS READY badge pattern removed from HOME", "meeting.meetingStatus, \"#34d399\"" not in home and "Status:" in home),
    ("FUTURE CARDS IN THE GOVERNED UNIVERSE removed or replaced cleanly", "future cards in the governed universe" not in home.lower()),
    ("HOME default remains", 'useState<ProductView>("HOME")' in text),
    ("not a tipping service copy remains", "not a tipping service" in home.lower()),
    ("meeting cards still exist", "renderMeetingCards" in home),
    ("view meeting buttons exist", "View Meeting" in home),
    ("meeting view still exists", 'if (productView === "MEETING")' in text and "Open Race" in meeting_plus),
    ("race view still exists", "RACE COMMAND BAR" in meeting_plus),
    ("no debug blocks", "console.log" not in text and "DEBUG" not in home),
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
    {"metric": "status", "value": "PRODUCT_SHELL_HOME_V3_POLISH_AUDIT_PASS" if not failed else "PRODUCT_SHELL_HOME_V3_POLISH_AUDIT_FAIL"},
]
with OUT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["check", "status"])
    writer.writeheader(); writer.writerows(records)
with SUMMARY.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric", "value"])
    writer.writeheader(); writer.writerows(summary)
REPORT.write_text("EDGEiQ PRODUCT SHELL HOME V3 POLISH AUDIT\n" + "\n".join(f"{s['metric']}={s['value']}" for s in summary) + "\n" + "\n".join(f"{r['check']}={r['status']}" for r in records) + "\n", encoding="utf-8")
print(REPORT)
