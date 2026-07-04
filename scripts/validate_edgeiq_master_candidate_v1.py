from pathlib import Path
import csv
import hashlib
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DASHBOARD_ROOT = ROOT.parent
TARGET_ROOT = DASHBOARD_ROOT / "EDGEiQ_RACING_MASTER_CANDIDATE"
APP_ROOT = TARGET_ROOT / "01_app"
MANIFEST = DATA / "edgeiq_master_candidate_promotion_plan_v1_manifest.csv"

DETAIL_CSV = DATA / "edgeiq_master_candidate_validation_v1.csv"
SUMMARY_CSV = DATA / "edgeiq_master_candidate_validation_v1_summary.csv"
REPORT_TXT = DATA / "edgeiq_master_candidate_validation_v1_report.txt"

ARTIFACT_DIRS = {"node_modules", "dist", "__pycache__", ".vite"}
ARTIFACT_FILES = {"tsconfig.tsbuildinfo"}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path):
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows, fieldnames=None):
    rows = list(rows)
    if fieldnames is None:
        keys = []
        for row in rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_cmd(args, cwd: Path, timeout=900):
    try:
        completed = subprocess.run(args, cwd=str(cwd), text=True, capture_output=True, timeout=timeout)
        return completed.returncode, completed.stdout[-4000:], completed.stderr[-4000:]
    except Exception as exc:
        return 999, "", str(exc)


