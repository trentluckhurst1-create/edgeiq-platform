from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SRC = ROOT / "src" / "edgeiq-os"

REGISTRY_CSV = DATA / "edgeiq_form_guide_v3_4_engine_registry.csv"
REGISTRY_JSON = DATA / "edgeiq_form_guide_v3_4_engine_registry.json"
REGISTRY_SUMMARY = DATA / "edgeiq_form_guide_v3_4_engine_registry_summary.txt"
FEED = DATA / "edgeiq_form_guide_enriched_v2.json"
JOIN_AUDIT = DATA / "edgeiq_form_guide_v3_4_engine_join_audit.csv"
COVERAGE = DATA / "edgeiq_form_guide_v3_4_coverage.csv"
COVERAGE_SUMMARY = DATA / "edgeiq_form_guide_v3_4_coverage_summary.txt"
AUDIT_TXT = DATA / "edgeiq_form_guide_v3_4_engine_wiring_audit.txt"
AUDIT_JSON = DATA / "edgeiq_form_guide_v3_4_engine_wiring_audit.json"

COMPONENT = SRC / "race" / "components" / "RaceFormGuideWorkspace.tsx"
NORMALISER = SRC / "race" / "services" / "formGuideNormaliser.ts"
FEED_SERVICE = SRC / "race" / "services" / "formGuideEnrichedFeed.ts"

REQUIRED_ENGINES = {
    "Weather",
    "Sectionals",
    "Benchmark",
    "Rating",
    "EPI",
    "EDGEiQ Price",
    "Early Speed",
    "Race Shape",
    "Suitability",
    "Late Speed",
    "Form Momentum",
    "Preparation Profile",
}

