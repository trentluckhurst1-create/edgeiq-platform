
from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
OUTDIR = ROOT / "docs" / "performance-intelligence" / "standard-time-investigation"
OUTDIR.mkdir(parents=True, exist_ok=True)
TARGET_NAME = "edgeiq_racingcom_calendar_discovery_v1.csv"
TARGET_PATH = "public/data/edgeiq_racingcom_calendar_discovery_v1.csv"
TARGET_WINDOWS = "public\\data\\edgeiq_racingcom_calendar_discovery_v1.csv"
NOW = datetime.now(timezone.utc).isoformat()

REFERENCE_LEDGER = OUTDIR / "edgeiq_racingcom_calendar_discovery_reference_ledger_v1.csv"
CANDIDATES = OUTDIR / "edgeiq_racingcom_calendar_discovery_producer_candidates_v1.csv"
LOGIC_LEDGER = OUTDIR / "edgeiq_racingcom_calendar_discovery_logic_ledger_v1.csv"
EXCERPTS = OUTDIR / "edgeiq_racingcom_calendar_discovery_producer_excerpts_v1.txt"
AUDIT = OUTDIR / "edgeiq_racingcom_calendar_discovery_producer_audit_v1.csv"
SUMMARY_JSON = OUTDIR / "edgeiq_racingcom_calendar_discovery_producer_v1.json"
REPORT_MD = OUTDIR / "edgeiq_racingcom_calendar_discovery_producer_v1.md"

SKIP_DIRS = {
    ".git", "node_modules", "dist", "build", ".vite", "__pycache__", ".pytest_cache",
    "outputs", ".venv", "venv", "coverage", ".next", ".cache", "approved-ui-rebuild",
    "screenshots", "checkpoints", "EDGEiQ_RACING_STAGING", "EDGEiQ_RACING_STAGING_CLEAN_V1"
}
TEXT_EXTS = {
    ".py", ".ps1", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json", ".csv", ".md", ".txt", ".yml", ".yaml", ".toml"
}
MAX_READ_BYTES = 1_500_000
SCAN_TOP_LEVEL_ALLOW = {"scripts", "src", "public", "docs", "contracts", "tests", ".github"}
PUBLIC_DATA_ALLOW = {TARGET_NAME}
DOCS_ALLOW_PREFIX = ("performance-intelligence",)

PATTERNS = {
    "target_filename": re.compile(re.escape(TARGET_NAME), re.I),
    "target_path": re.compile(re.escape(TARGET_PATH).replace("/", r"[/\\]"), re.I),
    "race_no_assignment": re.compile(r"(?:['\"]race_no['\"]\s*:|\brace_no\b\s*=|\['race_no'\]\s*=|\.race_no\s*=)", re.I),
    "race_url_assignment": re.compile(r"(?:['\"]race_url['\"]\s*:|\brace_url\b\s*=|\['race_url'\]\s*=|\.race_url\s*=)", re.I),
    "speed_data_url_assignment": re.compile(r"(?:['\"]speed_data_url['\"]\s*:|\bspeed_data_url\b\s*=|\['speed_data_url'\]\s*=|\.speed_data_url\s*=)", re.I),
    "fixed_range_1_13": re.compile(r"range\s*\(\s*1\s*,\s*13\s*\)", re.I),
    "fixed_race_range": re.compile(r"range\s*\(\s*1\s*,\s*(?:9|10|11|12|13|14|15|16|17|18|19|20|21)\s*\)", re.I),
    "race_url_construct": re.compile(r"/race/|\{race_no\}|race_no\}|raceNo\}|race-number", re.I),
    "speed_data_construct": re.compile(r"/speed-data|speed-data|speed_data", re.I),
    "meeting_level_derivation": re.compile(r"meeting_url|meeting_discovery|calendar_discovery|meeting-level|meeting level", re.I),
    "write_operation": re.compile(r"\.to_csv\s*\(|write_text\s*\(|open\s*\([^\n]*(?:['\"]w|mode\s*=\s*['\"]w)|DictWriter|csv\.writer", re.I),
    "input_source_literal": re.compile(r"(?:public[/\\]data[/\\][A-Za-z0-9_\-.]+\.(?:csv|json)|edgeiq_[A-Za-z0-9_\-.]+\.(?:csv|json)|https?://[^'\"\s)]+)", re.I),
}


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def iter_repo_files():
    import subprocess
    self_name = Path(__file__).name
    pattern = r"edgeiq_racingcom_calendar_discovery_v1\.csv|MEETS_BY_MONTH_MEETING_EXPANDED|GetMeetsByMonth|range\s*\(\s*1\s*,\s*13\s*\)|speed_data_url|/speed-data|/race/|race_url"
    roots = ["scripts", "docs/performance-intelligence"]
    candidates: set[Path] = set()
    for scan_root in roots:
        try:
            result = subprocess.run(
                ["rg", "-l", pattern, scan_root, "--glob", "*.py", "--glob", "*.ps1", "--glob", "*.md", "--glob", "*.csv", "--glob", "*.json", "--glob", "!**/checkpoints/**", "--glob", "!**/screenshots/**"],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=30,
            )
            for line in result.stdout.splitlines():
                if line.strip():
                    candidates.add(ROOT / line.strip())
        except Exception:
            pass
    candidates.add(ROOT / "public" / "data" / TARGET_NAME)
    preferred = ROOT / "scripts" / "build_edgeiq_racingcom_calendar_discovery_v1.py"
    if preferred.exists():
        candidates.add(preferred)
    legacy = ROOT / "scripts" / "build_edgeiq_racingcom_csv_ingestion_v1.py"
    if legacy.exists():
        candidates.add(legacy)
    for path in sorted(candidates, key=lambda p: rel(p)):
        if path.name == self_name:
            continue
        if not path.exists() or not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_EXTS:
            continue
        try:
            if path.stat().st_size > MAX_READ_BYTES and path.name != TARGET_NAME:
                continue
        except OSError:
            continue
        yield path


