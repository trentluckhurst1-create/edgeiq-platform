from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
SRC = ROOT / "src" / "edgeiq-os"
OUTPUT_ROOT = (
    ROOT
    / "docs"
    / "full-product-implementation"
    / "race-shell-standardisation-v1"
)

CSS_PATH = SRC / "styles" / "edgeiqOsV2.css"
PRESENTATION_PATH = SRC / "design-system" / "presentation.ts"

COMPONENT_CANDIDATES = [
    SRC / "race" / "RaceFileV3.tsx",
    SRC / "race" / "RaceFileV2.tsx",
    SRC / "race" / "components" / "RaceWorkspace.tsx",
    SRC / "race" / "components" / "FieldWorkspace.tsx",
    SRC / "race" / "components" / "RaceFormGuideWorkspace.tsx",
    SRC / "race" / "components" / "RaceIntelligenceWorkspace.tsx",
    SRC / "race" / "components" / "PerformanceWorkspace.tsx",
    SRC / "race" / "components" / "MapWorkspace.tsx",
    SRC / "race" / "components" / "MarketWorkspace.tsx",
    SRC / "race" / "components" / "OverviewWorkspace.tsx",
    SRC / "race" / "components" / "InsightsWorkspace.tsx",
    SRC / "race" / "components" / "EpiWorkspace.tsx",
    SRC / "race" / "components" / "ResultsWorkspace.tsx",
    SRC / "race" / "components" / "ReviewWorkspace.tsx",
]

SEARCH_TERMS = [
    "race-workspace",
    "race-shell",
    "race-header",
    "race-meta",
    "metadata",
    "workspace-tabs",
    "tab-bar",
    "runner-board",
    "field-workspace",
    "form-guide",
    "performance",
    "market",
    "overview",
    "insights",
    "results",
    "review",
    "table",
    "card",
]

CSS_PROPERTY_NAMES = [
    "font-family",
    "font-size",
    "font-weight",
    "line-height",
    "height",
    "min-height",
    "padding",
    "padding-top",
    "padding-right",
    "padding-bottom",
    "padding-left",
    "margin",
    "gap",
    "border",
    "border-radius",
    "text-align",
    "vertical-align",
    "table-layout",
    "overflow",
    "overflow-x",
]


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def find_components() -> list[Path]:
    located: list[Path] = []

    for path in COMPONENT_CANDIDATES:
        if path.exists() and path not in located:
            located.append(path)

    race_root = SRC / "race"
    if race_root.exists():
        for path in race_root.rglob("*.tsx"):
            lowered = path.name.lower()
            if any(
                term in lowered
                for term in [
                    "workspace",
                    "racefile",
                    "field",
                    "form",
                    "performance",
                    "market",
                    "overview",
                    "insight",
                    "result",
                    "review",
                    "map",
                    "epi",
                ]
            ):
                if path not in located:
                    located.append(path)

    return sorted(located)


def extract_class_names(text: str) -> list[str]:
    patterns = [
        r'className\s*=\s*"([^"]+)"',
        r"className\s*=\s*'([^']+)'",
        r'className\s*=\s*\{\s*`([^`]+)`\s*\}',
    ]
    names: set[str] = set()

    for pattern in patterns:
        for match in re.finditer(pattern, text):
            raw = match.group(1)
            raw = re.sub(r"\$\{[^}]+\}", " ", raw)
            for name in re.split(r"\s+", raw.strip()):
                if name and re.fullmatch(r"[A-Za-z0-9_-]+", name):
                    names.add(name)

    return sorted(names)


def extract_css_blocks(css: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []

    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css, flags=re.S):
        selector = re.sub(r"\s+", " ", match.group(1)).strip()
        body = match.group(2).strip()

        if not selector or selector.startswith("@"):
            continue

        declarations: dict[str, str] = {}
        for declaration in body.split(";"):
            if ":" not in declaration:
                continue
            key, value = declaration.split(":", 1)
            key = key.strip().lower()
            value = value.strip()
            if key and value:
                declarations[key] = value

        if declarations:
            blocks.append(
                {
                    "selector": selector,
                    "declarations": declarations,
                }
            )

    return blocks


