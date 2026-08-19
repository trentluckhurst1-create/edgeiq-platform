from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RACE_FILE = ROOT / "src" / "edgeiq-os" / "race" / "RaceFileV3.tsx"
MEETINGS_WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingsWorkspace.tsx"
REPORT_DIR = ROOT / "docs" / "full-product-implementation"
CSV_REPORT = REPORT_DIR / "EDGEIQ_NAVIGATION_STATE_CONFORMANCE_AUDIT_V1.csv"
MD_REPORT = REPORT_DIR / "EDGEIQ_NAVIGATION_STATE_CONFORMANCE_AUDIT_V1.md"


CHECKS = [
    {
        "id": "NAVIGATION_AUDIT_MARKER",
        "file": RACE_FILE,
        "required": 'EDGEIQ_NAVIGATION_STATE_EXPLICIT_SELECTION_V1',
        "description": "RaceFile has the explicit-selection navigation audit marker.",
    },
    {
        "id": "RESTORE_ONE_SHOT_GUARD",
        "file": RACE_FILE,
        "required": "if (!hasStoredRaceContext || restoreAttempted) return;",
        "description": "Persisted workspace restore cannot rerun after it has completed.",
    },
    {
        "id": "STALE_RESTORE_CANCELLED",
        "file": RACE_FILE,
        "required": "explicitSelectionEpoch.current !== restoreEpoch",
        "description": "Async persisted restore is ignored after explicit user selection.",
    },
    {
        "id": "DAY_CHANGE_CLEARS_MEETING",
        "file": RACE_FILE,
        "required": "setSelectedMeeting(null);",
        "description": "Changing day clears stale selected meeting context.",
    },
    {
        "id": "DAY_CHANGE_CLEARS_RACE",
        "file": RACE_FILE,
        "required": "setSelectedRace(null);",
        "description": "Changing day clears stale selected race context.",
    },
    {
        "id": "MEETING_SELECT_IS_NOT_OPEN",
        "file": MEETINGS_WORKSPACE,
        "required": "onSelect={() => onSelectMeeting(meeting.rawMeeting)}",
        "description": "Meetings table selection writes canonical selected meeting state.",
    },
    {
        "id": "RESTORE_LOADING_GUARD",
        "file": RACE_FILE,
        "required": "isWaitingForRestoredMeetingContext",
        "description": "Meeting workspace cannot mount before persisted selected meeting context is restored.",
    },
]


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    for check in CHECKS:
        text = check["file"].read_text(encoding="utf-8")
        passed = check["required"] in text
        rows.append(
            {
                "check_id": check["id"],
                "status": "PASS" if passed else "FAIL",
                "file": str(check["file"].relative_to(ROOT)),
                "description": check["description"],
                "required_token": check["required"],
            }
        )

    stale_open = "onSelect={() => onOpenMeeting(meeting.rawMeeting)}" in MEETINGS_WORKSPACE.read_text(
        encoding="utf-8"
    )
    rows.append(
        {
            "check_id": "NO_STALE_OPEN_ON_ROW_SELECT",
            "status": "FAIL" if stale_open else "PASS",
            "file": str(MEETINGS_WORKSPACE.relative_to(ROOT)),
            "description": "Meetings table row selection must not call onOpenMeeting directly.",
            "required_token": "absence:onSelect={() => onOpenMeeting(meeting.rawMeeting)}",
        }
    )

    with CSV_REPORT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["check_id", "status", "file", "description", "required_token"],
        )
        writer.writeheader()
        writer.writerows(rows)

    failed = [row for row in rows if row["status"] != "PASS"]
    lines = [
        "# EDGEiQ Navigation State Conformance Audit V1",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "| Check | Status | File | Description |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['check_id']} | {row['status']} | `{row['file']}` | {row['description']} |"
        )
    lines.extend(
        [
            "",
            "Required browser regression sequence:",
            "",
            "1. Open Meetings, select Flemington, open meeting, confirm header Flemington.",
            "2. Return to Meetings, select Wangaratta, open meeting, confirm header Wangaratta.",
            "3. Return to Meetings, select Flemington, open meeting, confirm header Flemington.",
            "4. Refresh and confirm header remains Flemington.",
            "",
            "Result: " + ("FAIL" if failed else "PASS"),
        ]
    )
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="")

    print(f"CSV report: {CSV_REPORT}")
    print(f"Markdown report: {MD_REPORT}")
    if failed:
        for row in failed:
            print(f"FAIL {row['check_id']}: {row['description']}")
        raise SystemExit(1)
    print("EDGEIQ_NAVIGATION_STATE_CONFORMANCE_AUDIT_PASS")


if __name__ == "__main__":
    main()