def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        try:
            return path.read_text(encoding="cp1252", errors="replace")
        except Exception:
            return ""


def clean_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: clean_cell(row.get(k, "")) for k in fieldnames})


def line_window(lines: list[str], line_no: int, radius: int = 5) -> str:
    start = max(1, line_no - radius)
    end = min(len(lines), line_no + radius)
    rendered = []
    for idx in range(start, end + 1):
        prefix = ">>" if idx == line_no else "  "
        rendered.append(f"{prefix} {idx}: {lines[idx-1].rstrip()}")
    return "\n".join(rendered)


def ast_source_segment(lines: list[str], node: ast.AST) -> str:
    lineno = getattr(node, "lineno", None)
    end_lineno = getattr(node, "end_lineno", lineno)
    if not lineno:
        return ""
    return " ".join(line.strip() for line in lines[lineno - 1:end_lineno])[:500]


def extract_python_ast(path: Path, text: str, lines: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        rows.append({
            "file": rel(path), "line_no": getattr(exc, "lineno", 0) or 0,
            "logic_type": "AST_PARSE_ERROR", "evidence": str(exc), "line": "", "near_target": "", "score": 0,
        })
        return rows

    def const_string(node: ast.AST) -> str:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.JoinedStr):
            return "".join(part.value if isinstance(part, ast.Constant) else "{expr}" for part in node.values)
        return ""

    for node in ast.walk(tree):
        lineno = getattr(node, "lineno", 0) or 0
        segment = ast_source_segment(lines, node)
        if isinstance(node, ast.For):
            call = node.iter
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "range":
                args = []
                for arg in call.args:
                    if isinstance(arg, ast.Constant):
                        args.append(repr(arg.value))
                    else:
                        args.append(type(arg).__name__)
                rows.append({
                    "file": rel(path), "line_no": lineno, "logic_type": "AST_RANGE_LOOP",
                    "evidence": f"range({', '.join(args)})", "line": segment, "near_target": "", "score": 4,
                })
        if isinstance(node, ast.Assign):
            targets = []
            for target in node.targets:
                if isinstance(target, ast.Name):
                    targets.append(target.id)
                elif isinstance(target, ast.Subscript):
                    key = const_string(target.slice)
                    if key:
                        targets.append(key)
            interesting = [t for t in targets if t in {"race_no", "race_url", "speed_data_url"}]
            for target in interesting:
                rows.append({
                    "file": rel(path), "line_no": lineno, "logic_type": f"AST_ASSIGN_{target.upper()}",
                    "evidence": target, "line": segment, "near_target": "", "score": 3,
                })
        if isinstance(node, (ast.Dict,)):
            for key in node.keys:
                key_text = const_string(key) if key is not None else ""
                if key_text in {"race_no", "race_url", "speed_data_url"}:
                    rows.append({
                        "file": rel(path), "line_no": lineno, "logic_type": f"AST_DICT_KEY_{key_text.upper()}",
                        "evidence": key_text, "line": segment, "near_target": "", "score": 2,
                    })
        if isinstance(node, ast.Call):
            func_name = ""
            if isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            elif isinstance(node.func, ast.Name):
                func_name = node.func.id
            call_text = segment
            if func_name in {"to_csv", "write_text", "open"} and TARGET_NAME in call_text:
                rows.append({
                    "file": rel(path), "line_no": lineno, "logic_type": "AST_TARGET_WRITE_CALL",
                    "evidence": func_name, "line": call_text, "near_target": "YES", "score": 10,
                })
            for arg in list(node.args) + [kw.value for kw in node.keywords]:
                s = const_string(arg)
                if TARGET_NAME in s:
                    rows.append({
                        "file": rel(path), "line_no": lineno, "logic_type": "AST_TARGET_LITERAL",
                        "evidence": s, "line": call_text, "near_target": "YES", "score": 5,
                    })
    return rows


