from pathlib import Path
from datetime import datetime, timezone
import csv
import hashlib
import shutil
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "public" / "data" / "edgeiq_repository_safe_migration_plan_v2_active_copy_manifest.csv"
STAGING_ROOT = ROOT.parent / "EDGEiQ_RACING_STAGING"
OUT = ROOT / "public" / "data" / "edgeiq_racing_staging_copy_v1.csv"
SUMMARY = ROOT / "public" / "data" / "edgeiq_racing_staging_copy_v1_summary.csv"
HASH_AUDIT = ROOT / "public" / "data" / "edgeiq_racing_staging_copy_v1_hash_validation.csv"
EXTRAS = ROOT / "public" / "data" / "edgeiq_racing_staging_copy_v1_extra_files.csv"
REPORT = ROOT / "public" / "data" / "edgeiq_racing_staging_copy_v1_report.txt"


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
    rows = list(csv.DictReader(MANIFEST.open("r", encoding="utf-8-sig", newline="")))
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    out_rows = []
    hash_rows = []
    expected_targets = set()
    copied = skipped_same = overwritten = missing = hash_fail = error_rows = 0
    for idx, row in enumerate(rows, start=1):
        source_rel = row.get("source_path", "").strip()
        expected_hash = row.get("source_sha256", "").strip().lower()
        copy_to = row.get("copy_to", "").strip()
        status = ""
        action = ""
        source_hash = ""
        target_hash = ""
        bytes_copied = 0
        dst = staging_target(copy_to)
        expected_targets.add(str(dst.resolve()).lower())
        try:
            src = safe_source_path(source_rel)
            if not src.exists():
                missing += 1
                status = "SOURCE_MISSING"
                action = "NOT_COPIED"
            else:
                source_hash = sha256_file(src).lower()
                if expected_hash and source_hash != expected_hash:
                    status = "SOURCE_HASH_CHANGED_FROM_MANIFEST"
                    action = "NOT_COPIED"
                    hash_fail += 1
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    existed = dst.exists()
                    existing_hash = sha256_file(dst).lower() if existed else ""
                    if existed and existing_hash == source_hash:
                        skipped_same += 1
                        status = "HASH_MATCH_ALREADY_PRESENT"
                        action = "SKIPPED"
                    else:
                        shutil.copy2(src, dst)
                        copied += 1
                        if existed:
                            overwritten += 1
                            action = "COPIED_OVER_EXISTING_STAGING_FILE"
                        else:
                            action = "COPIED_NEW"
                        status = "COPIED"
                    target_hash = sha256_file(dst).lower()
                    bytes_copied = dst.stat().st_size if dst.exists() else 0
                    if target_hash != source_hash:
                        status = "TARGET_HASH_MISMATCH"
                        hash_fail += 1
        except Exception as exc:
            error_rows += 1
            status = "ERROR"
            action = str(exc)
        record = {
            "row_no": idx,
            "source_path": source_rel,
            "target_path": str(dst),
            "copy_to_manifest": copy_to,
            "keep_reason": row.get("keep_reason", ""),
            "copy_mode": "COPY_ONLY_DO_NOT_MOVE",
            "action": action,
            "status": status,
            "source_sha256_manifest": expected_hash,
            "source_sha256_actual": source_hash,
            "target_sha256": target_hash,
            "hash_validated": "YES" if source_hash and target_hash and source_hash == target_hash and (not expected_hash or expected_hash == source_hash) else "NO",
            "bytes_copied_or_present": bytes_copied,
            "production_changed": "NO",
            "files_moved": "NO",
            "files_deleted": "NO",
        }
        out_rows.append(record)
        hash_rows.append({
            "source_path": source_rel,
            "target_path": str(dst),
            "source_sha256_actual": source_hash,
            "target_sha256": target_hash,
            "manifest_sha256": expected_hash,
            "validation_status": "PASS" if record["hash_validated"] == "YES" else "FAIL",
        })
    actual_files = [p for p in STAGING_ROOT.rglob("*") if p.is_file()]
    extra_rows = []
    for p in actual_files:
        resolved = str(p.resolve()).lower()
        if resolved not in expected_targets:
            extra_rows.append({
                "extra_file": str(p),
                "size_bytes": p.stat().st_size,
                "sha256": sha256_file(p),
                "status": "EXTRA_NOT_IN_V2_MANIFEST_NOT_DELETED",
            })
    pd.DataFrame(out_rows).to_csv(OUT, index=False)
    pd.DataFrame(hash_rows).to_csv(HASH_AUDIT, index=False)
    pd.DataFrame(extra_rows).to_csv(EXTRAS, index=False)
    total = len(out_rows)
    validated = sum(1 for r in out_rows if r["hash_validated"] == "YES")
    failed = total - validated
    extra_count = len(extra_rows)
    final_status = "EDGEIQ_RACING_STAGING_COPY_COMPLETE" if failed == 0 and extra_count == 0 else "EDGEIQ_RACING_STAGING_COPY_REVIEW_REQUIRED"
    summary_rows = [
        {"metric": "status", "value": final_status},
        {"metric": "staging_root", "value": str(STAGING_ROOT)},
        {"metric": "manifest_rows", "value": total},
        {"metric": "copied_rows", "value": copied},
        {"metric": "skipped_same_hash_rows", "value": skipped_same},
        {"metric": "overwritten_staging_files", "value": overwritten},
        {"metric": "source_missing_rows", "value": missing},
        {"metric": "hash_validated_rows", "value": validated},
        {"metric": "hash_failed_rows", "value": failed},
        {"metric": "extra_files_not_in_v2_manifest", "value": extra_count},
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
        "EDGEIQ_RACING_STAGING_COPY_V1",
        "===============================",
        f"Status: {final_status}",
        f"Staging root: {STAGING_ROOT}",
        f"Manifest rows: {total}",
        f"Copied rows: {copied}",
        f"Skipped same-hash rows: {skipped_same}",
        f"Overwritten staging files: {overwritten}",
        f"Source missing rows: {missing}",
        f"Hash validated rows: {validated}",
        f"Hash failed rows: {failed}",
        f"Extra files not in V2 manifest: {extra_count}",
        f"Error rows: {error_rows}",
        "",
        "Boundaries:",
        "- Copy-only mirror created/updated from V2 active manifest.",
        "- Current app path was not changed.",
        "- No source files were moved or deleted.",
        "- Extra staging files, if present, were reported and not deleted per instruction.",
        "- Production/pricing/probability/V6.1/V7.2G2/UI were not changed.",
    ]) + "\n", encoding="utf-8")
    print("STAGING_COPY_DONE", final_status, total, validated, failed, extra_count, STAGING_ROOT)


if __name__ == "__main__":
    main()
