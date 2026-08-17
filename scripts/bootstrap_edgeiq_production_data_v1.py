from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path("/var/data") if sys.platform != "win32" else Path("C:/EDGEIQ_RENDER_DATA")
DEFAULT_SEED_DIR = Path("/var/data/seed") if sys.platform != "win32" else Path("C:/EDGEIQ_DEPLOYMENT_SEED_V1")
MANIFEST_NAME = "edgeiq_production_seed_manifest_v1.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_manifest(seed_dir: Path) -> Path:
    candidates = [
        seed_dir / MANIFEST_NAME,
        seed_dir / "outputs" / "deployment-v1" / MANIFEST_NAME,
    ]
    for path in candidates:
        if path.exists():
            return path
    raise RuntimeError(f"Seed manifest not found in {seed_dir}")


def read_manifest(seed_dir: Path) -> dict:
    path = find_manifest(seed_dir)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "EDGEIQ_PRODUCTION_SEED_MANIFEST_V1":
        raise RuntimeError(f"Unexpected seed manifest schema: {path}")
    return payload


def validate_relative(path_text: str) -> Path:
    if "\\" in path_text:
        raise RuntimeError(f"Deployment path must use POSIX separators: {path_text}")
    candidate = Path(path_text)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise RuntimeError(f"Unsafe deployment path in seed manifest: {path_text}")
    return candidate


def seed_state_path(data_root: Path) -> Path:
    return data_root / "state" / "edgeiq_seed_state_v1.json"


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    shutil.move(str(tmp), str(path))


def import_seed(seed_dir: Path, data_root: Path, replace_existing: bool) -> dict:
    manifest = read_manifest(seed_dir)
    rows = manifest.get("rows", [])
    if not rows:
        raise RuntimeError("Seed manifest has no rows.")

    imported = []
    skipped = []
    failures = []
    staging = data_root / ".edgeiq_seed_import_staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    for row in rows:
        rel_path = validate_relative(str(row["deployment_relative_path"]))
        source = seed_dir / rel_path
        if not source.exists():
            failures.append({"file": str(rel_path), "failure": "SOURCE_MISSING"})
            continue
        expected_hash = str(row.get("sha256") or "").lower()
        actual_hash = sha256(source).lower() if expected_hash else ""
        if expected_hash and actual_hash != expected_hash:
            failures.append({"file": str(rel_path), "failure": "SHA256_MISMATCH"})
            continue
        target = data_root / rel_path
        if target.exists() and not replace_existing:
            target_hash = sha256(target).lower() if expected_hash else ""
            if expected_hash and target_hash == expected_hash:
                skipped.append({"file": str(rel_path), "reason": "EXISTING_MATCHES_MANIFEST"})
                continue
            failures.append({"file": str(rel_path), "failure": "TARGET_EXISTS_DIFFERENT"})
            continue
        staged = staging / rel_path
        staged.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, staged)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staged), str(target))
        imported.append({"file": str(rel_path), "bytes": source.stat().st_size})

    shutil.rmtree(staging, ignore_errors=True)
    if failures:
        raise RuntimeError(json.dumps({"seed_import_failures": failures[:20], "failure_count": len(failures)}))

    state = {
        "schema_version": "EDGEIQ_SEED_STATE_V1",
        "generated_at": utc_now(),
        "seed_dir": str(seed_dir),
        "data_root": str(data_root),
        "seed_manifest_generated_at": manifest.get("generated_at"),
        "seed_file_count": len(rows),
        "seed_size_bytes": manifest.get("seed_size_bytes"),
        "imported_files": len(imported),
        "skipped_existing_files": len(skipped),
        "status": "PASS",
    }
    write_json_atomic(seed_state_path(data_root), state)
    return state


def validate_seed_only(seed_dir: Path) -> dict:
    manifest = read_manifest(seed_dir)
    rows = manifest.get("rows", [])
    failures = []
    for row in rows:
        rel_path = validate_relative(str(row["deployment_relative_path"]))
        source = seed_dir / rel_path
        if not source.exists():
            failures.append({"file": str(rel_path), "failure": "SOURCE_MISSING"})
            continue
        expected_hash = str(row.get("sha256") or "").lower()
        if expected_hash and sha256(source).lower() != expected_hash:
            failures.append({"file": str(rel_path), "failure": "SHA256_MISMATCH"})
    return {
        "schema_version": "EDGEIQ_SEED_VALIDATE_ONLY_V1",
        "generated_at": utc_now(),
        "seed_dir": str(seed_dir),
        "seed_file_count": len(rows),
        "seed_size_bytes": manifest.get("seed_size_bytes"),
        "failure_count": len(failures),
        "failures": failures[:20],
        "status": "PASS" if not failures and bool(rows) else "FAIL",
    }


def audit_seed(data_root: Path) -> dict:
    state_path = seed_state_path(data_root)
    state = {}
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
    public_data = data_root / "public" / "data"
    docs_pi = data_root / "docs" / "performance-intelligence"
    market_data = data_root / "data" / "market" / "ladbrokes"
    checks = {
        "seed_state": state_path.exists(),
        "public_data": public_data.exists(),
        "performance_intelligence_source_warehouse": docs_pi.exists(),
        "market_data": market_data.exists(),
    }
    return {
        "schema_version": "EDGEIQ_SEED_AUDIT_V1",
        "generated_at": utc_now(),
        "data_root": str(data_root),
        "checks": checks,
        "state": state,
        "status": "PASS" if all(checks.values()) and state.get("status") == "PASS" else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-dir", type=Path, default=DEFAULT_SEED_DIR)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--replace-existing", action="store_true")
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--validate-seed-only", action="store_true")
    args = parser.parse_args()

    seed_dir = args.seed_dir.resolve()
    data_root = args.data_root.resolve()
    data_root.mkdir(parents=True, exist_ok=True)
    if args.validate_seed_only:
        report = validate_seed_only(seed_dir)
    elif args.audit_only:
        report = audit_seed(data_root)
    else:
        report = import_seed(seed_dir, data_root, args.replace_existing)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"EDGEIQ_PRODUCTION_DATA_BOOTSTRAP=FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
