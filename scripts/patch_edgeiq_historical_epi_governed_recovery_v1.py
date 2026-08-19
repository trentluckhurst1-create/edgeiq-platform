from __future__ import annotations

from datetime import datetime
from pathlib import Path
import py_compile
import shutil

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
TARGET = ROOT / "scripts" / "build_edgeiq_epi_workspace_terminal_feed_v1.py"
CHECKPOINT_ROOT = ROOT / "checkpoints"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT = CHECKPOINT_ROOT / f"EDGEIQ_BEFORE_HISTORICAL_EPI_GOVERNED_RECOVERY_{STAMP}"
BACKUP = CHECKPOINT / "scripts" / TARGET.name

if not TARGET.exists():
    raise SystemExit(f"TARGET_NOT_FOUND={TARGET}")

CHECKPOINT.mkdir(parents=True, exist_ok=True)
BACKUP.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(TARGET, BACKUP)

text = TARGET.read_text(encoding="utf-8-sig")

old_constant = '''TRACE = DATA / "edgeiq_epi_workspace_engineering_build_v1_trace.txt"
'''

new_constant = '''TRACE = DATA / "edgeiq_epi_workspace_engineering_build_v1_trace.txt"
HISTORICAL_EPI_CONFLICTS = DATA / "edgeiq_historical_epi_lookup_conflicts_v1.csv"
'''

if old_constant not in text:
    raise SystemExit("PATCH_BLOCK_NOT_FOUND=TRACE_CONSTANT")

text = text.replace(old_constant, new_constant, 1)

old_normalise_block = '''def normalise(value: Any) -> str:
    return "".join(ch for ch in clean(value).upper() if ch.isalnum())


def number_text(value: Any) -> str:
'''

new_normalise_block = '''def normalise(value: Any) -> str:
    return "".join(ch for ch in clean(value).upper() if ch.isalnum())


TRACK_ALIASES = {
    # Flemington
    "FLEMINGTON": "FLEM",
    "FLEM": "FLEM",

    # Caulfield / Caulfield Heath
    "CAULFIELD": "CAUL",
    "CAUL": "CAUL",
    "CAULFIELDHEATH": "CAUH",
    "CAUH": "CAUH",

    # Sandown
    "SANDOWN": "SANL",
    "SPORTSBETSANDOWNLAKESIDE": "SANL",
    "SANDOWNLAKESIDE": "SANL",
    "SANL": "SANL",
    "SPORTSBETSANDOWNHILLSIDE": "SANH",
    "SANDOWNHILLSIDE": "SANH",
    "SANH": "SANH",

    # Pakenham
    "PAKENHAM": "PAKM",
    "SOUTHSIDEPAKENHAM": "PAKM",
    "PAKM": "PAKM",
    "PAKENHAMSYNTHETIC": "PAKS",
    "SPORTSBETPAKENHAMSYNTHETIC": "PAKS",
    "PAKS": "PAKS",

    # Cranbourne
    "CRANBOURNE": "CRAN",
    "SOUTHSIDECRANBOURNE": "CRAN",
    "CRAN": "CRAN",

    # Geelong
    "GEELONG": "GEEL",
    "LADBROKESGEELONG": "GEEL",
    "GEEL": "GEEL",

    # Ballarat
    "BALLARAT": "BRAT",
    "SPORTSBETBALLARAT": "BRAT",
    "BRAT": "BRAT",
    "BALLARATSYNTHETIC": "BALS",
    "SPORTSBETBALLARATSYNTHETIC": "BALS",
    "BALS": "BALS",

    # Other Victorian tracks
    "WARRNAMBOOL": "WNBL",
    "WNBL": "WNBL",
    "WERRIBEE": "WERR",
    "PICKLEBETPARKWERRIBEE": "WERR",
    "WERR": "WERR",
    "MORNINGTON": "MORN",
    "MORN": "MORN",
    "WANGARATTA": "WANG",
    "SPORTSBETWANGARATTA": "WANG",
    "WANG": "WANG",
    "KYNETON": "KYNE",
    "BET365PARKKYNETON": "KYNE",
    "KYNE": "KYNE",
    "ECHUCA": "ECHA",
    "BET365ECHUCA": "ECHA",
    "ECHA": "ECHA",
    "SEYMOUR": "SEYM",
    "BET365SEYMOUR": "SEYM",
    "SEYM": "SEYM",
    "HORSHAM": "HSHM",
    "HSHM": "HSHM",
    "TERANG": "TER",
    "BET365TERANG": "TER",
    "TER": "TER",
    "COLAC": "CLAC",
    "BET365COLAC": "CLAC",
    "CLAC": "CLAC",
    "DONALD": "DON",
    "DON": "DON",
    "TATURA": "TAT",
    "TAT": "TAT",
    "ARARAT": "ARAT",
    "ARAT": "ARAT",
    "BENDIGO": "BDGO",
    "BDGO": "BDGO",
    "SALE": "SALE",
    "MOE": "MOE",
    "BENALLA": "BEN",
    "BEN": "BEN",
    "HAMILTON": "HAM",
    "HAM": "HAM",
    "SWANHILL": "SWAN",
    "SWAN": "SWAN",
    "MILDURA": "MILD",
    "MILD": "MILD",
    "STAWELL": "STAW",
    "STAW": "STAW",
    "CASTERTON": "CAST",
    "CAST": "CAST",
}


def canonical_track(value: Any) -> str:
    key = normalise(value)
    return TRACK_ALIASES.get(key, key)


def number_text(value: Any) -> str:
'''