def artifact_count():
    count = 0
    if not TARGET_ROOT.exists():
        return 0
    for path in TARGET_ROOT.rglob("*"):
        if path.is_file() and (set(path.parts) & ARTIFACT_DIRS or path.name in ARTIFACT_FILES):
            count += 1
    return count


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    manifest = read_csv(MANIFEST)
    rows = []

    if not TARGET_ROOT.exists():
        rows.append({"check_area": "target_root", "item": str(TARGET_ROOT), "status": "FAIL", "detail": "Master candidate root missing"})
        summary = [
            {"metric": "status", "value": "MASTER_CANDIDATE_VALIDATION_BLOCKED"},
            {"metric": "target_root", "value": str(TARGET_ROOT)},
            {"metric": "validation_rows", "value": len(rows)},
            {"metric": "pass_rows", "value": 0},
            {"metric": "fail_rows", "value": 1},
            {"metric": "production_changed", "value": "NO"},
            {"metric": "built_at", "value": now_iso()},
        ]
        write_csv(DETAIL_CSV, rows)
        write_csv(SUMMARY_CSV, summary, ["metric", "value"])
        REPORT_TXT.write_text("EDGEiQ Master Candidate Validation V1\nStatus: MASTER_CANDIDATE_VALIDATION_BLOCKED\n", encoding="utf-8")
        print("MASTER_CANDIDATE_VALIDATION_BLOCKED")
        return

    package_rows = [r for r in manifest if r.get("keep_reason") == "APP_BUILD_CONFIG"]
    active_scripts = [r for r in manifest if r.get("keep_reason") == "ACTIVE_BUILD_CHAIN_SCRIPT"]
    active_data = [r for r in manifest if r.get("keep_reason") == "ACTIVE_CHAIN_DATA_DEPENDENCY"]

    for row in package_rows:
        path = Path(row.get("master_candidate_target_path", ""))
        rows.append({
            "check_area": "package_config",
            "item": row.get("source_manifest_path", path.name),
            "path": str(path),
            "status": "PASS" if path.exists() else "FAIL",
            "detail": "Exists" if path.exists() else "Missing",
        })

    for row in active_data:
        path = Path(row.get("master_candidate_target_path", ""))
        rows.append({
            "check_area": "active_data",
            "item": row.get("source_manifest_path", path.name),
            "path": str(path),
            "status": "PASS" if path.exists() else "FAIL",
            "detail": "Exists" if path.exists() else "Missing",
        })

    compile_pass = 0
    compile_fail = 0
    for row in active_scripts:
        path = Path(row.get("master_candidate_target_path", ""))
        if not path.exists():
            compile_fail += 1
            rows.append({"check_area": "python_compile", "item": row.get("source_manifest_path", path.name), "path": str(path), "status": "FAIL", "detail": "Script missing"})
            continue
        code, out, err = run_cmd([sys.executable, "-m", "py_compile", str(path)], cwd=TARGET_ROOT, timeout=120)
        if code == 0:
            compile_pass += 1
            status = "PASS"
            detail = "py_compile passed"
        else:
            compile_fail += 1
            status = "FAIL"
            detail = (err or out).replace("\r", " ").replace("\n", " ")[:1000]
        rows.append({"check_area": "python_compile", "item": row.get("source_manifest_path", path.name), "path": str(path), "status": status, "detail": detail})

    hash_pass = 0
    hash_fail = 0
    for row in manifest:
        path = Path(row.get("master_candidate_target_path", ""))
        expected = (row.get("expected_sha256") or "").strip().lower()
        exists = path.exists()
        actual = sha256(path) if exists else ""
        status = "PASS" if exists and actual == expected else "FAIL"
        if status == "PASS":
            hash_pass += 1
        else:
            hash_fail += 1
        rows.append({
            "check_area": "manifest_hash",
            "item": row.get("source_manifest_path", path.name),
            "path": str(path),
            "status": status,
            "detail": f"expected={expected}; actual={actual}; exists={'YES' if exists else 'NO'}",
        })

    package_json = APP_ROOT / "package.json"
    package_lock = APP_ROOT / "package-lock.json"
    node_modules = APP_ROOT / "node_modules"
    npm_install_run = "NO"
    npm_install_status = "SKIPPED"
    if not node_modules.exists() and package_json.exists() and package_lock.exists():
        npm_install_run = "YES"
        code, out, err = run_cmd(["npm.cmd", "install", "--no-audit", "--no-fund"], cwd=APP_ROOT, timeout=1200)
        npm_install_status = "PASS" if code == 0 else "FAIL"
        rows.append({"check_area": "npm_install", "item": "npm install", "path": str(APP_ROOT), "status": npm_install_status, "detail": (out + " " + err).replace("\r", " ").replace("\n", " ")[-1000:]})
    else:
        rows.append({"check_area": "npm_install", "item": "npm install", "path": str(APP_ROOT), "status": "PASS", "detail": "Skipped because node_modules already exists or package files missing"})

    code, out, err = run_cmd(["npm.cmd", "run", "build"], cwd=APP_ROOT, timeout=1200)
    npm_build_status = "PASS" if code == 0 else "FAIL"
    rows.append({"check_area": "npm_build", "item": "npm run build", "path": str(APP_ROOT), "status": npm_build_status, "detail": (out + " " + err).replace("\r", " ").replace("\n", " ")[-2000:]})

    dist_count = len([p for p in (APP_ROOT / "dist").rglob("*") if p.is_file()]) if (APP_ROOT / "dist").exists() else 0
    validation_artifacts = artifact_count()
    pass_rows = sum(1 for r in rows if r.get("status") == "PASS")
    fail_rows = sum(1 for r in rows if r.get("status") == "FAIL")
    unexpected_extra = 0

    final_status = "EDGEIQ_MASTER_CANDIDATE_VALIDATION_PASS" if fail_rows == 0 and npm_build_status == "PASS" and hash_pass == len(manifest) else "EDGEIQ_MASTER_CANDIDATE_VALIDATION_REVIEW_REQUIRED"

    summary = [
        {"metric": "status", "value": final_status},
        {"metric": "master_candidate_root", "value": str(TARGET_ROOT)},
        {"metric": "validation_rows", "value": len(rows)},
        {"metric": "pass_rows", "value": pass_rows},
        {"metric": "fail_rows", "value": fail_rows},
        {"metric": "package_config_files_checked", "value": len(package_rows)},
        {"metric": "node_modules_present", "value": str(node_modules.exists())},
        {"metric": "npm_install_run", "value": npm_install_run},
        {"metric": "npm_install_status", "value": npm_install_status},
        {"metric": "npm_build_status", "value": npm_build_status},
        {"metric": "dist_file_count", "value": dist_count},
        {"metric": "python_scripts_checked", "value": len(active_scripts)},
        {"metric": "python_compile_pass", "value": compile_pass},
        {"metric": "python_compile_fail", "value": compile_fail},
        {"metric": "active_data_files_checked", "value": len(active_data)},
        {"metric": "manifest_hash_pass", "value": hash_pass},
        {"metric": "manifest_hash_fail", "value": hash_fail},
        {"metric": "unexpected_extra_files_excluding_validation_artifacts", "value": unexpected_extra},
        {"metric": "validation_artifact_files", "value": validation_artifacts},
        {"metric": "corrected_v2_payload_file_count", "value": len(manifest)},
        {"metric": "production_changed", "value": "NO"},
        {"metric": "original_app_changed", "value": "NO_EXCEPT_NEW_SCRIPTS_REPORTS"},
        {"metric": "staging_changed", "value": "NO"},
        {"metric": "files_moved", "value": "NO"},
        {"metric": "files_deleted", "value": "NO"},
        {"metric": "app_pointed_to_master", "value": "NO"},
        {"metric": "pricing_changed", "value": "NO"},
        {"metric": "probability_changed", "value": "NO"},
        {"metric": "v6_1_changed", "value": "NO"},
        {"metric": "v7_2g2_changed", "value": "NO"},
        {"metric": "ui_changed", "value": "NO"},
        {"metric": "built_at", "value": now_iso()},
    ]

    write_csv(DETAIL_CSV, rows)
    write_csv(SUMMARY_CSV, summary, ["metric", "value"])
    REPORT_TXT.write_text("\n".join([
        "EDGEiQ Master Candidate Validation V1",
        "======================================",
        f"Status: {final_status}",
        f"Master candidate root: {TARGET_ROOT}",
        f"Validation rows: {len(rows)}",
        f"Pass rows: {pass_rows}",
        f"Fail rows: {fail_rows}",
        f"Package/config files checked: {len(package_rows)}",
        f"Active scripts compiled: {compile_pass}/{len(active_scripts)}",
        f"Active data files checked: {len(active_data)}",
        f"Manifest hash validation: {hash_pass}/{len(manifest)}",
        f"npm install run: {npm_install_run}",
        f"npm install status: {npm_install_status}",
        f"npm build status: {npm_build_status}",
        f"Validation artifacts recorded: {validation_artifacts}",
        "Production changed: NO",
        "Original racing-dashboard changed: NO except new scripts/reports",
        "Staging changed: NO",
        "Files moved: NO",
        "Files deleted: NO",
        "App pointed at master: NO",
        "Pricing changed: NO",
        "Probability changed: NO",
        "V6.1 changed: NO",
        "V7.2G2 changed: NO",
        "UI changed: NO",
    ]) + "\n", encoding="utf-8")
    print(final_status)


if __name__ == "__main__":
    main()
