import csv
import re
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
HIDDEN_PERFORMANCE = DATA / "edgeiq_current_hidden_gem_feed_v1_1.csv"

OUT = DATA / "edgeiq_form_intelligence_v2.csv"
OUT_SUMMARY = DATA / "edgeiq_form_intelligence_v2_summary.csv"
OUT_AUDIT = DATA / "edgeiq_form_intelligence_v2_audit.csv"


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


def num(value: object) -> float | None:
    raw = text(value).replace("$", "").replace("%", "").replace(",", "")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def race_date(row: dict[str, str]) -> str:
    return text(row.get("current_race_date") or row.get("race_date") or row.get("meeting_date") or row.get("date") or row.get("raceDate"))


def race_no(row: dict[str, str]) -> str:
    return text(row.get("race_no") or row.get("raceNo") or row.get("race_number") or row.get("race"))


def horse(row: dict[str, str]) -> str:
    return text(row.get("horse") or row.get("horseName") or row.get("runner") or row.get("runner_name"))


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


def date_value(row: dict[str, str]) -> str:
    return text(row.get("run_date_iso") or row.get("run_date") or row.get("race_date"))[:10]


def epf_band(value: float | None) -> str:
    if value is None:
        return "UNKNOWN"
    if value >= 75:
        return "HIGH"
    if value >= 55:
        return "MID"
    if value > 0:
        return "LOW"
    return "UNKNOWN"


def performance_label(hidden: dict[str, str], rating: float | None, margin: str) -> str:
    if text(hidden.get("actionable_watch_flag")).upper() == "YES":
        return "STRONG CASE"
    if text(hidden.get("historical_watch_flag")).upper() == "YES":
        return "IMPROVING"
    margin_value = num(margin.replace("L", ""))
    if rating is not None and rating >= 65:
        return "IMPROVING"
    if margin_value is not None and margin_value > 8:
        return "BELOW EXPECTATIONS"
    return "NEUTRAL"


def customer_performance_narrative(value: str) -> str:
    cleaned = re.sub(r"hidden[- ]gem", "performance intelligence", value, flags=re.IGNORECASE)
    cleaned = re.sub(r"performance intelligence score \d+(?:\.\d+)? from ", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"No recent performance intelligence signal matched", "Neutral recent performance intelligence", cleaned, flags=re.IGNORECASE)
    return cleaned


def against_bias_flag(settling: str, shape: dict[str, str]) -> str:
    advantage = text(shape.get("pace_advantage_label")).upper()
    role = text(settling).upper()
    if not advantage or not role:
        return "UNKNOWN"
    if ("LEAD" in advantage or "ON PACE" in advantage or "FORWARD" in advantage) and ("BACK" in role or "OFF" in role):
        return "YES"
    if ("CLOSER" in advantage or "LATE" in advantage) and ("LEAD" in role or "ON" in role):
        return "YES"
    return "NO"


def compact_run(row: dict[str, str], shape: dict[str, str], hidden: dict[str, str]) -> dict[str, str]:
    rating = num(row.get("performance_rating") or row.get("run_rating") or row.get("rating"))
    settling = text(row.get("settling_position") or row.get("pos_800") or row.get("pos_400"))
    margin = text(row.get("margin"))
    label = performance_label(hidden, rating, margin)
    return {
        "date": date_value(row),
        "track": text(row.get("track")),
        "distance": text(row.get("distance")),
        "class": text(row.get("class_name") or row.get("race_class")),
        "finishing_position": text(row.get("finish_pos")),
        "beaten_margin": margin,
        "SP": text(row.get("sp") or row.get("sp_text") or row.get("starting_price")),
        "rating": "" if rating is None else f"{rating:.2f}",
        "settled_position": settling,
        "sectional_rank": text(row.get("closing_sectional_rank")),
        "against_bias_flag": against_bias_flag(settling, shape),
        "performance_label": label,
    }


