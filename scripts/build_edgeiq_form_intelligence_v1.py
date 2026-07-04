import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
RUNNER_FORM = DATA / "edgeiq_runner_form_engine_current.csv"
RUNNER_HISTORY = DATA / "runner_form_history.csv"
HISTORY_DETAIL = DATA / "edgeiq_runner_history_detail_v1.csv"
RACE_SHAPE = DATA / "edgeiq_race_shape_fallback_engine_v1.csv"
HIDDEN_GEM = DATA / "edgeiq_current_hidden_gem_feed_v1_1.csv"

OUT = DATA / "edgeiq_form_intelligence_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_form_intelligence_v1_summary.csv"
OUT_AUDIT = DATA / "edgeiq_form_intelligence_v1_audit.csv"


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


def horse_clean(value: object) -> str:
    raw = text(value).upper()
    while "(" in raw and ")" in raw:
        start = raw.find("(")
        end = raw.find(")", start)
        if end < 0:
            break
        raw = raw[:start] + raw[end + 1 :]
    return clean(raw)


def race_date(row: dict[str, str]) -> str:
    return text(row.get("current_race_date") or row.get("race_date") or row.get("meeting_date") or row.get("date") or row.get("raceDate"))


def race_no(row: dict[str, str]) -> str:
    return text(row.get("race_no") or row.get("raceNo") or row.get("race_number") or row.get("race"))


def horse(row: dict[str, str]) -> str:
    return text(row.get("horse") or row.get("horseName") or row.get("runner") or row.get("runner_name"))


def num(value: object) -> float | None:
    raw = text(value).replace("$", "").replace("%", "").replace(",", "")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def is_scratched(row: dict[str, str]) -> bool:
    blob = " ".join(
        text(row.get(key)).upper()
        for key in ["display_decision", "runner_status", "scratch_status", "is_scratched", "execution_action", "decision"]
    )
    return "SCRATCH" in blob or text(row.get("is_scratched")).upper() in {"YES", "Y", "TRUE", "1"}


def runner_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (clean(row.get("track")), race_no(row), horse_clean(row.get("horse_key") or horse(row)))


def race_key(row: dict[str, str]) -> tuple[str, str]:
    return (clean(row.get("track")), race_no(row))


def history_key(row: dict[str, str]) -> str:
    return horse_clean(row.get("horse_key") or horse(row))


def parse_date(value: object) -> str:
    raw = text(value)
    if not raw:
        return ""
    return raw[:10]


def sort_date_value(row: dict[str, str]) -> str:
    return parse_date(row.get("run_date_iso") or row.get("run_date") or row.get("race_date"))


def band_from_form_signal(value: str) -> str:
    signal = value.upper()
    if "STRONG" in signal or "PEAK" in signal:
        return "POSITIVE"
    if "MIXED" in signal or "SOME" in signal:
        return "NEUTRAL"
    if "LIMITED" in signal or "NO" in signal:
        return "LIMITED"
    return "DEVELOPING"