def relevant_css_blocks(
    css_blocks: list[dict[str, Any]],
    class_names: set[str],
) -> list[dict[str, Any]]:
    relevant: list[dict[str, Any]] = []

    for block in css_blocks:
        selector_lower = block["selector"].lower()

        selector_classes = set(
            re.findall(r"\.([A-Za-z0-9_-]+)", block["selector"])
        )

        is_class_match = bool(selector_classes & class_names)
        is_term_match = any(term in selector_lower for term in SEARCH_TERMS)

        if not is_class_match and not is_term_match:
            continue

        filtered = {
            key: value
            for key, value in block["declarations"].items()
            if key in CSS_PROPERTY_NAMES or key.startswith("--")
        }

        relevant.append(
            {
                "selector": block["selector"],
                "matched_classes": sorted(selector_classes & class_names),
                "properties": filtered,
                "all_declarations": block["declarations"],
            }
        )

    return relevant


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    css = read_text(CSS_PATH)
    presentation = read_text(PRESENTATION_PATH)
    components = find_components()

    component_rows: list[dict[str, Any]] = []
    all_classes: set[str] = set()

    for path in components:
        text = read_text(path)
        classes = extract_class_names(text)
        all_classes.update(classes)

        component_rows.append(
            {
                "path": relative(path),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else 0,
                "line_count": len(text.splitlines()),
                "class_names": classes,
                "uses_table": "<table" in text,
                "uses_shared_tabs": any(
                    term in text
                    for term in [
                        "RaceWorkspaceTabs",
                        "workspace-tabs",
                        "race-workspace-tabs",
                    ]
                ),
                "uses_shared_header": any(
                    term in text
                    for term in [
                        "RaceHeader",
                        "RaceWorkspaceHeader",
                        "race-header",
                    ]
                ),
            }
        )

    css_blocks = extract_css_blocks(css)
    relevant_blocks = relevant_css_blocks(css_blocks, all_classes)

    race_reference_blocks = [
        block
        for block in relevant_blocks
        if any(
            term in block["selector"].lower()
            for term in [
                "race-workspace",
                "race-shell",
                "race-header",
                "race-meta",
                "runner-board",
                "workspace-tabs",
            ]
        )
    ]

    result = {
        "status": "PASS",
        "root": str(ROOT),
        "css_path": relative(CSS_PATH),
        "presentation_path": relative(PRESENTATION_PATH),
        "component_count": len(component_rows),
        "component_rows": component_rows,
        "all_class_names": sorted(all_classes),
        "relevant_css_block_count": len(relevant_blocks),
        "relevant_css_blocks": relevant_blocks,
        "race_reference_blocks": race_reference_blocks,
        "presentation_source": presentation,
    }

    json_path = OUTPUT_ROOT / "EDGEIQ_RACE_SHELL_FORENSIC_INVENTORY_V1.json"
    md_path = OUTPUT_ROOT / "EDGEIQ_RACE_SHELL_FORENSIC_INVENTORY_V1.md"
    txt_path = OUTPUT_ROOT / "EDGEIQ_RACE_SHELL_SOURCE_EXTRACT_V1.txt"

    json_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    md_lines = [
        "# EDGEIQ Race Shell Forensic Inventory V1",
        "",
        "## Status",
        "",
        "PASS",
        "",
        "## Components",
        "",
    ]

    for row in component_rows:
        md_lines.extend(
            [
                f"### `{row['path']}`",
                "",
                f"- Lines: {row['line_count']}",
                f"- Classes: {len(row['class_names'])}",
                f"- Uses table: {row['uses_table']}",
                f"- Shared tabs detected: {row['uses_shared_tabs']}",
                f"- Shared header detected: {row['uses_shared_header']}",
                "",
            ]
        )

    md_lines.extend(
        [
            "## Race Reference CSS",
            "",
        ]
    )

    for block in race_reference_blocks:
        md_lines.append(f"### `{block['selector']}`")
        md_lines.append("")
        for key, value in block["all_declarations"].items():
            md_lines.append(f"- `{key}`: `{value}`")
        md_lines.append("")

    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    extract_parts: list[str] = []

    for row in component_rows:
        path = ROOT / row["path"]
        extract_parts.extend(
            [
                "=" * 100,
                row["path"],
                "=" * 100,
                read_text(path),
                "",
            ]
        )

    extract_parts.extend(
        [
            "=" * 100,
            relative(PRESENTATION_PATH),
            "=" * 100,
            presentation,
            "",
            "=" * 100,
            "RELEVANT CSS BLOCKS",
            "=" * 100,
        ]
    )

    for block in relevant_blocks:
        extract_parts.append(block["selector"] + " {")
        for key, value in block["all_declarations"].items():
            extract_parts.append(f"  {key}: {value};")
        extract_parts.append("}")
        extract_parts.append("")

    txt_path.write_text("\n".join(extract_parts), encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "PASS",
                "components": len(component_rows),
                "classes": len(all_classes),
                "relevant_css_blocks": len(relevant_blocks),
                "race_reference_blocks": len(race_reference_blocks),
                "json": str(json_path),
                "markdown": str(md_path),
                "source_extract": str(txt_path),
            },
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
