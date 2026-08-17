from pathlib import Path
import csv
import json
import re
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
MAP = DATA / "edgeiq_map_terminal_feed_v1.csv"
OUT = DATA / "edgeiq_nexus_current_runner_board_v1.csv"
SUMMARY = DATA / "edgeiq_nexus_current_runner_board_v1_summary.csv"


def text(v):
    return str(v if v is not None else "").strip()


def canon(v):
    return re.sub(r"[^A-Z0-9]+", "", text(v).upper())


def first(obj, *names):
    if not isinstance(obj, dict):
        return ""
    for name in names:
        value = obj.get(name)
        if value not in (None, ""):
            return value
    return ""


def read_csv(path):
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def runner_scratched(runner):
    official = (
        runner.get("official")
        if isinstance(runner, dict)
        and isinstance(runner.get("official"), dict)
        else {}
    )
    source = (
        runner.get("source")
        if isinstance(runner, dict)
        and isinstance(runner.get("source"), dict)
        else {}
    )

    values = [
        runner.get("scratched"),
        runner.get("is_scratched"),
        runner.get("status"),
        official.get("scratched"),
        official.get("status"),
        source.get("scratched"),
        source.get("is_scratched"),
        source.get("status"),
    ]

    return any(
        text(v).lower()
        in {
            "true",
            "scr",
            "scratched",
            "lscr",
            "late scratching",
        }
        for v in values
    )


