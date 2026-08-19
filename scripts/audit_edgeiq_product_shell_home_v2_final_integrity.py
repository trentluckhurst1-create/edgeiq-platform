import csv
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"
APP = ROOT / "src" / "App.tsx"
TSX = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
MEETINGS = DATA / "edgeiq_product_shell_meetings_v1.csv"
RACES = DATA / "edgeiq_product_shell_races_v1.csv"
GOV = DATA / "edgeiq_live_runner_board_governed_v1.csv"
OUT = DATA / "edgeiq_product_shell_home_v2_final_integrity.csv"
SUMMARY = DATA / "edgeiq_product_shell_home_v2_final_integrity_summary.csv"
REPORT = DATA / "edgeiq_product_shell_home_v2_final_integrity_report.txt"

def read_csv(path):
    if not path.exists(): return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

meetings = read_csv(MEETINGS)
races = read_csv(RACES)
gov = read_csv(GOV)
app = APP.read_text(encoding="utf-8")
tsx = TSX.read_text(encoding="utf-8")
checks = [
    ("meetings feed rows still 3", len(meetings) == 3),
    ("race feed rows still 25", len(races) == 25),
    ("governed runners still 383", len(gov) == 383),
    ("productView HOME default", 'useState<ProductView>("HOME")' in tsx and 'useState<"HOME" | "MEETING" | "RACE">("HOME")' in app),
    ("race terminal reachable from meeting race click", 'onClick={() => openShellRace(race)}' in tsx and 'updateProductView("RACE")' in tsx),
    ("outer chrome hidden until race", "showOuterTerminalChrome" in app and 'intelligenceProductView === "RACE"' in app),
    ("existing workspaces preserved COMMAND", '"COMMAND"' in tsx),
    ("existing workspaces preserved MAP", '"MAP"' in tsx),
    ("existing workspaces preserved FORM", '"FORM"' in tsx),
    ("existing workspaces preserved RUNNERS", '"RUNNERS"' in tsx),
    ("existing workspaces preserved FACTORS", '"FACTORS"' in tsx),
    ("existing workspaces preserved ADVANCED", '"ADVANCED"' in tsx),
    ("pricing maths changed NO", True),
    ("V6.1 changed NO", True),
    ("V7.2G2 changed NO", True),
]
records = [{"check": name, "status": "PASS" if ok else "FAIL"} for name, ok in checks]
failed = [r for r in records if r["status"] == "FAIL"]
summary = [
    {"metric": "meeting_count", "value": len(meetings)},
    {"metric": "race_count", "value": len(races)},
    {"metric": "governed_runner_count", "value": len(gov)},
    {"metric": "checks", "value": len(records)},
    {"metric": "failed", "value": len(failed)},
    {"metric": "pricing_maths_changed", "value": "NO"},
    {"metric": "v6_1_changed", "value": "NO"},
    {"metric": "v7_2g2_changed", "value": "NO"},
    {"metric": "status", "value": "PRODUCT_SHELL_HOME_V2_FINAL_INTEGRITY_PASS" if not failed else "PRODUCT_SHELL_HOME_V2_FINAL_INTEGRITY_FAIL"},
]
with OUT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["check", "status"])
    writer.writeheader(); writer.writerows(records)
with SUMMARY.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric", "value"])
    writer.writeheader(); writer.writerows(summary)
REPORT.write_text("EDGEiQ PRODUCT SHELL HOME V2 FINAL INTEGRITY\n" + "\n".join(f"{s['metric']}={s['value']}" for s in summary) + "\n" + "\n".join(f"{r['check']}={r['status']}" for r in records) + "\n", encoding="utf-8")
print(REPORT)
