from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT_DIR = ROOT / "docs" / "full-product-implementation"
PUBLIC_OUT = ROOT / "public" / "data"


APPROVED_WORKSPACES = [
    "HOME",
    "MEETINGS",
    "RACE",
    "FIELD",
    "FORM GUIDE",
    "PERFORMANCE",
    "EPI",
    "MAP",
    "MARKET",
    "OVERVIEW",
    "INSIGHTS",
    "RESULTS",
    "LAB",
    "COMPARE",
    "REVIEW",
    "SETTINGS",
]

WORKSPACE_COMPONENT_HINTS = {
    "HOME": ["EdgeiqOsHome", "HomeWorkspace"],
    "MEETINGS": ["MeetingsWorkspace"],
    "RACE": ["RaceWorkspace"],
    "FIELD": ["FieldWorkspace"],
    "FORM GUIDE": ["RaceFormGuideWorkspace", "FormGuideWorkspace"],
    "PERFORMANCE": ["PerformanceWorkspace", "EpiWorkspaceWorkspace"],
    "EPI": ["EpiWorkspaceWorkspace"],
    "MAP": ["MapWorkspace"],
    "MARKET": ["MarketWorkspace"],
    "OVERVIEW": ["OverviewWorkspace"],
    "INSIGHTS": ["InsightsWorkspace"],
    "RESULTS": ["ResultsWorkspace", "GlobalResultsWorkspace", "MeetingResultsWorkspace"],
    "LAB": ["LabWorkspace"],
    "COMPARE": ["CompareWorkspace"],
    "REVIEW": ["ReviewWorkspace", "ResultsWorkspace"],
    "SETTINGS": ["SettingsWorkspace"],
}

GOVERNED_METRIC_TERMS = [
    "EPI",
    "ERI",
    "Suitability",
    "Form Momentum",
    "Early Speed",
    "Late Speed",
    "EDGEiQ Price",
    "Race Shape",
    "EPF",
]

PROBLEM_LANGUAGE = [
    "confidence",
    "tip",
    "selection",
    "bet",
    "back",
    "lay",
    "AI",
    "placeholder",
    "fake",
    "mock",
    "demo",
    "star",
]

SADDLECLOTH_STYLE_PATTERNS = [
    "saddlecloth",
    "number chip",
    "runner-chip",
    "is-colour",
    "background-color",
    "border-radius: 999",
]


@dataclass
class SourceFile:
    path: Path
    text: str


def iter_source_files() -> list[SourceFile]:
    files: list[SourceFile] = []
    for path in SRC.rglob("*"):
        if path.suffix.lower() not in {".ts", ".tsx", ".css"}:
            continue
        if "CHECKPOINT" in path.name or path.name.endswith(".map"):
            continue
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        files.append(SourceFile(path, text))
    return files


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def component_exists(files: list[SourceFile], hints: list[str]) -> tuple[bool, list[str]]:
    hits: list[str] = []
    for source in files:
        for hint in hints:
            if hint in source.text or source.path.stem == hint:
                hits.append(rel(source.path))
                break
    return bool(hits), sorted(set(hits))


def find_nav_labels(files: list[SourceFile]) -> set[str]:
    labels: set[str] = set()
    for source in files:
        if source.path.name not in {"AppNavigation.tsx", "RaceWorkspace.tsx", "MeetingWorkspace.tsx"}:
            continue
        for match in re.finditer(r'label:\s*"([^"]+)"|"([A-Z][A-Z ]{2,})"', source.text):
            labels.add((match.group(1) or match.group(2)).strip().upper())
    return labels


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_workspace_route_audit(files: list[SourceFile]) -> list[dict[str, object]]:
    nav_labels = find_nav_labels(files)
    rows: list[dict[str, object]] = []
    for workspace in APPROVED_WORKSPACES:
        exists, component_paths = component_exists(files, WORKSPACE_COMPONENT_HINTS[workspace])
        nav_present = workspace.upper() in nav_labels or (
            workspace == "FORM GUIDE" and "FORM GUIDE" in nav_labels
        )
        status = "PASS" if exists and nav_present else "WARN" if exists else "FAIL"
        rows.append(
            {
                "workspace": workspace,
                "nav_present": "YES" if nav_present else "NO",
                "component_present": "YES" if exists else "NO",
                "component_paths": ";".join(component_paths[:8]),
                "status": status,
            }
        )
    return rows


