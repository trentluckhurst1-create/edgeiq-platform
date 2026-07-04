from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

AUDIT_OUT = DATA / "edgeiq_nexus_contextual_intelligence_v2_audit.csv"

FILES = {
    "trainer_context": DATA / "edgeiq_nexus_trainer_context_v2.csv",
    "jockey_context": DATA / "edgeiq_nexus_jockey_context_v2.csv",
    "partnership_context": DATA / "edgeiq_nexus_partnership_context_v2.csv",
    "style_alignment": DATA / "edgeiq_nexus_style_alignment_v2.csv",
    "contextual_score": DATA / "edgeiq_nexus_contextual_score_v2.csv",
    "live_contextual_feed": DATA / "edgeiq_live_nexus_contextual_feed_v2.csv",
    "summary": DATA / "edgeiq_nexus_contextual_intelligence_v2_summary.csv",
}

REQUIRED_COLUMNS = {
    "trainer_context": ["trainer", "context_type", "context_value", "starts", "wins", "win_pct", "places", "place_pct", "roi", "ae", "sample_band", "context_band"],
    "jockey_context": ["jockey", "context_type", "context_value", "rides", "wins", "win_pct", "places", "place_pct", "roi", "ae", "sample_band", "context_band"],
    "partnership_context": ["trainer", "jockey", "context_type", "context_value", "starts", "wins", "win_pct", "places", "place_pct", "roi", "ae", "sample_band", "partnership_band"],
    "style_alignment": ["runner_key", "runner_name", "race_date", "track", "race_no", "trainer", "jockey", "horse_run_style", "trainer_best_style", "jockey_best_style", "style_alignment_score", "style_alignment_band", "style_alignment_summary"],
    "contextual_score": ["runner_key", "runner_name", "race_date", "track", "race_no", "trainer", "jockey", "trainer_context_score", "jockey_context_score", "partnership_score", "style_alignment_score", "roi_score", "ae_score", "nexus_context_score", "nexus_context_band", "top_positive_1", "top_risk_1", "nexus_summary"],
    "live_contextual_feed": ["runner_key", "runner_name", "race_date", "track", "race_no", "trainer", "jockey", "nexus_context_score", "nexus_context_band", "trainer_recent_25_win_pct", "trainer_recent_50_win_pct", "trainer_recent_100_win_pct", "jockey_recent_25_win_pct", "jockey_recent_50_win_pct", "jockey_recent_100_win_pct", "trainer_best_context", "jockey_best_context", "partnership_band", "style_alignment_score", "style_alignment_band", "top_positive_1", "top_positive_2", "top_positive_3", "top_risk_1", "top_risk_2", "top_risk_3", "nexus_summary"],
    "summary": ["metric", "value"],
}


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def read_header_and_count(path: Path) -> tuple[list[str], int]:
    if not path.exists():
        return [], 0
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
        return header, sum(1 for _ in reader)


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def add(rows: list[dict[str, Any]], check: str, status: str, file: Path | str, detail: Any, count: int = 0) -> None:
    rows.append({"check": check, "status": status, "file": str(file), "detail": detail, "rows": count})


def write_audit(rows: list[dict[str, Any]]) -> None:
    with AUDIT_OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "file", "detail", "rows"], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    audit_rows: list[dict[str, Any]] = []
    headers: dict[str, list[str]] = {}
    counts: dict[str, int] = {}

    for name, path in FILES.items():
        header, count = read_header_and_count(path)
        headers[name] = header
        counts[name] = count
        add(audit_rows, f"{name}_file_exists", "PASS" if path.exists() else "FAIL", path, "exists" if path.exists() else "missing", count)
        if name != "summary":
            add(audit_rows, f"{name}_rows_gt_0", "PASS" if count > 0 else "FAIL", path, "rows > 0" if count > 0 else "no rows", count)

    for name, required in REQUIRED_COLUMNS.items():
        missing = [col for col in required if col not in set(headers.get(name, []))]
        add(audit_rows, f"{name}_required_columns_present", "PASS" if not missing else "FAIL", FILES[name], "OK" if not missing else "missing: " + ", ".join(missing), counts.get(name, 0))

    live_board_rows = read_header_and_count(DATA / "edgeiq_live_runner_board_v1.csv")[1]
    if live_board_rows > 0:
        add(audit_rows, "style_alignment_rows_gt_0_if_live_exists", "PASS" if counts.get("style_alignment", 0) > 0 else "FAIL", FILES["style_alignment"], f"live rows={live_board_rows}", counts.get("style_alignment", 0))
        add(audit_rows, "live_contextual_feed_rows_gt_0_if_live_exists", "PASS" if counts.get("live_contextual_feed", 0) > 0 else "FAIL", FILES["live_contextual_feed"], f"live rows={live_board_rows}", counts.get("live_contextual_feed", 0))

    populated_scores = 0
    score_rows = read_rows(FILES["contextual_score"])
    for row in score_rows:
        if text(row.get("nexus_context_score")):
            populated_scores += 1
    add(
        audit_rows,
        "nexus_context_score_populated_for_live_rows",
        "PASS" if live_board_rows == 0 or populated_scores > 0 else "FAIL",
        FILES["contextual_score"],
        f"{populated_scores} rows with nexus_context_score",
        populated_scores,
    )

    forbidden_hits: list[str] = []
    for name, header in headers.items():
        for column in header:
            if "barrier" in column.lower():
                forbidden_hits.append(f"{name}.{column}")
    for name, path in FILES.items():
        if "barrier" in path.name.lower():
            forbidden_hits.append(path.name)
    add(
        audit_rows,
        "no_forbidden_barrier_specialist_outputs_or_columns",
        "PASS" if not forbidden_hits else "FAIL",
        "outputs",
        "OK" if not forbidden_hits else "; ".join(forbidden_hits[:20]),
        len(forbidden_hits),
    )

    add(audit_rows, "summary_written", "PASS" if FILES["summary"].exists() and counts.get("summary", 0) > 0 else "FAIL", FILES["summary"], "summary rows written", counts.get("summary", 0))
    add(audit_rows, "audit_csv_written", "PASS", AUDIT_OUT, "audit CSV written by this script", len(audit_rows) + 1)

    write_audit(audit_rows)
    status_counts: dict[str, int] = {}
    for row in audit_rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    print(
        "EDGEiQ Nexus contextual intelligence V2 audit: "
        + ", ".join(f"{status}={count}" for status, count in sorted(status_counts.items()))
    )
    failures = [row for row in audit_rows if row["status"] == "FAIL"]
    if failures:
        for row in failures:
            print(f"FAIL {row['check']}: {row['detail']}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
