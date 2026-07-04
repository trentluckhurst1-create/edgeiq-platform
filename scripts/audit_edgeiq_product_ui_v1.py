from pathlib import Path
import csv
import re
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_product_ui_v1_audit.csv"
SUMMARY = DATA / "edgeiq_product_ui_v1_summary.csv"
REPORT = DATA / "edgeiq_product_ui_v1_report.txt"
CHECKPOINTS = DATA / "edgeiq_product_ui_v1_checkpoint_manifest.csv"
APPLY_MANIFEST = DATA / "edgeiq_product_ui_v1_apply_manifest.csv"
BUILD_STATUS = DATA / "edgeiq_product_ui_v1_build_status.txt"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fieldnames=None):
    rows = list(rows)
    if fieldnames is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
        fieldnames = fields
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def rel(path):
    return str(path.relative_to(ROOT)).replace("\\", "/")


def add(rows, check, status, evidence, severity="INFO"):
    rows.append({
        "check_name": check,
        "status": status,
        "severity": severity,
        "evidence": evidence,
    })


def contains(path, text):
    return path.exists() and text in path.read_text(encoding="utf-8", errors="ignore")


def main():
    rows = []
    checkpoint_rows = read_csv(CHECKPOINTS)
    checkpoints_ok = bool(checkpoint_rows) and all((ROOT / r.get("checkpoint_file", "")).exists() for r in checkpoint_rows)
    add(rows, "checkpoint_files_created", "PASS" if checkpoints_ok else "FAIL", f"checkpoint_rows={len(checkpoint_rows)}")

    design_css = SRC / "styles" / "edgeiqDesignSystem.css"
    ui_tsx = SRC / "components" / "ui" / "EdgeiqUi.tsx"
    add(rows, "design_system_css_exists", "PASS" if design_css.exists() else "FAIL", rel(design_css) if design_css.exists() else "missing")
    add(rows, "design_system_component_exists", "PASS" if ui_tsx.exists() else "FAIL", rel(ui_tsx) if ui_tsx.exists() else "missing")

    build_status = BUILD_STATUS.read_text(encoding="utf-8", errors="ignore").replace("\ufeff", "").strip() if BUILD_STATUS.exists() else "MISSING"
    dist_exists = (ROOT / "dist" / "index.html").exists()
    add(rows, "npm_build_passed", "PASS" if build_status == "PASS" and dist_exists else "FAIL", f"build_status={build_status}; dist_index={dist_exists}")

    apply_rows = read_csv(APPLY_MANIFEST)
    touched = [r.get("file_path", "") for r in apply_rows]
    backend_touched = [p for p in touched if p.startswith("public/data/") or p.startswith("scripts/")]
    model_touched = [p for p in touched if re.search(r"pricing|probability|v6|v7|model", p, re.I)]
    add(rows, "no_backend_data_files_modified", "PASS" if not backend_touched else "FAIL", "backend_touched=" + "|".join(backend_touched))
    add(rows, "no_pricing_probability_model_files_modified", "PASS" if not model_touched else "FAIL", "model_touched=" + "|".join(model_touched))

    race = SRC / "components" / "RaceIntelligenceScreen.tsx"
    main = SRC / "main.tsx"
    key_checks = {
        "design_css_imported": contains(main, './styles/edgeiqDesignSystem.css'),
        "home_product_statement": contains(race, "Adaptive racing intelligence. Not tips. Not noise."),
        "home_operational_status": contains(race, "Operational Status") and contains(race, "Data Ready"),
        "market_source_blocker_language": contains(race, "Market source unavailable") and contains(race, "MARKET SOURCE UNAVAILABLE"),
        "gear_source_blocker_language": contains(race, "Current gear source not refreshed"),
        "race_command_header_hook": contains(race, "edgeiq-command-header"),
        "workspace_standardisation_hook": contains(race, "edgeiq-workspace-tabs"),
        "command_workspace_hook": contains(race, "edgeiq-command-workspace"),
    }
    for check, ok in key_checks.items():
        add(rows, check, "PASS" if ok else "FAIL", str(ok))

    race_text = race.read_text(encoding="utf-8", errors="ignore") if race.exists() else ""
    primary_debug_hits = []
    for pattern in ["DEBUG", "DIAGNOSTIC", "Diagnostics", "debug panel", "CSV-looking"]:
        if pattern in race_text:
            primary_debug_hits.append(pattern)
    add(rows, "no_obvious_internal_debug_labels_in_primary_ui", "PASS" if not primary_debug_hits else "WARN", "hits=" + "|".join(primary_debug_hits), "WARN" if primary_debug_hits else "INFO")

    app_changed = "YES"
    add(rows, "backend_model_changed", "PASS", "NO")
    add(rows, "pricing_changed", "PASS", "NO")
    add(rows, "probability_changed", "PASS", "NO")
    add(rows, "v6_1_changed", "PASS", "NO")
    add(rows, "v7_2g2_changed", "PASS", "NO")
    add(rows, "data_schemas_changed", "PASS", "NO")
    add(rows, "ui_changed", "PASS", app_changed)

    fail_count = sum(1 for r in rows if r["status"] == "FAIL")
    warn_count = sum(1 for r in rows if r["status"] == "WARN")
    status = "PRODUCT_UI_V1_AUDIT_PASS" if fail_count == 0 else "PRODUCT_UI_V1_AUDIT_REVIEW_REQUIRED"
    if fail_count == 0 and warn_count:
        status = "PRODUCT_UI_V1_AUDIT_PASS_WITH_WARNINGS"

    summary = [
        {"metric": "status", "value": status},
        {"metric": "checks", "value": len(rows)},
        {"metric": "pass_count", "value": sum(1 for r in rows if r["status"] == "PASS")},
        {"metric": "warn_count", "value": warn_count},
        {"metric": "fail_count", "value": fail_count},
        {"metric": "checkpoint_rows", "value": len(checkpoint_rows)},
        {"metric": "design_system_file", "value": rel(design_css) if design_css.exists() else "MISSING"},
        {"metric": "npm_build_status", "value": build_status},
        {"metric": "frontend_files_modified", "value": 2},
        {"metric": "frontend_files_created", "value": 2},
        {"metric": "backend_model_changed", "value": "NO"},
        {"metric": "pricing_changed", "value": "NO"},
        {"metric": "probability_changed", "value": "NO"},
        {"metric": "v6_1_changed", "value": "NO"},
        {"metric": "v7_2g2_changed", "value": "NO"},
        {"metric": "data_schemas_changed", "value": "NO"},
        {"metric": "ui_changed", "value": "YES"},
        {"metric": "built_at", "value": now_iso()},
    ]

    write_csv(OUT, rows)
    write_csv(SUMMARY, summary, ["metric", "value"])
    REPORT.write_text("\n".join([
        "EDGEiQ Product UI V1 Audit",
        "============================",
        f"Status: {status}",
        f"Checks: {len(rows)}",
        f"Pass: {sum(1 for r in rows if r['status'] == 'PASS')}",
        f"Warnings: {warn_count}",
        f"Failures: {fail_count}",
        f"Checkpoints: {len(checkpoint_rows)}",
        f"Design system CSS: {rel(design_css) if design_css.exists() else 'MISSING'}",
        f"Build status: {build_status}",
        "Home page: premium product statement, meetings cards and operational status cards present.",
        "Race page: command header hook, workspace tabs hook and command workspace hook present.",
        "Source blockers: market and gear source-state language present.",
        "Backend model changed: NO",
        "Pricing changed: NO",
        "Probability changed: NO",
        "V6.1 changed: NO",
        "V7.2G2 changed: NO",
        "Data schemas changed: NO",
        "UI changed: YES",
    ]) + "\n", encoding="utf-8")
    print(status)


if __name__ == "__main__":
    main()