def canonical_group_stats() -> dict[str, Any]:
    csv_path = ROOT / "public" / "data" / TARGET_NAME
    stats: dict[str, Any] = {
        "target_exists": csv_path.exists(),
        "target_rows": 0,
        "target_columns": [],
        "groups_exact_1_12": 0,
        "groups_total": 0,
        "future_rows": 0,
        "future_exact_1_12_groups": 0,
        "sha256": "",
    }
    if not csv_path.exists():
        return stats
    body = csv_path.read_bytes()
    stats["sha256"] = hashlib.sha256(body).hexdigest()
    try:
        text = body.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(text.splitlines())
        rows = list(reader)
    except Exception as exc:
        stats["read_error"] = str(exc)
        return stats
    stats["target_rows"] = len(rows)
    stats["target_columns"] = reader.fieldnames or []
    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    future_groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    today = datetime.now().date()
    for row in rows:
        date_text = (row.get("race_date") or "").strip()
        track = (row.get("track") or "").strip()
        try:
            race_no = int(float(str(row.get("race_no") or "").strip()))
        except Exception:
            continue
        groups[(date_text, track)].append(race_no)
        try:
            d = datetime.fromisoformat(date_text[:10]).date()
            if d > today:
                stats["future_rows"] += 1
                future_groups[(date_text, track)].append(race_no)
        except Exception:
            pass
    exact = {tuple(range(1, 13))}
    stats["groups_total"] = len(groups)
    stats["groups_exact_1_12"] = sum(1 for nums in groups.values() if tuple(sorted(set(nums))) in exact)
    stats["future_exact_1_12_groups"] = sum(1 for nums in future_groups.values() if tuple(sorted(set(nums))) in exact)
    return stats


