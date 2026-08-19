from __future__ import annotations

import importlib.util
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
BUILDER = ROOT / "scripts" / "build_edgeiq_epi_workspace_terminal_feed_v1.py"
OUT = (
    ROOT
    / "docs"
    / "full-product-implementation"
    / "EPI_CATALOG_FORM_RACE_KEY_JOIN_AUDIT.txt"
)

spec = importlib.util.spec_from_file_location(
    "edgeiq_epi_join_audit",
    BUILDER,
)

if spec is None or spec.loader is None:
    raise SystemExit("BUILDER_IMPORT_FAILED")

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

catalog = module.read_json(module.CATALOG)
form_payload = module.read_json(module.FORM_GUIDE)

catalog_pairs = module.catalog_races(catalog)
form_index = module.form_race_index(form_payload)

form_rows: list[dict[str, Any]] = []

for race in form_payload.get("races", []) if isinstance(form_payload, dict) else []:
    if not isinstance(race, dict):
        continue

    date = module.clean(race.get("raceDate"))
    meeting = module.clean(race.get("meeting"))
    race_no = module.number_text(race.get("raceNumber"))
    key = module.race_match_key(date, meeting, race_no)

    form_rows.append(
        {
            "date": date,
            "meeting": meeting,
            "race_no": race_no,
            "key": key,
            "runner_count": len(race.get("runners", []) or []),
        }
    )

report = [
    "EDGEIQ CATALOG ↔ FORM GUIDE RACE-KEY JOIN AUDIT",
    "=" * 120,
    "",
    f"CATALOG_RACES={len(catalog_pairs)}",
    f"FORM_GUIDE_RACES={len(form_rows)}",
    f"FORM_INDEX_KEYS={len(form_index)}",
    "",
]

exact_matches = 0
date_race_candidates = 0
date_only_candidates = 0

for sequence, (meeting, race) in enumerate(catalog_pairs, start=1):
    catalog_date = module.clean(
        meeting.get("date")
        or race.get("raceDate")
        or race.get("date")
    )

    catalog_meeting_candidates = [
        meeting.get("meeting"),
        meeting.get("track"),
        meeting.get("venue"),
        meeting.get("meetingName"),
        race.get("meeting"),
        race.get("track"),
        race.get("venue"),
        race.get("meetingName"),
    ]

    catalog_meeting_values = []

    for value in catalog_meeting_candidates:
        cleaned = module.clean(value)

        if cleaned and cleaned not in catalog_meeting_values:
            catalog_meeting_values.append(cleaned)

    catalog_meeting = (
        catalog_meeting_values[0]
        if catalog_meeting_values
        else ""
    )

    catalog_race_no = module.number_text(
        race.get("raceNumber")
        or race.get("raceNo")
        or race.get("number")
    )

    current_key = module.race_match_key(
        catalog_date,
        catalog_meeting,
        catalog_race_no,
    )

    exact = form_index.get(current_key)

    if exact:
        exact_matches += 1

    same_date_race = [
        row
        for row in form_rows
        if row["date"] == catalog_date
        and row["race_no"] == catalog_race_no
    ]

    same_date = [
        row
        for row in form_rows
        if row["date"] == catalog_date
    ]

    if same_date_race:
        date_race_candidates += 1

    if same_date:
        date_only_candidates += 1

    candidate_pool = same_date_race or same_date or form_rows

    ranked_candidates = []

    for row in candidate_pool:
        best_similarity = 0.0
        best_catalog_name = catalog_meeting

        for candidate_name in catalog_meeting_values or [""]:
            similarity = SequenceMatcher(
                None,
                module.normalise(candidate_name),
                module.normalise(row["meeting"]),
            ).ratio()

            if similarity > best_similarity:
                best_similarity = similarity
                best_catalog_name = candidate_name

        ranked_candidates.append(
            (
                best_similarity,
                row,
                best_catalog_name,
            )
        )

    ranked_candidates.sort(
        key=lambda item: (
            item[0],
            item[1]["date"] == catalog_date,
            item[1]["race_no"] == catalog_race_no,
        ),
        reverse=True,
    )

    report.extend(
        [
            f"CATALOG_RACE_{sequence}",
            "-" * 120,
            f"CATALOG_DATE={catalog_date!r}",
            f"CATALOG_MEETING_SELECTED={catalog_meeting!r}",
            f"CATALOG_MEETING_CANDIDATES={catalog_meeting_values!r}",
            f"CATALOG_RACE_NO={catalog_race_no!r}",
            f"CATALOG_KEY={current_key!r}",
            f"EXACT_MATCH={'YES' if exact else 'NO'}",
            f"SAME_DATE_RACE_CANDIDATES={len(same_date_race)}",
            f"SAME_DATE_CANDIDATES={len(same_date)}",
            "",
            "TOP FORM GUIDE CANDIDATES",
        ]
    )

    for rank, (similarity, row, matched_name) in enumerate(
        ranked_candidates[:5],
        start=1,
    ):
        report.append(
            " | ".join(
                [
                    f"RANK={rank}",
                    f"SIMILARITY={similarity:.3f}",
                    f"CATALOG_NAME={matched_name!r}",
                    f"FORM_DATE={row['date']!r}",
                    f"FORM_MEETING={row['meeting']!r}",
                    f"FORM_RACE_NO={row['race_no']!r}",
                    f"FORM_KEY={row['key']!r}",
                    f"RUNNERS={row['runner_count']}",
                ]
            )
        )

    report.append("")

report.extend(
    [
        "=" * 120,
        "SUMMARY",
        "-" * 120,
        f"EXACT_MATCHES={exact_matches}",
        f"CATALOG_RACES_WITH_SAME_DATE_RACE_CANDIDATE={date_race_candidates}",
        f"CATALOG_RACES_WITH_SAME_DATE_CANDIDATE={date_only_candidates}",
    ]
)

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(report), encoding="utf-8")

print("\n".join(report))
print(f"WROTE={OUT}")
print("EDGEIQ_CATALOG_FORM_RACE_KEY_JOIN_AUDIT_PASS")
