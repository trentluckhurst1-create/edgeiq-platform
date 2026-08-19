from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from edgeiq_beta_intelligence_v1_common import (
    DATA,
    EARLY_SPEED,
    LIVE_SPEED_MAP,
    clean,
    evidence_coverage,
    load_current_projection,
    load_current_runners,
    load_exact_csv,
    now_utc,
    round_or_none,
    to_float,
    write_csv,
    write_json,
    write_summary,
)


VERSION = "CURRENT_RACE_SHAPE_V2"
OUT_JSON = DATA / "edgeiq_current_race_shape_v2.json"
OUT_CSV = DATA / "edgeiq_current_race_shape_v2.csv"
GAP_AUDIT = DATA / "edgeiq_race_shape_v2_gap_audit.csv"
GAP_SUMMARY = DATA / "edgeiq_race_shape_v2_gap_summary.txt"
EVIDENCE_AUDIT = DATA / "edgeiq_current_race_shape_v2_evidence_audit.csv"
COVERAGE_SUMMARY = DATA / "edgeiq_current_race_shape_v2_coverage_summary.txt"


def supported_speed_map(row: dict[str, Any] | None) -> bool:
    if not row:
        return False
    confidence = clean(row.get("confidence")).upper()
    bucket = clean(row.get("speed_map_bucket") or row.get("map_style")).upper()
    evidence_fields = [
        row.get("historic_speed_bucket"),
        row.get("memory_projected_map_style"),
        row.get("run_style_cluster"),
        row.get("sectional_profile"),
        row.get("tempo_fit"),
    ]
    if confidence == "LOW" and bucket == "MIDFIELD" and not any(clean(item) for item in evidence_fields):
        return False
    return any(clean(item) for item in [bucket, *evidence_fields])


def race_pressure(race_rows: list[dict[str, Any]], early_rows: dict[tuple[str, str, str, str], dict[str, Any]]) -> str:
    values = [to_float(early_rows.get(row["identity"], {}).get("earlySpeed")) for row in race_rows]
    values = [value for value in values if value is not None]
    if len(values) < 3:
        return "UNRESOLVED"
    leader_count = sum(1 for value in values if value >= 58)
    if leader_count >= 4:
        return "HIGH"
    if leader_count >= 2:
        return "MODERATE"
    return "CONTROLLED"


def classify_runner(row: dict[str, Any], rank: int | None, field_count: int, pressure: str, speed_map_row: dict[str, Any] | None) -> tuple[str | None, str | None, list[str], int, int, str]:
    reasons: list[str] = []
    factors = 0
    available = 0

    if supported_speed_map(speed_map_row):
        available += 1
        factors += 1
        fit = clean(speed_map_row.get("tempo_fit")).upper()
        bucket = clean(speed_map_row.get("speed_map_bucket") or speed_map_row.get("map_style")).upper()
        if fit and fit not in {"MIDFIELD", "UNKNOWN"}:
            reasons.append(f"Current map evidence: {fit}.")
            return fit, bucket or None, reasons[:3], factors, available, "LIVE_SPEED_MAP_SUPPORTED"
        if bucket and bucket != "MIDFIELD":
            reasons.append(f"Projected map style: {bucket}.")
            return bucket, bucket, reasons[:3], factors, available, "LIVE_SPEED_MAP_SUPPORTED"

    early = to_float(row.get("earlySpeed"))
    if early is not None and rank is not None and field_count:
        available += 1
        factors += 1
        percentile = rank / max(1, field_count)
        if percentile <= 0.25:
            zone = "ON_SPEED"
            if pressure == "HIGH":
                shape = "PRESSURE_RISK"
                reasons.append("Strong early profile faces genuine race pressure.")
            else:
                shape = "MAP_ADVANTAGE"
                reasons.append("Early speed projects into the forward group.")
        elif percentile <= 0.55:
            zone = "MIDFIELD"
            shape = "NEUTRAL"
            reasons.append("Early speed supports a midfield settling position.")
        else:
            zone = "BACK"
            shape = "CLOSING_SETUP" if pressure in {"HIGH", "MODERATE"} else "NEEDS_TEMPO"
            reasons.append("Late map depends on race pressure developing.")
        return shape, zone, reasons[:3], factors, available, "CURRENT_EARLY_SPEED_ADAPTER"

    return None, None, reasons, factors, available, "NO_APPROVED_RACE_SHAPE_EVIDENCE"


