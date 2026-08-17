from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from edgeiq_current_feed_authority_v1 import (
    FEED_CONTRACTS,
    FeedInspection,
    choose_current_feed_authority,
    clean_text,
    comparable_row,
    equivalence_status,
    get_operational_date,
    inspect_feed_freshness,
    runner_identity,
)


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
PERFORMANCE = ROOT / "public" / "performance-intelligence"
OUT_DIR = ROOT / "outputs" / "current-feed-authority-v1"
OUT_CSV = OUT_DIR / "edgeiq_current_feed_authority_inventory_v1.csv"
OUT_SUMMARY = OUT_DIR / "edgeiq_current_feed_authority_inventory_v1_summary.json"


CRITICAL_FEEDS: list[dict[str, Any]] = [
    {"logical_feed": "edgeiq_three_day_window_v1", "paths": [DATA / "edgeiq_three_day_window_v1.json"], "date_requirement": "WINDOW", "critical": True, "producer": "build_edgeiq_three_day_window_v1.py"},
    {"logical_feed": "edgeiq_three_day_product_catalog_v1", "paths": [DATA / "edgeiq_three_day_product_catalog_v1.json"], "date_requirement": "WINDOW", "critical": True, "producer": "build_edgeiq_three_day_product_catalog_v1.py"},
    {"logical_feed": "edgeiq_vic_three_day_meeting_universe", "paths": [DATA / "edgeiq_vic_three_day_meeting_universe.csv"], "date_requirement": "WINDOW", "critical": True, "producer": "build_edgeiq_vic_three_day_meeting_universe.py"},
    {"logical_feed": "edgeiq_vic_three_day_race_list_v1", "paths": [DATA / "edgeiq_vic_three_day_race_list_v1.csv"], "date_requirement": "WINDOW", "critical": True, "producer": "build_edgeiq_racingcom_three_day_race_list_v1.py"},
    {"logical_feed": "race_fields", "paths": [DATA / "race_fields.csv"], "date_requirement": "WINDOW", "critical": True, "producer": "build_edgeiq_current_race_fields_from_product_catalog_v1.py"},
    {"logical_feed": "edgeiq_epi_current_rating_v1", "paths": [DATA / "edgeiq_epi_current_rating_v1.csv", DATA / "edgeiq_epi_current_rating_v1.json"], "critical": True, "producer": "build_edgeiq_current_runner_scoped_performance_chain_v1.py"},
    {"logical_feed": "edgeiq_fair_price_epr_v1", "paths": [DATA / "edgeiq_fair_price_epr_v1.csv"], "critical": True, "producer": "build_edgeiq_fair_price_epr_v1.py"},
    {"logical_feed": "edgeiq_current_market_v1", "paths": [DATA / "edgeiq_current_market_v1.csv", DATA / "edgeiq_current_market_v1.json"], "critical": True, "producer": "build_edgeiq_current_market_v1.py"},
    {"logical_feed": "edgeiq_current_early_speed_v1", "paths": [DATA / "edgeiq_current_early_speed_v1.csv", DATA / "edgeiq_current_early_speed_v1.json"], "critical": True, "producer": "build_edgeiq_current_early_speed_v1.py"},
    {"logical_feed": "edgeiq_current_late_speed_v1", "paths": [DATA / "edgeiq_current_late_speed_v1.csv", DATA / "edgeiq_current_late_speed_v1.json"], "critical": True, "producer": "build_edgeiq_current_late_speed_v1.py"},
    {"logical_feed": "edgeiq_current_suitability_v1", "paths": [DATA / "edgeiq_current_suitability_v1.csv", DATA / "edgeiq_current_suitability_v1.json"], "critical": True, "producer": "build_edgeiq_current_suitability_v1.py"},
    {"logical_feed": "edgeiq_current_form_momentum_v1", "paths": [DATA / "edgeiq_current_form_momentum_v1.csv", DATA / "edgeiq_current_form_momentum_v1.json"], "critical": True, "producer": "build_edgeiq_current_form_momentum_v1.py"},
    {"logical_feed": "edgeiq_current_race_shape_v2", "paths": [DATA / "edgeiq_current_race_shape_v2.csv", DATA / "edgeiq_current_race_shape_v2.json"], "critical": True, "producer": "build_edgeiq_current_race_shape_v2.py"},
    {"logical_feed": "edgeiq_form_guide_enriched_v2", "paths": [DATA / "edgeiq_form_guide_enriched_v2.csv", DATA / "edgeiq_form_guide_enriched_v2.json"], "critical": True, "producer": "build_edgeiq_form_guide_enriched_v2.py"},
    {"logical_feed": "edgeiq_market_terminal_feed_v1", "paths": [DATA / "edgeiq_market_terminal_feed_v1.csv"], "critical": True, "producer": "build_edgeiq_market_terminal_feed_v1.py"},
    {"logical_feed": "edgeiq_map_terminal_feed_v1", "paths": [DATA / "edgeiq_map_terminal_feed_v1.csv"], "critical": True, "producer": "build_edgeiq_map_terminal_feed_v1.py"},
    {"logical_feed": "edgeiq_current_race_intelligence_v1", "paths": [DATA / "edgeiq_current_race_intelligence_v1.json"], "date_requirement": "NOT_APPLICABLE", "critical": False, "producer": "build_edgeiq_current_race_intelligence_v1.py"},
    {"logical_feed": "edgeiq_current_true_track_feed_v1", "paths": [DATA / "edgeiq_current_true_track_feed_v1.csv"], "date_requirement": "NOT_APPLICABLE", "critical": False, "producer": "build_edgeiq_current_true_track_feed_v1.py"},
    {"logical_feed": "edgeiq_metropolitan_weather_v1", "paths": [DATA / "edgeiq_metropolitan_weather_v1.json"], "date_requirement": "NOT_APPLICABLE", "critical": False, "producer": "build_edgeiq_metropolitan_weather_v1.py"},
    {"logical_feed": "edgeiq_victorian_track_weather_v1", "paths": [DATA / "edgeiq_victorian_track_weather_v1.json"], "date_requirement": "NOT_APPLICABLE", "critical": False, "producer": "build_edgeiq_victorian_track_weather_v1.py"},
    {"logical_feed": "edgeiq_on_track_weather_governed_v1_2", "paths": [DATA / "edgeiq_on_track_weather_governed_v1_2.csv", DATA / "edgeiq_on_track_weather_governed_v1_2.json"], "date_requirement": "NOT_APPLICABLE", "critical": False, "producer": "build_edgeiq_on_track_weather_governed_v1_2.py"},
    {"logical_feed": "edgeiq_meeting_results_terminal_feed_v1", "paths": [DATA / "edgeiq_meeting_results_terminal_feed_v1.csv"], "critical": True, "producer": "build_edgeiq_meeting_results_terminal_feed_v1.py"},
    {"logical_feed": "edgeiq_performance_intelligence_product_feeds_v1", "paths": [PERFORMANCE / "edgeiq_performance_intelligence_product_feeds_v1.json"], "date_requirement": "NOT_APPLICABLE", "critical": False, "producer": "performance-intelligence/product-integration/build_edgeiq_performance_intelligence_product_feeds_v1.py"},
]