def build_mock_data_audit(files: list[SourceFile]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    horse_like = re.compile(r"\b(VERDAD|CEOLWULF|KIRWAN|SONOFTHEBEAST|RUBARE|CAITLIN|FLEMINGTON R5)\b", re.I)
    for source in files:
        if "CHECKPOINT" in source.path.name:
            continue
        for i, line in enumerate(source.text.splitlines(), start=1):
            lowered = line.lower()
            if horse_like.search(line) or any(term in lowered for term in ["mock", "demo", "placeholder", "hardcoded"]):
                rows.append(
                    {
                        "file": rel(source.path),
                        "line": i,
                        "risk": "HIGH" if horse_like.search(line) else "MEDIUM",
                        "snippet": line.strip()[:260],
                    }
                )
    return rows


def build_saddlecloth_audit(files: list[SourceFile]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for source in files:
        if source.path.suffix.lower() not in {".tsx", ".css"}:
            continue
        for i, line in enumerate(source.text.splitlines(), start=1):
            lowered = line.lower()
            if "saddle" in lowered or "silk" in lowered or "number-chip" in lowered:
                context = source.text.splitlines()[max(0, i - 4): i + 3]
                joined = " ".join(context).lower()
                risk = "HIGH" if any(pattern in joined for pattern in ["background", "border-radius: 999", "chip"]) else "REVIEW"
                rows.append(
                    {
                        "file": rel(source.path),
                        "line": i,
                        "risk": risk,
                        "snippet": line.strip()[:260],
                    }
                )
    return rows


def build_governed_metric_audit(files: list[SourceFile]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for term in GOVERNED_METRIC_TERMS:
        hits: list[str] = []
        service_hits: list[str] = []
        for source in files:
            if term.lower().replace("edgeiq ", "") in source.text.lower():
                hits.append(rel(source.path))
                if "/services/" in rel(source.path) or source.path.name.endswith("Service.ts"):
                    service_hits.append(rel(source.path))
        rows.append(
            {
                "metric": term,
                "source_hits": len(set(hits)),
                "service_hits": len(set(service_hits)),
                "status": "PASS" if service_hits else "WARN",
                "example_sources": ";".join(sorted(set(hits))[:8]),
                "example_services": ";".join(sorted(set(service_hits))[:8]),
            }
        )
    return rows


def build_language_audit(files: list[SourceFile]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for source in files:
        if source.path.suffix.lower() not in {".ts", ".tsx"}:
            continue
        for i, line in enumerate(source.text.splitlines(), start=1):
            lowered = line.lower()
            found = [term for term in PROBLEM_LANGUAGE if re.search(rf"\b{re.escape(term.lower())}\b", lowered)]
            if found:
                rows.append(
                    {
                        "file": rel(source.path),
                        "line": i,
                        "terms": ",".join(found),
                        "snippet": line.strip()[:260],
                    }
                )
    return rows


def write_markdown_report(
    route_rows: list[dict[str, object]],
    mock_rows: list[dict[str, object]],
    saddle_rows: list[dict[str, object]],
    metric_rows: list[dict[str, object]],
    language_rows: list[dict[str, object]],
) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    route_failures = [row for row in route_rows if row["status"] != "PASS"]
    metric_warnings = [row for row in metric_rows if row["status"] != "PASS"]
    content = [
        "# EDGEiQ Full Product Foundation Audit V1",
        "",
        "## Summary",
        f"- Workspace route warnings/failures: {len(route_failures)}",
        f"- Mock/demo/hardcoded risk hits: {len(mock_rows)}",
        f"- Saddlecloth style review hits: {len(saddle_rows)}",
        f"- Governed metric service warnings: {len(metric_warnings)}",
        f"- Product-language review hits: {len(language_rows)}",
        "",
        "## Workspace Route Status",
    ]
    for row in route_rows:
        content.append(f"- {row['workspace']}: {row['status']} (nav={row['nav_present']}, component={row['component_present']})")
    content.extend(
        [
            "",
            "## Notes",
            "- This audit is static. It identifies wiring and production-facing risk; browser smoke tests still decide runtime status.",
            "- A WARN result means the workspace or metric exists but needs human review or stronger canonical-service evidence.",
            "- A FAIL result means the approved workspace was not found in the active source tree under the expected component names.",
        ]
    )
    (OUT_DIR / "EDGEIQ_FULL_PRODUCT_FOUNDATION_AUDIT_V1.md").write_text("\n".join(content) + "\n", encoding="utf-8")


def main() -> int:
    files = iter_source_files()
    route_rows = build_workspace_route_audit(files)
    mock_rows = build_mock_data_audit(files)
    saddle_rows = build_saddlecloth_audit(files)
    metric_rows = build_governed_metric_audit(files)
    language_rows = build_language_audit(files)

    write_csv(PUBLIC_OUT / "edgeiq_workspace_route_audit_v1.csv", route_rows)
    write_csv(PUBLIC_OUT / "edgeiq_mock_data_audit_v1.csv", mock_rows)
    write_csv(PUBLIC_OUT / "edgeiq_saddlecloth_style_audit_v1.csv", saddle_rows)
    write_csv(PUBLIC_OUT / "edgeiq_governed_metric_audit_v1.csv", metric_rows)
    write_csv(PUBLIC_OUT / "edgeiq_ui_language_audit_v1.csv", language_rows)
    write_markdown_report(route_rows, mock_rows, saddle_rows, metric_rows, language_rows)

    summary = {
        "workspace_route_non_pass": sum(1 for row in route_rows if row["status"] != "PASS"),
        "mock_data_hits": len(mock_rows),
        "saddlecloth_style_hits": len(saddle_rows),
        "governed_metric_warnings": sum(1 for row in metric_rows if row["status"] != "PASS"),
        "language_hits": len(language_rows),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