def main() -> None:
    reference_rows: list[dict[str, Any]] = []
    logic_rows: list[dict[str, Any]] = []
    excerpt_hits: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    file_metrics: dict[str, Counter] = defaultdict(Counter)
    file_inputs: dict[str, set[str]] = defaultdict(set)
    scanned_files = 0

    for path in iter_repo_files():
        scanned_files += 1
        text = safe_read(path)
        if not text:
            continue
        lines = text.splitlines()
        file_key = rel(path)
        target_vars: set[str] = set()
        for probe_line in lines:
            if TARGET_NAME in probe_line:
                m = re.search(r"\b([A-Z][A-Z0-9_]{1,40})\s*=", probe_line)
                if m:
                    target_vars.add(m.group(1))
        for line_no, line in enumerate(lines, start=1):
            matched_patterns = []
            for name, rx in PATTERNS.items():
                if rx.search(line):
                    matched_patterns.append(name)
            if not matched_patterns:
                continue
            for name in matched_patterns:
                if name == "input_source_literal":
                    for m in PATTERNS[name].finditer(line):
                        file_inputs[file_key].add(m.group(0))
                    continue
                row = {
                    "file": file_key,
                    "line_no": line_no,
                    "pattern": name,
                    "role": "REFERENCE",
                    "line": line.strip()[:1200],
                }
                if name in {"target_filename", "target_path"}:
                    reference_rows.append(row)
                    file_metrics[file_key]["target_references"] += 1
                    excerpt_hits[file_key].append((line_no, name, line_window(lines, line_no)))
                else:
                    logic_type = name.upper()
                    score = {
                        "write_operation": 4,
                        "fixed_range_1_13": 8,
                        "fixed_race_range": 5,
                        "race_no_assignment": 3,
                        "race_url_assignment": 3,
                        "speed_data_url_assignment": 3,
                        "race_url_construct": 2,
                        "speed_data_construct": 2,
                        "meeting_level_derivation": 1,
                    }.get(name, 1)
                    near_target = "YES" if TARGET_NAME in text else "NO"
                    logic_rows.append({
                        "file": file_key,
                        "line_no": line_no,
                        "logic_type": logic_type,
                        "evidence": name,
                        "line": line.strip()[:1200],
                        "near_target": near_target,
                        "score": score,
                    })
                    file_metrics[file_key][name] += 1
                    if name == "write_operation" and (TARGET_NAME in line or any(re.search(r"\b" + re.escape(var) + r"\b", line) for var in target_vars)):
                        logic_rows.append({
                            "file": file_key,
                            "line_no": line_no,
                            "logic_type": "TARGET_WRITE_OPERATION",
                            "evidence": "target literal or target output variable written",
                            "line": line.strip()[:1200],
                            "near_target": "YES",
                            "score": 25,
                        })
                        file_metrics[file_key]["target_write_hits"] += 1
                        excerpt_hits[file_key].append((line_no, "TARGET_WRITE_OPERATION", line_window(lines, line_no)))
                    if name in {"fixed_range_1_13", "fixed_race_range", "race_url_construct", "speed_data_construct", "write_operation", "race_no_assignment", "race_url_assignment", "speed_data_url_assignment"}:
                        excerpt_hits[file_key].append((line_no, name, line_window(lines, line_no)))
        if path.suffix.lower() == ".py":
            ast_rows = extract_python_ast(path, text, lines)
            for row in ast_rows:
                row["near_target"] = row.get("near_target") or ("YES" if TARGET_NAME in text else "NO")
                logic_rows.append(row)
                file_metrics[file_key][row["logic_type"]] += 1
                if row["logic_type"] in {"AST_RANGE_LOOP", "AST_TARGET_WRITE_CALL", "AST_ASSIGN_RACE_NO", "AST_ASSIGN_RACE_URL", "AST_ASSIGN_SPEED_DATA_URL"}:
                    line_no = int(row.get("line_no") or 0)
                    if line_no:
                        excerpt_hits[file_key].append((line_no, row["logic_type"], line_window(lines, line_no)))

    candidate_rows: list[dict[str, Any]] = []
    for file_key, metrics in file_metrics.items():
        target_refs = metrics.get("target_references", 0)
        write_hits = metrics.get("write_operation", 0) + metrics.get("AST_TARGET_WRITE_CALL", 0)
        target_write_hits = metrics.get("target_write_hits", 0) + metrics.get("AST_TARGET_WRITE_CALL", 0)
        fixed_hits = metrics.get("fixed_range_1_13", 0) + metrics.get("fixed_race_range", 0) + metrics.get("AST_RANGE_LOOP", 0)
        race_no_hits = metrics.get("race_no_assignment", 0) + metrics.get("AST_ASSIGN_RACE_NO", 0) + metrics.get("AST_DICT_KEY_RACE_NO", 0)
        race_url_hits = metrics.get("race_url_assignment", 0) + metrics.get("AST_ASSIGN_RACE_URL", 0) + metrics.get("AST_DICT_KEY_RACE_URL", 0)
        speed_url_hits = metrics.get("speed_data_url_assignment", 0) + metrics.get("AST_ASSIGN_SPEED_DATA_URL", 0) + metrics.get("AST_DICT_KEY_SPEED_DATA_URL", 0)
        constructs_race = metrics.get("race_url_construct", 0)
        constructs_speed = metrics.get("speed_data_construct", 0)
        meeting_hits = metrics.get("meeting_level_derivation", 0)
        score = (
            target_refs * 12 + target_write_hits * 80 + write_hits * 8 + fixed_hits * 8 + race_no_hits * 4 +
            race_url_hits * 4 + speed_url_hits * 4 + constructs_race * 2 + constructs_speed * 2 + meeting_hits
        )
        is_source_script = file_key.startswith("scripts/") and file_key.endswith(".py")
        assessment = "LOW_SIGNAL"
        if is_source_script and target_refs and target_write_hits and (fixed_hits or race_no_hits) and (race_url_hits or speed_url_hits or constructs_race or constructs_speed):
            assessment = "LIKELY_PRODUCER"
        elif is_source_script and target_refs and target_write_hits:
            assessment = "PRODUCER_CANDIDATE"
        elif is_source_script and target_refs:
            assessment = "SOURCE_REFERENCE_ONLY"
        elif target_refs:
            assessment = "ARTIFACT_OR_DOC_REFERENCE"
        candidate_rows.append({
            "file": file_key,
            "producer_assessment": assessment,
            "score": score,
            "target_references": target_refs,
            "write_hits": write_hits,
            "target_write_hits": target_write_hits,
            "fixed_range_hits": fixed_hits,
            "race_no_hits": race_no_hits,
            "race_url_hits": race_url_hits,
            "speed_data_url_hits": speed_url_hits,
            "constructs_race_url_hits": constructs_race,
            "constructs_speed_data_hits": constructs_speed,
            "meeting_level_derivation_hits": meeting_hits,
            "input_source_mentions": " | ".join(sorted(file_inputs.get(file_key, set()))[:80]),
        })
    candidate_rows.sort(key=lambda r: (0 if str(r.get("producer_assessment")) == "LIKELY_PRODUCER" else 1 if str(r.get("producer_assessment")) == "PRODUCER_CANDIDATE" else 2, -int(r["score"]), r["file"]))
    for idx, row in enumerate(candidate_rows, start=1):
        row["producer_rank"] = idx

    exact_producer = ""
    producer_decision = "PRODUCER_NOT_UNIQUELY_IDENTIFIED"
    if candidate_rows:
        top = candidate_rows[0]
        if top["producer_assessment"] == "LIKELY_PRODUCER":
            exact_producer = str(top["file"])
            producer_decision = "PRODUCER_IDENTIFIED"
        elif top["producer_assessment"] == "PRODUCER_CANDIDATE":
            exact_producer = str(top["file"])
            producer_decision = "PRODUCER_CANDIDATE_IDENTIFIED_REQUIRES_REVIEW"

    target_stats = canonical_group_stats()
    producer_logic = [r for r in logic_rows if exact_producer and r.get("file") == exact_producer]
    fixed_lines = [r for r in producer_logic if "RANGE" in r.get("logic_type", "") or r.get("logic_type") in {"FIXED_RANGE_1_13", "FIXED_RACE_RANGE"}]
    race_url_lines = [r for r in producer_logic if "RACE_URL" in r.get("logic_type", "") or r.get("logic_type") == "RACE_URL_CONSTRUCT"]
    speed_url_lines = [r for r in producer_logic if "SPEED" in r.get("logic_type", "")]
    write_lines = [r for r in producer_logic if r.get("logic_type") == "TARGET_WRITE_OPERATION" or r.get("logic_type") == "AST_TARGET_WRITE_CALL"]

    audit_rows = [
        {"check": "repository_scanned", "status": "PASS", "count": scanned_files, "detail": "Text files scanned excluding generated/cache directories."},
        {"check": "target_calendar_file_exists", "status": "PASS" if target_stats.get("target_exists") else "FAIL", "count": int(bool(target_stats.get("target_exists"))), "detail": str(ROOT / "public" / "data" / TARGET_NAME)},
        {"check": "target_reference_rows_found", "status": "PASS" if reference_rows else "FAIL", "count": len(reference_rows), "detail": "References to edgeiq_racingcom_calendar_discovery_v1.csv."},
        {"check": "producer_identified", "status": "PASS" if producer_decision == "PRODUCER_IDENTIFIED" else "PARTIAL", "count": 1 if exact_producer else 0, "detail": exact_producer or producer_decision},
        {"check": "fixed_race_expansion_code_found", "status": "PASS" if fixed_lines else "FAIL", "count": len(fixed_lines), "detail": "; ".join(f"{r['file']}:{r['line_no']}" for r in fixed_lines[:12])},
        {"check": "race_url_construction_found", "status": "PASS" if race_url_lines else "FAIL", "count": len(race_url_lines), "detail": "; ".join(f"{r['file']}:{r['line_no']}" for r in race_url_lines[:12])},
        {"check": "speed_data_url_construction_found", "status": "PASS" if speed_url_lines else "FAIL", "count": len(speed_url_lines), "detail": "; ".join(f"{r['file']}:{r['line_no']}" for r in speed_url_lines[:12])},
        {"check": "target_write_operation_found", "status": "PASS" if write_lines else "FAIL", "count": len(write_lines), "detail": "; ".join(f"{r['file']}:{r['line_no']}" for r in write_lines[:12])},
        {"check": "calendar_contains_race_level_fields", "status": "PASS" if all(c in target_stats.get("target_columns", []) for c in ["race_no", "race_url", "speed_data_url"]) else "FAIL", "count": len(target_stats.get("target_columns", [])), "detail": ", ".join(target_stats.get("target_columns", []))},
        {"check": "calendar_exact_1_12_groups", "status": "FAIL" if target_stats.get("groups_exact_1_12", 0) else "PASS", "count": target_stats.get("groups_exact_1_12", 0), "detail": "Exact 1-12 race groups in contaminated target file."},
    ]

    schedule_source_mode = "UNKNOWN"
    if fixed_lines and (race_url_lines or speed_url_lines):
        schedule_source_mode = "FABRICATED_FROM_FIXED_LOOP"
    elif race_url_lines or speed_url_lines:
        schedule_source_mode = "URLS_CONSTRUCTED_OR_ASSIGNED_REQUIRES_REVIEW"
    elif exact_producer:
        schedule_source_mode = "PRODUCER_FOUND_NO_FIXED_LOOP_IN_TOP_FILE"

    write_csv(REFERENCE_LEDGER, reference_rows, ["file", "line_no", "pattern", "role", "line"])
    write_csv(CANDIDATES, candidate_rows, [
        "producer_rank", "file", "producer_assessment", "score", "target_references", "write_hits",
        "fixed_range_hits", "target_write_hits", "race_no_hits", "race_url_hits", "speed_data_url_hits",
        "constructs_race_url_hits", "constructs_speed_data_hits", "meeting_level_derivation_hits", "input_source_mentions",
    ])
    write_csv(LOGIC_LEDGER, logic_rows, ["file", "line_no", "logic_type", "evidence", "line", "near_target", "score"])
    write_csv(AUDIT, audit_rows, ["check", "status", "count", "detail"])

    with EXCERPTS.open("w", encoding="utf-8") as fh:
        fh.write("EDGEiQ Racing.com Calendar Discovery Producer Excerpts V1\n")
        fh.write(f"Generated UTC: {NOW}\n")
        fh.write(f"Decision: {producer_decision}\n")
        fh.write(f"Exact producer: {exact_producer or 'NOT IDENTIFIED'}\n\n")
        priority_files = []
        if exact_producer:
            priority_files.append(exact_producer)
        priority_files.extend([r["file"] for r in candidate_rows[:10] if r["file"] not in priority_files])
        for file_key in priority_files:
            hits = excerpt_hits.get(file_key, [])[:20]
            if not hits:
                continue
            fh.write("=" * 100 + "\n")
            fh.write(f"FILE: {file_key}\n")
            fh.write("=" * 100 + "\n")
            seen = set()
            for line_no, kind, window in hits:
                dedupe = (line_no, kind)
                if dedupe in seen:
                    continue
                seen.add(dedupe)
                fh.write(f"\n--- {kind} at line {line_no} ---\n")
                fh.write(window)
                fh.write("\n")

    summary = {
        "generated_utc": NOW,
        "decision": producer_decision,
        "exact_producer": exact_producer,
        "schedule_source_mode": schedule_source_mode,
        "repository_root": str(ROOT),
        "files_scanned": scanned_files,
        "reference_rows": len(reference_rows),
        "logic_rows": len(logic_rows),
        "candidate_rows": len(candidate_rows),
        "target_stats": target_stats,
        "top_candidates": candidate_rows[:12],
        "producer_fixed_race_expansion_lines": fixed_lines[:20],
        "producer_race_url_construction_lines": race_url_lines[:20],
        "producer_speed_data_url_construction_lines": speed_url_lines[:20],
        "producer_write_lines": write_lines[:20],
        "input_sources": sorted(file_inputs.get(exact_producer, set())) if exact_producer else [],
        "artifacts": [str(p.relative_to(ROOT)) for p in [REFERENCE_LEDGER, CANDIDATES, LOGIC_LEDGER, EXCERPTS, AUDIT, SUMMARY_JSON, REPORT_MD]],
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")

    md = []
    md.append("# EDGEiQ Racing.com Calendar Discovery Producer Trace V1")
    md.append("")
    md.append(f"Generated UTC: `{NOW}`")
    md.append("")
    md.append("## Decision")
    md.append("")
    md.append(f"- Decision: `{producer_decision}`")
    md.append(f"- Exact producer: `{exact_producer or 'NOT IDENTIFIED'}`")
    md.append(f"- Race schedule source mode: `{schedule_source_mode}`")
    md.append("")
    md.append("## Target Artifact Facts")
    md.append("")
    md.append(f"- Target file exists: `{target_stats.get('target_exists')}`")
    md.append(f"- Target rows: `{target_stats.get('target_rows')}`")
    md.append(f"- Target columns: `{', '.join(target_stats.get('target_columns', []))}`")
    md.append(f"- Exact 1-12 meeting groups: `{target_stats.get('groups_exact_1_12')}`")
    md.append(f"- Future rows: `{target_stats.get('future_rows')}`")
    md.append(f"- Future exact 1-12 groups: `{target_stats.get('future_exact_1_12_groups')}`")
    md.append(f"- SHA-256: `{target_stats.get('sha256')}`")
    md.append("")
    md.append("## Exact Evidence Lines")
    md.append("")
    md.append("### Fixed Race Expansion")
    if fixed_lines:
        for row in fixed_lines[:20]:
            md.append(f"- `{row['file']}:{row['line_no']}` - `{row['line']}`")
    else:
        md.append("- None found in top producer candidate.")
    md.append("")
    md.append("### Race URL Construction")
    if race_url_lines:
        for row in race_url_lines[:20]:
            md.append(f"- `{row['file']}:{row['line_no']}` - `{row['line']}`")
    else:
        md.append("- None found in top producer candidate.")
    md.append("")
    md.append("### Speed Data URL Construction")
    if speed_url_lines:
        for row in speed_url_lines[:20]:
            md.append(f"- `{row['file']}:{row['line_no']}` - `{row['line']}`")
    else:
        md.append("- None found in top producer candidate.")
    md.append("")
    md.append("### Target Write Operation")
    if write_lines:
        for row in write_lines[:20]:
            md.append(f"- `{row['file']}:{row['line_no']}` - `{row['line']}`")
    else:
        md.append("- None found in top producer candidate.")
    md.append("")
    md.append("## Upstream Inputs Mentioned By Producer")
    md.append("")
    inputs = sorted(file_inputs.get(exact_producer, set())) if exact_producer else []
    if inputs:
        for item in inputs:
            md.append(f"- `{item}`")
    else:
        md.append("- No input source literals identified by this trace.")
    md.append("")
    md.append("## Top Producer Candidates")
    md.append("")
    md.append("| Rank | File | Assessment | Score | Target refs | Write hits | Fixed ranges | Race URL hits | Speed URL hits |")
    md.append("|---:|---|---|---:|---:|---:|---:|---:|---:|")
    for row in candidate_rows[:12]:
        md.append(f"| {row['producer_rank']} | `{row['file']}` | `{row['producer_assessment']}` | {row['score']} | {row['target_references']} | {row['write_hits']} | {row['fixed_range_hits']} | {row['race_url_hits'] + row['constructs_race_url_hits']} | {row['speed_data_url_hits'] + row['constructs_speed_data_hits']} |")
    md.append("")
    md.append("## Finding")
    md.append("")
    if schedule_source_mode == "FABRICATED_FROM_FIXED_LOOP":
        md.append("The calendar discovery producer fabricates race-level rows from a fixed race-number loop and constructs race/speed-data URLs rather than parsing a verified race schedule from observed source content.")
    else:
        md.append("The trace did not conclusively prove a fixed-loop producer in the top candidate; inspect the candidate and logic ledgers before modifying discovery logic.")
    md.append("")
    md.append("## Artifacts")
    md.append("")
    for artifact in summary["artifacts"]:
        md.append(f"- `{artifact}`")
    md.append("")
    REPORT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps({
        "decision": producer_decision,
        "exact_producer": exact_producer,
        "schedule_source_mode": schedule_source_mode,
        "files_scanned": scanned_files,
        "target_rows": target_stats.get("target_rows"),
        "artifacts": summary["artifacts"],
    }, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
