from __future__ import annotations

import csv
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HISTORICAL_RUN_STYLE = DATA / "edgeiq_historical_run_style_v1.csv"
HISTORICAL_RESULTS_SUMMARY = DATA / "edgeiq_historical_results_warehouse_v2_graphql_summary.csv"
TRACK_PROFILE = DATA / "edgeiq_track_profile_v1.csv"
LIVE_RUNNER_BOARD = DATA / "edgeiq_live_runner_board_governed_v1.csv"
RACE_LIST = DATA / "edgeiq_vic_three_day_race_list_v1.csv"
RACE_SHAPE = DATA / "edgeiq_race_shape_fallback_engine_v1.csv"

OUT_ENGINE = DATA / "edgeiq_track_bias_engine_v1.csv"
OUT_LIVE = DATA / "edgeiq_live_track_bias_feed_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_track_bias_engine_summary_v1.csv"

TRACK_ALIASES = {
    "SPORTSBETSANDOWNLAKESIDE": "SANL",
    "SANDOWNLAKESIDE": "SANL",
    "SPORTSBETSANDOWNHILLSIDE": "SANH",
    "SANDOWNHILLSIDE": "SANH",
    "SPORTSBETBALLARATSYNTHETIC": "BALLARAT",
    "BALLARATSYNTHETIC": "BALLARAT",
    "BET365SEYMOUR": "SEYM",
    "SEYMOUR": "SEYM",
    "LADBROKESGEELONG": "GEEL",
    "GEELONG": "GEEL",
    "PAKENHAM": "PAKM",
    "PAKENHAMSYNTHETIC": "PAKM",
    "FLEMINGTON": "FLEM",
    "CAULFIELD": "CAUL",
    "WERRIBEE": "WERR",
}


ENGINE_FIELDS = [
    "track",
    "track_key",
    "distance_band",
    "condition_band",
    "field_size_band",
    "rail_bucket",
    "run_style",
    "context_sample",
    "style_sample",
    "wins",
    "places",
    "win_pct",
    "place_pct",
    "baseline_win_pct",
    "baseline_place_pct",
    "style_advantage_score",
    "bias_band",
    "confidence",
    "sample_band",
    "track_profile_label",
    "track_profile_confidence",
    "roi_status",
    "ae_status",
    "bias_summary",
    "built_at",
]