if old_normalise_block not in text:
    raise SystemExit("PATCH_BLOCK_NOT_FOUND=NORMALISE_BLOCK")

text = text.replace(old_normalise_block, new_normalise_block, 1)

old_collect = '''def collect_historical_keys(form_races: dict[tuple[str, str, str], dict[str, Any]]) -> set[tuple[str, str, str, str]]:
    keys: set[tuple[str, str, str, str]] = set()
    for race in form_races.values():
        for runner in race.get("runners", []) or []:
            horse_key = runner_match_key(runner.get("runnerName"))
            for run in runner.get("fullForm", []) or []:
                distance = number_text(run.get("distance"))
                key = (horse_key, clean(run.get("date")), normalise(run.get("track")), distance)
                if horse_key and key[1] and key[2]:
                    keys.add(key)
    return keys
'''

new_collect = '''def collect_historical_keys(form_races: dict[tuple[str, str, str], dict[str, Any]]) -> set[tuple[str, str, str, str]]:
    keys: set[tuple[str, str, str, str]] = set()
    for race in form_races.values():
        for runner in race.get("runners", []) or []:
            horse_key = runner_match_key(runner.get("runnerName"))
            for run in runner.get("fullForm", []) or []:
                distance = number_text(run.get("distance"))
                key = (
                    horse_key,
                    clean(run.get("date")),
                    canonical_track(run.get("track")),
                    distance,
                )
                if horse_key and key[1] and key[2]:
                    keys.add(key)
    return keys
'''

if old_collect not in text:
    raise SystemExit("PATCH_BLOCK_NOT_FOUND=COLLECT_HISTORICAL_KEYS")

text = text.replace(old_collect, new_collect, 1)

old_index = '''def historical_rating_index(required_keys: set[tuple[str, str, str, str]]) -> dict[tuple[str, str, str, str], dict[str, str]]:
    index: dict[tuple[str, str, str, str], dict[str, str]] = {}
    if not required_keys:
        return index
    for row in read_csv_rows(HISTORICAL_RATING) or []:
        horse = runner_match_key(row.get("horse"))
        date = clean(row.get("race_date"))
        track = normalise(row.get("track"))
        distance = number_text(row.get("distance"))
        key = (horse, date, track, distance)
        if key in required_keys and key not in index:
            index[key] = row
    return index
'''

new_index = '''def historical_rating_index(
    required_keys: set[tuple[str, str, str, str]]
) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
    governed: dict[tuple[str, str, str, str], dict[str, Any]] = {}

    if not required_keys:
        return governed

    for row in read_csv_rows(HISTORICAL_RATING) or []:
        horse = runner_match_key(row.get("horse"))
        date = clean(row.get("race_date"))
        track = canonical_track(row.get("track"))
        distance = number_text(row.get("distance"))
        key = (horse, date, track, distance)

        if key in required_keys:
            grouped.setdefault(key, []).append(row)

    conflicts: list[dict[str, str]] = []

    for key, rows in grouped.items():
        rated_rows: list[tuple[float, dict[str, str]]] = []

        for row in rows:
            rating = metric_float(row.get("performance_rating_v6_1_research"))
            if rating is not None:
                rated_rows.append((rating, row))

        unique_ratings = sorted({rating for rating, _ in rated_rows})

        if len(unique_ratings) == 1:
            rating = unique_ratings[0]

            source_files = sorted(
                {
                    clean(row.get("source_file")) or clean(row.get("_source_file"))
                    for _, row in rated_rows
                    if clean(row.get("source_file")) or clean(row.get("_source_file"))
                }
            )

            built_values = sorted(
                {
                    clean(row.get("built_at_v6_1_research"))
                    for _, row in rated_rows
                    if clean(row.get("built_at_v6_1_research"))
                }
            )

            governed[key] = {
                "status": "UNIQUE" if len(rows) == 1 else "SAME_RATING_MULTIPLE_ROWS",
                "rating": rating,
                "source_files": source_files,
                "built_at": built_values[-1] if built_values else "",
                "match_count": len(rows),
            }
            continue

        if len(unique_ratings) > 1:
            horse, date, track, distance = key
            source_files = sorted(
                {
                    clean(row.get("source_file")) or clean(row.get("_source_file"))
                    for row in rows
                    if clean(row.get("source_file")) or clean(row.get("_source_file"))
                }
            )

            governed[key] = {
                "status": "CONFLICTING_RATINGS",
                "rating": None,
                "ratings": unique_ratings,
                "source_files": source_files,
                "built_at": "",
                "match_count": len(rows),
            }

            conflicts.append(
                {
                    "horse_key": horse,
                    "race_date": date,
                    "canonical_track": track,
                    "distance": distance,
                    "match_count": str(len(rows)),
                    "candidate_ratings": " | ".join(
                        f"{rating:.10g}" for rating in unique_ratings
                    ),
                    "source_files": " | ".join(source_files),
                    "decision": "HISTORICAL_EPI_UNAVAILABLE_CONFLICT",
                }
            )
            continue

        governed[key] = {
            "status": "NO_RATED_ROWS",
            "rating": None,
            "source_files": [],
            "built_at": "",
            "match_count": len(rows),
        }

    conflict_fields = [
        "horse_key",
        "race_date",
        "canonical_track",
        "distance",
        "match_count",
        "candidate_ratings",
        "source_files",
        "decision",
    ]

    with HISTORICAL_EPI_CONFLICTS.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=conflict_fields)
        writer.writeheader()
        writer.writerows(
            sorted(
                conflicts,
                key=lambda row: (
                    row["horse_key"],
                    row["race_date"],
                    row["canonical_track"],
                    row["distance"],
                ),
            )
        )

    return governed
'''

