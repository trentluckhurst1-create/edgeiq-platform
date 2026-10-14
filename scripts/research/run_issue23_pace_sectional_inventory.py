from pathlib import Path
import csv
import json
import os
import re

ROOTS = [
    Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH"),
    Path(r"C:\EDGEIQ_ISSUE23"),
    Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM"),
]
TERMS = re.compile(r"pace|section|split|speed|tempo|race.?shape|early|late|run.?style|position|600m|400m|200m|track.?condition", re.I)
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next"}
EXTS = {".csv", ".parquet", ".json", ".jsonl", ".py", ".md"}
MAX_SOURCE_BYTES = 2_000_000
MAX_PRINT = 150

print("ISSUE23 — PACE / SECTIONAL / RACE SHAPE HISTORICAL INVENTORY")
print("MODE=READ_ONLY; NO MODEL FIT; NO OUTCOME ROWS READ")
print("CSV=HEADER_ONLY; PARQUET=SCHEMA_ONLY; SOURCE=KEYWORD LINES ONLY")
print("2025_2026_OUTCOME_ROWS_READ=NO")
hits = []
counts = {"files_seen": 0, "csv_headers": 0, "parquet_schemas": 0, "source_matches": 0}
for root in ROOTS:
    if not root.exists():
        print(f"MISSING_ROOT={root}")
        continue
    for folder, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS]
        for filename in files:
            path = Path(folder) / filename
            ext = path.suffix.lower()
            if ext not in EXTS:
                continue
            counts["files_seen"] += 1
            name_hit = bool(TERMS.search(str(path)))
            try:
                size = path.stat().st_size
                if ext == ".csv":
                    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
                        cols = next(csv.reader(f), [])
                    counts["csv_headers"] += 1
                    matched = [c for c in cols if TERMS.search(c)]
                    if matched:
                        hits.append((str(path), "CSV_HEADER", size, ", ".join(matched[:35])))
                elif ext == ".parquet":
                    try:
                        import pyarrow.parquet as pq
                        cols = pq.read_schema(path).names
                        counts["parquet_schemas"] += 1
                        matched = [c for c in cols if TERMS.search(c)]
                        if matched:
                            hits.append((str(path), "PARQUET_SCHEMA", size, ", ".join(matched[:35])))
                    except ImportError:
                        if name_hit:
                            hits.append((str(path), "PARQUET_SCHEMA_UNAVAILABLE", size, "pyarrow missing"))
                elif ext in {".py", ".md"} and size <= MAX_SOURCE_BYTES:
                    with path.open("r", encoding="utf-8-sig", errors="replace") as f:
                        matched = []
                        for line_no, line in enumerate(f, 1):
                            if TERMS.search(line) and (TERMS.search(filename) or any(k in line.lower() for k in ("feature", "column", "sectional", "pace", "speed", "tempo", "race_shape"))):
                                matched.append(f"{line_no}:{line.strip()[:115]}")
                                if len(matched) == 4:
                                    break
                    if matched:
                        counts["source_matches"] += 1
                        hits.append((str(path), "SOURCE_REFERENCE", size, " | ".join(matched)))
            except (OSError, UnicodeError, StopIteration, csv.Error) as e:
                if name_hit:
                    hits.append((str(path), "READ_ERROR", size if 'size' in locals() else 0, str(e)[:100]))
hits.sort(key=lambda x: (0 if x[1] in {"CSV_HEADER", "PARQUET_SCHEMA"} else 1, 0 if "research" in x[0].lower() else 1, x[0]))
print("COUNTS=" + json.dumps(counts, sort_keys=True))
print(f"FEATURE_BEARING_FILES={len(hits)}")
for path, kind, size, detail in hits[:MAX_PRINT]:
    print(f"{kind} | {size} bytes | {path}\n  {detail}")
if len(hits) > MAX_PRINT:
    print(f"TRUNCATED={len(hits)-MAX_PRINT}; refine scope if needed")
print("NEXT=VERIFY_POINT_IN_TIME_LINEAGE_AND_YEAR_COVERAGE_BEFORE_ANY_EXPERIMENT")
