from pathlib import Path
from datetime import datetime, timezone
import csv
import hashlib
import shutil
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "public" / "data" / "edgeiq_repository_safe_migration_plan_v2_active_copy_manifest.csv"
STAGING_ROOT = ROOT.parent / "EDGEiQ_RACING_STAGING_CLEAN_V1"
OUT = ROOT / "public" / "data" / "edgeiq_racing_staging_clean_v1_copy.csv"
SUMMARY = ROOT / "public" / "data" / "edgeiq_racing_staging_clean_v1_summary.csv"
HASH_AUDIT = ROOT / "public" / "data" / "edgeiq_racing_staging_clean_v1_hash_validation.csv"
EXTRAS = ROOT / "public" / "data" / "edgeiq_racing_staging_clean_v1_extra_files.csv"
REPORT = ROOT / "public" / "data" / "edgeiq_racing_staging_clean_v1_report.txt"


def sha256_file(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def staging_target(copy_to: str) -> Path:
    normalized = copy_to.replace("\\", "/")
    parts = [p for p in normalized.split("/") if p]
    if parts and parts[0].upper() == "EDGEIQ_RACING":
        parts = parts[1:]
    return STAGING_ROOT.joinpath(*parts)


def safe_source_path(source_path: str) -> Path:
    src = (ROOT / source_path).resolve()
    root = ROOT.resolve()
    if not str(src).lower().startswith(str(root).lower()):
        raise RuntimeError(f"Unsafe source path outside repo: {source_path}")
    return src


def main():
    if not MANIFEST.exists():
        raise FileNotFoundError(MANIFEST)
    if STAGING_ROOT.exists():
        raise RuntimeError(f"Clean staging root already exists; refusing to overwrite or delete: {STAGING_ROOT}")
    rows = list(csv.DictReader(MANIFEST.open("r", encoding="utf-8-sig", newline="")))
    STAGING_ROOT.mkdir(parents=True, exist_ok=False)
    out_rows = []
    hash_rows = []
    expected_targets = set()
    copied = missing = hash_fail = error_rows = 0
    for idx, row in enumerate(rows, start=1):
        source_rel = row.get("source_path", "").strip()
        expected_hash = row.get("source_sha256", "").strip().lower()
        copy_to = row.get("copy_to", "").strip()
        dst = staging_target(copy_to)
        expected_targets.add(str(dst.resolve()).lower())
        source_hash = ""
        target_hash = ""
        action = ""
        status = ""
        bytes_present = 0
        try:
            src = safe_source_path(source_rel)
            if not src.exists():
                missing += 1
                action = "NOT_COPIED"
                status = "SOURCE_MISSING"
            else:
                source_hash = sha256_file(src).lower()
                if expected_hash and source_hash != expected_hash:
                    hash_fail += 1
                    action = "NOT_COPIED"
                    status = "SOURCE_HASH_CHANGED_FROM_MANIFEST"
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    copied += 1
                    action = "COPIED_NEW"
                    target_hash = sha256_file(dst).lower()
                    bytes_present = dst.stat().st_size
                    if target_hash != source_hash:
                        hash_fail += 1
                        status = "TARGET_HASH_MISMATCH"
                    else:
                        status = "COPIED_AND_HASH_VALIDATED"
        except Exception as exc:
            error_rows += 1
            action = str(exc)
            status = "ERROR"
        valid = source_hash and target_hash and source_hash == target_hash and (not expected_hash or expected_hash == source_hash)
        out_rows.append({
            "row_no": idx,
            "source_path": source_rel,
            "target_path": str(dst),
            "copy_to_manifest": copy_to,
            "keep_reason": row.get("keep_reason", ""),
            "action": action,
            "status": status,
            "source_sha256_manifest": expected_hash,
            "source_sha256_actual": source_hash,
            "target_sha256": target_hash,
            "hash_validated": "YES" if valid else "NO",
            "bytes_present": bytes_present,
            "copy_mode": "COPY_ONLY_DO_NOT_MOVE",
            "production_changed": "NO",
            "files_moved": "NO",
            "files_deleted": "NO",
        })
        hash_rows.append({
            "source_path": source_rel,
            "target_path": str(dst),
            "manifest_sha256": expected_hash,
            "source_sha256_actual": source_hash,
            "target_sha256": target_hash,
            "validation_status": "PASS" if valid else "FAIL",
        })
    actual_files = [p for p in STAGING_ROOT.rglob("*") if p.is_file()]
    extra_rows = []
    for p in actual_files:
        if str(p.resolve()).lower() not in expected_targets:
            extra_rows.append({
                "extra_file": str(p),
                "size_bytes": p.stat().st_size,
                "sha256": sha256_file(p),
                "status": "EXTRA_NOT_IN_CORRECTED_V2_MANIFEST",
            })
    pd.DataFrame(out_rows).to_csv(OUT, index=False)
    pd.DataFrame(hash_rows).to_csv(HASH_AUDIT, index=False)
    pd.DataFrame(extra_rows).to_csv(EXTRAS, index=False)
    total = len(out_rows)
    validated = sum(1 for r in out_rows if r["hash_validated"] == "YES")
    extra_count = len(extra_rows)
    failed = total - validated
    final_status = "EDGEIQ_RACING_STAGING_CLEAN_V1_COMPLETE" if total == 145 and validated == 145 and failed == 0 and extra_count == 0 and error_rows == 0 and missing == 0 else "EDGEIQ_RACING_STAGING_CLEAN_V1_REVIEW_REQUIRED"
    summary_rows = [
        {"metric": "status", "value": final_status},
        {"metric": "staging_root", "value": str(STAGING_ROOT)},
        {"metric": "manifest_rows", "value": total},
        {"metric": "copied_rows", "value": copied},
        {"metric": "source_missing_rows", "value": missing},
        {"metric": "hash_validated_rows", "value": validated},
        {"metric": "hash_failed_rows", "value": failed},
        {"metric": "extra_files_not_in_manifest", "value": extra_count},
        {"metric": "actual_staging_file_count", "value": len(actual_files)},
        {"metric": "error_rows", "value": error_rows},
        {"metric": "production_changed", "value": "NO"},
        {"metric": "pricing_changed", "value": "NO"},
        {"metric": "probability_changed", "value": "NO"},
        {"metric": "v6_1_changed", "value": "NO"},
        {"metric": "v7_2g2_changed", "value": "NO"},
        {"metric": "ui_changed", "value": "NO"},
        {"metric": "files_moved", "value": "NO"},
        {"metric": "files_deleted", "value": "NO"},
        {"metric": "app_pointed_to_staging", "value": "NO"},
        {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
    ]
    pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)
    REPORT.write_text("\n".join([
        "EDGEIQ_RACING_STAGING_CLEAN_V1",
        "=================================",
        f"Status: {final_status}",
        f"Staging root: {STAGING_ROOT}",
        f"Manifest rows: {total}",
        f"Copied rows: {copied}",
        f"Hash validated rows: {validated}",
        f"Hash failed rows: {failed}",
        f"Extra files not in manifest: {extra_count}",
        f"Actual staging file count: {len(actual_files)}",
        f"Source missing rows: {missing}",
        f"Error rows: {error_rows}",
        "",
        "Boundaries:",
        "- New clean staging root created from corrected V2 manifest only.",
        "- Directory structure preserved from manifest targets.",
        "- Original racing-dashboard was not moved, deleted, or pointed at staging.",
        "- Existing EDGEiQ_RACING_STAGING folder was not modified or deleted by this clean-root policy.",
        "- Production/pricing/probability/V6.1/V7.2G2/UI were not changed.",
    ]) + "\n", encoding="utf-8")
    print("STAGING_CLEAN_DONE", final_status, total, validated, extra_count, STAGING_ROOT)


if __name__ == "__main__":
    main()
