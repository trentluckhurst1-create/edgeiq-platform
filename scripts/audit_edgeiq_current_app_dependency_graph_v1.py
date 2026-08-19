from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "engineering" / "EDGEIQ_CURRENT_APP_DEPENDENCY_GRAPH_20260715.md"
OUT_TXT = ROOT / "public" / "data" / "edgeiq_current_app_dependency_graph_v1_audit.txt"
OUT_JSON = ROOT / "public" / "data" / "edgeiq_current_app_dependency_graph_v1_audit.json"
MARKER = "EDGEIQ_CURRENT_APP_DEPENDENCY_GRAPH_V1_AUDIT_PASS"

REQUIRED_TERMS = [
    "EPI",
    "EDGEiQ Price",
    "early speed",
    "late speed",
    "suitability",
    "form momentum",
    "ERI",
    "market fluctuation",
    "map lane/order",
    "runner style",
    "historical EPI tiles",
    "runner insights",
    "scratchings",
    "barriers",
    "weights",
    "jockey",
    "trainer",
    "gear",
    "race results",
    "historical form",
    "recent form",
    "sectionals",
    "RaceFormGuideWorkspace.tsx",
    "MapWorkspace.tsx",
    "MarketWorkspace.tsx",
    "OverviewWorkspace.tsx",
    "InsightsWorkspace.tsx",
    "EpiWorkspaceWorkspace.tsx",
    "resultsFeed.ts",
    "edgeiq_form_guide_enriched_v2.json",
    "edgeiq_map_terminal_feed_v1.csv",
    "edgeiq_market_terminal_feed_v1.csv",
    "edgeiq_insights_terminal_feed_v1.csv",
    "edgeiq_epi_workspace_terminal_feed_v1.csv",
]


def main() -> None:
    failures: list[str] = []
    warnings: list[str] = []
    text = DOC_PATH.read_text(encoding="utf-8", errors="replace") if DOC_PATH.exists() else ""

    if not DOC_PATH.exists():
        failures.append(f"Missing dependency graph document: {DOC_PATH}")
    if len(text) < 5000:
        failures.append("Dependency graph document is unexpectedly small")

    lower = text.lower()
    for term in REQUIRED_TERMS:
        if term.lower() not in lower:
            failures.append(f"Missing required dependency term: {term}")

    if "React displays governed data only" in text:
        warnings.append("Document includes rule language rather than dependency evidence")

    status = "PASS" if not failures else "FAIL"
    payload = {
        "marker": MARKER if status == "PASS" else "EDGEIQ_CURRENT_APP_DEPENDENCY_GRAPH_V1_AUDIT_FAIL",
        "status": status,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "document": str(DOC_PATH),
        "checks": {
            "required_terms": len(REQUIRED_TERMS),
            "document_bytes": len(text.encode("utf-8")),
        },
        "failures": failures,
        "warnings": warnings,
    }

    OUT_TXT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        payload["marker"],
        f"status={status}",
        f"document={DOC_PATH}",
        f"required_terms={len(REQUIRED_TERMS)}",
        f"document_bytes={payload['checks']['document_bytes']}",
    ]
    if failures:
        lines.append("failures:")
        lines.extend(f"- {failure}" for failure in failures)
    if warnings:
        lines.append("warnings:")
        lines.extend(f"- {warning}" for warning in warnings)
    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("\n".join(lines))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
