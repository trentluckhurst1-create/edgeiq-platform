import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "OverviewWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
FEEDS = {
    "overview": ROOT / "public" / "data" / "edgeiq_overview_terminal_feed_v1.csv",
    "epi": ROOT / "public" / "data" / "edgeiq_epi_workspace_terminal_feed_v1.csv",
    "map": ROOT / "public" / "data" / "edgeiq_map_terminal_feed_v1.csv",
}
OUT_CSV = ROOT / "docs" / "full-product-implementation" / "edgeiq_overview_final_spec_audit_v1.csv"
OUT_MD = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_OVERVIEW_FINAL_SPEC_AUDIT_V1.md"

REQUIRED_COMPONENT_TOKENS = [
    "SummaryCards",
    "WhatMattersToday",
    "SpeedMapPreview",
    "EpiSnapshot",
    "RunnerBoard",
    "DataGaps",
    "loadOverviewTerminalFeed",
    "loadEpiWorkspaceTerminalFeed",
    "loadMapTerminalFeed",
]

REJECTED_COMPONENT_TOKENS = [
    "formatBenchmarkConfidence",
    ">Confidence<",
    "Race Command Centre",
    "Command Centreiness",
    "Risk Watch",
    "Primary Actions",
    "Back/Lay",
    "Best bet",
    "Tip",
]


def count_rows(path: Path) -> int:
    if not path.exists():
        return -1
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def main() -> None:
    rows = []
    source = COMPONENT.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")

    for token in REQUIRED_COMPONENT_TOKENS:
        rows.append({
            "check": f"component_has_{token}",
            "status": "PASS" if token in source else "FAIL",
            "detail": token,
        })

    for token in REJECTED_COMPONENT_TOKENS:
        rows.append({
            "check": f"component_rejects_{token}",
            "status": "PASS" if token not in source else "FAIL",
            "detail": token,
        })

    rows.append({
        "check": "css_has_overview_final_spec_marker",
        "status": "PASS" if "EDGEIQ OVERVIEW FINAL SPEC V1" in css else "FAIL",
        "detail": "scoped overview CSS present",
    })

    for name, path in FEEDS.items():
        row_count = count_rows(path)
        rows.append({
            "check": f"{name}_feed_exists",
            "status": "PASS" if row_count >= 0 else "FAIL",
            "detail": str(path),
        })
        rows.append({
            "check": f"{name}_feed_under_frontend_guard",
            "status": "PASS" if 0 <= row_count <= 10000 else "FAIL",
            "detail": str(row_count),
        })

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        writer.writerows(rows)

    failed = [row for row in rows if row["status"] != "PASS"]
    OUT_MD.write_text(
        "# EDGEiQ Overview Final Spec Audit V1\n\n"
        f"Result: {'PASS' if not failed else 'FAIL'}\n\n"
        f"Checks: {len(rows)}\n\n"
        f"Failures: {len(failed)}\n\n"
        + "\n".join(f"- {row['check']}: {row['status']} ({row['detail']})" for row in rows)
        + ("\n\nEDGEIQ_OVERVIEW_FINAL_SPEC_AUDIT_PASS\n" if not failed else "\n"),
        encoding="utf-8",
    )

    if failed:
        for row in failed:
            print(f"FAIL {row['check']}: {row['detail']}")
        raise SystemExit(1)

    print("EDGEIQ_OVERVIEW_FINAL_SPEC_AUDIT_PASS")


if __name__ == "__main__":
    main()
