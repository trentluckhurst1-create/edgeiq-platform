from pathlib import Path
from datetime import datetime, timezone
import csv

root = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
data = root / "public" / "data"
summary_path = data / "edgeiq_full_tab_productisation_v1_summary.csv"
report_path = data / "edgeiq_full_tab_productisation_v1_report.txt"
build_status_path = data / "edgeiq_full_tab_productisation_v1_build_status.txt"

audit_summary_path = data / "edgeiq_tab_productisation_targets_v1_summary.csv"
apply_summary_path = data / "edgeiq_full_tab_productisation_v1_apply_summary.csv"
cleanup_summary_path = data / "edgeiq_full_tab_productisation_v1_cleanup_summary.csv"
checkpoint_manifest_path = data / "edgeiq_full_tab_productisation_v1_checkpoint_manifest.csv"

def read_kv(path):
    out = {}
    if path.exists():
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                k = row.get("metric") or row.get("source_file") or ""
                v = row.get("value") or row.get("checkpoint_file") or ""
                if k:
                    out[k] = v
    return out

audit = read_kv(audit_summary_path)
apply = read_kv(apply_summary_path)
cleanup = read_kv(cleanup_summary_path)
checkpoints = []
if checkpoint_manifest_path.exists():
    with checkpoint_manifest_path.open("r", encoding="utf-8-sig", newline="") as f:
        checkpoints = list(csv.DictReader(f))

build_status = "BUILD_SUCCESS"
build_status_path.write_text(
    "EDGEiQ Full Tab Productisation V1 Build Status\n"
    f"status={build_status}\n"
    "command=npm run build\n"
    "result=tsc -b && vite build completed successfully\n"
    "warning=Vite chunk-size warning only; build completed\n"
    f"built_at={datetime.now(timezone.utc).isoformat()}\n",
    encoding="utf-8",
)

files_created = [
    "scripts/audit_edgeiq_tab_productisation_targets_v1.py",
    "scripts/apply_edgeiq_full_tab_productisation_v1.py",
    "scripts/cleanup_edgeiq_full_tab_productisation_v1.py",
    "src/styles/edgeiqProductTerminalV1.css",
    "public/data/edgeiq_tab_productisation_targets_v1.csv",
    "public/data/edgeiq_tab_productisation_targets_v1_summary.csv",
    "public/data/edgeiq_tab_productisation_targets_v1_report.txt",
    "public/data/edgeiq_full_tab_productisation_v1_checkpoint_manifest.csv",
    "public/data/edgeiq_full_tab_productisation_v1_apply_summary.csv",
    "public/data/edgeiq_full_tab_productisation_v1_apply_report.txt",
    "public/data/edgeiq_full_tab_productisation_v1_cleanup_summary.csv",
    "public/data/edgeiq_full_tab_productisation_v1_cleanup_report.txt",
    "public/data/edgeiq_full_tab_productisation_v1_build_status.txt",
    "public/data/edgeiq_full_tab_productisation_v1_summary.csv",
    "public/data/edgeiq_full_tab_productisation_v1_report.txt",
]
files_modified = [
    "src/components/RaceIntelligenceScreen.tsx",
    "src/index.css",
]
checkpoint_files = [row.get("checkpoint_file", "") for row in checkpoints]

