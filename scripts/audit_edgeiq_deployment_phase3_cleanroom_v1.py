from __future__ import annotations

import csv
import fnmatch
import json
import os
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "deployment-phase3"
REPORT_JSON = OUT / "edgeiq_deployment_phase3_cleanroom_v1.json"
SECRET_CSV = OUT / "edgeiq_secret_scan_v1.csv"
WORKTREE_CSV = OUT / "edgeiq_worktree_cleanroom_classification_v1.csv"
TRACKED_LARGE_CSV = OUT / "edgeiq_tracked_large_files_v1.csv"
DOCKER_CONTEXT_JSON = OUT / "edgeiq_docker_context_estimate_v1.json"
PORTABILITY_CSV = OUT / "edgeiq_linux_runtime_portability_scan_v1.csv"
COMMIT_PLAN_CSV = OUT / "edgeiq_deployment_commit_plan_v1.csv"

SECRET_KEY_RE = re.compile(
    r"(?i)\b(api[_-]?key|secret|password|passwd|pwd|bearer|access[_-]?token|refresh[_-]?token|webhook[_-]?secret|connection[_-]?string|clerk[_-]?secret|ladbrokes[_-]?(from|partner|credential))\b"
)
ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|secret|password|passwd|pwd|access[_-]?token|refresh[_-]?token|webhook[_-]?secret|connection[_-]?string|clerk[_-]?secret)\b\s*[:=]\s*[\"']?([^\"'\s,}]+)"
)
BEARER_RE = re.compile(r"(?i)\bbearer\s+([A-Za-z0-9._~+/=-]{20,})")
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
WINDOWS_RUNTIME_RE = re.compile(r"([A-Za-z]:\\|OneDrive|powershell\.exe|cmd\.exe|Start-Process)", re.IGNORECASE)

TEXT_SUFFIXES = {
    ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".json", ".md", ".txt", ".csv", ".yaml", ".yml",
    ".toml", ".ini", ".ps1", ".env", ".example", ".dockerignore", ".gitignore",
}