def main() -> None:
    generated_at = now_utc()
    current = load_current_runners()
    early = load_current_projection(EARLY_SPEED, "earlySpeed")
    speed_map = load_exact_csv(LIVE_SPEED_MAP, "horse")

    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in current:
        grouped[row["raceIdentity"]].append(row)

    output: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    categories: Counter = Counter()
    gap_counts: Counter = Counter()

    for race_key, race_rows in grouped.items():
        pressure = race_pressure(race_rows, early)
        early_sorted = sorted(
            [(row, to_float(early.get(row["identity"], {}).get("earlySpeed"))) for row in race_rows],
            key=lambda item: item[1] if item[1] is not None else -999,
            reverse=True,
        )
        rank_map = {row["identity"]: index + 1 for index, (row, value) in enumerate(early_sorted) if value is not None}
        for runner in race_rows:
            early_row = early.get(runner["identity"], {})
            speed_map_row = speed_map.get(runner["identity"])
            runner_payload = {**runner, "earlySpeed": early_row.get("earlySpeed")}
            shape, zone, reasons, factor_count, available_count, method = classify_runner(
                runner_payload,
                rank_map.get(runner["identity"]),
                len(race_rows),
                pressure,
                speed_map_row,
            )
            if runner["isScratched"]:
                shape = None
                zone = None
                method = "SCRATCHED"
                reasons = []
            reason = ""
            if not shape:
                if runner["isScratched"]:
                    reason = "SCRATCHED"
                elif not speed_map_row and runner["identity"] not in early:
                    reason = "NO_SPEED_MAP_ROW"
                elif not supported_speed_map(speed_map_row) and early_row.get("earlySpeed") in (None, ""):
                    reason = "NO_RUN_STYLE_EVIDENCE"
                else:
                    reason = "INSUFFICIENT_HISTORICAL_RUNS"
                gaps.append(
                    {
                        "raceDate": runner["raceDate"],
                        "meeting": runner["meeting"],
                        "raceNumber": runner["raceNumber"],
                        "runnerNumber": runner["runnerNumber"],
                        "runnerName": runner["runnerName"],
                        "blankReason": reason,
                        "hasSpeedMapRow": "YES" if speed_map_row else "NO",
                        "hasEarlySpeed": "YES" if early_row.get("earlySpeed") not in (None, "") else "NO",
                    }
                )
                gap_counts[reason] += 1
            else:
                categories[shape] += 1

            output.append(
                {
                    "raceDate": runner["raceDate"],
                    "meeting": runner["meeting"],
                    "raceNumber": runner["raceNumber"],
                    "runnerId": runner["runnerId"],
                    "runnerNumber": runner["runnerNumber"],
                    "runnerName": runner["runnerName"],
                    "normalizedRunner": runner["normalizedRunner"],
                    "raceShape": shape,
                    "projectedZone": zone,
                    "racePressure": pressure,
                    "earlySpeed": early_row.get("earlySpeed"),
                    "evidenceFactorCount": factor_count,
                    "availableFactorCount": available_count,
                    "evidenceCoverage": evidence_coverage(factor_count, max(available_count, 1)) if factor_count else None,
                    "publicReasons": reasons,
                    "sourceVersion": VERSION,
                    "generatedAt": generated_at,
                    "asOfDate": runner["raceDate"],
                    "joinMethod": method,
                    "blankReason": reason,
                }
            )
            evidence_rows.append(
                {
                    "raceDate": runner["raceDate"],
                    "meeting": runner["meeting"],
                    "raceNumber": runner["raceNumber"],
                    "runnerName": runner["runnerName"],
                    "source": method,
                    "speedMapSupported": "YES" if supported_speed_map(speed_map_row) else "NO",
                    "earlySpeed": early_row.get("earlySpeed", ""),
                    "raceShape": shape or "",
                    "projectedZone": zone or "",
                    "defaultMidfieldRestored": "NO",
                    "asOfSafe": "YES",
                }
            )

    payload = {
        "schemaVersion": "edgeiq_current_race_shape_v2",
        "sourceVersion": VERSION,
        "generatedAt": generated_at,
        "methodology": {
            "definition": "Runner-level expression of how the projected race pattern affects the runner.",
            "minimumEvidence": "Supported speed-map evidence or approved current Early Speed V1 rank inside the selected race.",
            "notAllowed": "No runner receives MIDFIELD merely because a race row exists.",
        },
        "runners": output,
    }
    write_json(OUT_JSON, payload)
    write_csv(OUT_CSV, output, ["raceDate", "meeting", "raceNumber", "runnerId", "runnerNumber", "runnerName", "normalizedRunner", "raceShape", "projectedZone", "racePressure", "earlySpeed", "evidenceFactorCount", "availableFactorCount", "evidenceCoverage", "publicReasons", "sourceVersion", "generatedAt", "asOfDate", "joinMethod", "blankReason"])
    write_csv(GAP_AUDIT, gaps, ["raceDate", "meeting", "raceNumber", "runnerNumber", "runnerName", "blankReason", "hasSpeedMapRow", "hasEarlySpeed"])
    write_csv(EVIDENCE_AUDIT, evidence_rows)
    total = len(output)
    populated = sum(1 for row in output if row["raceShape"])
    write_summary(
        COVERAGE_SUMMARY,
        [
            "EDGEIQ CURRENT RACE SHAPE V2 COVERAGE",
            f"rows={total}",
            f"populated={populated}",
            f"blank={total - populated}",
            "category_counts=" + ", ".join(f"{k}:{v}" for k, v in sorted(categories.items())),
            "gap_counts=" + ", ".join(f"{k}:{v}" for k, v in sorted(gap_counts.items())),
        ],
    )
    write_summary(
        GAP_SUMMARY,
        [
            "EDGEIQ RACE SHAPE V2 GAP SUMMARY",
            *[f"{k}: {v}" for k, v in sorted(gap_counts.items())],
        ],
    )
    print(f"CURRENT_RACE_SHAPE_V2 rows={total} populated={populated} blank={total - populated}")


if __name__ == "__main__":
    main()
