from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BUILDER = ROOT / "scripts" / "performance-intelligence" / "phase1_6_1" / "build_edgeiq_corrected_performance_facts_phase1_6_1.py"

text = BUILDER.read_text(encoding="utf-8")
text = text.replace("import shutil\n", "import shutil\nimport time\n", 1)

old = '''def remove_failed_staging_dirs() -> None:
    WAREHOUSE_ROOT.mkdir(parents=True, exist_ok=True)
    for path in WAREHOUSE_ROOT.iterdir():
        if path.is_dir() and path.name.startswith(".") and path.name.endswith(".staging"):
            for child in path.rglob("*"):
                if child.is_file():
                    restore_writable(child)
            shutil.rmtree(path)
'''

new = '''def remove_failed_staging_dirs() -> None:
    WAREHOUSE_ROOT.mkdir(parents=True, exist_ok=True)
    for path in WAREHOUSE_ROOT.iterdir():
        if path.is_dir() and path.name.startswith(".") and path.name.endswith(".staging"):
            last_error: Exception | None = None
            for attempt in range(1, 11):
                for child in path.rglob("*"):
                    if child.is_file():
                        restore_writable(child)
                try:
                    shutil.rmtree(path)
                    last_error = None
                    break
                except Exception as exc:
                    last_error = exc
                    time.sleep(1.5)
            if last_error is not None:
                diagnostic = {
                    "marker": "EDGEIQ_PERFORMANCE_INTELLIGENCE_PHASE1_6_1_STAGING_CLEANUP_BLOCKED",
                    "staging_dir": str(path),
                    "error": repr(last_error),
                    "instruction": "Close any process holding files under this failed staging directory and rerun.",
                }
                AUDIT_DIR.mkdir(parents=True, exist_ok=True)
                write_json(
                    AUDIT_DIR / "edgeiq_performance_intelligence_phase1_6_1_failed_latest.json",
                    diagnostic,
                )
                raise RuntimeError(
                    "Failed staging cleanup blocked by Windows file handle: "
                    + str(path)
                ) from last_error
'''

if old not in text:
    raise SystemExit("STAGING_CLEANUP_BLOCK_NOT_FOUND")

BUILDER.write_text(text.replace(old, new, 1), encoding="utf-8")
print("PHASE1_6_1_STAGING_CLEANUP_RETRY_PATCH_APPLIED")
