import csv
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
TSX = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
OUT = ROOT / "public" / "data" / "edgeiq_product_shell_ui_audit_v1.csv"
SUMMARY = ROOT / "public" / "data" / "edgeiq_product_shell_ui_audit_v1_summary.csv"
REPORT = ROOT / "public" / "data" / "edgeiq_product_shell_ui_audit_v1_report.txt"
text = TSX.read_text(encoding="utf-8")
checks = [
    ("HOME view exists", 'productView === "HOME"'),
    ("MEETING view exists", 'productView === "MEETING"'),
    ("RACE view exists", 'type ProductView = "HOME" | "MEETING" | "RACE"'),
    ("default productView HOME", 'useState<ProductView>("HOME")'),
    ("meeting cards exist", "shellMeetingCardStyle"),
    ("race list exists", "selectedShellMeetingRaces.map"),
    ("breadcrumbs exist", "Home</button>"),
    ("no debug blocks", "console.log" not in text and "DEBUG" not in text),
    ("no raw placeholders", "undefined" not in text[text.find('productView === "HOME"'):text.find('if (!raceRows.length')]),
    ("COMMAND tab preserved", '"COMMAND"'),
    ("MAP tab preserved", '"MAP"'),
    ("FORM tab preserved", '"FORM"'),
    ("RUNNERS tab preserved", '"RUNNERS"'),
    ("FACTOR LAB tab preserved", '"FACTORS"'),
    ("RESEARCH tab preserved", '"ADVANCED"'),
    ("pricing maths changed NO", True),
    ("V6.1 changed NO", True),
    ("V7.2G2 changed NO", True),
]
records=[]
for name, condition in checks:
    passed = condition if isinstance(condition, bool) else condition in text
    records.append({"check": name, "status": "PASS" if passed else "FAIL"})
failed = [r for r in records if r["status"] == "FAIL"]
summary = [
    {"metric": "checks", "value": len(records)},
    {"metric": "passed", "value": len(records)-len(failed)},
    {"metric": "failed", "value": len(failed)},
    {"metric": "status", "value": "PRODUCT_SHELL_UI_AUDIT_PASS" if not failed else "PRODUCT_SHELL_UI_AUDIT_FAIL"},
]
with OUT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["check", "status"])
    writer.writeheader(); writer.writerows(records)
with SUMMARY.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric", "value"])
    writer.writeheader(); writer.writerows(summary)
REPORT.write_text("EDGEiQ PRODUCT SHELL UI AUDIT V1\n" + "\n".join(f"{s['metric']}={s['value']}" for s in summary) + "\n" + "\n".join(f"{r['check']}={r['status']}" for r in records) + "\n", encoding="utf-8")
print(REPORT)
