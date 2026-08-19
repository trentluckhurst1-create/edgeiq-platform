from __future__ import annotations

import json
import os
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from edgeiq_beta_intelligence_v1_common import DATA, ROOT, clean, stats, to_float, write_csv, write_distribution, write_json, write_summary


PRELIGHT = DATA / "edgeiq_beta_intelligence_completion_v1_preflight_status.txt"
ENRICHED = DATA / "edgeiq_form_guide_enriched_v2.json"
RACE_INTELLIGENCE = DATA / "edgeiq_current_race_intelligence_v1.json"
OVERVIEW_AUDIT = DATA / "edgeiq_overview_v1_evidence_audit.csv"
SEMANTIC_CSV = DATA / "edgeiq_beta_intelligence_v1_semantic_audit.csv"
SEMANTIC_SUMMARY = DATA / "edgeiq_beta_intelligence_v1_semantic_summary.txt"
DIST_CSV = DATA / "edgeiq_beta_intelligence_v1_distribution.csv"
DIST_SUMMARY = DATA / "edgeiq_beta_intelligence_v1_distribution_summary.txt"
AUDIT_TXT = DATA / "edgeiq_beta_intelligence_completion_v1_audit.txt"
AUDIT_JSON = DATA / "edgeiq_beta_intelligence_completion_v1_audit.json"


def read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    import csv

    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        return list(csv.DictReader(handle))


