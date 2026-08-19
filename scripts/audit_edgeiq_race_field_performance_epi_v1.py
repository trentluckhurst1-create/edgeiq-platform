from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "full-product-implementation"
PUBLIC = ROOT / "public" / "data"

FILES = [
    ROOT / "src" / "edgeiq-os" / "race" / "RaceFileV3.tsx",
    ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx",
    ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceIntelligenceWorkspace.tsx",
    ROOT / "src" / "edgeiq-os" / "race" / "components" / "FieldWorkspace.tsx",
    ROOT / "src" / "edgeiq-os" / "race" / "components" / "PerformanceWorkspace.tsx",
    ROOT / "src" / "edgeiq-os" / "race" / "components" / "EpiWorkspaceWorkspace.tsx",
    ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css",
]

def text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""

def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else ["check", "status", "detail"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

source = "\n".join(text(path) for path in FILES)

checks = [
    {
        "check": "RACE route maps to RACE workspace tab",
        "status": "PASS" if 'race: "RACE"' in text(ROOT / "src" / "edgeiq-os" / "race" / "RaceFileV3.tsx") else "FAIL",
        "detail": "RaceFileV3 global route mapping",
    },
    {
        "check": "Approved race runner board labels present",
        "status": "PASS" if all(label in source for label in ["EPI SPD", "EDGEiQ", "Runner Board", "What Matters Today"]) else "FAIL",
        "detail": "RACE workspace labels",
    },
    {
        "check": "Approved field labels present",
        "status": "PASS" if all(label in text(ROOT / "src" / "edgeiq-os" / "race" / "components" / "FieldWorkspace.tsx") for label in ["EDGEiQ", "LAST FIVE STARTS", "STATUS"]) else "FAIL",
        "detail": "FIELD workspace labels",
    },
    {
        "check": "Performance and EPI components differ",
        "status": "PASS" if "Performance Heat Map" in source and "EPI Matrix" in source else "FAIL",
        "detail": "PERFORMANCE is not an EPI ranking clone",
    },
    {
        "check": "No visible Confidence label in tranche workspaces",
        "status": "PASS" if not re.search(r">\s*Confidence\s*<|[\"']Confidence[\"']", source) else "FAIL",
        "detail": "Visible label scan",
    },
    {
        "check": "No product-facing demo/mock/sample runner rows",
        "status": "PASS" if not re.search(r"demo runner|sample runner|mock runner|synthetic runner", source, re.I) else "FAIL",
        "detail": "Mock data language scan",
    },
    {
        "check": "No coloured saddlecloth number background classes added",
        "status": "PASS" if "saddlecloth-number" not in source and "runner-number-badge" not in source else "FAIL",
        "detail": "Saddlecloth style scan",
    },
]

write_csv(PUBLIC / "edgeiq_workspace_route_audit_v1.csv", checks[:1])
write_csv(PUBLIC / "edgeiq_mock_data_audit_v1.csv", [checks[5]])
write_csv(PUBLIC / "edgeiq_saddlecloth_style_audit_v1.csv", [checks[6]])
write_csv(PUBLIC / "edgeiq_governed_metric_audit_v1.csv", checks[1:4])
write_csv(PUBLIC / "edgeiq_ui_language_audit_v1.csv", [checks[4]])
write_csv(DOC / "edgeiq_race_field_performance_epi_audit_v1.csv", checks)

md = ["# EDGEIQ Race/Field/Performance/EPI Audit V1", ""]
for row in checks:
    md.append(f"- {row['status']}: {row['check']} - {row['detail']}")
(DOC / "EDGEIQ_RACE_FIELD_PERFORMANCE_EPI_AUDIT_V1.md").write_text("\n".join(md) + "\n", encoding="utf-8")

failed = [row for row in checks if row["status"] != "PASS"]
if failed:
    for row in failed:
        print(f"FAIL: {row['check']} :: {row['detail']}")
    raise SystemExit(1)

print("EDGEIQ_RACE_FIELD_PERFORMANCE_EPI_AUDIT_PASS")
