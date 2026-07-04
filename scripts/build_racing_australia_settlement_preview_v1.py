from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

CANDIDATE_IN = DATA / "racing_australia_settlement_candidate_v1.csv"
PREVIEW_OUT = DATA / "racing_australia_settlement_preview_v1.csv"
AUDIT_OUT = DATA / "racing_australia_settlement_preview_v1_audit.csv"

MANUAL_SOURCE = "USER_VERIFIED_OFFICIAL_RACING_AUSTRALIA_PAGE"
MANUAL_NOTE = (
    "User manually verified official Racing Australia race result pages show this runner "
    "as scratched with red text / strike-through. Preview only; price truth history not modified."
)

PREVIEW_COLUMNS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key",
    "finish_position",
    "won",
    "starting_price",
    "result_status",
    "settlement_blocker",
    "result_source",
    "match_status",
    "notes",
]

AUDIT_COLUMNS = ["section", "metric", "value", "source_path", "notes", "built_at"]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean(value: object) -> str:
    text = str(value or "").strip()
    if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"}:
        return ""
    return text


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def preview_row(row: dict[str, str]) -> dict[str, object]:
    result_status = clean(row.get("result_status"))
    output = {column: clean(row.get(column)) for column in PREVIEW_COLUMNS}
    if result_status == "NON_RUNNER_UNCONFIRMED":
        output.update(
            {
                "finish_position": "SCR",
                "won": "FALSE",
                "starting_price": "",
                "result_status": "CONFIRMED_SCRATCHED",
                "settlement_blocker": "",
                "result_source": MANUAL_SOURCE,
                "match_status": "MANUAL_CONFIRMED_RA_SCRATCHED",
                "notes": MANUAL_NOTE,
            }
        )
    return output


def audit_row(section: str, metric: str, value: object, source_path: Path | str = "", notes: str = "") -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "source_path": str(source_path),
        "notes": notes,
        "built_at": now_utc(),
    }


def build_audit(input_rows: list[dict[str, str]], preview_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    input_status = Counter(clean(row.get("result_status")) for row in input_rows)
    preview_status = Counter(clean(row.get("result_status")) for row in preview_rows)
    blocker_count = sum(1 for row in preview_rows if clean(row.get("settlement_blocker")))
    safe_statuses = {"FINAL", "FAILED_TO_FINISH", "CONFIRMED_SCRATCHED"}
    settlement_ready = len(preview_rows) == 87 and blocker_count == 0 and all(
        clean(row.get("result_status")) in safe_statuses for row in preview_rows
    )
    unique_runners = {
        "|".join(
            [
                clean(row.get("race_date")),
                clean(row.get("track")),
                clean(row.get("race_no")),
                clean(row.get("horse_key")),
            ]
        )
        for row in preview_rows
    }

    rows = [
        audit_row("input", "candidate_rows_loaded", len(input_rows), CANDIDATE_IN),
        audit_row("input_status", "candidate_final_rows", input_status.get("FINAL", 0), CANDIDATE_IN),
        audit_row("input_status", "candidate_failed_to_finish_rows", input_status.get("FAILED_TO_FINISH", 0), CANDIDATE_IN),
        audit_row("input_status", "candidate_non_runner_unconfirmed_rows", input_status.get("NON_RUNNER_UNCONFIRMED", 0), CANDIDATE_IN),
        audit_row("output", "total_rows", len(preview_rows), PREVIEW_OUT),
        audit_row("output", "unique_runners", len(unique_runners), PREVIEW_OUT),
        audit_row("output_status", "FINAL", preview_status.get("FINAL", 0), PREVIEW_OUT),
        audit_row("output_status", "FAILED_TO_FINISH", preview_status.get("FAILED_TO_FINISH", 0), PREVIEW_OUT),
        audit_row("output_status", "CONFIRMED_SCRATCHED", preview_status.get("CONFIRMED_SCRATCHED", 0), PREVIEW_OUT),
        audit_row("output_status", "OTHER_STATUS_ROWS", len(preview_rows) - preview_status.get("FINAL", 0) - preview_status.get("FAILED_TO_FINISH", 0) - preview_status.get("CONFIRMED_SCRATCHED", 0), PREVIEW_OUT),
        audit_row("manual_verification", "manual_source", MANUAL_SOURCE, PREVIEW_OUT, MANUAL_NOTE),
        audit_row("settlement", "settlement_blockers", blocker_count, PREVIEW_OUT),
        audit_row("settlement", "SETTLEMENT_READY", "TRUE" if settlement_ready else "FALSE", PREVIEW_OUT),
    ]
    for race_no, count in sorted(Counter(clean(row.get("race_no")) for row in preview_rows).items(), key=lambda item: int(item[0])):
        rows.append(audit_row("race_count", f"R{race_no}", count, PREVIEW_OUT))
    return rows


def main() -> None:
    input_rows = read_csv(CANDIDATE_IN)
    preview_rows = [preview_row(row) for row in input_rows]
    audit_rows = build_audit(input_rows, preview_rows)

    write_csv(PREVIEW_OUT, preview_rows, PREVIEW_COLUMNS)
    write_csv(AUDIT_OUT, audit_rows, AUDIT_COLUMNS)

    print("=" * 96)
    print("RACING AUSTRALIA SETTLEMENT PREVIEW V1 - REVIEW ONLY")
    print("=" * 96)
    for row in audit_rows:
        if row["section"] in {"output", "output_status", "settlement", "manual_verification"}:
            print(f"{row['section']},{row['metric']},{row['value']},{row['notes']}")
    print(f"wrote: {PREVIEW_OUT}")
    print(f"wrote: {AUDIT_OUT}")
    print("=" * 96)


if __name__ == "__main__":
    main()
