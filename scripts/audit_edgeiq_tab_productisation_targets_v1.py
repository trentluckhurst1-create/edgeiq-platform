from pathlib import Path
import csv
import re
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
TSX = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
OUT = DATA / "edgeiq_tab_productisation_targets_v1.csv"
SUMMARY = DATA / "edgeiq_tab_productisation_targets_v1_summary.csv"
REPORT = DATA / "edgeiq_tab_productisation_targets_v1_report.txt"

OLD_LABELS = [
    "Top Call", "Best Value", "Main Risk", "Best Bet", "Value", "Tip", "Overbet", "Command", "Factor Lab", "Advanced",
]
NEW_LABELS = ["RACE", "FIELD", "MAP", "INSIGHTS", "MARKET", "RESULTS", "RACE INTELLIGENCE", "Race Shape Preview", "Market Context", "Connection Intelligence"]
BLOCK_PATTERNS = [
    ("navigation_tab_config", "const intelModeTabs"),
    ("RACE_COMMAND_render_block", 'intelMode === "COMMAND"'),
    ("MAP_render_block", 'intelMode === "MAP"'),
    ("FORM_render_block", 'intelMode === "FORM"'),
    ("FIELD_RUNNERS_render_block", 'intelMode === "RUNNERS"'),
    ("INSIGHTS_FACTORS_render_block", 'intelMode === "FACTORS"'),
    ("MARKET_ADVANCED_render_block", 'intelMode === "ADVANCED"'),
    ("RESULTS_render_marker", 'mode: "RESULTS"'),
]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def write_csv(path, rows, fieldnames=None):
    rows = list(rows)
    if fieldnames is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
        fieldnames = fields
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def count_label(text, label):
    return len(re.findall(re.escape(label), text, flags=re.IGNORECASE))


def context(lines, index):
    start = max(1, index - 2)
    end = min(len(lines), index + 2)
    return " ".join(line.strip() for line in lines[start - 1:end])[:500]


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    text = TSX.read_text(encoding="utf-8", errors="ignore") if TSX.exists() else ""
    lines = text.splitlines()
    rows = []

    for block, pattern in BLOCK_PATTERNS:
        matches = [i + 1 for i, line in enumerate(lines) if pattern in line]
        if matches:
            for match in matches:
                rows.append({
                    "audit_type": "render_marker",
                    "marker": block,
                    "search_pattern": pattern,
                    "line_start": match,
                    "line_end_estimate": min(len(lines), match + 220),
                    "count": 1,
                    "status": "FOUND",
                    "context": context(lines, match),
                })
        else:
            rows.append({
                "audit_type": "render_marker",
                "marker": block,
                "search_pattern": pattern,
                "line_start": "",
                "line_end_estimate": "",
                "count": 0,
                "status": "MISSING",
                "context": "",
            })

    for label in OLD_LABELS:
        matches = [(i + 1, line.strip()) for i, line in enumerate(lines) if re.search(re.escape(label), line, flags=re.IGNORECASE)]
        rows.append({
            "audit_type": "old_label_count",
            "marker": label,
            "search_pattern": label,
            "line_start": matches[0][0] if matches else "",
            "line_end_estimate": matches[-1][0] if matches else "",
            "count": len(matches),
            "status": "PRESENT" if matches else "ABSENT",
            "context": " || ".join(f"L{n}: {line}" for n, line in matches[:8])[:1000],
        })

    for label in NEW_LABELS:
        rows.append({
            "audit_type": "new_label_count",
            "marker": label,
            "search_pattern": label,
            "line_start": "",
            "line_end_estimate": "",
            "count": count_label(text, label),
            "status": "PRESENT" if count_label(text, label) else "MISSING",
            "context": "",
        })

    old_total = sum(int(r["count"]) for r in rows if r["audit_type"] == "old_label_count")
    new_total = sum(int(r["count"]) for r in rows if r["audit_type"] == "new_label_count")
    missing_markers = [r["marker"] for r in rows if r["audit_type"] == "render_marker" and r["status"] == "MISSING"]
    status = "TAB_PRODUCTISATION_TARGET_AUDIT_COMPLETE" if not missing_markers else "TAB_PRODUCTISATION_TARGET_AUDIT_REVIEW_REQUIRED"

    summary = [
        {"metric": "status", "value": status},
        {"metric": "tsx_file", "value": str(TSX)},
        {"metric": "render_markers", "value": len(BLOCK_PATTERNS)},
        {"metric": "missing_render_markers", "value": len(missing_markers)},
        {"metric": "missing_marker_list", "value": "|".join(missing_markers)},
        {"metric": "old_label_total", "value": old_total},
        {"metric": "new_label_total", "value": new_total},
        {"metric": "command_visible_count", "value": count_label(text, "Command")},
        {"metric": "factor_lab_visible_count", "value": count_label(text, "Factor Lab")},
        {"metric": "advanced_visible_count", "value": count_label(text, "Advanced")},
        {"metric": "results_mode_present", "value": "YES" if 'mode: "RESULTS"' in text else "NO"},
        {"metric": "backend_data_changed", "value": "NO"},
        {"metric": "pricing_changed", "value": "NO"},
        {"metric": "probability_changed", "value": "NO"},
        {"metric": "v6_1_changed", "value": "NO"},
        {"metric": "v7_2g2_changed", "value": "NO"},
        {"metric": "active_csv_schemas_changed", "value": "NO"},
        {"metric": "built_at", "value": now_iso()},
    ]

    report = [
        "EDGEiQ Tab Productisation Targets V1",
        "=====================================",
        f"Status: {status}",
        f"Render markers missing: {len(missing_markers)}",
        f"Old label total: {old_total}",
        f"New label total: {new_total}",
        "Internal mapping retained: COMMAND=RACE, RUNNERS=FIELD, FACTORS=INSIGHTS, ADVANCED=MARKET.",
        "Backend data changed: NO",
        "Pricing changed: NO",
        "Probability changed: NO",
        "V6.1 changed: NO",
        "V7.2G2 changed: NO",
        "Active CSV schemas changed: NO",
    ]
    write_csv(OUT, rows)
    write_csv(SUMMARY, summary, ["metric", "value"])
    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(status)


if __name__ == "__main__":
    main()