def main() -> None:
    active = [row for row in read_csv(RUNNER_BOARD) if not is_scratched(row)]
    form_rows = {runner_key(row): row for row in read_csv(RUNNER_FORM)}
    race_shapes = {race_key(row): row for row in read_csv(RACE_SHAPE)}
    hidden_rows = {runner_key(row): row for row in read_csv(HIDDEN_GEM)}

    histories: dict[str, list[dict[str, str]]] = defaultdict(list)
    for source in [read_csv(HISTORY_DETAIL), read_csv(RUNNER_HISTORY)]:
        for row in source:
            key = history_key(row)
            if key:
                histories[key].append(row)
    for rows in histories.values():
        rows.sort(key=sort_date_value, reverse=True)

    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    output_rows: list[dict[str, object]] = []
    audit_rows: list[dict[str, object]] = []
    band_counts: Counter[str] = Counter()

    for runner in active:
        key = runner_key(runner)
        h_key = history_key(runner)
        form = form_rows.get(key, {})
        shape = race_shapes.get(race_key(runner), {})
        hidden = hidden_rows.get(key, {})
        recent = histories.get(h_key, [])
        last = recent[0] if recent else {}

        last_rating = num(form.get("last_start_rating")) or num(last.get("performance_rating")) or num(last.get("run_rating"))
        avg_rating = num(form.get("avg_rating_last5"))
        peak_rating = num(form.get("peak_rating") or form.get("best_rating_last5"))
        epf = num(runner.get("early_speed_rating")) or num(runner.get("projected_spd")) or num(runner.get("total_rating_points"))
        form_signal = text(form.get("form_signal")) or ("LIMITED FORM" if not recent else "DEVELOPING FORM")
        form_cycle = text(form.get("form_cycle")) or "UNKNOWN"
        performance_note = text(hidden.get("hidden_gem_narrative"))
        form_narrative = text(form.get("form_narrative"))

        race_shape = text(shape.get("race_shape_label") or shape.get("tempo_label")) or text(runner.get("speed_map_bucket")) or "UNKNOWN"
        settling = text(runner.get("settling_band") or runner.get("speed_map_bucket") or runner.get("run_style")) or "UNKNOWN"
        bias_notes = text(shape.get("pace_advantage_label")) or text(shape.get("race_shape_narrative")) or "No strong race-shape bias note."
        performance_intelligence = " ".join(part for part in [form_narrative, performance_note] if part).strip()
        if not performance_intelligence:
            performance_intelligence = f"{horse(runner)} has limited recent form intelligence in the current EDGEiQ sources."

        band = band_from_form_signal(form_signal)
        evidence_quality = "HIGH" if len(recent) >= 5 else "MEDIUM" if len(recent) >= 2 else "LIMITED"
        band_counts[band] += 1

        output_rows.append(
            {
                "current_race_date": race_date(runner),
                "track": text(runner.get("track")),
                "race_no": race_no(runner),
                "horse": horse(runner),
                "horse_key": text(runner.get("horse_key")) or horse_clean(horse(runner)),
                "date": parse_date(last.get("run_date_iso") or last.get("run_date") or last.get("race_date")),
                "distance": text(last.get("distance") or runner.get("distance")),
                "class": text(last.get("class_name") or last.get("race_class") or runner.get("race_class")),
                "position": text(last.get("finish_pos")),
                "margin": text(last.get("margin")),
                "SP": text(last.get("sp") or last.get("sp_text") or last.get("starting_price")),
                "rating": "" if last_rating is None else f"{last_rating:.2f}",
                "EPF": "" if epf is None else f"{epf:.2f}",
                "race_shape": race_shape,
                "settling_position": settling,
                "bias_notes": bias_notes,
                "performance_intelligence": performance_intelligence,
                "form_signal": form_signal,
                "form_cycle": form_cycle,
                "recent_runs_found": text(form.get("recent_runs_found")) or len(recent),
                "avg_rating_last5": "" if avg_rating is None else f"{avg_rating:.2f}",
                "peak_rating": "" if peak_rating is None else f"{peak_rating:.2f}",
                "form_band": band,
                "evidence_quality": evidence_quality,
                "built_at": built_at,
            }
        )
        audit_rows.append(
            {
                "horse": horse(runner),
                "track": text(runner.get("track")),
                "race_no": race_no(runner),
                "form_row_found": "YES" if bool(form) else "NO",
                "history_rows_found": len(recent),
                "race_shape_found": "YES" if bool(shape) else "NO",
                "performance_intelligence_found": "YES" if bool(performance_note) else "NO",
                "evidence_quality": evidence_quality,
            }
        )

    fields = [
        "current_race_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "date",
        "distance",
        "class",
        "position",
        "margin",
        "SP",
        "rating",
        "EPF",
        "race_shape",
        "settling_position",
        "bias_notes",
        "performance_intelligence",
        "form_signal",
        "form_cycle",
        "recent_runs_found",
        "avg_rating_last5",
        "peak_rating",
        "form_band",
        "evidence_quality",
        "built_at",
    ]
    write_csv(OUT, output_rows, fields)
    write_csv(OUT_AUDIT, audit_rows, ["horse", "track", "race_no", "form_row_found", "history_rows_found", "race_shape_found", "performance_intelligence_found", "evidence_quality"])

    summary = [
        {"metric": "active_runner_rows", "value": len(active)},
        {"metric": "form_rows_output", "value": len(output_rows)},
        {"metric": "form_rows_with_history", "value": sum(1 for row in audit_rows if int(row["history_rows_found"]) > 0)},
        {"metric": "race_shape_rows_found", "value": sum(1 for row in audit_rows if row["race_shape_found"] == "YES")},
        {"metric": "performance_intelligence_rows_found", "value": sum(1 for row in audit_rows if row["performance_intelligence_found"] == "YES")},
    ]
    for band, count in sorted(band_counts.items()):
        summary.append({"metric": f"form_band::{band}", "value": count})
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])

    print(f"Wrote {OUT} ({len(output_rows)} rows)")
    print(f"Wrote {OUT_SUMMARY}")
    print(f"Wrote {OUT_AUDIT}")


if __name__ == "__main__":
    main()
