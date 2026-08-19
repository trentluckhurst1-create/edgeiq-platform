import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
CONNECTION_FEED = DATA / "edgeiq_connection_intelligence_v2_1.csv"
OUT_DETAIL = DATA / "edgeiq_connection_render_state_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_connection_render_state_v1_summary.csv"


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


def clean_track(value: object) -> str:
    return "".join(ch for ch in text(value).upper() if ch.isalnum())


def clean_horse(value: object) -> str:
    raw = text(value).upper()
    while "(" in raw and ")" in raw:
        start = raw.find("(")
        end = raw.find(")", start)
        if end < 0:
            break
        raw = raw[:start] + raw[end + 1 :]
    return "".join(ch for ch in raw if ch.isalnum())


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


def connection_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (race_date(row), clean_track(row.get("track") or row.get("meeting")), race_no(row), clean_horse(row.get("horse_key") or horse(row)))


def has_material_evidence(row: dict[str, str] | None) -> bool:
    if not row:
        return False
    band = text(row.get("connection_band")).upper().replace(" ", "_")
    status = text(row.get("connection_evidence_status")).upper().replace(" ", "_")
    if band in {"", "--", "NO_EVIDENCE"}:
        return False
    if status in {"NO_CONNECTION", "NO_EVIDENCE"}:
        return False
    evidence_fields = [
        "connection_score",
        "connection_angle_1",
        "connection_angle_2",
        "connection_angle_3",
        "connection_risk_1",
        "connection_narrative",
        "evidence_quality",
        "trainer_track_read",
        "jockey_track_read",
        "combo_read",
    ]
    return any(text(row.get(key)) and text(row.get(key)) != "--" for key in evidence_fields)


def meaningful_angles(row: dict[str, str] | None) -> list[str]:
    if not row:
        return []
    values = []
    for key in ["connection_angle_1", "connection_angle_2", "connection_angle_3"]:
        value = text(row.get(key))
        normalized = value.upper()
        if value and normalized not in {"--", "LIMITED SAMPLE"}:
            values.append(value)
    return values


def fallback_read_patterns(row: dict[str, str] | None) -> list[str]:
    if not row:
        return []
    values = []
    for key in [
        "trainer_track_read",
        "trainer_distance_read",
        "trainer_prep_read",
        "trainer_market_read",
        "jockey_track_read",
        "jockey_distance_read",
        "combo_read",
    ]:
        value = text(row.get(key))
        normalized = value.upper()
        if value and normalized not in {"--", "LIMITED SAMPLE"} and not normalized.startswith("NOT APPLICABLE"):
            values.append(value)
    return values


def main() -> None:
    runners = [row for row in read_csv(RUNNER_BOARD) if not is_scratched(row)]
    connections = read_csv(CONNECTION_FEED)
    connection_by_key = {connection_key(row): row for row in connections}

    rows: list[dict[str, object]] = []
    hidden_reasons: Counter[str] = Counter()
    suppression_conditions: Counter[str] = Counter()

    for runner in runners:
        key = connection_key(runner)
        connection = connection_by_key.get(key)
        material = has_material_evidence(connection)
        angles = meaningful_angles(connection)
        fallback_patterns = fallback_read_patterns(connection)
        narrative = text((connection or {}).get("connection_narrative"))
        band = text((connection or {}).get("connection_band")).upper().replace("_", " ") or "--"
        status = text((connection or {}).get("connection_evidence_status")).upper().replace("_", " ") or "--"

        show_connection_card = material
        show_connection_insights = material and bool(narrative)
        show_connection_evidence = material and bool(angles or fallback_patterns or narrative)
        show_connection_tab = material
        legacy_angle_only_evidence = material and bool(angles)

        reasons = []
        if not connection:
            reasons.append("NO_JOINED_CONNECTION_ROW")
        if connection and not material:
            reasons.append("NO_MATERIAL_EVIDENCE")
        if material and not show_connection_card:
            reasons.append("showConnectionCard_FALSE_WITH_MATERIAL_EVIDENCE")
            suppression_conditions["showConnectionCard"] += 1
        if material and not show_connection_insights:
            reasons.append("showConnectionInsights_FALSE_WITH_MATERIAL_EVIDENCE")
            suppression_conditions["showConnectionInsights"] += 1
        if material and not show_connection_evidence:
            reasons.append("showConnectionEvidence_FALSE_WITH_MATERIAL_EVIDENCE")
            suppression_conditions["showConnectionEvidence"] += 1
        if material and not legacy_angle_only_evidence:
            suppression_conditions["legacyAngleOnlyEvidence"] += 1
        if material and not show_connection_tab:
            reasons.append("showConnectionTab_FALSE_WITH_MATERIAL_EVIDENCE")
            suppression_conditions["showConnectionTab"] += 1
        if not reasons:
            reasons.append("VISIBLE")

        reason = "|".join(reasons)
        hidden_reasons[reason] += 1
        rows.append(
            {
                "selected_runner_name": horse(runner),
                "race_date": race_date(runner),
                "track": text(runner.get("track")),
                "race_no": race_no(runner),
                "connection_band": band,
                "connection_status": status,
                "material_evidence_flag": "YES" if material else "NO",
                "showConnectionCard": "YES" if show_connection_card else "NO",
                "showConnectionInsights": "YES" if show_connection_insights else "NO",
                "showConnectionEvidence": "YES" if show_connection_evidence else "NO",
                "showConnectionTab": "YES" if show_connection_tab else "NO",
                "render_hidden_reason": reason,
            }
        )

    fields = [
        "selected_runner_name",
        "race_date",
        "track",
        "race_no",
        "connection_band",
        "connection_status",
        "material_evidence_flag",
        "showConnectionCard",
        "showConnectionInsights",
        "showConnectionEvidence",
        "showConnectionTab",
        "render_hidden_reason",
    ]
    write_csv(OUT_DETAIL, rows, fields)

    summary = [
        {"metric": "active_runner_rows", "value": len(runners)},
        {"metric": "connection_rows", "value": len(connections)},
        {"metric": "material_evidence_rows", "value": sum(1 for row in rows if row["material_evidence_flag"] == "YES")},
        {"metric": "non_material_rows", "value": sum(1 for row in rows if row["material_evidence_flag"] == "NO")},
        {"metric": "showConnectionCard_false_with_material_evidence", "value": suppression_conditions["showConnectionCard"]},
        {"metric": "showConnectionInsights_false_with_material_evidence", "value": suppression_conditions["showConnectionInsights"]},
        {"metric": "showConnectionEvidence_false_with_material_evidence", "value": suppression_conditions["showConnectionEvidence"]},
        {"metric": "showConnectionTab_false_with_material_evidence", "value": suppression_conditions["showConnectionTab"]},
        {"metric": "legacy_angle_only_evidence_false_with_material_evidence", "value": suppression_conditions["legacyAngleOnlyEvidence"]},
    ]
    for reason, count in sorted(hidden_reasons.items()):
        summary.append({"metric": f"render_hidden_reason::{reason}", "value": count})

    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT_DETAIL} ({len(rows)} rows)")
    print(f"Wrote {OUT_SUMMARY}")


if __name__ == "__main__":
    main()
