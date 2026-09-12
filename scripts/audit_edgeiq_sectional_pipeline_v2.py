from __future__ import annotations

import csv
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_sectional_pipeline_v2_audit.csv"
SUMMARY = DATA / "edgeiq_sectional_pipeline_v2_summary.csv"
FAILURES = DATA / "edgeiq_sectional_split_failure_reasons_v2.csv"
PATTERNS = ("sectional", "racingcom", "racing_com", "split", "tempo")
SKIP_PARTS = {"node_modules", "dist", ".git", "__pycache__"}
SKIP_FILES = {
    OUT.name.lower(), SUMMARY.name.lower(), FAILURES.name.lower(),
    "edgeiq_sectional_pipeline_audit.csv", "edgeiq_sectional_pipeline_summary.csv",
}

MISSING = {"", "-", "nan", "none", "null", "undefined", "n/a"}
LAST_ALIASES = {
    200: ("last200", "last_200", "l200", "last 200"),
    400: ("last400", "last_400", "l400", "last 400"),
    600: ("last600", "last_600", "l600", "last 600"),
}
RANGES = {200: (8.0, 22.0), 400: (16.0, 45.0), 600: (24.0, 70.0)}


def clean(v: object) -> str:
    s = str(v or "").strip()
    return "" if s.lower() in MISSING else s


def norm_name(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def parse_time(v: object) -> tuple[float | None, str]:
    raw = clean(v)
    if not raw:
        return None, "BLANK"
    if not re.search(r"\d", raw):
        return None, "TEXT"
    if ":" in raw:
        if not re.fullmatch(r"\d{1,3}:\d{1,2}(?:\.\d+)?", raw):
            return None, "MALFORMED_TIME"
        a, b = raw.split(":", 1)
        try:
            return float(a) * 60.0 + float(b), "MMSS_FORMAT"
        except ValueError:
            return None, "MALFORMED_TIME"
    stripped = re.sub(r"[^0-9.\-]", "", raw)
    try:
        x = float(stripped)
    except ValueError:
        return None, "TEXT"
    if x < 0:
        return x, "NEGATIVE"
    if x == 0:
        return x, "ZERO"
    return x, "SECONDS_FORMAT"


def find_col(fields: list[str], aliases: tuple[str, ...]) -> str:
    lookup = {norm_name(f): f for f in fields}
    for a in aliases:
        k = norm_name(a)
        if k in lookup:
            return lookup[k]
    return ""


def split_map(fields: list[str]) -> dict[int, str]:
    return {d: find_col(fields, a) for d, a in LAST_ALIASES.items() if find_col(fields, a)}


def generic_split_cols(fields: list[str]) -> list[str]:
    out = []
    for f in fields:
        n = f.lower()
        if any(x in n for x in ("rating", "confidence", "grade", "source", "comment", "note", "index", "score")):
            continue
        if "split" in n or re.fullmatch(r"sectional_?\d{3}", n):
            out.append(f)
    return out


def classify_named(distance: int, value: object) -> str:
    x, fmt = parse_time(value)
    if x is None:
        return fmt
    if fmt in {"NEGATIVE", "ZERO"}:
        return fmt
    lo, hi = RANGES[distance]
    if x < lo:
        return "OUT_OF_RANGE_LOW"
    if x > hi:
        return "OUT_OF_RANGE_HIGH"
    return "VALID_" + fmt


def candidate_csvs() -> list[Path]:
    out = []
    for p in ROOT.rglob("*.csv"):
        if p.name.lower() in SKIP_FILES:
            continue
        if any(part.lower() in SKIP_PARTS for part in p.parts):
            continue
        if any(k in p.name.lower() for k in PATTERNS):
            out.append(p)
    return sorted(out, key=lambda p: str(p).lower())


def audit_file(path: Path) -> tuple[dict[str, object], Counter]:
    counts = Counter()
    rows = 0
    named_rows = 0
    valid_rows = 0
    generic_only_rows = 0
    fields: list[str] = []
    error = ""
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as h:
            r = csv.DictReader(h)
            fields = list(r.fieldnames or [])
            named = split_map(fields)
            generic = generic_split_cols(fields)
            for row in r:
                rows += 1
                has_named = False
                row_valid = False
                for d, col in named.items():
                    raw = clean(row.get(col))
                    if not raw:
                        counts[f"LAST{d}_BLANK"] += 1
                        continue
                    has_named = True
                    reason = classify_named(d, raw)
                    counts[f"LAST{d}_{reason}"] += 1
                    if reason.startswith("VALID_"):
                        row_valid = True
                if has_named:
                    named_rows += 1
                elif generic and any(clean(row.get(c)) for c in generic):
                    generic_only_rows += 1
                    counts["GENERIC_SPLIT_ONLY_ROW"] += 1
                if row_valid:
                    valid_rows += 1
    except Exception as exc:
        error = str(exc)
        counts["FILE_READ_ERROR"] += 1

    layout = "NAMED_LAST_SPLITS" if split_map(fields) else "GENERIC_SPLITS" if generic_split_cols(fields) else "NO_SECTIONAL_SCHEMA"
    status = "FAIL" if error else "OK" if valid_rows else "WARN"
    return ({
        "source_file": str(path.relative_to(ROOT)),
        "rows": rows,
        "layout": layout,
        "named_split_rows": named_rows,
        "valid_named_split_rows": valid_rows,
        "generic_only_rows": generic_only_rows,
        "field_count": len(fields),
        "last200_col": split_map(fields).get(200, ""),
        "last400_col": split_map(fields).get(400, ""),
        "last600_col": split_map(fields).get(600, ""),
        "error": error,
        "status": status,
    }, counts)


def write(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    tmp.replace(path)


def main() -> None:
    audit_rows = []
    total = Counter()
    for i, path in enumerate(candidate_csvs(), 1):
        row, counts = audit_file(path)
        audit_rows.append(row)
        total.update(counts)
        if i % 50 == 0:
            print(f"AUDITED {i} files")

    write(OUT, audit_rows, ["source_file","rows","layout","named_split_rows","valid_named_split_rows","generic_only_rows","field_count","last200_col","last400_col","last600_col","error","status"])
    failure_rows = [{"reason": k, "count": v} for k, v in total.most_common()]
    write(FAILURES, failure_rows, ["reason","count"])

    metrics = [
        {"metric":"run_timestamp_utc","value":datetime.now(timezone.utc).isoformat()},
        {"metric":"files","value":len(audit_rows)},
        {"metric":"rows","value":sum(int(r["rows"]) for r in audit_rows)},
        {"metric":"named_split_rows","value":sum(int(r["named_split_rows"]) for r in audit_rows)},
        {"metric":"valid_named_split_rows","value":sum(int(r["valid_named_split_rows"]) for r in audit_rows)},
        {"metric":"generic_only_rows","value":sum(int(r["generic_only_rows"]) for r in audit_rows)},
        {"metric":"files_with_valid_named_splits","value":sum(1 for r in audit_rows if int(r["valid_named_split_rows"]) > 0)},
        {"metric":"failed_files","value":sum(1 for r in audit_rows if r["status"] == "FAIL")},
    ]
    write(SUMMARY, metrics, ["metric","value"])
    print("="*88)
    print("EDGEIQ SECTIONAL PIPELINE AUDIT V2")
    print("="*88)
    for m in metrics:
        print(f"{m['metric']}: {m['value']}")
    print("AUDIT:", OUT)
    print("FAILURES:", FAILURES)

if __name__ == "__main__":
    main()