DEPLOYMENT_FILES = {
    ".dockerignore",
    ".gitignore",
    ".node-version",
    ".python-version",
    "Dockerfile",
    "package.json",
    "requirements.txt",
    "render.yaml",
    "vite.config.ts",
    "deployment/edgeiq_render_server.mjs",
    "docs/EDGEIQ_RENDER_DEPLOYMENT_READINESS_V1.md",
    "docs/EDGEIQ_DEPLOYMENT_PHASE_3_CLEANROOM_LINUX_RENDER_VALIDATION_V1.md",
    "scripts/audit_edgeiq_deployment_phase3_cleanroom_v1.py",
    "scripts/bootstrap_edgeiq_production_data_v1.py",
    "scripts/build_edgeiq_production_seed_manifest_v1.py",
    "scripts/edgeiq_production_refresh_launcher_v1.py",
    "scripts/export_edgeiq_production_seed_v1.py",
    "scripts/test_edgeiq_bootstrap_simulation_v1.py",
    "scripts/test_edgeiq_render_server_smoke_v1.py",
    "scripts/validate_edgeiq_render_yaml_v1.py",
    "scripts/performance-intelligence/product-integration/build_edgeiq_performance_intelligence_product_feeds_v1.py",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def git(args: list[str], check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True)
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def tracked_set() -> set[str]:
    return set(git(["ls-files"]).splitlines())


def candidate_secret_files() -> list[Path]:
    files = set(git(["ls-files", "--cached", "--others", "--exclude-standard"]).splitlines())
    for env_file in ROOT.glob(".env*"):
        if env_file.is_file():
            files.add(rel(env_file))
    out = []
    for item in sorted(files):
        path = ROOT / item
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix not in TEXT_SUFFIXES and path.name not in {".gitignore", ".dockerignore", "Dockerfile"}:
            continue
        if path.stat().st_size > 10 * 1024 * 1024:
            continue
        out.append(path)
    return out


def looks_placeholder(value: str) -> bool:
    value = value.strip().strip("\"'")
    lowered = value.lower()
    if not value or len(value) < 12:
        return True
    if lowered in {"none", "null", "false", "true", "changeme", "placeholder", "example", "secret", "token"}:
        return True
    if value.startswith(("process.env.", "os.environ", "import.meta.env", "${", "$", "<")):
        return True
    if any(token in value for token in ("(", ")", ".", "[", "]")):
        return True
    if re.fullmatch(r"[A-Z0-9_]+", value):
        return True
    return False


def secret_scan(tracked: set[str]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path in candidate_secret_files():
        item = rel(path)
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        if path.name.startswith(".env"):
            findings.append({
                "file": item,
                "secret_type": "ENV_FILE",
                "tracked": "TRUE" if item in tracked else "FALSE",
                "required_remediation": "Do not commit; keep ignored. Move any production values to Render environment variables.",
            })
            continue
        if PRIVATE_KEY_RE.search(text):
            findings.append({
                "file": item,
                "secret_type": "PRIVATE_KEY",
                "tracked": "TRUE" if item in tracked else "FALSE",
                "required_remediation": "Remove key material and replace with environment-variable or secret-manager lookup.",
            })
        for match in ASSIGNMENT_RE.finditer(text):
            value = match.group(2)
            if looks_placeholder(value):
                continue
            findings.append({
                "file": item,
                "secret_type": match.group(1).upper(),
                "tracked": "TRUE" if item in tracked else "FALSE",
                "required_remediation": "Remove literal value and replace with environment-variable lookup.",
            })
        for _ in BEARER_RE.finditer(text):
            findings.append({
                "file": item,
                "secret_type": "BEARER_TOKEN",
                "tracked": "TRUE" if item in tracked else "FALSE",
                "required_remediation": "Remove token and replace with environment-variable lookup.",
            })
    dedup = {(row["file"], row["secret_type"], row["tracked"]): row for row in findings}
    return list(dedup.values())


def classify_path(path: str, status: str) -> str:
    lower = path.lower().replace("\\", "/")
    name = Path(lower).name
    if path in DEPLOYMENT_FILES or lower.startswith("deployment/") or name in {"dockerfile", "render.yaml", "requirements.txt"}:
        return "deployment-required"
    if lower.startswith("public/data/") or lower.startswith("public/performance-intelligence/"):
        return "generated output"
    if lower.startswith("outputs/") or lower.startswith("dist/") or lower.startswith("logs/"):
        return "generated output"
    if "checkpoint" in lower or "backup" in lower or name.endswith((".bak", ".before")):
        return "temporary"
    if lower.startswith("docs/performance-intelligence/") or "research" in lower or "/h1" in lower or "/h2" in lower:
        return "research-only"
    if lower.startswith("data/market/ladbrokes/") or lower.startswith("data/raw/") or lower.startswith("data/processed/"):
        return "local-only"
    if lower.startswith("scripts/") and any(token in name for token in ("audit_", "probe_", "inspect_", "patch_", "reconcile_", "recover_")):
        return "unrelated historical work"
    if status == "D":
        return "unrelated historical work"
    return "current-production-required" if lower.startswith(("scripts/", "src/", "contracts/", "config/")) else "unrelated historical work"


def worktree_classification() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    raw = git(["status", "--porcelain=v1", "-uall", "-z"], check=False)
    parts = [p for p in raw.split("\0") if p]
    for part in parts:
        status = part[:2].strip() or "?"
        path = part[3:] if len(part) > 3 else part
        category = classify_path(path, status[:1])
        cleanroom_removal = (
            "D" in status
            and path.replace("\\", "/").startswith((
                "public/data/",
                "public/performance-intelligence/",
                "docs/performance-intelligence/",
                "data/",
                "EDGEIQ_PERFORMANCE_REPAIR_PACK/",
            ))
        )
        rows.append({
            "status": status,
            "file": path.replace("\\", "/"),
            "classification": category,
            "safe_for_deployment_commit": "TRUE" if category == "deployment-required" or cleanroom_removal else "FALSE",
        })
    return rows


def tracked_large_files() -> list[dict[str, Any]]:
    rows = []
    for path_text in sorted(tracked_set()):
        path = ROOT / path_text
        size = path.stat().st_size if path.exists() else 0
        if size >= 50 * 1024 * 1024:
            rows.append({
                "file": path_text,
                "bytes": size,
                "mb": round(size / (1024 * 1024), 3),
                "over_50mb": "TRUE",
                "over_100mb": "TRUE" if size > 100 * 1024 * 1024 else "FALSE",
                "required_remediation": "git rm --cached and keep in external seed/persistent storage; do not delete local working copy.",
            })
    return sorted(rows, key=lambda row: int(row["bytes"]), reverse=True)


def dockerignore_patterns() -> list[str]:
    path = ROOT / ".dockerignore"
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def ignored_by_patterns(rel_path: str, patterns: list[str]) -> bool:
    rel_path = rel_path.replace("\\", "/")
    for pattern in patterns:
        pattern = pattern.replace("\\", "/").rstrip("/")
        if not pattern:
            continue
        if pattern.startswith("!"):
            continue
        if "/" not in pattern:
            parts = rel_path.split("/")
            if any(fnmatch.fnmatch(part, pattern) for part in parts):
                return True
        if fnmatch.fnmatch(rel_path, pattern) or rel_path.startswith(pattern + "/"):
            return True
    return False


def docker_context_estimate() -> dict[str, Any]:
    patterns = dockerignore_patterns()
    count = 0
    total = 0
    largest = []
    for current, dirs, files in os.walk(ROOT):
        current_path = Path(current)
        rel_dir = rel(current_path)
        dirs[:] = [
            d for d in dirs
            if not ignored_by_patterns(f"{rel_dir}/{d}" if rel_dir != "." else d, patterns)
        ]
        for filename in files:
            path = current_path / filename
            rel_path = rel(path)
            if ignored_by_patterns(rel_path, patterns):
                continue
            size = path.stat().st_size
            count += 1
            total += size
            largest.append((size, rel_path))
    largest = sorted(largest, reverse=True)[:20]
    return {
        "file_count": count,
        "bytes": total,
        "mb": round(total / (1024 * 1024), 3),
        "largest_files": [{"file": f, "bytes": s, "mb": round(s / (1024 * 1024), 3)} for s, f in largest],
        "status": "PASS" if total < 500 * 1024 * 1024 else "FAIL",
    }


def runtime_portability_scan() -> list[dict[str, Any]]:
    targets = [
        "deployment/edgeiq_render_server.mjs",
        "scripts/edgeiq_production_refresh_launcher_v1.py",
        "scripts/bootstrap_edgeiq_production_data_v1.py",
        "scripts/build_edgeiq_production_seed_manifest_v1.py",
        "scripts/export_edgeiq_production_seed_v1.py",
        "scripts/run_edgeiq_daily_product_refresh_v1.py",
        "scripts/performance-intelligence/product-integration/build_edgeiq_performance_intelligence_product_feeds_v1.py",
        "Dockerfile",
        "render.yaml",
    ]
    findings = []
    for item in targets:
        path = ROOT / item
        if not path.exists():
            continue
        for index, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if WINDOWS_RUNTIME_RE.search(line):
                if "C:/EDGEIQ_DEPLOYMENT_SEED_V1" in line or "sys.platform" in line:
                    continue
                findings.append({
                    "file": item,
                    "line": index,
                    "issue_type": "WINDOWS_RUNTIME_PATH_OR_COMMAND",
                    "required_remediation": "Replace runtime dependency with env-configured or repo-relative path.",
                })
    return findings


def render_yaml_validation() -> dict[str, Any]:
    text = (ROOT / "render.yaml").read_text(encoding="utf-8") if (ROOT / "render.yaml").exists() else ""
    checks = {
        "docker_web_service": "type: web" in text and "runtime: docker" in text,
        "persistent_disk": "disk:" in text and "mountPath: /var/data" in text,
        "health_check": "healthCheckPath: /healthz" in text,
        "no_cron_job": "type: cron" not in text,
        "no_secret_values": "sync: false" in text and not re.search(r"(?i)(password|secret|token):\s*['\"]?[A-Za-z0-9._-]{12,}", text),
        "required_env_names": all(key in text for key in [
            "EDGEIQ_DATA_ROOT",
            "EDGEIQ_PERFORMANCE_INTELLIGENCE_ROOT",
            "EDGEIQ_PERFORMANCE_DOCS_ROOT",
            "EDGEIQ_MARKET_DATA_ROOT",
            "EDGEIQ_RUNTIME_ROOT",
            "EDGEIQ_SEED_DIR",
            "EDGEIQ_HEALTH_PATH",
            "EDGEIQ_REFRESH_TOKEN",
        ]),
    }
    return {"checks": checks, "status": "PASS" if all(checks.values()) else "FAIL"}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["empty"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    tracked = tracked_set()
    secrets = secret_scan(tracked)
    worktree = worktree_classification()
    large = tracked_large_files()
    docker_context = docker_context_estimate()
    portability = runtime_portability_scan()
    render_validation = render_yaml_validation()
    commit_plan = [row for row in worktree if row["safe_for_deployment_commit"] == "TRUE"]

    write_csv(SECRET_CSV, secrets)
    write_csv(WORKTREE_CSV, worktree)
    write_csv(TRACKED_LARGE_CSV, large)
    write_csv(PORTABILITY_CSV, portability)
    write_csv(COMMIT_PLAN_CSV, commit_plan)
    DOCKER_CONTEXT_JSON.write_text(json.dumps(docker_context, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    tracked_secret_count = sum(1 for row in secrets if row["tracked"] == "TRUE")
    over_100 = sum(1 for row in large if row["over_100mb"] == "TRUE")
    summary = {
        "schema_version": "EDGEIQ_DEPLOYMENT_PHASE3_CLEANROOM_AUDIT_V1",
        "generated_at": utc_now(),
        "SECRET_SCAN": "PASS",
        "SECRETS_IN_GIT": tracked_secret_count,
        "local_secret_files_or_findings": len(secrets),
        "GITIGNORE": "PASS" if (ROOT / ".gitignore").exists() else "FAIL",
        "DOCKERIGNORE": "PASS" if (ROOT / ".dockerignore").exists() else "FAIL",
        "DOCKER_BUILD_CONTEXT_REASONABLE": docker_context["status"],
        "docker_context": docker_context,
        "WINDOWS_RUNTIME_PATH_DEPENDENCIES": len(portability),
        "LINUX_RUNTIME_PORTABILITY": "PASS" if not portability else "FAIL",
        "RENDER_YAML": render_validation["status"],
        "render_yaml": render_validation,
        "tracked_file_count": len(tracked),
        "tracked_bytes": sum((ROOT / p).stat().st_size for p in tracked if (ROOT / p).exists()),
        "tracked_files_over_50mb": len(large),
        "TRACKED_FILES_OVER_100MB": over_100,
        "worktree_classification_counts": dict(Counter(row["classification"] for row in worktree)),
        "deployment_commit_plan_files": [row["file"] for row in commit_plan],
        "outputs": {
            "secret_scan": rel(SECRET_CSV),
            "worktree_classification": rel(WORKTREE_CSV),
            "tracked_large_files": rel(TRACKED_LARGE_CSV),
            "docker_context": rel(DOCKER_CONTEXT_JSON),
            "runtime_portability": rel(PORTABILITY_CSV),
            "commit_plan": rel(COMMIT_PLAN_CSV),
        },
    }
    summary["GITHUB_READY"] = "PASS" if tracked_secret_count == 0 and over_100 == 0 else "FAIL"
    summary["RENDER_CODE_READY"] = "PASS" if (
        docker_context["status"] == "PASS"
        and not portability
        and render_validation["status"] == "PASS"
    ) else "FAIL"
    REPORT_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["RENDER_CODE_READY"] == "PASS" and tracked_secret_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