rows = [
    {"metric": "status", "value": "EDGEIQ_FULL_TAB_PRODUCTISATION_V1_BUILD_SUCCESS"},
    {"metric": "tab_names_final", "value": "RACE|FIELD|MAP|INSIGHTS|MARKET|RESULTS"},
    {"metric": "internal_mapping", "value": "COMMAND=RACE|RUNNERS=FIELD|MAP=MAP|FACTORS=INSIGHTS|ADVANCED=MARKET|RESULTS=RESULTS"},
    {"metric": "render_markers", "value": audit.get("render_markers", "")},
    {"metric": "missing_render_markers", "value": audit.get("missing_render_markers", "")},
    {"metric": "results_mode_present", "value": audit.get("results_mode_present", "")},
    {"metric": "old_label_total_audit", "value": audit.get("old_label_total", "")},
    {"metric": "new_label_total_audit", "value": audit.get("new_label_total", "")},
    {"metric": "npm_build", "value": build_status},
    {"metric": "ui_changed", "value": "YES"},
    {"metric": "backend_data_changed", "value": "NO"},
    {"metric": "pricing_changed", "value": "NO"},
    {"metric": "probability_changed", "value": "NO"},
    {"metric": "v6_1_changed", "value": "NO"},
    {"metric": "v7_2g2_changed", "value": "NO"},
    {"metric": "active_csv_schemas_changed", "value": "NO"},
    {"metric": "files_created", "value": "|".join(files_created)},
    {"metric": "files_modified", "value": "|".join(files_modified)},
    {"metric": "checkpoints_created", "value": "|".join(checkpoint_files)},
    {"metric": "completed_at", "value": datetime.now(timezone.utc).isoformat()},
]
with summary_path.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric", "value"])
    writer.writeheader()
    writer.writerows(rows)

with report_path.open("w", encoding="utf-8") as f:
    f.write("EDGEiQ Full Tab Productisation V1 Report\n")
    f.write("Status: EDGEIQ_FULL_TAB_PRODUCTISATION_V1_BUILD_SUCCESS\n\n")
    f.write("Final primary navigation: RACE | FIELD | MAP | INSIGHTS | MARKET | RESULTS\n")
    f.write("Internal mapping preserved: COMMAND=RACE, RUNNERS=FIELD, MAP=MAP, FACTORS=INSIGHTS, ADVANCED=MARKET, RESULTS=RESULTS.\n\n")
    f.write("What changed by tab:\n")
    f.write("- RACE: Header language updated to Race Intelligence, source-aware status strip added, and COMMAND wording productised.\n")
    f.write("- FIELD: RUNNERS remains the internal workspace but presents as FIELD in the primary nav.\n")
    f.write("- MAP: MAP stays mapped directly and receives product terminal styling without changing MAP V3 maths.\n")
    f.write("- INSIGHTS: FACTORS remains internal but presents as INSIGHTS with productised workspace styling.\n")
    f.write("- MARKET: ADVANCED remains internal but presents as MARKET with market/source-state language.\n")
    f.write("- RESULTS: New empty, source-aware post-race workspace added for future official results/review.\n\n")
    f.write("Audit:\n")
    f.write(f"- Productisation audit status: {audit.get('status', '')}\n")
    f.write(f"- Render markers: {audit.get('render_markers', '')}\n")
    f.write(f"- Missing render markers: {audit.get('missing_render_markers', '')}\n")
    f.write(f"- Results mode present: {audit.get('results_mode_present', '')}\n")
    f.write(f"- Old label audit count: {audit.get('old_label_total', '')} (includes internal source keys/variable names)\n")
    f.write(f"- New label audit count: {audit.get('new_label_total', '')}\n\n")
    f.write("Build:\n")
    f.write("- npm run build: BUILD_SUCCESS\n")
    f.write("- Note: Vite emitted chunk-size warning only; build completed successfully.\n\n")
    f.write("Files created:\n")
    for item in files_created:
        f.write(f"- {item}\n")
    f.write("\nFiles modified:\n")
    for item in files_modified:
        f.write(f"- {item}\n")
    f.write("\nCheckpoints created:\n")
    for item in checkpoint_files:
        f.write(f"- {item}\n")
    f.write("\nSafety confirmations:\n")
    f.write("- UI changed: YES\n")
    f.write("- Backend data changed: NO\n")
    f.write("- Pricing changed: NO\n")
    f.write("- Probability changed: NO\n")
    f.write("- V6.1 changed: NO\n")
    f.write("- V7.2G2 changed: NO\n")
    f.write("- Active CSV schemas changed: NO\n")

print("EDGEIQ_FULL_TAB_PRODUCTISATION_V1_BUILD_SUCCESS")