PROPRIETARY_FIELDS = [
    "rating",
    "epi",
    "earlySpeed",
    "edgeiqPrice",
    "suitability",
    "raceShape",
    "lateSpeed",
    "formMomentum",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        return list(csv.DictReader(handle))


def is_source_value(value: Any) -> bool:
    return isinstance(value, dict) and {"value", "source", "version", "asAt"}.issubset(value.keys())


def check_source_value(name: str, value: Any, failures: list[str]) -> None:
    if not is_source_value(value):
        failures.append(f"{name} is not source-wrapped.")
        return
    if value.get("value") not in (None, "") and not value.get("source"):
        failures.append(f"{name} has a value without source lineage.")
    if value.get("value") not in (None, "") and not value.get("version"):
        failures.append(f"{name} has a value without version lineage.")


def main() -> None:
    failures: list[str] = []
    warnings: list[str] = []

    for path in [REGISTRY_CSV, REGISTRY_JSON, REGISTRY_SUMMARY, FEED, JOIN_AUDIT, COVERAGE, COVERAGE_SUMMARY]:
        if not path.exists():
            failures.append(f"Missing required output: {path}")

    registry_rows: list[dict[str, str]] = []
    if REGISTRY_CSV.exists():
        registry_rows = read_csv(REGISTRY_CSV)
        engines = {row.get("engine_name", "") for row in registry_rows}
        missing = REQUIRED_ENGINES - engines
        if missing:
            failures.append(f"Engine registry missing: {', '.join(sorted(missing))}")
        for engine in REQUIRED_ENGINES:
            matching = [row for row in registry_rows if row.get("engine_name") == engine]
            if not matching:
                continue
            if not any(row.get("source_file") or row.get("reason") for row in matching):
                failures.append(f"{engine} has no documented source or rejection reason.")

    if FEED.exists():
        payload = json.loads(FEED.read_text(encoding="utf-8"))
        if payload.get("schemaVersion") != "edgeiq_form_guide_enriched_v2":
            failures.append("Enriched feed schemaVersion is not edgeiq_form_guide_enriched_v2.")
        contract = payload.get("sourceContract") or {}
        for key in ["weather", "sectionals", "benchmark", "rating", "pricing", "earlySpeed", "preparation"]:
            if not contract.get(key):
                failures.append(f"Source contract missing {key}.")
        runner_count = 0
        duplicate_keys: set[tuple[Any, ...]] = set()
        seen_keys: set[tuple[Any, ...]] = set()
        for race in payload.get("races", []):
            race_key = (race.get("raceDate"), race.get("meeting"), race.get("raceNumber"))
            if race.get("weather") and not race["weather"].get("weatherSource"):
                failures.append(f"Weather object lacks source for {race_key}.")
            for runner in race.get("runners", []):
                runner_count += 1
                key = (*race_key, runner.get("runnerNumber"), runner.get("normalisedRunnerName"))
                if key in seen_keys:
                    duplicate_keys.add(key)
                seen_keys.add(key)
                for field in PROPRIETARY_FIELDS:
                    check_source_value(field, runner.get(field), failures)
                market = runner.get("marketPrice")
                if is_source_value(market):
                    source = str(market.get("source") or "").lower()
                    if "starting" in source or "historical" in source:
                        failures.append(f"Historical SP source used as current market for {key}.")
                edgeiq_price = runner.get("edgeiqPrice")
                if is_source_value(edgeiq_price) and edgeiq_price.get("value") not in (None, ""):
                    market_value = market.get("value") if is_source_value(market) else market
                    if str(edgeiq_price.get("value")) == str(market_value) and "market" in str(edgeiq_price.get("source", "")).lower():
                        failures.append(f"EDGEiQ Price appears to be market fallback for {key}.")
                for run in runner.get("fullForm", []):
                    for field in ["raceRating", "historicalEpi", "benchmarkEvidence", "historicalEarlySpeed", "historicalLateSpeed", "historicalSpeedRating", "historicalSuitability", "historicalFormMomentum"]:
                        check_source_value(f"historical.{field}", run.get(field), failures)
                    indices = run.get("sectionalIndices")
                    if indices:
                        for field in ["index800To600", "index600To400", "index400To200", "index200ToFinish", "finishLen"]:
                            check_source_value(f"sectional.{field}", indices.get(field), failures)
        if runner_count != 503:
            failures.append(f"Expected 503 runners in V3.4 feed; found {runner_count}.")
        if duplicate_keys:
            failures.append(f"Duplicate runner keys found: {len(duplicate_keys)}")

    if JOIN_AUDIT.exists():
        joins = read_csv(JOIN_AUDIT)
        ambiguous = [row for row in joins if row.get("ambiguity_reason")]
        if ambiguous:
            failures.append(f"Ambiguous joins accepted: {len(ambiguous)}")
        duplicate_count = len(joins) - len({(row.get("race_date"), row.get("meeting"), row.get("race_number"), row.get("runner_number"), row.get("runner_name")) for row in joins})
        if duplicate_count:
            failures.append(f"Duplicate runner keys in join audit: {duplicate_count}")

    if FEED_SERVICE.exists():
        service_text = FEED_SERVICE.read_text(encoding="utf-8")
        if "edgeiq_form_guide_enriched_v2.json" not in service_text:
            failures.append("Frontend service does not consume edgeiq_form_guide_enriched_v2.json.")
    if NORMALISER.exists():
        normaliser_text = NORMALISER.read_text(encoding="utf-8")
        if "metricText" not in normaliser_text or "sectionalIndices" not in normaliser_text:
            failures.append("Normaliser does not unwrap V3.4 source values/sectional indices.")
    if COMPONENT.exists():
        component_text = COMPONENT.read_text(encoding="utf-8")
        for marker in ["scrollIntoView", "Metric Guide", "createPortal", "eiq-form-header-tooltip"]:
            if marker not in component_text:
                failures.append(f"V3.3 UI structure marker missing: {marker}")
        if "eiq-form-tooltip-trigger" in component_text:
            failures.append("Visible info-icon tooltip trigger returned.")

    if COVERAGE_SUMMARY.exists():
        text = COVERAGE_SUMMARY.read_text(encoding="utf-8")
        if "Current-date gaps are not backfilled" not in text:
            warnings.append("Coverage summary does not explicitly state current-date backfill guard.")

    status = "EDGEIQ_FORM_GUIDE_V3_4_ENGINE_WIRING_AUDIT_PASS" if not failures else "EDGEIQ_FORM_GUIDE_V3_4_ENGINE_WIRING_AUDIT_FAIL"
    result = {"status": status, "failures": failures, "warnings": warnings}
    AUDIT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    AUDIT_TXT.write_text(
        "\n".join(
            [
                status,
                "",
                "Failures:",
                *(failures or ["None"]),
                "",
                "Warnings:",
                *(warnings or ["None"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(status)
    for failure in failures:
        print(f"FAIL: {failure}")
    for warning in warnings:
        print(f"WARN: {warning}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
