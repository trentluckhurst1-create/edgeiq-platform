from __future__ import annotations

import csv
import hashlib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
INFILE = DATA / "edgeiq_sectional_identity_recovery_v3_files.csv"
OUT = DATA / "edgeiq_sectional_source_roles_v3.csv"
SUMMARY = DATA / "edgeiq_sectional_source_roles_v3_summary.csv"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def classify(rel: str) -> str:
    s = rel.replace("\\", "/").lower()
    if s.startswith("checkpoints/"):
        return "CHECKPOINT_COPY"
    if "/public/data/" in "/" + s or s.startswith("public/data/"):
        return "LIVE_DATA"
    return "OTHER"


def main() -> None:
    if not INFILE.exists():
        raise SystemExit(f"Missing prerequisite: {INFILE}")
    rows = []
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    with INFILE.open("r", newline="", encoding="utf-8-sig") as h:
        for r in csv.DictReader(h):
            rel = r["source_file"]
            p = ROOT / rel
            digest = sha256(p) if p.exists() else ""
            role = classify(rel)
            row = dict(r)
            row["source_role"] = role
            row["sha256"] = digest
            rows.append(row)
            if digest:
                groups[digest].append(row)

    for digest, members in groups.items():
        live = [m for m in members if m["source_role"] == "LIVE_DATA"]
        canonical = live[0]["source_file"] if live else members[0]["source_file"]
        for m in members:
            m["duplicate_group_size"] = str(len(members))
            m["canonical_source_file"] = canonical
            m["duplicate_disposition"] = "PRIMARY" if m["source_file"] == canonical else "DUPLICATE_COPY"

    fields = list(rows[0].keys()) if rows else []
    with OUT.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=fields)
        w.writeheader(); w.writerows(rows)

    total = sum(int(r.get("target_rows") or 0) for r in rows)
    live_total = sum(int(r.get("target_rows") or 0) for r in rows if r.get("source_role") == "LIVE_DATA")
    primary_total = sum(int(r.get("target_rows") or 0) for r in rows if r.get("duplicate_disposition") == "PRIMARY")
    dup_total = sum(int(r.get("target_rows") or 0) for r in rows if r.get("duplicate_disposition") == "DUPLICATE_COPY")
    unique_hashes = len(groups)
    summary = [
        ("input_quarantine_rows", total),
        ("source_files", len(rows)),
        ("unique_content_hashes", unique_hashes),
        ("live_data_rows", live_total),
        ("primary_rows_after_duplicate_collapse", primary_total),
        ("duplicate_copy_rows", dup_total),
    ]
    with SUMMARY.open("w", newline="", encoding="utf-8") as h:
        w = csv.writer(h); w.writerow(["metric","value"]); w.writerows(summary)

    print("="*90)
    print("EDGEIQ SECTIONAL SOURCE ROLE AUDIT V3")
    print("="*90)
    for k,v in summary: print(f"{k}: {v}")
    print("OUT:", OUT)
    print("SUMMARY:", SUMMARY)


if __name__ == "__main__":
    main()
