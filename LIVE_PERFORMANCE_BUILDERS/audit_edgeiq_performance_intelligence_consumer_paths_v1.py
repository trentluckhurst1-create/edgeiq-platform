from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
OUT = DOCS / "edgeiq_performance_intelligence_consumer_paths_v1.csv"
SUMMARY = DOCS / "edgeiq_performance_intelligence_consumer_paths_summary_v1.json"
REPORT = DOCS / "edgeiq_performance_intelligence_consumer_paths_report_v1.md"

TERMS = [
    "edgeiq_standard_time_fact_v1.csv",
    "edgeiq_lengths_versus_standard_fact_v1.csv",
    "edgeiq_racingcom_performance_warehouse_v2.csv",
    "edgeiq_racingcom_performance_warehouse_v2_RUNNER_CANDIDATE.csv",
    "edgeiq_racingcom_performance_warehouse_v2_GRAPHQL_CANDIDATE.csv",
    "edgeiq_epi",
]


def scan() -> list[dict[str, str]]:
    rows = []
    for base in [ROOT / "src", ROOT / "scripts", ROOT / "docs"]:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.suffix.lower() not in {".ts", ".tsx", ".js", ".jsx", ".py", ".md", ".json"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for term in TERMS:
                if term in text:
                    rel = str(path.relative_to(ROOT))
                    candidate = "YES" if "RUNNER_CANDIDATE" in term or "GRAPHQL_CANDIDATE" in term else "NO"
                    consumer_type = "UI" if rel.startswith("src") else ("SCRIPT" if rel.startswith("scripts") else "DOC")
                    rows.append({"file": rel, "term": term, "consumer_type": consumer_type, "candidate_or_research_path": candidate, "status": "REVIEW" if candidate == "YES" and consumer_type == "UI" else "OK"})
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = ["file", "term", "consumer_type", "candidate_or_research_path", "status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def main() -> int:
    rows = scan()
    ui_candidate_refs = [r for r in rows if r["consumer_type"] == "UI" and r["candidate_or_research_path"] == "YES"]
    required = {
        "production_warehouse": DATA / "edgeiq_racingcom_performance_warehouse_v2.csv",
        "standard_time": DATA / "edgeiq_standard_time_fact_v1.csv",
        "lengths_v_standard": DATA / "edgeiq_lengths_versus_standard_fact_v1.csv",
        "epi_manifest": DATA / "edgeiq_epi_warehouse_release_manifest_v1.json",
    }
    missing = [name for name, path in required.items() if not path.exists()]
    decision = "PERFORMANCE_INTELLIGENCE_CONSUMER_PATHS_PASS" if not ui_candidate_refs and not missing else "PERFORMANCE_INTELLIGENCE_CONSUMER_PATHS_REVIEW"
    write_csv(OUT, rows)
    summary = {
        "decision": decision,
        "consumer_references": len(rows),
        "ui_candidate_or_research_refs": len(ui_candidate_refs),
        "missing_required_outputs": missing,
        "standard_time_rows": count_rows(required["standard_time"]),
        "lengths_v_standard_rows": count_rows(required["lengths_v_standard"]),
        "react_calculates_benchmarks": "NO_EVIDENCE_FOUND",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    REPORT.write_text(f"# Performance Intelligence Consumer Paths V1\n\nDecision: `{decision}`\n\nUI candidate/research references: `{len(ui_candidate_refs)}`\nMissing required outputs: `{len(missing)}`\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if decision.endswith("_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
