from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "outputs" / "deployment-v1" / "edgeiq_production_seed_manifest_v1.json"
DEFAULT_SEED_DIR = Path(os.environ.get("EDGEIQ_LOCAL_SEED_EXPORT_DIR", "EDGEIQ_DEPLOYMENT_SEED_V1"))


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_manifest(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "EDGEIQ_PRODUCTION_SEED_MANIFEST_V1":
        raise RuntimeError(f"Unexpected seed manifest schema: {path}")
    return payload


def safe_clean_target(target: Path, replace: bool) -> None:
    target = target.resolve()
    if target.exists() and any(target.iterdir()):
        if not replace:
            raise RuntimeError(f"Seed directory is not empty; rerun with --replace: {target}")
        if target == Path(target.anchor).resolve() or target == ROOT.resolve():
            raise RuntimeError(f"Refusing to clean unsafe seed target: {target}")
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--seed-dir", type=Path, default=DEFAULT_SEED_DIR)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    seed_dir = args.seed_dir.resolve()
    payload = read_manifest(manifest_path)
    rows = payload.get("rows", [])
    if not rows:
        raise RuntimeError("Seed manifest has no rows.")

    total_bytes = sum(int(row.get("size_bytes", 0)) for row in rows)
    report = {
        "schema_version": "EDGEIQ_PRODUCTION_SEED_EXPORT_V1",
        "generated_at": utc_now(),
        "manifest": str(manifest_path),
        "seed_dir": str(seed_dir),
        "file_count": len(rows),
        "total_bytes": total_bytes,
        "total_mb": round(total_bytes / (1024 * 1024), 3),
        "dry_run": args.dry_run,
        "status": "PASS",
        "files": [],
    }

    if not args.dry_run:
        safe_clean_target(seed_dir, args.replace)

    for row in rows:
        source = ROOT / str(row["relative_path"])
        destination = seed_dir / str(row["deployment_relative_path"])
        if not source.exists():
            raise RuntimeError(f"Seed source missing: {source}")
        report["files"].append(
            {
                "source": str(source),
                "destination": str(destination),
                "bytes": source.stat().st_size,
                "sha256": row.get("sha256", ""),
            }
        )
        if args.dry_run:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    if not args.dry_run:
        manifest_out = seed_dir / "outputs" / "deployment-v1"
        manifest_out.mkdir(parents=True, exist_ok=True)
        shutil.copy2(manifest_path, manifest_out / manifest_path.name)
        shutil.copy2(manifest_path, seed_dir / "edgeiq_production_seed_manifest_v1.json")
        report_path = manifest_out / "edgeiq_production_seed_export_v1_report.json"
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in report if key != "files"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"EDGEIQ_PRODUCTION_SEED_EXPORT=FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