if old_index not in text:
    raise SystemExit("PATCH_BLOCK_NOT_FOUND=HISTORICAL_RATING_INDEX")

text = text.replace(old_index, new_index, 1)

old_lookup = '''def historical_epi_for_run(runner: dict[str, Any], run: dict[str, Any], historical: dict[tuple[str, str, str, str], dict[str, str]]) -> tuple[float | None, str, str]:
    direct = metric_float(run.get("historicalEpi"))
    if direct is not None:
        value = run.get("historicalEpi") if isinstance(run.get("historicalEpi"), dict) else {}
        return direct, clean(value.get("source")) or "edgeiq_form_guide_enriched_v2.json:historicalEpi", clean(value.get("version") or value.get("asAt"))
    key = (
        runner_match_key(runner.get("runnerName")),
        clean(run.get("date")),
        normalise(run.get("track")),
        number_text(run.get("distance")),
    )
    row = historical.get(key)
    if not row:
        return None, "", ""
    rating = metric_float(row.get("performance_rating_v6_1_research"))
    return (
        rating,
        "edgeiq_historical_performance_rating_v6_1_research.csv:performance_rating_v6_1_research" if rating is not None else "",
        clean(row.get("built_at_v6_1_research")),
    )
'''

new_lookup = '''def historical_epi_for_run(
    runner: dict[str, Any],
    run: dict[str, Any],
    historical: dict[tuple[str, str, str, str], dict[str, Any]],
) -> tuple[float | None, str, str]:
    direct = metric_float(run.get("historicalEpi"))

    if direct is not None:
        value = (
            run.get("historicalEpi")
            if isinstance(run.get("historicalEpi"), dict)
            else {}
        )
        return (
            direct,
            clean(value.get("source"))
            or "edgeiq_form_guide_enriched_v2.json:historicalEpi",
            clean(value.get("version") or value.get("asAt")),
        )

    key = (
        runner_match_key(runner.get("runnerName")),
        clean(run.get("date")),
        canonical_track(run.get("track")),
        number_text(run.get("distance")),
    )

    result = historical.get(key)

    if not result:
        return None, "", ""

    if result.get("status") not in {
        "UNIQUE",
        "SAME_RATING_MULTIPLE_ROWS",
    }:
        return None, "", ""

    rating = metric_float(result.get("rating"))

    if rating is None:
        return None, "", ""

    status = clean(result.get("status"))
    source_suffix = (
        ":same_rating_duplicates_collapsed"
        if status == "SAME_RATING_MULTIPLE_ROWS"
        else ""
    )

    return (
        rating,
        (
            "edgeiq_historical_performance_rating_v6_1_research.csv:"
            "performance_rating_v6_1_research"
            f"{source_suffix}"
        ),
        clean(result.get("built_at")),
    )
'''

if old_lookup not in text:
    raise SystemExit("PATCH_BLOCK_NOT_FOUND=HISTORICAL_EPI_FOR_RUN")

text = text.replace(old_lookup, new_lookup, 1)

TARGET.write_text(text, encoding="utf-8")
py_compile.compile(str(TARGET), doraise=True)

print("EDGEIQ HISTORICAL EPI GOVERNED RECOVERY PATCH")
print("=" * 100)
print(f"TARGET={TARGET}")
print(f"BACKUP={BACKUP}")
print("PATCHED=TRACE_CONSTANT")
print("PATCHED=CANONICAL_TRACK_GOVERNANCE")
print("PATCHED=COLLECT_HISTORICAL_KEYS")
print("PATCHED=HISTORICAL_RATING_INDEX")
print("PATCHED=HISTORICAL_EPI_FOR_RUN")
print("PYTHON_COMPILE=PASS")
print("EDGEIQ_HISTORICAL_EPI_GOVERNED_RECOVERY_PATCH_PASS")
