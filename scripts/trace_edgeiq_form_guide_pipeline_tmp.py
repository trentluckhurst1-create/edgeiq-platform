from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
TARGET = ROOT / "scripts" / "build_edgeiq_epi_workspace_terminal_feed_v1.py"
OUT = ROOT / "docs" / "full-product-implementation" / "FORM_GUIDE_PIPELINE_TRACE.txt"

text = TARGET.read_text(encoding="utf-8", errors="replace")
tree = ast.parse(text)

constants = {}

for node in tree.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                try:
                    constants[target.id] = ast.literal_eval(node.value)
                except Exception:
                    constants[target.id] = ast.unparse(node.value)

report = [
    "EDGEIQ FORM GUIDE PIPELINE TRACE",
    "=" * 110,
    f"TARGET_BUILDER={TARGET}",
    "",
    "BUILDER CONSTANTS",
    "-" * 110,
]

for key in sorted(constants):
    if any(token in key.upper() for token in ["FORM", "CATALOG", "OUT", "SUMMARY", "TRACE"]):
        report.append(f"{key}={constants[key]!r}")

report.extend([
    "",
    "FORM-GUIDE-RELATED FILES",
    "-" * 110,
])

patterns = [
    "*form*guide*.json",
    "*form*guide*.csv",
    "*form*guide*.py",
    "*form*.json",
]

seen = set()

for pattern in patterns:
    for path in ROOT.rglob(pattern):
        if not path.is_file():
            continue
        resolved = str(path.resolve()).lower()
        if resolved in seen:
            continue
        seen.add(resolved)

        try:
            stat = path.stat()
            report.append(
                f"{path} | modified={stat.st_mtime} | size={stat.st_size}"
            )
        except Exception as exc:
            report.append(f"{path} | STAT_ERROR={exc}")

report.extend([
    "",
    "SCRIPTS REFERENCING FORM GUIDE OUTPUT",
    "-" * 110,
])

for path in (ROOT / "scripts").rglob("*.py"):
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue

    lowered = content.lower()

    if "form_guide" in lowered or "form guide" in lowered:
        matches = []
        for lineno, line in enumerate(content.splitlines(), start=1):
            if "form_guide" in line.lower() or "form guide" in line.lower():
                matches.append(f"{lineno}: {line.strip()}")

        report.append("")
        report.append(str(path))
        report.extend(matches[:40])

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(report), encoding="utf-8")

print("\n".join(report))
print(f"WROTE={OUT}")
print("FORM_GUIDE_PIPELINE_TRACE_PASS")
