from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "performance-intelligence" / "identity-profiler-v1"
OUT.mkdir(parents=True, exist_ok=True)

RELEVANT_PATTERNS = [
    "build_edgeiq_identity_repository_profiler*.py",
    "scripts/build_edgeiq_identity_repository_profiler*.py",
    "scripts/*identity*profiler*.py",
    "scripts/*edgeiq_identity*profiler*.py",
    "docs/performance-intelligence/identity-profiler-v1*/*",
    "docs/performance-intelligence/identity-profiler-v1/**/*",
]

CLASS_RULES = [
    (re.compile(r"(^|/)build_edgeiq_identity_repository_profiler_v1\.py$", re.I), "CANONICAL"),
    (re.compile(r"STEP10[0-9]|step10[0-9]", re.I), "SUPERSEDED"),
    (re.compile(r"patch|fix|repair|promote", re.I), "PATCH_GENERATOR"),
    (re.compile(r"inspect|audit|forensic", re.I), "FORENSIC_TOOL"),
    (re.compile(r"run[-_ ]?log|\.log$", re.I), "RUN_LOG"),
    (re.compile(r"failed|failure|error", re.I), "FAILED_RUN"),
    (re.compile(r"\.tmp$|\.partial$|checkpoint", re.I), "TEMPORARY"),
    (re.compile(r"crosswalk|identity_graph|canonical_identity|manifest|catalogue|completion|schema_validation|data_contract", re.I), "VALID_OUTPUT"),
]

VALID_SUFFIXES = {".py", ".csv", ".json", ".md", ".txt", ".log"}


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except Exception:
        return str(path)


def run_git(args: list[str]) -> str:
    try:
        cp = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, timeout=30)
        return (cp.stdout or cp.stderr or "").strip()
    except Exception as exc:
        return f"ERROR: {exc}"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def classify(path: Path) -> str:
    rp = rel(path)
    if not path.exists():
        return "UNKNOWN"
    for rx, cls in CLASS_RULES:
        if rx.search(rp):
            return cls
    if path.suffix.lower() in {".csv", ".json", ".md", ".txt"} and "identity-profiler-v1" in rp:
        return "VALID_OUTPUT"
    if path.suffix.lower() == ".py" and "identity" in rp.lower() and "profiler" in rp.lower():
        return "SUPERSEDED"
    return "UNKNOWN"


def iter_relevant_files() -> list[Path]:
    files: set[Path] = set()
    for pat in RELEVANT_PATTERNS:
        for p in ROOT.glob(pat):
            if p.is_file() and p.suffix.lower() in VALID_SUFFIXES:
                files.add(p)
    return sorted(files, key=lambda p: (str(p).lower()))


def py_compile(path: Path) -> tuple[bool, str]:
    if path.suffix.lower() != ".py":
        return False, "not_python"
    cp = subprocess.run([sys.executable, "-m", "py_compile", str(path)], cwd=ROOT, text=True, capture_output=True)
    return cp.returncode == 0, (cp.stderr or cp.stdout or "ok").strip()


def line_count(path: Path, cap: int = 10_000_000) -> int | None:
    try:
        if path.stat().st_size > 750 * 1024 * 1024:
            return None
        with path.open("rb") as f:
            return sum(1 for _ in f)
    except Exception:
        return None


def main() -> int:
    now = datetime.now(timezone.utc).isoformat()
    files = iter_relevant_files()
    rows = []
    newest_profiler = None
    for p in files:
        st = p.stat()
        cls = classify(p)
        compiles = ""
        compile_msg = ""
        if p.suffix.lower() == ".py":
            ok, msg = py_compile(p)
            compiles = "YES" if ok else "NO"
            compile_msg = msg[:500]
        rows.append({
            "path": rel(p),
            "classification": cls,
            "size_bytes": st.st_size,
            "modified_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
            "sha256": sha256(p),
            "line_count": line_count(p),
            "python_compiles": compiles,
            "compile_message": compile_msg,
        })
        if "identity_repository_profiler" in p.name.lower() and p.suffix.lower() == ".py":
            if newest_profiler is None or st.st_mtime > newest_profiler.stat().st_mtime:
                newest_profiler = p

    csv_path = OUT / "edgeiq_identity_profiler_final_state_forensic_v1.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["path", "classification", "size_bytes", "modified_utc", "sha256", "line_count", "python_compiles", "compile_message"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader(); w.writerows(rows)

    status = run_git(["status", "--porcelain=v1"])
    status_lines = [ln for ln in status.splitlines() if ln.strip()]
    class_counts = {}
    for r in rows:
        class_counts[r["classification"]] = class_counts.get(r["classification"], 0) + 1
    huge_crosswalks = [r for r in rows if "crosswalk" in r["path"].lower() and int(r["size_bytes"] or 0) > 50_000_000]
    temp_outputs = [r for r in rows if r["classification"] == "TEMPORARY"]
    step108 = [r for r in rows if "step108" in r["path"].lower()]
    canonical = ROOT / "build_edgeiq_identity_repository_profiler_v1.py"
    canonical_compile = py_compile(canonical) if canonical.exists() else (False, "missing")

    summary = {
        "generated_utc": now,
        "root": str(ROOT),
        "branch": run_git(["branch", "--show-current"]),
        "last_commits": run_git(["log", "-5", "--oneline"]),
        "git_status_line_count": len(status_lines),
        "relevant_artifact_count": len(rows),
        "classification_counts": class_counts,
        "newest_profiler": rel(newest_profiler) if newest_profiler else "NONE",
        "canonical_exists": canonical.exists(),
        "canonical_compiles": canonical_compile[0],
        "canonical_compile_message": canonical_compile[1][:500],
        "step108_artifacts": len(step108),
        "huge_crosswalks_over_50mb": len(huge_crosswalks),
        "temporary_artifacts": len(temp_outputs),
    }
    (OUT / "edgeiq_identity_profiler_final_state_forensic_v1_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md = OUT / "EDGEIQ_IDENTITY_PROFILER_FINAL_STATE_FORENSIC_V1.md"
    md.write_text("\n".join([
        "# EDGEiQ Identity Profiler Final State Forensic V1",
        "",
        f"Generated UTC: {now}",
        f"Root: `{ROOT}`",
        f"Branch: `{summary['branch']}`",
        f"Git status line count: {len(status_lines)}",
        f"Relevant artifacts: {len(rows)}",
        f"Newest profiler: `{summary['newest_profiler']}`",
        f"Canonical exists: {summary['canonical_exists']}",
        f"Canonical compiles: {summary['canonical_compiles']}",
        f"STEP108 artifacts: {len(step108)}",
        f"Huge crosswalks >50MB: {len(huge_crosswalks)}",
        f"Temporary/checkpoint artifacts: {len(temp_outputs)}",
        "",
        "## Classification Counts",
        *[f"- {k}: {v}" for k, v in sorted(class_counts.items())],
        "",
        "## Latest Commits",
        "```",
        summary["last_commits"],
        "```",
        "",
        "## Notes",
        "Full artifact inventory is in `edgeiq_identity_profiler_final_state_forensic_v1.csv`.",
        "Full git porcelain output is intentionally not printed to avoid flooding the recovery run.",
    ]), encoding="utf-8")

    print(json.dumps({
        "status": "FORENSIC_AUDIT_WRITTEN",
        "artifacts": len(rows),
        "dirty_lines": len(status_lines),
        "newest_profiler": summary["newest_profiler"],
        "canonical_exists": summary["canonical_exists"],
        "canonical_compiles": summary["canonical_compiles"],
        "report": rel(md),
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