def value_of(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("value")
    return value


def flatten_enriched() -> list[dict[str, Any]]:
    payload = read_json(ENRICHED)
    rows: list[dict[str, Any]] = []
    for race in payload.get("races", []) if isinstance(payload, dict) else []:
        for runner in race.get("runners", []) or []:
            row = dict(runner)
            row["_raceDate"] = race.get("raceDate")
            row["_meeting"] = race.get("meeting")
            row["_raceNumber"] = race.get("raceNumber")
            rows.append(row)
    return rows


def metric_values(rows: list[dict[str, Any]], field: str) -> list[float]:
    out: list[float] = []
    for row in rows:
        value = to_float(value_of(row.get(field)))
        if value is not None:
            out.append(value)
    return out


def metric_count(rows: list[dict[str, Any]], field: str) -> int:
    return len(metric_values(rows, field))


def populated_count(rows: list[dict[str, Any]], field: str) -> int:
    return sum(1 for row in rows if clean(value_of(row.get(field))))


def equality_rate(rows: list[dict[str, Any]], left: str, right: str) -> float:
    compared = 0
    same = 0
    for row in rows:
        a = to_float(value_of(row.get(left)))
        b = to_float(value_of(row.get(right)))
        if a is None or b is None:
            continue
        compared += 1
        if round(a, 2) == round(b, 2):
            same += 1
    return 0.0 if compared == 0 else round((same / compared) * 100, 2)


def contains_any(text: str, terms: list[str]) -> bool:
    upper = text.upper()
    return any(term.upper() in upper for term in terms)


def contains_tipping_language(text: str) -> bool:
    position_context = re.search(r"\blead\b.*\bon pace\b.*\bmidfield\b.*\bback\b", text, flags=re.IGNORECASE)
    if position_context:
        text = re.sub(r"\bback\b", "rear", text, flags=re.IGNORECASE)
    return bool(re.search(r"\b(BET|BACK|LAY|TIP|TIPPING)\b|VALUE\s+BET", text, flags=re.IGNORECASE))


def build_distribution(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    metrics = [
        ("EPI", "epi"),
        ("EDGEiQ Price", "edgeiqPrice"),
        ("Early Speed", "earlySpeed"),
        ("Late Speed", "lateSpeed"),
        ("Suitability", "suitability"),
        ("Form Momentum", "formMomentum"),
    ]
    total = len(rows)
    out: list[dict[str, Any]] = []
    for label, field in metrics:
        values = metric_values(rows, field)
        s = stats(values)
        flag = "OK"
        if s["count"] and s["unique"] <= 3:
            flag = "LOW_UNIQUE_VALUES"
        if s["zero_count"]:
            flag = "ZERO_VALUES_PRESENT_REVIEWED"
        out.append({
            "metric": label,
            "count": s["count"],
            "coverage_pct": round((s["count"] / total) * 100, 1) if total else 0,
            "minimum": s["min"],
            "maximum": s["max"],
            "mean": s["mean"],
            "median": s["median"],
            "standard_deviation": s["stddev"],
            "unique_values": s["unique"],
            "null_count": total - s["count"],
            "zero_count": s["zero_count"],
            "flag": flag,
        })
    shape_counts = Counter(clean(value_of(row.get("raceShape"))) for row in rows if clean(value_of(row.get("raceShape"))))
    for key, count in sorted(shape_counts.items()):
        out.append({
            "metric": f"Race Shape: {key}",
            "count": count,
            "coverage_pct": round((count / total) * 100, 1) if total else 0,
            "minimum": "",
            "maximum": "",
            "mean": "",
            "median": "",
            "standard_deviation": "",
            "unique_values": "",
            "null_count": "",
            "zero_count": "",
            "flag": "CATEGORY_COUNT",
        })
    return out


def build_semantic(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    checks = [
        ("EPI is not Suitability", "epi", "suitability", 80.0),
        ("EPI is not Early Speed", "epi", "earlySpeed", 80.0),
        ("EPI is not Late Speed", "epi", "lateSpeed", 80.0),
        ("Late Speed is not Form Momentum", "lateSpeed", "formMomentum", 80.0),
        ("Market is not EDGEiQ Price", "marketPrice", "edgeiqPrice", 80.0),
    ]
    out: list[dict[str, Any]] = []
    ok = True
    for label, left, right, limit in checks:
        rate = equality_rate(rows, left, right)
        passed = rate < limit
        ok = ok and passed
        out.append({
            "check": label,
            "left": left,
            "right": right,
            "identical_rate_pct": rate,
            "threshold_pct": limit,
            "status": "PASS" if passed else "FAIL",
        })
    missing_zero = any(to_float(value_of(row.get(field))) == 0 for row in rows for field in ["epi", "earlySpeed", "lateSpeed", "suitability"])
    out.append({
        "check": "Unavailable values are not represented as zero",
        "left": "core_metrics",
        "right": "zero",
        "identical_rate_pct": "",
        "threshold_pct": "",
        "status": "WARN" if missing_zero else "PASS",
    })
    return out, ok


def main() -> None:
    rows = flatten_enriched()
    race_intelligence = read_json(RACE_INTELLIGENCE)
    overview_rows = read_csv(OVERVIEW_AUDIT)
    race_shape_gaps = read_csv(DATA / "edgeiq_race_shape_v2_gap_audit.csv")
    suitability_asof = read_csv(DATA / "edgeiq_suitability_v1_asof_audit.csv")
    momentum_asof = read_csv(DATA / "edgeiq_form_momentum_v1_asof_audit.csv")
    weather_coverage = (DATA / "edgeiq_weather_beta_v1_coverage_summary.txt").read_text(encoding="utf-8", errors="replace") if (DATA / "edgeiq_weather_beta_v1_coverage_summary.txt").exists() else ""
    map_source = (ROOT / "src" / "edgeiq-os" / "race" / "components" / "MapWorkspace.tsx").read_text(encoding="utf-8", errors="replace")
    overview_source = (ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx").read_text(encoding="utf-8", errors="replace")
    src_text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in (ROOT / "src").rglob("*.ts*") if "CHECKPOINT" not in path.name)

    distribution_rows = build_distribution(rows)
    write_distribution(DIST_CSV, DIST_SUMMARY, distribution_rows)
    semantic_rows, semantic_ok = build_semantic(rows)
    write_csv(SEMANTIC_CSV, semantic_rows, ["check", "left", "right", "identical_rate_pct", "threshold_pct", "status"])
    write_summary(SEMANTIC_SUMMARY, [
        "EDGEIQ BETA INTELLIGENCE V1 SEMANTIC SUMMARY",
        *[f"{row['check']}: {row['status']} identical_rate={row['identical_rate_pct']}" for row in semantic_rows],
    ])

    npm_command = "npm.cmd" if os.name == "nt" else "npm"
    build = subprocess.run([npm_command, "run", "build"], cwd=ROOT, capture_output=True, text=True, shell=False)
    build_ok = build.returncode == 0

    overview_tipping = any(contains_tipping_language(row.get("text", "")) for row in overview_rows)
    future_unsafe = any(row.get("future_rows_used") not in {"", "0", None} for row in suitability_asof + momentum_asof)
    selected_unsafe = any(row.get("selected_race_result_rows_used") not in {"", "0", None} for row in suitability_asof + momentum_asof)

    checks = {
        "preflight_status_exists": PRELIGHT.exists(),
        "existing_speed_audit_exists": (DATA / "edgeiq_current_speed_projection_v1_audit.txt").exists(),
        "existing_current_intelligence_audit_exists": (DATA / "edgeiq_current_intelligence_v1_1_audit.txt").exists(),
        "suitability_spec_exists": (ROOT / "docs" / "EDGEIQ_SUITABILITY_ENGINE_V1_SPEC.md").exists(),
        "suitability_source_inventory_exists": (DATA / "edgeiq_suitability_v1_source_inventory.csv").exists(),
        "suitability_builder_exists": (ROOT / "scripts" / "build_edgeiq_current_suitability_v1.py").exists(),
        "suitability_populated": metric_count(rows, "suitability") > 0,
        "form_momentum_spec_exists": (ROOT / "docs" / "EDGEIQ_FORM_MOMENTUM_ENGINE_V1_SPEC.md").exists(),
        "form_momentum_source_inventory_exists": (DATA / "edgeiq_form_momentum_v1_source_inventory.csv").exists(),
        "form_momentum_builder_exists": (ROOT / "scripts" / "build_edgeiq_current_form_momentum_v1.py").exists(),
        "form_momentum_populated": metric_count(rows, "formMomentum") > 0,
        "race_shape_gap_audit_exists": bool(race_shape_gaps),
        "race_shape_improved": populated_count(rows, "raceShape") > 152,
        "no_default_midfield_restored": "default every unsupported runner to midfield" not in map_source.lower(),
        "early_speed_coverage_preserved": metric_count(rows, "earlySpeed") >= 252,
        "late_speed_coverage_preserved": metric_count(rows, "lateSpeed") >= 257,
        "weather_coverage_audit_exists": "EDGEIQ WEATHER BETA V1 COVERAGE" in weather_coverage,
        "weather_contract_exists": (DATA / "edgeiq_race_weather_v1.json").exists(),
        "map_feed_exists": (DATA / "edgeiq_current_map_v1.json").exists(),
        "map_has_unresolved_not_default_midfield": "UNRESOLVED" in map_source,
        "map_orientation_documented": "leaders left, barrier 1 bottom" in (DATA / "edgeiq_current_map_v1.json").read_text(encoding="utf-8", errors="replace"),
        "overview_feed_exists": RACE_INTELLIGENCE.exists(),
        "overview_audit_exists": bool(overview_rows),
        "overview_no_tipping_language": not overview_tipping,
        "overview_source_tags_present": all(clean(row.get("source")) for row in overview_rows),
        "current_market_separate_from_edgeiq_price": semantic_ok,
        "no_future_or_selected_race_leakage": not future_unsafe and not selected_unsafe,
        "no_proprietary_engine_sources_in_react": not contains_any(src_text, ["private weight", "build_edgeiq_current_suitability_v1"]),
        "form_guide_all_runner_workflow_intact": "scrollToRunner" in src_text and "runner-profile-" in src_text,
        "workspace_tabs_intact": all(token in overview_source for token in ['"FORM GUIDE"', '"MARKET"', '"MAP"', '"OVERVIEW"']),
        "npm_build_passes": build_ok,
    }
    status = "EDGEIQ_BETA_INTELLIGENCE_COMPLETION_V1_AUDIT_PASS" if all(checks.values()) else "EDGEIQ_BETA_INTELLIGENCE_COMPLETION_V1_AUDIT_FAIL"

    lines = [status, "", "Checks:"]
    lines += [f"{key}: {'PASS' if value else 'FAIL'}" for key, value in checks.items()]
    lines += [
        "",
        "Coverage:",
        f"EPI: {metric_count(rows, 'epi')} / {len(rows)}",
        f"EDGEiQ Price: {metric_count(rows, 'edgeiqPrice')} / {len(rows)}",
        f"Race Shape: {populated_count(rows, 'raceShape')} / {len(rows)}",
        f"Early Speed: {metric_count(rows, 'earlySpeed')} / {len(rows)}",
        f"Late Speed: {metric_count(rows, 'lateSpeed')} / {len(rows)}",
        f"Suitability: {metric_count(rows, 'suitability')} / {len(rows)}",
        f"Form Momentum: {metric_count(rows, 'formMomentum')} / {len(rows)}",
        "",
        "Build:",
        "PASS" if build_ok else "FAIL",
        build.stderr[-2000:] if not build_ok else "Vite build completed; known chunk-size warning may remain.",
    ]
    write_summary(AUDIT_TXT, lines)
    write_json(AUDIT_JSON, {
        "status": status,
        "checks": checks,
        "coverage": {
            "total": len(rows),
            "epi": metric_count(rows, "epi"),
            "edgeiqPrice": metric_count(rows, "edgeiqPrice"),
            "raceShape": populated_count(rows, "raceShape"),
            "earlySpeed": metric_count(rows, "earlySpeed"),
            "lateSpeed": metric_count(rows, "lateSpeed"),
            "suitability": metric_count(rows, "suitability"),
            "formMomentum": metric_count(rows, "formMomentum"),
        },
        "distributionReport": str(DIST_CSV),
        "semanticAudit": str(SEMANTIC_CSV),
        "npmBuildReturnCode": build.returncode,
    })
    print(status)


if __name__ == "__main__":
    main()