def source_files() -> list[Path]:
    roots = [ROOT / "scripts", ROOT / "src"]
    paths: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix.lower() in {".py", ".ps1", ".ts", ".tsx", ".js", ".mjs", ".cjs"} and "CHECKPOINT" not in path.name and "BEFORE" not in path.name:
                paths.append(path)
    return paths


def consumer_index(logical_paths: list[Path]) -> dict[str, list[str]]:
    names = {path.name for path in logical_paths}
    index: dict[str, list[str]] = {name: [] for name in names}
    for source in source_files():
        try:
            text = source.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = source.relative_to(ROOT).as_posix()
        for name in names:
            if name in text:
                index[name].append(rel)
    return index


def compare_pair(left: FeedInspection, right: FeedInspection) -> dict[str, Any]:
    left_map = {runner_identity(row): comparable_row(row) for row in left.records if runner_identity(row).strip("|")}
    right_map = {runner_identity(row): comparable_row(row) for row in right.records if runner_identity(row).strip("|")}
    left_keys = set(left_map)
    right_keys = set(right_map)
    common = sorted(left_keys & right_keys)
    differing_values = []
    for key in common:
        if left_map[key] != right_map[key]:
            different_fields = sorted(
                field
                for field in set(left_map[key]) | set(right_map[key])
                if left_map[key].get(field, "") != right_map[key].get(field, "")
            )
            differing_values.append({"key": key, "fields": different_fields[:20]})
            if len(differing_values) >= 20:
                break
    return {
        "left": left.path.name,
        "right": right.path.name,
        "missing_left_to_right": len(left_keys - right_keys),
        "missing_right_to_left": len(right_keys - left_keys),
        "differing_value_rows": len(differing_values),
        "differing_value_examples": differing_values,
    }


