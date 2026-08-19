import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
TRUE_TRACK = DATA / "edgeiq_true_track_rating_v1.csv"
OUT = DATA / "edgeiq_surface_intelligence_feed_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_surface_intelligence_feed_v1_summary.csv"
OUT_AUDIT = DATA / "edgeiq_surface_intelligence_feed_v1_audit.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def text(value: object) -> str:
    return str(value or "").strip()


def clean(value: object) -> str:
    return "".join(ch for ch in text(value).upper() if ch.isalnum())


def num(value: object) -> float | None:
    raw = text(value).replace(",", "")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def race_date(row: dict[str, str]) -> str:
    return text(row.get("race_date") or row.get("current_race_date") or row.get("date"))


def race_no(row: dict[str, str]) -> str:
    return text(row.get("race_no") or row.get("race_number") or row.get("race"))


def is_scratched(row: dict[str, str]) -> bool:
    blob = " ".join(text(row.get(key)).upper() for key in ["display_decision", "runner_status", "scratch_status", "is_scratched"])
    return "SCRATCH" in blob or text(row.get("is_scratched")).upper() in {"YES", "TRUE", "1", "Y"}


def condition_number(condition: str) -> int | None:
    digits = "".join(ch for ch in condition if ch.isdigit())
    return int(digits) if digits else None


def normalise_condition(value: object) -> str:
    raw = text(value).upper().replace(" ", "")
    if not raw or raw in {"--", "UNKNOWN"}:
        return "UNKNOWN"
    return raw


def edgeiq_condition(row: dict[str, str]) -> str:
    return normalise_condition(row.get("edgeiq_true_track_rating") or row.get("edgeiq_condition") or row.get("true_track_band"))


def surface_delta(official: str, edgeiq: str, variant: float | None) -> tuple[str, str]:
    official_num = condition_number(official)
    edgeiq_num = condition_number(edgeiq)
    if official_num is not None and edgeiq_num is not None:
        diff = edgeiq_num - official_num
        if diff <= -2:
            return ("SIGNIFICANTLY_FIRMER", "Track has played significantly firmer than the official rating.")
        if diff == -1:
            return ("FIRMER", "Track has played slightly firmer than the official rating.")
        if diff == 0:
            return ("IN_LINE", "Track has played broadly in line with the official rating.")
        if diff == 1:
            return ("SOFTER", "Track has played slightly softer than the official rating.")
        return ("SIGNIFICANTLY_SOFTER", "Track has played significantly softer than the official rating.")
    if variant is not None:
        if variant <= -0.5:
            return ("FIRMER", "Timed evidence points firmer than the official surface read.")
        if variant >= 0.5:
            return ("SOFTER", "Timed evidence points softer than the official surface read.")
    return ("UNKNOWN", "Surface intelligence is official-rating only for this race.")


def variant_band(variant: float | None, fallback: str) -> str:
    if fallback:
        return fallback
    if variant is None:
        return "UNKNOWN"
    if variant <= -0.75:
        return "FAST_VARIANT"
    if variant >= 0.75:
        return "SLOW_VARIANT"
    return "NEUTRAL_VARIANT"


def main() -> None:
    active = [row for row in read_csv(RUNNER_BOARD) if not is_scratched(row)]
    races: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in active:
        races.setdefault((race_date(row), clean(row.get("track")), race_no(row)), row)

    exact: dict[tuple[str, str], dict[str, str]] = {}
    by_track: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_csv(TRUE_TRACK):
        track_key = clean(row.get("track"))
        exact[(race_date(row), track_key)] = row
        by_track[track_key].append(row)

    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out: list[dict[str, object]] = []
    audit: list[dict[str, object]] = []
    for key, race in sorted(races.items()):
        date, track_key, race_number = key
        profile = exact.get((date, track_key))
        match_method = "EXACT_DATE_TRACK"
        if not profile:
            profiles = by_track.get(track_key, [])
            profile = profiles[-1] if profiles else {}
            match_method = "TRACK_PROFILE_FALLBACK" if profile else "OFFICIAL_ONLY"

        official = normalise_condition(profile.get("official_condition") or race.get("track_condition"))
        edgeiq = edgeiq_condition(profile) if profile else "UNKNOWN"
        variant = num(profile.get("variant_sec"))
        delta, narrative = surface_delta(official, edgeiq, variant)
        if edgeiq == "UNKNOWN":
            edgeiq = official
        out.append(
            {
                "race_date": date,
                "track": text(race.get("track")),
                "race_no": race_number,
                "official_condition": official,
                "edgeiq_condition": edgeiq,
                "surface_delta": delta,
                "variant_band": variant_band(variant, text(profile.get("true_track_band"))),
                "variant_seconds": f"{variant:.2f}" if variant is not None else "",
                "confidence": text(profile.get("confidence_band")) or ("LOW" if match_method == "OFFICIAL_ONLY" else "UNKNOWN"),
                "surface_narrative": narrative,
                "match_method": match_method,
                "built_at": built_at,
            }
        )
        audit.append(
            {
                "race_date": date,
                "track": text(race.get("track")),
                "race_no": race_number,
                "match_method": match_method,
                "true_track_profile_found": "YES" if bool(profile) else "NO",
                "official_condition_present": "YES" if official != "UNKNOWN" else "NO",
                "edgeiq_condition_present": "YES" if edgeiq != "UNKNOWN" else "NO",
                "variant_seconds_present": "YES" if variant is not None else "NO",
            }
        )

    summary = [
        {"metric": "race_rows", "value": len(out)},
        {"metric": "exact_matches", "value": sum(1 for row in audit if row["match_method"] == "EXACT_DATE_TRACK")},
        {"metric": "track_profile_fallbacks", "value": sum(1 for row in audit if row["match_method"] == "TRACK_PROFILE_FALLBACK")},
        {"metric": "official_only", "value": sum(1 for row in audit if row["match_method"] == "OFFICIAL_ONLY")},
        {"metric": "surface_delta::SIGNIFICANTLY_FIRMER", "value": sum(1 for row in out if row["surface_delta"] == "SIGNIFICANTLY_FIRMER")},
        {"metric": "surface_delta::FIRMER", "value": sum(1 for row in out if row["surface_delta"] == "FIRMER")},
        {"metric": "surface_delta::IN_LINE", "value": sum(1 for row in out if row["surface_delta"] == "IN_LINE")},
        {"metric": "surface_delta::SOFTER", "value": sum(1 for row in out if row["surface_delta"] == "SOFTER")},
        {"metric": "surface_delta::SIGNIFICANTLY_SOFTER", "value": sum(1 for row in out if row["surface_delta"] == "SIGNIFICANTLY_SOFTER")},
        {"metric": "surface_delta::UNKNOWN", "value": sum(1 for row in out if row["surface_delta"] == "UNKNOWN")},
    ]

    fields = [
        "race_date",
        "track",
        "race_no",
        "official_condition",
        "edgeiq_condition",
        "surface_delta",
        "variant_band",
        "variant_seconds",
        "confidence",
        "surface_narrative",
        "match_method",
        "built_at",
    ]
    write_csv(OUT, out, fields)
    write_csv(OUT_AUDIT, audit, ["race_date", "track", "race_no", "match_method", "true_track_profile_found", "official_condition_present", "edgeiq_condition_present", "variant_seconds_present"])
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