def main() -> None:
    active = [row for row in read_csv(RUNNER_BOARD) if not is_scratched(row)]
    form_rows = {runner_key(row): row for row in read_csv(RUNNER_FORM)}
    shape_rows = {race_key(row): row for row in read_csv(RACE_SHAPE)}
    hidden_rows = {runner_key(row): row for row in read_csv(HIDDEN_PERFORMANCE)}

    histories: dict[str, list[dict[str, str]]] = defaultdict(list)
    for source_rows in [read_csv(HISTORY_DETAIL), read_csv(RUNNER_HISTORY)]:
        for row in source_rows:
            key = history_key(row)
            if key:
                histories[key].append(row)
    for rows in histories.values():
        rows.sort(key=date_value, reverse=True)

    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    output_rows: list[dict[str, object]] = []
    audit_rows: list[dict[str, object]] = []
    label_counts: Counter[str] = Counter()

    for runner in active:
        key = runner_key(runner)
        h_key = history_key(runner)
        form = form_rows.get(key, {})
        shape = shape_rows.get(race_key(runner), {})
        hidden = hidden_rows.get(key, {})
        recent = histories.get(h_key, [])[:5]
        last = recent[0] if recent else {}
        last_run = compact_run(last, shape, hidden) if last else {}

        epf = num(runner.get("early_speed_rating")) or num(runner.get("projected_spd")) or num(runner.get("total_rating_points"))
        label = text(last_run.get("performance_label")) or performance_label(hidden, None, "")
        label_counts[label] += 1

        narrative = customer_performance_narrative(text(hidden.get("hidden_gem_narrative")))
        if not narrative:
            narrative = text(form.get("form_narrative"))
        if not narrative:
            narrative = f"{horse(runner)} has limited recent form evidence in the current EDGEiQ history spine."

        out = {
            "current_race_date": race_date(runner),
            "track": text(runner.get("track")),
            "race_no": race_no(runner),
            "horse": horse(runner),
            "horse_key": text(runner.get("horse_key")) or horse_clean(horse(runner)),
            "finishing_position": text(last_run.get("finishing_position")),
            "beaten_margin": text(last_run.get("beaten_margin")),
            "SP": text(last_run.get("SP")),
            "settled_position": text(last_run.get("settled_position")) or text(runner.get("settling_band") or runner.get("speed_map_bucket") or runner.get("run_style")),
            "race_shape": text(shape.get("race_shape_label")) or "UNKNOWN",
            "pace_pressure": text(shape.get("tempo_label") or shape.get("pressure_risk")) or "UNKNOWN",
            "sectional_rank": text(last_run.get("sectional_rank")),
            "against_bias_flag": text(last_run.get("against_bias_flag")) or "UNKNOWN",
            "performance_intelligence_narrative": narrative,
            "performance_intelligence_label": label,
            "EPF": "" if epf is None else f"{epf:.2f}",
            "EPF_band": epf_band(epf),
            "form_signal": text(form.get("form_signal")) or ("LIMITED FORM" if not recent else "DEVELOPING FORM"),
            "form_cycle": text(form.get("form_cycle")) or "UNKNOWN",
            "recent_runs_found": len(recent),
            "evidence_quality": "HIGH" if len(recent) >= 5 else "MEDIUM" if len(recent) >= 2 else "LIMITED",
            "built_at": built_at,
        }

        for index in range(5):
            run = compact_run(recent[index], shape, hidden) if index < len(recent) else {}
            prefix = f"last_start_{index + 1}_"
            for field in [
                "date",
                "track",
                "distance",
                "class",
                "finishing_position",
                "beaten_margin",
                "SP",
                "rating",
                "settled_position",
                "sectional_rank",
                "against_bias_flag",
                "performance_label",
            ]:
                out[prefix + field] = text(run.get(field))

        output_rows.append(out)
        audit_rows.append(
            {
                "horse": horse(runner),
                "track": text(runner.get("track")),
                "race_no": race_no(runner),
                "history_runs_found": len(histories.get(h_key, [])),
                "last_five_runs_output": len(recent),
                "race_shape_found": "YES" if bool(shape) else "NO",
                "sectional_rank_available": "YES" if any(text(run.get("closing_sectional_rank")) for run in recent) else "NO",
                "performance_label": label,
                "EPF_band": epf_band(epf),
            }
        )

    base_fields = [
        "current_race_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "finishing_position",
        "beaten_margin",
        "SP",
        "settled_position",
        "race_shape",
        "pace_pressure",
        "sectional_rank",
        "against_bias_flag",
        "performance_intelligence_narrative",
        "performance_intelligence_label",
        "EPF",
        "EPF_band",
        "form_signal",
        "form_cycle",
        "recent_runs_found",
        "evidence_quality",
        "built_at",
    ]
    run_fields = [
        f"last_start_{index}_{field}"
        for index in range(1, 6)
        for field in [
            "date",
            "track",
            "distance",
            "class",
            "finishing_position",
            "beaten_margin",
            "SP",
            "rating",
            "settled_position",
            "sectional_rank",
            "against_bias_flag",
            "performance_label",
        ]
    ]
    write_csv(OUT, output_rows, base_fields + run_fields)
    write_csv(
        OUT_AUDIT,
        audit_rows,
        ["horse", "track", "race_no", "history_runs_found", "last_five_runs_output", "race_shape_found", "sectional_rank_available", "performance_label", "EPF_band"],
    )

    summary = [
        {"metric": "active_runner_rows", "value": len(active)},
        {"metric": "form_rows_output", "value": len(output_rows)},
        {"metric": "rows_with_history", "value": sum(1 for row in audit_rows if int(row["history_runs_found"]) > 0)},
        {"metric": "rows_with_last_five_runs", "value": sum(1 for row in audit_rows if int(row["last_five_runs_output"]) >= 5)},
        {"metric": "rows_with_race_shape", "value": sum(1 for row in audit_rows if row["race_shape_found"] == "YES")},
        {"metric": "rows_with_sectional_rank", "value": sum(1 for row in audit_rows if row["sectional_rank_available"] == "YES")},
    ]
    for label, count in sorted(label_counts.items()):
        summary.append({"metric": f"performance_label::{label}", "value": count})
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])

    print(f"Wrote {OUT} ({len(output_rows)} rows)")
    print(f"Wrote {OUT_SUMMARY}")
    print(f"Wrote {OUT_AUDIT}")


if __name__ == "__main__":
    main()