def risk_classification(
    inspection: FeedInspection,
    selected: Path | None,
    group_equivalence: str,
    critical: bool,
    has_multiple: bool,
) -> str:
    if not inspection.exists:
        return "UNKNOWN"
    if selected and inspection.path.resolve() == selected.resolve():
        if inspection.freshness_status in {"STALE", "FUTURE_DATE_INVALID", "DATE_NOT_PRESENT"} and critical:
            return "STALE_SOURCE_RISK"
        if has_multiple:
            return "DUAL_SOURCE_SAFE"
        return "SAFE"
    if group_equivalence == "DIVERGENT" and critical and not FEED_CONTRACTS.get(inspection.logical_feed):
        return "DIVERGENT_SOURCE_RISK"
    if inspection.freshness_status == "STALE" and critical:
        return "STALE_SOURCE_RISK"
    if has_multiple and not FEED_CONTRACTS.get(inspection.logical_feed):
        return "AMBIGUOUS_AUTHORITY"
    return "SAFE"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    operational_today = get_operational_date()
    all_paths = [path for feed in CRITICAL_FEEDS for path in feed["paths"]]
    consumers = consumer_index(all_paths)
    rows: list[dict[str, Any]] = []
    selected_by_feed: dict[str, dict[str, Any]] = {}
    dual_source_feeds: list[str] = []
    stale_source_selection = 0
    ambiguous_critical_authorities = 0
    unexplained_divergence = 0
    governance_failures: list[str] = []
    equivalence_details: dict[str, Any] = {}

    for feed in CRITICAL_FEEDS:
        logical = feed["logical_feed"]
        paths = [Path(path) for path in feed["paths"]]
        critical = bool(feed.get("critical"))
        date_requirement = feed.get("date_requirement")
        inspections = [
            inspect_feed_freshness(
                path,
                logical,
                operational_today=operational_today,
                date_requirement=date_requirement,
            )
            for path in paths
        ]
        present = [item for item in inspections if item.exists]
        if len(present) > 1:
            dual_source_feeds.append(logical)
        group_equivalence = equivalence_status(inspections)
        selected_path: Path | None = None
        selection_reason = ""
        try:
            selected_path, selected_inspection, _, selection_reason = choose_current_feed_authority(
                paths,
                logical,
                operational_today=operational_today,
                critical=critical,
                date_requirement=date_requirement,
            )
            selected_by_feed[logical] = {
                "selected_source": str(selected_path.relative_to(ROOT)),
                "format": selected_path.suffix.lower().lstrip("."),
                "embedded_date": selected_inspection.embedded_date,
                "current_date": selected_inspection.operational_today,
                "freshness": selected_inspection.freshness_status,
                "equivalence": group_equivalence,
                "status": "PASS",
                "selection_reason": selection_reason,
            }
            if selected_inspection.freshness_status != "CURRENT" and selected_inspection.freshness_status != "NOT_APPLICABLE":
                stale_source_selection += 1
        except Exception as exc:
            governance_failures.append(f"{logical}: {exc}")
            selected_by_feed[logical] = {
                "selected_source": "",
                "format": "",
                "embedded_date": "",
                "current_date": operational_today.isoformat(),
                "freshness": "FAIL",
                "equivalence": group_equivalence,
                "status": "FAIL",
                "selection_reason": str(exc),
            }
            if critical:
                ambiguous_critical_authorities += 1

        if len(present) > 1:
            comparisons = []
            for idx, left in enumerate(present):
                for right in present[idx + 1:]:
                    comparisons.append(compare_pair(left, right))
            equivalence_details[logical] = {
                "equivalence_status": group_equivalence,
                "contract": FEED_CONTRACTS.get(logical, {}).get("model", "UNSPECIFIED"),
                "comparisons": comparisons,
            }
            if group_equivalence == "DIVERGENT" and not FEED_CONTRACTS.get(logical):
                unexplained_divergence += 1

        if critical and len(present) > 1 and not FEED_CONTRACTS.get(logical):
            ambiguous_critical_authorities += 1

        representation_group = f"{logical}:{'MULTI' if len(present) > 1 else 'SINGLE'}"
        for inspection in inspections:
            currently_selected = bool(selected_path and inspection.path.exists() and inspection.path.resolve() == selected_path.resolve())
            risk = risk_classification(
                inspection,
                selected_path,
                group_equivalence,
                critical,
                len(present) > 1,
            )
            rows.append(
                {
                    "logical_feed": logical,
                    "physical_path": str(inspection.path.relative_to(ROOT)) if inspection.path.is_absolute() else str(inspection.path),
                    "format": inspection.format,
                    "producer": clean_text(feed.get("producer")),
                    "consumers": ";".join(sorted(consumers.get(inspection.path.name, []))),
                    "embedded_date": inspection.embedded_date,
                    "mtime": inspection.mtime,
                    "rows": inspection.rows,
                    "races": inspection.races,
                    "runners": inspection.runners,
                    "operational_today": inspection.operational_today,
                    "freshness_status": inspection.freshness_status,
                    "representation_group": representation_group,
                    "equivalence_status": group_equivalence,
                    "currently_selected_by_consumer": "TRUE" if currently_selected else "FALSE",
                    "selection_reason": selection_reason if currently_selected else "Not selected; see governed authority row for this logical feed.",
                    "risk_classification": risk,
                }
            )

    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    critical_status = {
        logical: payload
        for logical, payload in selected_by_feed.items()
        if next((feed.get("critical") for feed in CRITICAL_FEEDS if feed["logical_feed"] == logical), False)
    }
    current_critical_failures = [
        logical
        for logical, payload in critical_status.items()
        if payload["status"] != "PASS" or payload["freshness"] not in {"CURRENT", "NOT_APPLICABLE"}
    ]
    summary = {
        "schema_version": "edgeiq_current_feed_authority_inventory_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "operational_today": operational_today.isoformat(),
        "logical_feeds_audited": len(CRITICAL_FEEDS),
        "physical_representations_audited": len(rows),
        "dual_source_feeds": sorted(dual_source_feeds),
        "stale_source_selection": stale_source_selection,
        "ambiguous_critical_authorities": ambiguous_critical_authorities,
        "unexplained_source_divergence": unexplained_divergence,
        "governance_failures": governance_failures,
        "selected_authorities": selected_by_feed,
        "equivalence_details": equivalence_details,
        "final_gates": {
            "CURRENT_FEED_AUTHORITY_INVENTORY": "PASS" if not governance_failures else "FAIL",
            "DUAL_SOURCE_FEEDS_IDENTIFIED": "PASS",
            "STALE_SOURCE_SELECTION": stale_source_selection,
            "AMBIGUOUS_CRITICAL_AUTHORITIES": ambiguous_critical_authorities,
            "CURRENT_CRITICAL_FEEDS": "PASS" if not current_critical_failures else "FAIL",
            "CURRENT_REPRESENTATION_EQUIVALENCE": "PASS_OR_GOVERNED_SINGLE_SOURCE" if unexplained_divergence == 0 else "FAIL",
            "UNEXPLAINED_SOURCE_DIVERGENCE": unexplained_divergence,
            "CURRENT_FEED_FRESHNESS_AUTHORITY": "PASS" if not governance_failures and stale_source_selection == 0 and ambiguous_critical_authorities == 0 and unexplained_divergence == 0 and not current_critical_failures else "FAIL",
        },
    }
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("EDGEIQ_CURRENT_FEED_AUTHORITY_INVENTORY_V1")
    for key, value in summary["final_gates"].items():
        print(f"{key}={value}")
    print(f"OUTPUT_CSV={OUT_CSV}")
    print(f"OUTPUT_SUMMARY={OUT_SUMMARY}")
    return 0 if summary["final_gates"]["CURRENT_FEED_FRESHNESS_AUTHORITY"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
