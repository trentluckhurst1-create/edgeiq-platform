import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "InsightsWorkspace.tsx"
FEED = ROOT / "public" / "data" / "edgeiq_insights_terminal_feed_v1.csv"
DOCS = ROOT / "docs" / "full-product-implementation"
REPORT_MD = DOCS / "EDGEIQ_INSIGHTS_FINAL_SPEC_AUDIT_V1.md"
REPORT_CSV = DOCS / "edgeiq_insights_final_spec_audit_v1.csv"

REQUIRED_COMPONENT_TOKENS = [
    "ApprovedInsightCategories",
    "Stable Intent",
    "Preparation Stage",
    "Heavy Skill",
    "Campaign Profile",
    "RunnerInsightsTable",
    "DataGaps",
    "CertifiedEvidencePanel",
    "loadInsightsTerminalFeed",
]

REJECTED_COMPONENT_TOKENS = [
    ("rejected_formatter_absent", "formatBenchmark" + "Con" + "fidence"),
    ("rejected_certainty_header_absent", ">" + "Con" + "fidence" + "<"),
    ("rejected_certainty_upper_absent", "CON" + "FIDENCE"),
    ("rejected_helper_panel_absent", "How To Use"),
    ("rejected_best_bet_absent", "best bet"),
    ("rejected_tip_absent", "tip"),
    ("rejected_wager_cta_absent", "recommended wager"),
    ("rejected_generic_analysis_absent", "generic AI"),
]


def check(condition: bool, name: str, detail: str) -> dict[str, str]:
    return {
        "check": name,
        "status": "PASS" if condition else "FAIL",
        "detail": detail,
    }


def count_feed_rows() -> int:
    if not FEED.exists():
        return -1
    with FEED.open("r", encoding="utf-8-sig", newline="") as handle:
        return max(0, sum(1 for _ in csv.DictReader(handle)))


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    text = COMPONENT.read_text(encoding="utf-8")
    rows: list[dict[str, str]] = []

    for token in REQUIRED_COMPONENT_TOKENS:
        rows.append(check(token in text, f"required_token::{token}", "Component contains required governed Insights structure."))

    for name, token in REJECTED_COMPONENT_TOKENS:
        rows.append(check(token.lower() not in text.lower(), name, "Rejected product-facing language is absent from Insights component."))

    feed_rows = count_feed_rows()
    rows.append(check(feed_rows >= 0, "feed_exists", str(FEED)))
    rows.append(check(0 <= feed_rows <= 10000, "feed_row_guard", f"rows={feed_rows}"))

    passed = all(row["status"] == "PASS" for row in rows)

    with REPORT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# EDGEiQ Insights Final Spec Audit V1",
        "",
        f"Status: {'PASS' if passed else 'FAIL'}",
        f"Feed rows: {feed_rows}",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row['check']} | {row['status']} | {row['detail']} |")
    if passed:
        lines.extend(["", "EDGEIQ_INSIGHTS_FINAL_SPEC_AUDIT_PASS"])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if not passed:
        print("EDGEIQ_INSIGHTS_FINAL_SPEC_AUDIT_FAIL")
        raise SystemExit(1)
    print("EDGEIQ_INSIGHTS_FINAL_SPEC_AUDIT_PASS")


if __name__ == "__main__":
    main()
