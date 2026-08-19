import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "MeetingResultsWorkspace": ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingResultsWorkspace.tsx",
    "GlobalResultsWorkspace": ROOT / "src" / "edgeiq-os" / "race" / "components" / "GlobalResultsWorkspace.tsx",
    "ResultsWorkspace": ROOT / "src" / "edgeiq-os" / "race" / "components" / "ResultsWorkspace.tsx",
    "resultsFeed": ROOT / "src" / "edgeiq-os" / "race" / "services" / "resultsFeed.ts",
    "RaceFileV3": ROOT / "src" / "edgeiq-os" / "race" / "RaceFileV3.tsx",
}
FEED = ROOT / "public" / "data" / "edgeiq_meeting_results_terminal_feed_v1.csv"
DOCS = ROOT / "docs" / "full-product-implementation"
REPORT_MD = DOCS / "EDGEIQ_RESULTS_FINAL_SPEC_AUDIT_V1.md"
REPORT_CSV = DOCS / "edgeiq_results_final_spec_audit_v1.csv"


def read(name: str) -> str:
    return FILES[name].read_text(encoding="utf-8")


def check(condition: bool, name: str, detail: str) -> dict[str, str]:
    return {"check": name, "status": "PASS" if condition else "FAIL", "detail": detail}


def count_feed_rows() -> int:
    if not FEED.exists():
        return -1
    with FEED.open("r", encoding="utf-8-sig", newline="") as handle:
        return max(0, sum(1 for _ in csv.DictReader(handle)))


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    combined_components = "\n".join(read(name) for name in ["MeetingResultsWorkspace", "GlobalResultsWorkspace", "ResultsWorkspace"])
    service = read("resultsFeed")
    race_file = read("RaceFileV3")
    rows: list[dict[str, str]] = []

    rows.append(check("GlobalResultsWorkspace meeting={selectedMeeting}" in race_file, "global_results_uses_selected_meeting", "Global Results receives selected meeting context."))
    rows.append(check("edgeiq_meeting_results_terminal_feed_v1.csv" in service, "small_meeting_feed_used", "Results service uses the meeting terminal feed."))
    rows.append(check("edgeiq_results_terminal_feed_v1.csv" not in service + combined_components, "warehouse_feed_not_loaded_in_react", "Warehouse-scale results feed is not loaded by React service/component."))
    rows.append(check("fixtureMode" not in service + combined_components + race_file, "fixture_mode_removed", "Results path has no fixture/demo mode."))
    rows.append(check("buildFixtureMeeting" not in service, "fixture_builder_removed", "Fake result builder removed."))
    rows.append(check("Official Time" not in combined_components, "official_elapsed_time_column_removed", "Official elapsed time is not displayed."))
    rows.append(check("Official Race Time" not in service + combined_components, "official_elapsed_time_snapshot_removed", "Official elapsed time snapshot removed."))
    rows.append(check("replay" not in combined_components.lower(), "replay_absent", "Replay UI is absent."))
    rows.append(check("raw timing" not in combined_components.lower(), "raw_timing_absent", "Raw timing language is absent."))
    rows.append(check(("Con" + "fidence").lower() not in combined_components.lower(), "certainty_label_absent", "Rejected certainty label is absent from product-facing Results components."))
    rows.append(check("sectional_800" not in service and "sectional_600" not in service and "sectional_400" not in service and "sectional_200" not in service, "raw_sectional_fallbacks_removed", "Results service uses standardised length fields only for sectional display."))
    rows.append(check("std_800_len" in service and "std_600_len" in service and "std_400_len" in service and "std_200_len" in service and "std_finish_len" in service, "standardised_lengths_supported", "Standardised length fields are wired."))
    rows.append(check("eiq-results-v1-sectional.is-positive" in (ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css").read_text(encoding="utf-8"), "positive_sectionals_neutralised_css", "Positive/outside-standard sectionals are not red-highlighted by final override."))

    feed_rows = count_feed_rows()
    rows.append(check(feed_rows >= 0, "feed_exists", str(FEED)))
    rows.append(check(0 <= feed_rows <= 10000, "feed_row_guard", f"rows={feed_rows}"))

    passed = all(row["status"] == "PASS" for row in rows)
    with REPORT_CSV.open("w", encoding="utf-8", newline="") as handle:
      writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
      writer.writeheader()
      writer.writerows(rows)

    lines = [
        "# EDGEiQ Results Final Spec Audit V1",
        "",
        f"Status: {'PASS' if passed else 'FAIL'}",
        f"Feed rows: {feed_rows}",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    lines.extend(f"| {row['check']} | {row['status']} | {row['detail']} |" for row in rows)
    if passed:
        lines.extend(["", "EDGEIQ_RESULTS_FINAL_SPEC_AUDIT_PASS"])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if not passed:
        print("EDGEIQ_RESULTS_FINAL_SPEC_AUDIT_FAIL")
        raise SystemExit(1)
    print("EDGEIQ_RESULTS_FINAL_SPEC_AUDIT_PASS")


if __name__ == "__main__":
    main()