LIVE_FIELDS = [
    "race_date",
    "day_bucket",
    "track",
    "normalised_track",
    "race_no",
    "race_key",
    "distance",
    "distance_band",
    "track_condition",
    "condition_band",
    "field_size",
    "field_size_band",
    "rail_position",
    "rail_bucket",
    "projected_pace",
    "pace_advantage_label",
    "preferred_styles",
    "risk_styles",
    "bias_band",
    "confidence",
    "evidence_sample",
    "fallback_level",
    "bias_summary",
    "built_at",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def text(value: object) -> str:
    return str(value or "").strip()


def clean(value: object) -> str:
    return "".join(ch for ch in text(value).upper() if ch.isalnum())


def track_key_for(value: object) -> str:
    key = clean(value)
    if key.startswith("SPORTSBET"):
        key = key.replace("SPORTSBET", "", 1)
    if key.startswith("LADBROKES"):
        key = key.replace("LADBROKES", "", 1)
    return TRACK_ALIASES.get(key, key)


def num(value: object) -> float | None:
    raw = text(value).replace(",", "").replace("%", "")
    if not raw:
        return None
    try:
        value_num = float(raw)
    except ValueError:
        return None
    return value_num if math.isfinite(value_num) else None


def pct(part: float, whole: float) -> float:
    return round((part / whole) * 100, 2) if whole else 0.0


def band_distance(value: object) -> str:
    raw = text(value).upper()
    match = num(raw.split("-")[0].replace("M", ""))
    if match is None:
        return "UNKNOWN"
    distance = int(match)
    if distance < 1200:
        return "SPRINT_SHORT"
    if distance < 1400:
        return "SPRINT"
    if distance < 1600:
        return "MILE"
    if distance < 2000:
        return "MIDDLE"
    return "STAYING"


def band_condition(value: object) -> str:
    raw = text(value).upper()
    if not raw:
        return "UNKNOWN"
    if "FIRM" in raw or "GOOD" in raw:
        return "GOOD"
    if "SOFT" in raw:
        return "SOFT"
    if "HEAVY" in raw:
        return "HEAVY"
    if "SYNTH" in raw or "POLY" in raw:
        return "SYNTHETIC"
    return raw


def band_field_size(value: object) -> str:
    field_size = num(value)
    if field_size is None or field_size <= 0:
        return "UNKNOWN"
    if field_size <= 7:
        return "SMALL"
    if field_size <= 11:
        return "MEDIUM"
    if field_size <= 14:
        return "LARGE"
    return "BIG"


def rail_bucket(value: object) -> str:
    raw = text(value).upper()
    if not raw:
        return "UNKNOWN"
    if "TRUE" in raw:
        return "TRUE"
    number = num(raw.split("M")[0])
    if number is None:
        return "UNKNOWN"
    if number <= 3:
        return "LOW"
    if number <= 7:
        return "MID"
    return "WIDE"


def style_name(value: object) -> str:
    raw = text(value).upper().replace(" ", "_").replace("-", "_")
    aliases = {
        "LEADER": "LEADER",
        "LEAD": "LEADER",
        "ONPACE": "ON_PACE",
        "ON_PACE": "ON_PACE",
        "MIDFIELD": "MIDFIELD",
        "BACKMARKER": "BACKMARKER",
        "BACK_MARKER": "BACKMARKER",
    }
    return aliases.get(raw, "UNKNOWN")


def confidence(style_sample: int, context_sample: int) -> str:
    if style_sample >= 100 and context_sample >= 200:
        return "HIGH"
    if style_sample >= 50 and context_sample >= 100:
        return "MEDIUM"
    if style_sample >= 20:
        return "LOW"
    return "SOURCE_GAP"


def sample_band(sample: int) -> str:
    if sample >= 200:
        return "DEEP"
    if sample >= 100:
        return "STRONG"
    if sample >= 50:
        return "MODERATE"
    if sample >= 20:
        return "LIGHT"
    return "THIN"


def bias_band(score: float, style_sample: int) -> str:
    if style_sample < 20:
        return "LOW_SAMPLE"
    if score >= 62:
        return "STRONG_POSITIVE"
    if score >= 54:
        return "POSITIVE"
    if score <= 38:
        return "STRONG_NEGATIVE"
    if score <= 46:
        return "NEGATIVE"
    return "NEUTRAL"


def race_key(row: dict[str, str]) -> str:
    existing = text(row.get("race_key"))
    if existing:
        return existing
    return f"{text(row.get('race_date'))}_{clean(row.get('track') or row.get('normalised_track'))}_R{text(row.get('race_no'))}"


def load_track_profiles() -> dict[tuple[str, str, str], dict[str, str]]:
    profiles: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in read_csv(TRACK_PROFILE):
        key = (
            track_key_for(row.get("track") or row.get("track_key")),
            text(row.get("distance_bucket") or row.get("distance_band") or "UNKNOWN").upper(),
            band_condition(row.get("condition_group") or row.get("track_condition")),
        )
        profiles[key] = row
    return profiles


def build_engine_rows(built_at: str) -> list[dict[str, object]]:
    rows = read_csv(HISTORICAL_RUN_STYLE)
    context_totals: dict[tuple[str, str, str, str, str], dict[str, object]] = defaultdict(lambda: {"starts": 0, "wins": 0, "places": 0, "track": ""})
    style_totals: dict[tuple[str, str, str, str, str, str], dict[str, object]] = defaultdict(lambda: {"starts": 0, "wins": 0, "places": 0, "track": ""})

    for row in rows:
        track_key = track_key_for(row.get("track_key") or row.get("track"))
        if not track_key:
            continue
        dist = band_distance(row.get("distance_bucket") or row.get("distance"))
        condition = band_condition(row.get("condition_group") or row.get("track_condition"))
        field_band = band_field_size(row.get("field_size"))
        rail = rail_bucket(row.get("rail_position"))
        style = style_name(row.get("run_style_v1") or row.get("run_style"))
        finish = num(row.get("finish_pos") or row.get("finish") or row.get("finish_num"))
        if finish is None or finish <= 0:
            continue
        ckey = (track_key, dist, condition, field_band, rail)
        skey = (*ckey, style)
        context_totals[ckey]["starts"] = int(context_totals[ckey]["starts"]) + 1
        context_totals[ckey]["wins"] = int(context_totals[ckey]["wins"]) + (1 if finish == 1 else 0)
        context_totals[ckey]["places"] = int(context_totals[ckey]["places"]) + (1 if finish <= 3 else 0)
        context_totals[ckey]["track"] = text(row.get("track"))
        style_totals[skey]["starts"] = int(style_totals[skey]["starts"]) + 1
        style_totals[skey]["wins"] = int(style_totals[skey]["wins"]) + (1 if finish == 1 else 0)
        style_totals[skey]["places"] = int(style_totals[skey]["places"]) + (1 if finish <= 3 else 0)
        style_totals[skey]["track"] = text(row.get("track"))

    profiles = load_track_profiles()
    engine_rows: list[dict[str, object]] = []
    for skey, stats in sorted(style_totals.items()):
        track_key, dist, condition, field_band, rail, style = skey
        context = context_totals[(track_key, dist, condition, field_band, rail)]
        starts = int(stats["starts"])
        context_sample = int(context["starts"])
        wins = int(stats["wins"])
        places = int(stats["places"])
        win_pct = pct(wins, starts)
        place_pct = pct(places, starts)
        baseline_win = pct(int(context["wins"]), context_sample)
        baseline_place = pct(int(context["places"]), context_sample)
        advantage = round(max(0.0, min(100.0, 50 + ((win_pct - baseline_win) * 1.1) + ((place_pct - baseline_place) * 0.55))), 2)
        profile = profiles.get((track_key, dist, condition), {})
        band = bias_band(advantage, starts)
        conf = confidence(starts, context_sample)
        summary = (
            f"{text(stats['track']) or track_key} {dist} {condition} {field_band}: "
            f"{style} rates {band} from {starts} starts versus a {context_sample} runner context."
        )
        engine_rows.append({
            "track": text(stats["track"]) or track_key,
            "track_key": track_key,
            "distance_band": dist,
            "condition_band": condition,
            "field_size_band": field_band,
            "rail_bucket": rail,
            "run_style": style,
            "context_sample": context_sample,
            "style_sample": starts,
            "wins": wins,
            "places": places,
            "win_pct": win_pct,
            "place_pct": place_pct,
            "baseline_win_pct": baseline_win,
            "baseline_place_pct": baseline_place,
            "style_advantage_score": advantage,
            "bias_band": band,
            "confidence": conf,
            "sample_band": sample_band(starts),
            "track_profile_label": text(profile.get("track_profile_label")) or "UNKNOWN",
            "track_profile_confidence": text(profile.get("track_profile_confidence")) or "SOURCE_GAP",
            "roi_status": "SOURCE_GAP",
            "ae_status": "SOURCE_GAP",
            "bias_summary": summary,
            "built_at": built_at,
        })
    return engine_rows


def race_shape_lookup() -> dict[tuple[str, str, str], dict[str, str]]:
    out = {}
    for row in read_csv(RACE_SHAPE):
        out[(text(row.get("race_date")), track_key_for(row.get("track")), text(row.get("race_no")))] = row
    return out


def race_rows_from_live() -> list[dict[str, str]]:
    source = read_csv(RACE_LIST)
    if source:
        return source
    active = [row for row in read_csv(LIVE_RUNNER_BOARD) if "SCRATCH" not in text(row.get("runner_status") or row.get("scratch_status")).upper()]
    races: dict[tuple[str, str, str], dict[str, str]] = {}
    field_sizes: defaultdict[tuple[str, str, str], int] = defaultdict(int)
    for row in active:
        key = (text(row.get("race_date")), track_key_for(row.get("track")), text(row.get("race_no")))
        races.setdefault(key, row)
        field_sizes[key] += 1
    output = []
    for key, row in races.items():
        merged = dict(row)
        merged["field_size"] = str(field_sizes[key])
        output.append(merged)
    return output


def matching_engine_rows(engine_rows: list[dict[str, object]], track_key: str, dist: str, condition: str, field_band: str, rail: str) -> tuple[list[dict[str, object]], str]:
    levels = [
        ([row for row in engine_rows if row["track_key"] == track_key and row["distance_band"] == dist and row["condition_band"] == condition and row["field_size_band"] == field_band and row["rail_bucket"] == rail], "TRACK_DISTANCE_CONDITION_FIELD_RAIL"),
        ([row for row in engine_rows if row["track_key"] == track_key and row["distance_band"] == dist and row["condition_band"] == condition and row["field_size_band"] == field_band], "TRACK_DISTANCE_CONDITION_FIELD"),
        ([row for row in engine_rows if row["track_key"] == track_key and row["distance_band"] == dist and row["condition_band"] == condition], "TRACK_DISTANCE_CONDITION"),
        ([row for row in engine_rows if row["track_key"] == track_key and row["distance_band"] == dist and row["field_size_band"] == field_band], "TRACK_DISTANCE_FIELD"),
        ([row for row in engine_rows if row["track_key"] == track_key and row["distance_band"] == dist], "TRACK_DISTANCE"),
        ([row for row in engine_rows if row["track_key"] == track_key], "TRACK_ONLY"),
    ]
    for rows, level in levels:
        if rows:
            return rows, level
    return [], "NO_MATCH"


def build_live_rows(engine_rows: list[dict[str, object]], built_at: str) -> list[dict[str, object]]:
    shapes = race_shape_lookup()
    runner_field_sizes: defaultdict[tuple[str, str, str], int] = defaultdict(int)
    for runner in read_csv(LIVE_RUNNER_BOARD):
        if "SCRATCH" in text(runner.get("runner_status") or runner.get("scratch_status") or runner.get("is_scratched")).upper():
            continue
        runner_field_sizes[(text(runner.get("race_date")), track_key_for(runner.get("track")), text(runner.get("race_no")))] += 1
    live_rows = []
    seen = set()
    for row in race_rows_from_live():
        date = text(row.get("race_date"))
        track_display = text(row.get("track") or row.get("normalised_track"))
        track_key = track_key_for(row.get("normalised_track") or row.get("track"))
        race_number = text(row.get("race_no"))
        key = (date, track_key, race_number)
        if key in seen or not track_key or not race_number:
            continue
        seen.add(key)
        dist = band_distance(row.get("distance"))
        condition = band_condition(row.get("track_condition") or row.get("condition_group"))
        field_size_value = text(row.get("field_size"))
        if not field_size_value:
            field_size_value = str(runner_field_sizes.get(key, 0) or "")
        field_band = band_field_size(field_size_value)
        rail = rail_bucket(row.get("rail_position"))
        matches, fallback = matching_engine_rows(engine_rows, track_key, dist, condition, field_band, rail)
        matches = sorted(matches, key=lambda item: (float(item["style_advantage_score"]), int(item["style_sample"])), reverse=True)
        positive = [text(item["run_style"]) for item in matches if text(item["bias_band"]) in {"STRONG_POSITIVE", "POSITIVE"}]
        risk = [text(item["run_style"]) for item in matches if text(item["bias_band"]) in {"STRONG_NEGATIVE", "NEGATIVE"}]
        best = matches[0] if matches else {}
        evidence_sample = int(best.get("context_sample") or 0) if best else 0
        conf = text(best.get("confidence")) if best else "SOURCE_GAP"
        if conf == "HIGH" and evidence_sample < 200:
            conf = "MEDIUM"
        shape = shapes.get(key, {})
        summary = "No supported track-bias sample for this race context."
        if best:
            summary = (
                f"{track_display} R{race_number}: {', '.join(positive[:2]) or text(best.get('run_style'))} profiles best "
                f"for {dist}/{condition}/{field_band}; evidence sample {evidence_sample} via {fallback}."
            )
        live_rows.append({
            "race_date": date,
            "day_bucket": text(row.get("day_bucket")),
            "track": track_display,
            "normalised_track": text(row.get("normalised_track")) or track_display,
            "race_no": race_number,
            "race_key": race_key(row),
            "distance": text(row.get("distance")),
            "distance_band": dist,
            "track_condition": text(row.get("track_condition")),
            "condition_band": condition,
            "field_size": field_size_value,
            "field_size_band": field_band,
            "rail_position": text(row.get("rail_position")),
            "rail_bucket": rail,
            "projected_pace": text(shape.get("tempo_label") or shape.get("race_shape_label")) or "UNKNOWN",
            "pace_advantage_label": text(shape.get("pace_advantage_label")) or "UNKNOWN",
            "preferred_styles": " | ".join(dict.fromkeys(positive[:3])) if positive else text(best.get("run_style")) if best else "UNKNOWN",
            "risk_styles": " | ".join(dict.fromkeys(risk[:3])) if risk else "UNKNOWN",
            "bias_band": text(best.get("bias_band")) if best else "UNKNOWN",
            "confidence": conf,
            "evidence_sample": evidence_sample,
            "fallback_level": fallback,
            "bias_summary": summary,
            "built_at": built_at,
        })
    return live_rows


def write_summary(engine_rows: list[dict[str, object]], live_rows: list[dict[str, object]], built_at: str) -> None:
    hist_summary = {row.get("status", "source"): row for row in read_csv(HISTORICAL_RESULTS_SUMMARY)}
    source_rows = ""
    if hist_summary:
        first = next(iter(hist_summary.values()))
        source_rows = text(first.get("rows"))
    rows = [
        {"metric": "status", "value": "TRACK_BIAS_ENGINE_V1_BUILT"},
        {"metric": "historical_results_rows_available", "value": source_rows},
        {"metric": "engine_rows", "value": len(engine_rows)},
        {"metric": "live_rows", "value": len(live_rows)},
        {"metric": "high_confidence_engine_rows", "value": sum(1 for row in engine_rows if row["confidence"] == "HIGH")},
        {"metric": "medium_confidence_engine_rows", "value": sum(1 for row in engine_rows if row["confidence"] == "MEDIUM")},
        {"metric": "source_gap_engine_rows", "value": sum(1 for row in engine_rows if row["confidence"] == "SOURCE_GAP")},
        {"metric": "built_at", "value": built_at},
    ]
    write_csv(OUT_SUMMARY, rows, ["metric", "value"])


def main() -> None:
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    engine_rows = build_engine_rows(built_at)
    live_rows = build_live_rows(engine_rows, built_at)
    write_csv(OUT_ENGINE, engine_rows, ENGINE_FIELDS)
    write_csv(OUT_LIVE, live_rows, LIVE_FIELDS)
    write_summary(engine_rows, live_rows, built_at)
    print(f"Track bias engine built: engine_rows={len(engine_rows)} live_rows={len(live_rows)}")


if __name__ == "__main__":
    main()