def main():
    if not CATALOG.exists():
        raise RuntimeError(
            f"Missing governed product catalog: {CATALOG}"
        )

    payload = json.loads(
        CATALOG.read_text(
            encoding="utf-8-sig",
            errors="replace",
        )
    )

    meetings = payload.get("meetings", [])
    if not isinstance(meetings, list):
        raise RuntimeError(
            "Product catalog meetings is not a list."
        )

    map_rows = read_csv(MAP)
    map_index = {}

    for row in map_rows:
        key = (
            text(row.get("race_date"))[:10],
            canon(row.get("track")),
            text(row.get("race_no")),
            canon(row.get("horse")),
        )
        map_index[key] = row

    rows = []

    for meeting in meetings:
        if not isinstance(meeting, dict):
            continue

        meeting_date = text(
            first(
                meeting,
                "date",
                "raceDate",
                "race_date",
                "meetingDate",
            )
        )[:10]

        meeting_track = text(
            first(
                meeting,
                "track",
                "meeting",
                "venue",
                "trackName",
                "name",
            )
        )

        races = meeting.get("races", [])
        if not isinstance(races, list):
            continue

        for race in races:
            if not isinstance(race, dict):
                continue

            race_date = text(
                first(
                    race,
                    "raceDate",
                    "race_date",
                    "date",
                )
            )[:10] or meeting_date

            track = text(
                first(
                    race,
                    "track",
                    "meeting",
                    "venue",
                    "trackName",
                )
            ) or meeting_track

            race_no = text(
                first(
                    race,
                    "raceNo",
                    "race_no",
                    "number",
                    "raceNumber",
                    "no",
                )
            )

            distance = text(
                first(
                    race,
                    "distance",
                    "distanceMetres",
                    "distance_m",
                )
            )

            race_class = text(
                first(
                    race,
                    "raceClass",
                    "race_class",
                    "class",
                    "className",
                    "grade",
                )
            )

            track_condition = text(
                first(
                    race,
                    "trackCondition",
                    "track_condition",
                    "condition",
                )
            ) or text(
                first(
                    meeting,
                    "trackCondition",
                    "track_condition",
                    "condition",
                    "trackRating",
                    "track_rating",
                )
            )

            runners = race.get("runners", [])
            if not isinstance(runners, list):
                continue

            for runner in runners:
                if not isinstance(runner, dict):
                    continue

                horse = text(
                    first(
                        runner,
                        "horse",
                        "horseName",
                        "runnerName",
                        "name",
                    )
                )

                if not horse:
                    continue

                key = (
                    race_date,
                    canon(track),
                    race_no,
                    canon(horse),
                )

                map_row = map_index.get(key, {})

                trainer = text(
                    first(
                        runner,
                        "trainer",
                        "trainerName",
                    )
                )

                jockey = text(
                    first(
                        runner,
                        "jockey",
                        "jockeyName",
                    )
                )

                run_style = text(
                    first(
                        map_row,
                        "run_style",
                        "projected_position",
                    )
                ) or text(
                    first(
                        runner,
                        "projected_run_style",
                        "run_style",
                        "settling_band",
                        "speed_map_bucket",
                    )
                )

                row = {
                    "runner_key": "|".join(
                        [
                            race_date,
                            track,
                            race_no,
                            horse,
                        ]
                    ),
                    "race_date": race_date,
                    "track": track,
                    "race_no": race_no,
                    "horse": horse,
                    "trainer": trainer,
                    "jockey": jockey,
                    "distance": distance,
                    "track_condition": track_condition,
                    "race_class": race_class,
                    "run_style": run_style,
                    "projected_run_style": run_style,
                    "settling_band": "",
                    "speed_map_bucket": run_style,
                    "is_scratched": (
                        "YES"
                        if runner_scratched(runner)
                        else "NO"
                    ),
                    "source": (
                        "EDGEIQ_THREE_DAY_PRODUCT_CATALOG_V1"
                    ),
                    "run_style_source": (
                        "EDGEIQ_MAP_TERMINAL_FEED_V1"
                        if map_row
                        else "PRODUCT_CATALOG"
                    ),
                }

                rows.append(row)

    fields = [
        "runner_key",
        "race_date",
        "track",
        "race_no",
        "horse",
        "trainer",
        "jockey",
        "distance",
        "track_condition",
        "race_class",
        "run_style",
        "projected_run_style",
        "settling_band",
        "speed_map_bucket",
        "is_scratched",
        "source",
        "run_style_source",
    ]

    write_csv(OUT, rows, fields)

    dates = sorted(
        {
            text(r["race_date"])[:10]
            for r in rows
            if text(r["race_date"])
        }
    )

    races = {
        (
            r["race_date"],
            canon(r["track"]),
            r["race_no"],
        )
        for r in rows
    }

    missing_trainer = sum(
        1 for r in rows if not text(r["trainer"])
    )
    missing_jockey = sum(
        1 for r in rows if not text(r["jockey"])
    )
    missing_style = sum(
        1 for r in rows if not text(r["run_style"])
    )

    summary = [
        {
            "metric": "built_at",
            "value": datetime.now(
                timezone.utc
            ).isoformat(timespec="seconds"),
        },
        {
            "metric": "source",
            "value": CATALOG.name,
        },
        {
            "metric": "rows",
            "value": len(rows),
        },
        {
            "metric": "races",
            "value": len(races),
        },
        {
            "metric": "dates",
            "value": "|".join(dates),
        },
        {
            "metric": "missing_trainer",
            "value": missing_trainer,
        },
        {
            "metric": "missing_jockey",
            "value": missing_jockey,
        },
        {
            "metric": "missing_run_style",
            "value": missing_style,
        },
    ]

    write_csv(
        SUMMARY,
        summary,
        ["metric", "value"],
    )

    print(
        "NEXUS_CURRENT_RUNNER_BOARD=PASS"
    )
    print(
        f"ROWS={len(rows)}"
    )
    print(
        f"RACES={len(races)}"
    )
    print(
        "DATES=" + "|".join(dates)
    )
    print(
        f"MISSING_TRAINER={missing_trainer}"
    )
    print(
        f"MISSING_JOCKEY={missing_jockey}"
    )
    print(
        f"MISSING_RUN_STYLE={missing_style}"
    )


if __name__ == "__main__":
    main()
