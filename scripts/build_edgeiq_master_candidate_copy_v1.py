from pathlib import Path
import csv
import hashlib
import shutil
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DASHBOARD_ROOT = ROOT.parent
SOURCE_ROOT = DASHBOARD_ROOT / "EDGEiQ_RACING_STAGING_CLEAN_V1"
TARGET_ROOT = DASHBOARD_ROOT / "EDGEiQ_RACING_MASTER_CANDIDATE"
MANIFEST = DATA / "edgeiq_master_candidate_promotion_plan_v1_manifest.csv"

COPY_CSV = DATA / "edgeiq_master_candidate_copy_v1.csv"
SUMMARY_CSV = DATA / "edgeiq_master_candidate_copy_v1_summary.csv"
HASH_CSV = DATA / "edgeiq_master_candidate_copy_v1_hash_validation.csv"
EXTRA_CSV = DATA / "edgeiq_master_candidate_copy_v1_extra_files.csv"
REPORT_TXT = DATA / "edgeiq_master_candidate_copy_v1_report.txt"

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


def read_manifest():
    if not MANIFEST.exists():
        raise FileNotFoundError(f"Missing manifest: {MANIFEST}")
    with MANIFEST.open("r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return rows


def write_csv(path: Path, rows, fieldnames=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    if fieldnames is None:
        keys = []
        for row in rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def is_artifact(path: Path) -> bool:
    parts = set(path.parts)
    return bool(parts & ARTIFACT_DIRS) or path.name in ARTIFACT_FILES


def rel_to(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    rows = read_manifest()
    copy_rows = []
    hash_rows = []
    extra_rows = []

    status = "MASTER_CANDIDATE_COPY_NOT_STARTED"
    blocker = ""

    if not SOURCE_ROOT.exists():
        status = "BLOCKED_SOURCE_STAGING_MISSING"
        blocker = str(SOURCE_ROOT)
    elif TARGET_ROOT.exists():
        existing_files = [p for p in TARGET_ROOT.rglob("*") if p.is_file()]
        if existing_files:
            status = "BLOCKED_TARGET_EXISTS"
            blocker = f"Target exists with {len(existing_files)} files. Refusing blind overwrite."
        else:
            status = "TARGET_EXISTS_EMPTY_SAFE_TO_COPY"
    else:
        status = "READY_TO_COPY"

    expected_target_rel = set()
    expected_count = len(rows)

    for row in rows:
        source_path = Path(row.get("staging_source_path", ""))
        target_path = Path(row.get("master_candidate_target_path", ""))
        expected_hash = (row.get("expected_sha256") or "").strip().lower()
        source_rel = row.get("source_manifest_path", "")
        keep_reason = row.get("keep_reason", "")
        target_rel = rel_to(target_path, TARGET_ROOT) if str(target_path).startswith(str(TARGET_ROOT)) else str(target_path)
        expected_target_rel.add(target_rel)
        source_exists = source_path.exists()
        copied = "NO"
        actual_hash = ""
        row_status = "PENDING"

        if status in {"READY_TO_COPY", "TARGET_EXISTS_EMPTY_SAFE_TO_COPY"}:
            if not source_exists:
                row_status = "SOURCE_MISSING"
            elif is_artifact(source_path):
                row_status = "SKIPPED_VALIDATION_ARTIFACT"
            else:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target_path)
                copied = "YES"
                actual_hash = sha256(target_path)
                row_status = "COPIED_HASH_PASS" if actual_hash == expected_hash else "COPIED_HASH_FAIL"
        else:
            row_status = status

        copy_rows.append({
            "step_no": row.get("step_no", ""),
            "source_manifest_path": source_rel,
            "keep_reason": keep_reason,
            "staging_source_path": str(source_path),
            "master_candidate_target_path": str(target_path),
            "source_exists": "YES" if source_exists else "NO",
            "copied": copied,
            "expected_sha256": expected_hash,
            "actual_sha256": actual_hash,
            "status": row_status,
        })

    if status in {"READY_TO_COPY", "TARGET_EXISTS_EMPTY_SAFE_TO_COPY"}:
        for row in rows:
            target_path = Path(row.get("master_candidate_target_path", ""))
            expected_hash = (row.get("expected_sha256") or "").strip().lower()
            actual_hash = sha256(target_path) if target_path.exists() else ""
            hash_rows.append({
                "source_manifest_path": row.get("source_manifest_path", ""),
                "keep_reason": row.get("keep_reason", ""),
                "target_path": str(target_path),
                "exists": "YES" if target_path.exists() else "NO",
                "expected_sha256": expected_hash,
                "actual_sha256": actual_hash,
                "hash_status": "PASS" if target_path.exists() and actual_hash == expected_hash else "FAIL",
            })
        if TARGET_ROOT.exists():
            for path in TARGET_ROOT.rglob("*"):
                if path.is_file() and not is_artifact(path):
                    rel = rel_to(path, TARGET_ROOT)
                    if rel not in expected_target_rel:
                        extra_rows.append({
                            "extra_file": rel,
                            "full_path": str(path),
                            "size_bytes": path.stat().st_size,
                            "status": "EXTRA_ACTIVE_FILE",
                        })
    else:
        hash_rows = [{
            "source_manifest_path": row.get("source_manifest_path", ""),
            "keep_reason": row.get("keep_reason", ""),
            "target_path": row.get("master_candidate_target_path", ""),
            "exists": "NO",
            "expected_sha256": row.get("expected_sha256", ""),
            "actual_sha256": "",
            "hash_status": status,
        } for row in rows]

    copied_count = sum(1 for r in copy_rows if r["copied"] == "YES")
    hash_pass = sum(1 for r in hash_rows if r.get("hash_status") == "PASS")
    hash_fail = sum(1 for r in hash_rows if r.get("hash_status") == "FAIL")
    source_missing = sum(1 for r in copy_rows if r["source_exists"] == "NO")
    extra_count = len(extra_rows)

    if status in {"READY_TO_COPY", "TARGET_EXISTS_EMPTY_SAFE_TO_COPY"}:
        final_status = "MASTER_CANDIDATE_COPY_SUCCESS" if copied_count == expected_count and hash_pass == expected_count and extra_count == 0 else "MASTER_CANDIDATE_COPY_REVIEW_REQUIRED"
    else:
        final_status = status

    summary = [
        {"metric": "status", "value": final_status},
        {"metric": "source_root", "value": str(SOURCE_ROOT)},
        {"metric": "target_root", "value": str(TARGET_ROOT)},
        {"metric": "manifest_rows", "value": expected_count},
        {"metric": "copied_files", "value": copied_count},
        {"metric": "source_missing", "value": source_missing},
        {"metric": "hash_pass", "value": hash_pass},
        {"metric": "hash_fail", "value": hash_fail},
        {"metric": "extra_active_files", "value": extra_count},
        {"metric": "excluded_validation_artifacts", "value": "node_modules;dist;tsconfig.tsbuildinfo;__pycache__;.vite"},
        {"metric": "production_changed", "value": "NO"},
        {"metric": "original_racing_dashboard_changed", "value": "NO_EXCEPT_NEW_SCRIPTS_REPORTS"},
        {"metric": "staging_changed", "value": "NO"},
        {"metric": "files_moved", "value": "NO"},
        {"metric": "files_deleted", "value": "NO"},
        {"metric": "app_pointed_to_master", "value": "NO"},
        {"metric": "pricing_changed", "value": "NO"},
        {"metric": "probability_changed", "value": "NO"},
        {"metric": "v6_1_changed", "value": "NO"},
        {"metric": "v7_2g2_changed", "value": "NO"},
        {"metric": "ui_changed", "value": "NO"},
        {"metric": "blocker", "value": blocker},
        {"metric": "built_at", "value": now_iso()},
    ]

    write_csv(COPY_CSV, copy_rows)
    write_csv(HASH_CSV, hash_rows)
    write_csv(EXTRA_CSV, extra_rows, fieldnames=["extra_file", "full_path", "size_bytes", "status"])
    write_csv(SUMMARY_CSV, summary, fieldnames=["metric", "value"])

    report = [
        "EDGEiQ Master Candidate Copy V1",
        "=================================",
        f"Status: {final_status}",
        f"Source: {SOURCE_ROOT}",
        f"Target: {TARGET_ROOT}",
        f"Manifest rows: {expected_count}",
        f"Copied files: {copied_count}",
        f"Hash pass: {hash_pass}",
        f"Hash fail: {hash_fail}",
        f"Extra active files: {extra_count}",
        "Copy type: COPY_ONLY",
        "Validation artifacts excluded: node_modules, dist, tsconfig.tsbuildinfo, __pycache__, .vite",
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
    ]
    if blocker:
        report.append(f"Blocker: {blocker}")
    REPORT_TXT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(final_status)


if __name__ == "__main__":
    main()
