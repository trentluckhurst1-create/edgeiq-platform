import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
TRUE_TRACK = DATA / "edgeiq_true_track_rating_v1.csv"

OUT = DATA / "edgeiq_current_true_track_feed_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_current_true_track_feed_v1_summary.csv"
OUT_AUDIT = DATA / "edgeiq_current_true_track_feed_v1_audit.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def text(value: object) -> str:
    return str(value or "").strip()


def clean(value: object) -> str:
    return "".join(ch for ch in text(value).upper() if ch.isalnum())


def race_date(row: dict[str, str]) -> str:
    return text(row.get("race_date") or row.get("current_race_date") or row.get("date"))


def race_no(row: dict[str, str]) -> str:
    return text(row.get("race_no") or row.get("race_number") or row.get("race"))


def is_scratched(row: dict[str, str]) -> bool:
    return "SCRATCH" in " ".join(text(row.get(key)).upper() for key in ["display_decision", "runner_status", "scratch_status", "is_scratched"])


def condition_group(value: str) -> str:
    upper = value.upper().replace(" ", "")
    if upper.startswith("HEAVY"):
        return "HEAVY"
    if upper.startswith("SOFT"):
        return "SOFT"
    if upper.startswith("GOOD"):
        return "GOOD"
    if upper.startswith("FAST") or upper.startswith("FIRM"):
        return "FAST"
    return upper or "UNKNOWN"


def main() -> None:
    active = [row for row in read_csv(RUNNER_BOARD) if not is_scratched(row)]
    races: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in active:
        key = (race_date(row), clean(row.get("track")), race_no(row))
        races.setdefault(key, row)

    history_by_track: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    exact: dict[tuple[str, str], dict[str, str]] = {}
    for row in read_csv(TRUE_TRACK):
        history_by_track[clean(row.get("track"))].append(row)
        exact[(race_date(row), clean(row.get("track")))] = row

    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = []
    audit = []
    for key, race in sorted(races.items()):
        date, track_key, race_number = key
        official = text(race.get("track_condition")) or "UNKNOWN"
        source = exact.get((date, track_key))
        fallback_rows = history_by_track.get(track_key, [])
        fallback = fallback_rows[-1] if fallback_rows else {}
        used = source or fallback
        edgeiq_condition = text(used.get("edgeiq_true_track_rating")) or official
        official_group = condition_group(official)
        edgeiq_group = condition_group(edgeiq_condition)
        if source:
            variant = text(source.get("true_track_band")) or "CURRENT_MATCH"
            match_method = "EXACT_DATE_TRACK"
        elif used:
            variant = "HISTORICAL_TRACK_PROFILE"
            match_method = "TRACK_PROFILE_FALLBACK"
        else:
            variant = "OFFICIAL_ONLY"
            match_method = "OFFICIAL_ONLY"
        if official_group == edgeiq_group:
            surface_delta = "ALIGNED"
        elif edgeiq_group in {"SOFT", "HEAVY"} and official_group in {"GOOD", "FAST"}:
            surface_delta = "PLAYS_SOFTER"
        elif edgeiq_group in {"GOOD", "FAST"} and official_group in {"SOFT", "HEAVY"}:
            surface_delta = "PLAYS_FIRMER"
        else:
            surface_delta = "WATCH"
        summary = text(used.get("track_rating_narrative")) or f"Official condition is {official}. EDGEiQ current read is {edgeiq_condition}."
        out.append(
            {
                "race_date": date,
                "track": text(race.get("track")),
                "race_no": race_number,
                "official_condition": official,
                "edgeiq_condition": edgeiq_condition,
                "surface_delta": surface_delta,
                "variant_summary": summary,
                "variant_band": variant,
                "confidence_band": text(used.get("confidence_band")) or "LOW",
                "match_method": match_method,
                "built_at": built_at,
            }
        )
        audit.append({"race_date": date, "track": text(race.get("track")), "race_no": race_number, "match_method": match_method})

    write_csv(OUT, out, ["race_date", "track", "race_no", "official_condition", "edgeiq_condition", "surface_delta", "variant_summary", "variant_band", "confidence_band", "match_method", "built_at"])
    write_csv(OUT_AUDIT, audit, ["race_date", "track", "race_no", "match_method"])
    summary = [
        {"metric": "race_rows", "value": len(out)},
        {"metric": "exact_matches", "value": sum(1 for row in out if row["match_method"] == "EXACT_DATE_TRACK")},
        {"metric": "profile_fallbacks", "value": sum(1 for row in out if row["match_method"] == "TRACK_PROFILE_FALLBACK")},
        {"metric": "official_only", "value": sum(1 for row in out if row["match_method"] == "OFFICIAL_ONLY")},
    ]
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
