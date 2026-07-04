from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HISTORICAL_RESULTS = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
HISTORICAL_RUN_STYLE = DATA / "edgeiq_historical_run_style_v1.csv"
LIVE_GOVERNED = DATA / "edgeiq_live_runner_board_governed_v1.csv"
LIVE_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"

TRAINER_RECENT_OUT = DATA / "edgeiq_trainer_recent_form_engine_v1.csv"
JOCKEY_RECENT_OUT = DATA / "edgeiq_jockey_recent_form_engine_v1.csv"
JOCKEY_STYLE_OUT = DATA / "edgeiq_jockey_run_style_engine_v1.csv"
TRAINER_STYLE_OUT = DATA / "edgeiq_trainer_run_style_engine_v1.csv"
PARTNERSHIP_OUT = DATA / "edgeiq_trainer_jockey_partnership_engine_v1.csv"
LIVE_NEXUS_OUT = DATA / "edgeiq_live_nexus_feature_feed_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_nexus_feature_engine_summary_v1.csv"
AUDIT_OUT = DATA / "edgeiq_nexus_feature_engine_audit_v1.csv"

WINDOWS = (25, 50, 100)
RUN_STYLE_BANDS = ("LEADER", "ON_PACE", "MIDFIELD", "OFF_PACE", "REAR")


