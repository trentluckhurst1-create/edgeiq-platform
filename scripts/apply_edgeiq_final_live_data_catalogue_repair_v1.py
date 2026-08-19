from pathlib import Path

path = Path('scripts/build_edgeiq_three_day_product_catalog_v1.py')
text = path.read_text(encoding='utf-8')

text = text.replace(
'''CSV_SOURCES = [
    RACE_LIST,
    DATA / "race_fields.csv",
    DATA / "edgeiq_vic_three_day_race_fields.csv",
    DATA / "edgeiq_vic_three_day_meeting_universe.csv",
    DATA / "edgeiq_tab_calendar_racecards_vic_v1.csv",
]
''',
'''CSV_SOURCES = [
    DATA / "edgeiq_vic_three_day_meeting_calendar_v1.csv",
    RACE_LIST,
    DATA / "race_fields.csv",
    DATA / "edgeiq_vic_three_day_race_fields.csv",
    DATA / "edgeiq_vic_three_day_meeting_universe.csv",
    DATA / "edgeiq_tab_calendar_racecards_vic_v1.csv",
]
''')

text = text.replace(
'''def meeting_display_name(value: Any) -> str:
    text = clean_text(value) or ""

    text = re.sub(
        r"^(SPORTSBET|LADBROKES|BET365)[-\\s]+",
        "",
        text,
        flags=re.IGNORECASE,
    )

    return re.sub(r"\\s+", " ", text).strip()
''',
'''def meeting_display_name(value: Any) -> str:
    text = clean_text(value) or ""

    text = re.sub(
        r"^(SPORTSBET|LADBROKES|BET365)[-\\s]+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"SYNTHETIC(?:THETIC)+",
        "SYNTHETIC",
        text,
        flags=re.IGNORECASE,
    )

    return re.sub(r"\\s+", " ", text).strip()
''')

text = text.replace(
'''def add_csv_sources() -> None:
    for path in CSV_SOURCES:
''',
'''def current_csv_meeting_identities() -> set[tuple[str, str]]:
    identities: set[tuple[str, str]] = set()

    for path in CSV_SOURCES:
        if not path.exists():
            continue

        try:
            with path.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as handle:
                rows = list(csv.DictReader(handle))
        except Exception:
            continue

        for row in rows:
            date_value = parse_date(first(row, DATE_KEYS))
            name_value = clean_text(first(row, MEETING_KEYS))
            if date_value in TARGET_DATE_SET and name_value and is_victorian_meeting(name_value) and not excluded_event(row):
                identities.add((date_value, meeting_key(name_value)))

    return identities


def add_csv_sources() -> None:
    for path in CSV_SOURCES:
''')

text = text.replace(
'''            if (
                date_value not in TARGET_DATE_SET
                or not name_value
                or not is_victorian_meeting(name_value)
                or excluded_event(row)
                or race_number is None
            ):
                continue

            grouped[
                (
                    date_value,
                    meeting_key(name_value),
                    race_number,
                )
            ].append(row)
''',
'''            if (
                date_value not in TARGET_DATE_SET
                or not name_value
                or not is_victorian_meeting(name_value)
                or excluded_event(row)
            ):
                continue

            ensure_meeting(name_value, date_value, row)

            if race_number is None:
                continue

            grouped[
                (
                    date_value,
                    meeting_key(name_value),
                    race_number,
                )
            ].append(row)
''')

text = text.replace(
'''add_csv_sources()

meeting_rows = list(meetings.values())
''',
'''add_csv_sources()

valid_csv_identities = current_csv_meeting_identities()
if valid_csv_identities:
    meetings = {
        identity: meeting
        for identity, meeting in meetings.items()
        if identity in valid_csv_identities
    }

meeting_rows = list(meetings.values())
''')

path.write_text(text, encoding='utf-8')
print('EDGEIQ_PRODUCT_CATALOG_SOURCE_RECONCILIATION_PATCHED')