def text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def canon(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", text(value).upper())


def parse_date(value: Any) -> date | None:
    raw = text(value)
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d%b%y", "%d%b%Y", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw[:10] if fmt == "%Y-%m-%d" else raw, fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def to_float(value: Any) -> float | None:
    raw = text(value).replace("$", "").replace(",", "")
    if not raw:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", raw)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def to_int(value: Any) -> int | None:
    val = to_float(value)
    if val is None or not math.isfinite(val):
        return None
    return int(round(val))


def distance_bucket(distance: Any) -> str:
    metres = to_float(distance)
    if metres is None:
        return "UNKNOWN"
    if metres <= 1200:
        return "SPRINT"
    if metres <= 1600:
        return "MILE"
    if metres <= 2000:
        return "MIDDLE"
    return "STAYING"


def class_bucket(value: Any) -> str:
    raw = text(value).upper()
    if not raw:
        return "UNKNOWN"
    if "MDN" in raw or "MAIDEN" in raw:
        return "MAIDEN"
    if "BM" in raw:
        match = re.search(r"BM\s?(\d+)", raw)
        return f"BM{match.group(1)}" if match else "BENCHMARK"
    if "GROUP" in raw or re.search(r"\bG[123]\b", raw):
        return "GROUP"
    if "LISTED" in raw or raw == "LR":
        return "LISTED"
    if "HCP" in raw:
        return "HANDICAP"
    return raw[:32]


def normalise_run_style(row: dict[str, Any]) -> str:
    pos800 = to_float(row.get("pos800"))
    if pos800 is not None:
        if pos800 <= 1.5:
            return "LEADER"
        if pos800 <= 3.5:
            return "ON_PACE"
        if pos800 <= 6.5:
            return "MIDFIELD"
        if pos800 <= 9.5:
            return "OFF_PACE"
        return "REAR"
    raw = text(row.get("run_style_v1") or row.get("run_style")).upper().replace(" ", "_")
    if raw in {"LEADER", "FRONT_RUNNER", "FRONTRUNNER"}:
        return "LEADER"
    if raw in {"ONPACE", "ON_PACE", "PROMINENT"}:
        return "ON_PACE"
    if raw == "MIDFIELD":
        return "MIDFIELD"
    if raw in {"OFF_PACE", "BACKMARKER"}:
        return "OFF_PACE"
    if raw in {"REAR", "DEEP_BACKMARKER"}:
        return "REAR"
    return ""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def metric_block(starts_rows: list[dict[str, Any]], prefix: str = "") -> dict[str, Any]:
    starts = len(starts_rows)
    wins = sum(1 for row in starts_rows if to_int(row.get("won")) == 1 or to_int(row.get("finish_num") or row.get("finish")) == 1)
    places = sum(1 for row in starts_rows if to_int(row.get("placed")) == 1 or (to_int(row.get("finish_num") or row.get("finish")) or 999) <= 3)
    sp_values = [to_float(row.get("starting_price_decimal")) for row in starts_rows]
    sp_values = [value for value in sp_values if value and value > 1.0]
    expected_wins = sum(1.0 / value for value in sp_values)
    returns = sum((to_float(row.get("starting_price_decimal")) or 0.0) for row in starts_rows if to_int(row.get("won")) == 1 or to_int(row.get("finish_num") or row.get("finish")) == 1)
    win_pct = (wins / starts * 100.0) if starts else 0.0
    place_pct = (places / starts * 100.0) if starts else 0.0
    roi = ((returns - starts) / starts * 100.0) if starts else 0.0
    ae = (wins / expected_wins) if expected_wins > 0 else 0.0
    avg_sp = (sum(sp_values) / len(sp_values)) if sp_values else 0.0
    return {
        f"{prefix}starts": starts,
        f"{prefix}wins": wins,
        f"{prefix}places": places,
        f"{prefix}win_pct": round(win_pct, 2),
        f"{prefix}place_pct": round(place_pct, 2),
        f"{prefix}roi_pct": round(roi, 2),
        f"{prefix}ae": round(ae, 3),
        f"{prefix}avg_sp": round(avg_sp, 2),
    }


def momentum_band(metrics: dict[str, Any], prefix: str) -> str:
    starts = int(metrics.get(f"{prefix}starts") or 0)
    roi = float(metrics.get(f"{prefix}roi_pct") or 0.0)
    ae = float(metrics.get(f"{prefix}ae") or 0.0)
    win_pct = float(metrics.get(f"{prefix}win_pct") or 0.0)
    if starts < 8:
        return "NEUTRAL"
    if ae >= 1.35 and roi >= 10 and win_pct >= 18:
        return "FLYING"
    if ae >= 1.12 and roi >= 0:
        return "HOT"
    if ae <= 0.65 and roi <= -35:
        return "COLD"
    if ae <= 0.82 and roi <= -20:
        return "COOL"
    return "NEUTRAL"


def build_recent_form(rows: list[dict[str, Any]], entity_col: str, label: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    names: dict[str, str] = {}
    for row in rows:
        key = canon(row.get(entity_col))
        if not key:
            continue
        grouped[key].append(row)
        names.setdefault(key, text(row.get(entity_col)))

    out: list[dict[str, Any]] = []
    for key, starts_rows in grouped.items():
        sorted_rows = sorted(starts_rows, key=lambda r: (r.get("_race_date") or date.min, text(r.get("race_id"))), reverse=True)
        record: dict[str, Any] = {
            f"{label}_canonical": key,
            f"{label}_name": names.get(key, key),
            "latest_race_date": max((r.get("_race_date") for r in sorted_rows if r.get("_race_date")), default=None),
            "total_starts_in_source": len(sorted_rows),
        }
        for window in WINDOWS:
            block = metric_block(sorted_rows[:window], f"last_{window}_")
            record.update(block)
            record[f"last_{window}_momentum_band"] = momentum_band(block, f"last_{window}_")
        out.append(record)

    out.sort(key=lambda r: (-int(r.get("total_starts_in_source") or 0), text(r.get(f"{label}_name"))))
    for record in out:
        if isinstance(record.get("latest_race_date"), date):
            record["latest_race_date"] = record["latest_race_date"].isoformat()
    return out


def build_run_style(rows: list[dict[str, Any]], entity_col: str, label: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    names: dict[str, str] = {}
    for row in rows:
        key = canon(row.get(entity_col))
        style = text(row.get("_run_style_band"))
        if not key or style not in RUN_STYLE_BANDS:
            continue
        grouped[(key, style)].append(row)
        names.setdefault(key, text(row.get(entity_col)))

    out: list[dict[str, Any]] = []
    for (key, style), starts_rows in grouped.items():
        block = metric_block(starts_rows, "")
        out.append({
            f"{label}_canonical": key,
            f"{label}_name": names.get(key, key),
            "run_style_band": style,
            **block,
        })
    out.sort(key=lambda r: (text(r.get(f"{label}_name")), RUN_STYLE_BANDS.index(text(r.get("run_style_band"))) if text(r.get("run_style_band")) in RUN_STYLE_BANDS else 99))
    return out


def build_run_style_lookup(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    lookup: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        race_date = parse_date(row.get("race_date"))
        horse_key = canon(row.get("horse_key") or row.get("horse"))
        style = normalise_run_style(row)
        if not race_date or not horse_key or not style:
            continue
        lookup.setdefault((horse_key, race_date.isoformat()), row | {"_run_style_band": style})
    return lookup


def enrich_historical_rows(rows: list[dict[str, str]], style_lookup: dict[tuple[str, str], dict[str, str]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for row in rows:
        if text(row.get("scratched")).upper() == "TRUE":
            continue
        race_date = parse_date(row.get("race_date"))
        if not race_date:
            continue
        row2: dict[str, Any] = dict(row)
        row2["_race_date"] = race_date
        horse_key = canon(row.get("horse_code") or row.get("horse"))
        style_row = style_lookup.get((horse_key, race_date.isoformat())) or style_lookup.get((canon(row.get("horse")), race_date.isoformat()))
        row2["_run_style_band"] = text((style_row or {}).get("_run_style_band"))
        row2["_distance_bucket"] = distance_bucket(row.get("distance"))
        row2["_class_bucket"] = class_bucket(row.get("race_class"))
        enriched.append(row2)
    return enriched


def build_partnership(rows: list[dict[str, Any]], live_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    trainer_names: dict[str, str] = {}
    jockey_names: dict[str, str] = {}
    for row in rows:
        trainer_key = canon(row.get("trainer"))
        jockey_key = canon(row.get("jockey"))
        if not trainer_key or not jockey_key:
            continue
        grouped[(trainer_key, jockey_key)].append(row)
        trainer_names.setdefault(trainer_key, text(row.get("trainer")))
        jockey_names.setdefault(jockey_key, text(row.get("jockey")))

    max_date = max((r.get("_race_date") for r in rows if r.get("_race_date")), default=None)
    cutoff = (max_date - timedelta(days=365)) if max_date else None

    live_combo_contexts: dict[tuple[str, str, str, str, str], dict[str, str]] = {}
    for live in live_rows:
        trainer_key = canon(live.get("trainer"))
        jockey_key = canon(live.get("jockey"))
        if not trainer_key or not jockey_key:
            continue
        track_key = canon(live.get("track"))
        dist_key = distance_bucket(live.get("distance"))
        class_key = class_bucket(live.get("race_class"))
        live_combo_contexts[(trainer_key, jockey_key, track_key, dist_key, class_key)] = live

    out: list[dict[str, Any]] = []
    for context_key, live in live_combo_contexts.items():
        trainer_key, jockey_key, track_key, dist_key, class_key = context_key
        combo_rows = grouped.get((trainer_key, jockey_key), [])
        last12_rows = [r for r in combo_rows if cutoff and r.get("_race_date") and r["_race_date"] >= cutoff]
        track_rows = [r for r in combo_rows if canon(r.get("track")) == track_key]
        distance_rows = [r for r in combo_rows if text(r.get("_distance_bucket")) == dist_key]
        class_rows = [r for r in combo_rows if text(r.get("_class_bucket")) == class_key]
        out.append({
            "trainer_canonical": trainer_key,
            "jockey_canonical": jockey_key,
            "combo_canonical": f"{trainer_key}|{jockey_key}",
            "trainer_name": text(live.get("trainer")) or trainer_names.get(trainer_key, trainer_key),
            "jockey_name": text(live.get("jockey")) or jockey_names.get(jockey_key, jockey_key),
            "current_track": text(live.get("track")),
            "current_distance_bucket": dist_key,
            "current_class_bucket": class_key,
            **metric_block(combo_rows, "lifetime_"),
            **metric_block(last12_rows, "last_12_months_"),
            **metric_block(track_rows, "track_combo_"),
            **metric_block(distance_rows, "distance_combo_"),
            **metric_block(class_rows, "class_combo_"),
        })

    if not out:
        for (trainer_key, jockey_key), combo_rows in sorted(grouped.items(), key=lambda item: -len(item[1]))[:1000]:
            last12_rows = [r for r in combo_rows if cutoff and r.get("_race_date") and r["_race_date"] >= cutoff]
            out.append({
                "trainer_canonical": trainer_key,
                "jockey_canonical": jockey_key,
                "combo_canonical": f"{trainer_key}|{jockey_key}",
                "trainer_name": trainer_names.get(trainer_key, trainer_key),
                "jockey_name": jockey_names.get(jockey_key, jockey_key),
                "current_track": "",
                "current_distance_bucket": "",
                "current_class_bucket": "",
                **metric_block(combo_rows, "lifetime_"),
                **metric_block(last12_rows, "last_12_months_"),
                **metric_block([], "track_combo_"),
                **metric_block([], "distance_combo_"),
                **metric_block([], "class_combo_"),
            })
    return out


def index_by(rows: list[dict[str, Any]], key_field: str) -> dict[str, dict[str, Any]]:
    return {text(row.get(key_field)): row for row in rows if text(row.get(key_field))}


def index_style(rows: list[dict[str, Any]], entity_field: str) -> dict[tuple[str, str], dict[str, Any]]:
    return {(text(row.get(entity_field)), text(row.get("run_style_band"))): row for row in rows}


def build_live_feed(
    live_rows: list[dict[str, str]],
    trainer_recent: list[dict[str, Any]],
    jockey_recent: list[dict[str, Any]],
    trainer_style: list[dict[str, Any]],
    jockey_style: list[dict[str, Any]],
    partnerships: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    trainer_recent_idx = index_by(trainer_recent, "trainer_canonical")
    jockey_recent_idx = index_by(jockey_recent, "jockey_canonical")
    trainer_style_idx = index_style(trainer_style, "trainer_canonical")
    jockey_style_idx = index_style(jockey_style, "jockey_canonical")
    partnership_idx = {(
        text(row.get("trainer_canonical")),
        text(row.get("jockey_canonical")),
        canon(row.get("current_track")),
        text(row.get("current_distance_bucket")),
        text(row.get("current_class_bucket")),
    ): row for row in partnerships}
    partnership_any_idx = {(text(row.get("trainer_canonical")), text(row.get("jockey_canonical"))): row for row in partnerships}

    out: list[dict[str, Any]] = []
    for row in live_rows:
        trainer_key = canon(row.get("trainer"))
        jockey_key = canon(row.get("jockey"))
        run_style = normalise_run_style({"run_style_v1": row.get("run_style") or row.get("speed_map_bucket") or row.get("settling_band")}) or "UNKNOWN"
        dist_key = distance_bucket(row.get("distance"))
        class_key = class_bucket(row.get("race_class"))
        partnership = partnership_idx.get((trainer_key, jockey_key, canon(row.get("track")), dist_key, class_key)) or partnership_any_idx.get((trainer_key, jockey_key), {})
        trainer_recent_row = trainer_recent_idx.get(trainer_key, {})
        jockey_recent_row = jockey_recent_idx.get(jockey_key, {})
        trainer_style_row = trainer_style_idx.get((trainer_key, run_style), {})
        jockey_style_row = jockey_style_idx.get((jockey_key, run_style), {})
        feature_hits = sum(1 for candidate in (trainer_recent_row, jockey_recent_row, trainer_style_row, jockey_style_row, partnership) if candidate)
        out.append({
            "race_date": text(row.get("race_date")),
            "track": text(row.get("track")),
            "race_no": text(row.get("race_no")),
            "horse": text(row.get("horse")),
            "trainer": text(row.get("trainer")),
            "jockey": text(row.get("jockey")),
            "trainer_canonical": trainer_key,
            "jockey_canonical": jockey_key,
            "combo_canonical": f"{trainer_key}|{jockey_key}" if trainer_key and jockey_key else "",
            "run_style_band": run_style,
            "distance_bucket": dist_key,
            "class_bucket": class_key,
            "trainer_last25_starts": trainer_recent_row.get("last_25_starts", 0),
            "trainer_last25_win_pct": trainer_recent_row.get("last_25_win_pct", 0),
            "trainer_last25_place_pct": trainer_recent_row.get("last_25_place_pct", 0),
            "trainer_last25_roi_pct": trainer_recent_row.get("last_25_roi_pct", 0),
            "trainer_last25_ae": trainer_recent_row.get("last_25_ae", 0),
            "trainer_last25_avg_sp": trainer_recent_row.get("last_25_avg_sp", 0),
            "trainer_last25_momentum_band": trainer_recent_row.get("last_25_momentum_band", "NEUTRAL"),
            "trainer_last50_starts": trainer_recent_row.get("last_50_starts", 0),
            "trainer_last50_win_pct": trainer_recent_row.get("last_50_win_pct", 0),
            "trainer_last50_place_pct": trainer_recent_row.get("last_50_place_pct", 0),
            "trainer_last50_roi_pct": trainer_recent_row.get("last_50_roi_pct", 0),
            "trainer_last50_ae": trainer_recent_row.get("last_50_ae", 0),
            "trainer_last50_avg_sp": trainer_recent_row.get("last_50_avg_sp", 0),
            "trainer_last50_momentum_band": trainer_recent_row.get("last_50_momentum_band", "NEUTRAL"),
            "trainer_last100_starts": trainer_recent_row.get("last_100_starts", 0),
            "trainer_last100_win_pct": trainer_recent_row.get("last_100_win_pct", 0),
            "trainer_last100_place_pct": trainer_recent_row.get("last_100_place_pct", 0),
            "trainer_last100_roi_pct": trainer_recent_row.get("last_100_roi_pct", 0),
            "trainer_last100_ae": trainer_recent_row.get("last_100_ae", 0),
            "trainer_last100_avg_sp": trainer_recent_row.get("last_100_avg_sp", 0),
            "trainer_last100_momentum_band": trainer_recent_row.get("last_100_momentum_band", "NEUTRAL"),
            "jockey_last25_starts": jockey_recent_row.get("last_25_starts", 0),
            "jockey_last25_win_pct": jockey_recent_row.get("last_25_win_pct", 0),
            "jockey_last25_place_pct": jockey_recent_row.get("last_25_place_pct", 0),
            "jockey_last25_roi_pct": jockey_recent_row.get("last_25_roi_pct", 0),
            "jockey_last25_ae": jockey_recent_row.get("last_25_ae", 0),
            "jockey_last25_avg_sp": jockey_recent_row.get("last_25_avg_sp", 0),
            "jockey_last25_momentum_band": jockey_recent_row.get("last_25_momentum_band", "NEUTRAL"),
            "jockey_last50_starts": jockey_recent_row.get("last_50_starts", 0),
            "jockey_last50_win_pct": jockey_recent_row.get("last_50_win_pct", 0),
            "jockey_last50_place_pct": jockey_recent_row.get("last_50_place_pct", 0),
            "jockey_last50_roi_pct": jockey_recent_row.get("last_50_roi_pct", 0),
            "jockey_last50_ae": jockey_recent_row.get("last_50_ae", 0),
            "jockey_last50_avg_sp": jockey_recent_row.get("last_50_avg_sp", 0),
            "jockey_last50_momentum_band": jockey_recent_row.get("last_50_momentum_band", "NEUTRAL"),
            "jockey_last100_starts": jockey_recent_row.get("last_100_starts", 0),
            "jockey_last100_win_pct": jockey_recent_row.get("last_100_win_pct", 0),
            "jockey_last100_place_pct": jockey_recent_row.get("last_100_place_pct", 0),
            "jockey_last100_roi_pct": jockey_recent_row.get("last_100_roi_pct", 0),
            "jockey_last100_ae": jockey_recent_row.get("last_100_ae", 0),
            "jockey_last100_avg_sp": jockey_recent_row.get("last_100_avg_sp", 0),
            "jockey_last100_momentum_band": jockey_recent_row.get("last_100_momentum_band", "NEUTRAL"),
            "trainer_run_style_starts": trainer_style_row.get("starts", 0),
            "trainer_run_style_win_pct": trainer_style_row.get("win_pct", 0),
            "trainer_run_style_place_pct": trainer_style_row.get("place_pct", 0),
            "trainer_run_style_roi_pct": trainer_style_row.get("roi_pct", 0),
            "trainer_run_style_ae": trainer_style_row.get("ae", 0),
            "trainer_run_style_avg_sp": trainer_style_row.get("avg_sp", 0),
            "jockey_run_style_rides": jockey_style_row.get("starts", 0),
            "jockey_run_style_win_pct": jockey_style_row.get("win_pct", 0),
            "jockey_run_style_place_pct": jockey_style_row.get("place_pct", 0),
            "jockey_run_style_roi_pct": jockey_style_row.get("roi_pct", 0),
            "jockey_run_style_ae": jockey_style_row.get("ae", 0),
            "jockey_run_style_avg_sp": jockey_style_row.get("avg_sp", 0),
            "combo_lifetime_starts": partnership.get("lifetime_starts", 0),
            "combo_lifetime_win_pct": partnership.get("lifetime_win_pct", 0),
            "combo_lifetime_place_pct": partnership.get("lifetime_place_pct", 0),
            "combo_lifetime_roi_pct": partnership.get("lifetime_roi_pct", 0),
            "combo_lifetime_ae": partnership.get("lifetime_ae", 0),
            "combo_last12m_starts": partnership.get("last_12_months_starts", 0),
            "combo_last12m_win_pct": partnership.get("last_12_months_win_pct", 0),
            "combo_track_starts": partnership.get("track_combo_starts", 0),
            "combo_distance_starts": partnership.get("distance_combo_starts", 0),
            "combo_class_starts": partnership.get("class_combo_starts", 0),
            "nexus_feature_coverage_count": feature_hits,
            "nexus_feature_status": "FEATURES_AVAILABLE" if feature_hits else "NO_FEATURE_MATCH",
        })
    return out


def fieldnames_from(rows: list[dict[str, Any]]) -> list[str]:
    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                fields.append(key)
                seen.add(key)
    return fields


def main() -> None:
    raw_results = read_csv(HISTORICAL_RESULTS)
    style_rows = read_csv(HISTORICAL_RUN_STYLE)
    live_rows = read_csv(LIVE_GOVERNED) or read_csv(LIVE_BOARD)

    style_lookup = build_run_style_lookup(style_rows)
    historical_rows = enrich_historical_rows(raw_results, style_lookup)

    trainer_recent = build_recent_form(historical_rows, "trainer", "trainer")
    jockey_recent = build_recent_form(historical_rows, "jockey", "jockey")
    trainer_style = build_run_style(historical_rows, "trainer", "trainer")
    jockey_style = build_run_style(historical_rows, "jockey", "jockey")
    partnerships = build_partnership(historical_rows, live_rows)
    live_nexus = build_live_feed(live_rows, trainer_recent, jockey_recent, trainer_style, jockey_style, partnerships)

    write_csv(TRAINER_RECENT_OUT, trainer_recent, fieldnames_from(trainer_recent))
    write_csv(JOCKEY_RECENT_OUT, jockey_recent, fieldnames_from(jockey_recent))
    write_csv(TRAINER_STYLE_OUT, trainer_style, fieldnames_from(trainer_style))
    write_csv(JOCKEY_STYLE_OUT, jockey_style, fieldnames_from(jockey_style))
    write_csv(PARTNERSHIP_OUT, partnerships, fieldnames_from(partnerships))
    write_csv(LIVE_NEXUS_OUT, live_nexus, fieldnames_from(live_nexus))

    summary_rows = [
        {"metric": "historical_result_rows_loaded", "value": len(raw_results)},
        {"metric": "historical_result_rows_used", "value": len(historical_rows)},
        {"metric": "historical_run_style_rows_loaded", "value": len(style_rows)},
        {"metric": "historical_run_style_lookup_rows", "value": len(style_lookup)},
        {"metric": "historical_rows_with_run_style", "value": sum(1 for r in historical_rows if text(r.get("_run_style_band")))},
        {"metric": "live_runner_rows_loaded", "value": len(live_rows)},
        {"metric": "trainer_recent_form_rows", "value": len(trainer_recent)},
        {"metric": "jockey_recent_form_rows", "value": len(jockey_recent)},
        {"metric": "trainer_run_style_rows", "value": len(trainer_style)},
        {"metric": "jockey_run_style_rows", "value": len(jockey_style)},
        {"metric": "trainer_jockey_partnership_rows", "value": len(partnerships)},
        {"metric": "live_nexus_feature_feed_rows", "value": len(live_nexus)},
        {"metric": "live_nexus_rows_with_features", "value": sum(1 for r in live_nexus if int(r.get("nexus_feature_coverage_count") or 0) > 0)},
        {"metric": "production_changed", "value": "NO"},
        {"metric": "pricing_changed", "value": "NO"},
        {"metric": "ratings_changed", "value": "NO"},
        {"metric": "v6_1_changed", "value": "NO"},
        {"metric": "v7_2g2_changed", "value": "NO"},
    ]
    write_csv(SUMMARY_OUT, summary_rows, ["metric", "value"])

    audit_rows = [
        {"check": "historical_results_source_exists", "status": "PASS" if HISTORICAL_RESULTS.exists() else "FAIL", "detail": str(HISTORICAL_RESULTS)},
        {"check": "historical_run_style_source_exists", "status": "PASS" if HISTORICAL_RUN_STYLE.exists() else "WARN", "detail": str(HISTORICAL_RUN_STYLE)},
        {"check": "live_runner_source_exists", "status": "PASS" if live_rows else "WARN", "detail": str(LIVE_GOVERNED if LIVE_GOVERNED.exists() else LIVE_BOARD)},
        {"check": "trainer_recent_form_rows_gt_0", "status": "PASS" if trainer_recent else "FAIL", "detail": len(trainer_recent)},
        {"check": "jockey_recent_form_rows_gt_0", "status": "PASS" if jockey_recent else "FAIL", "detail": len(jockey_recent)},
        {"check": "trainer_run_style_rows_gt_0", "status": "PASS" if trainer_style else "FAIL", "detail": len(trainer_style)},
        {"check": "jockey_run_style_rows_gt_0", "status": "PASS" if jockey_style else "FAIL", "detail": len(jockey_style)},
        {"check": "partnership_rows_gt_0", "status": "PASS" if partnerships else "FAIL", "detail": len(partnerships)},
        {"check": "live_nexus_feed_rows_gt_0_when_live_exists", "status": "PASS" if (not live_rows or live_nexus) else "FAIL", "detail": len(live_nexus)},
        {"check": "live_nexus_features_available", "status": "PASS" if sum(1 for r in live_nexus if int(r.get("nexus_feature_coverage_count") or 0) > 0) else "WARN", "detail": sum(1 for r in live_nexus if int(r.get("nexus_feature_coverage_count") or 0) > 0)},
    ]
    write_csv(AUDIT_OUT, audit_rows, ["check", "status", "detail"])
    failed = [row for row in audit_rows if row["status"] == "FAIL"]
    print(f"EDGEiQ Nexus V2 feature engine built. Failures: {len(failed)}")
    for row in summary_rows:
        print(f"{row['metric']}: {row['value']}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
