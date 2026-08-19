from __future__ import annotations

import ast
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "public" / "data"
OUT_DIR = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "audits"
    / "phase0_2"
)

MAX_TEXT_BYTES = 2_000_000
MAX_SAMPLE_ROWS = 5

DOMAINS: dict[str, dict[str, list[str]]] = {
    "results_warehouse": {
        "scripts": [
            "scripts/build_edgeiq_canonical_results_truth_v1.py",
            "scripts/build_edgeiq_historical_results_warehouse_v2_graphql.py",
            "scripts/build_edgeiq_racingcom_results_warehouse_all_v1.py",
            "scripts/build_edgeiq_results_warehouse_full_consolidation_v1.py",
            "scripts/build_edgeiq_results_master.py",
            "scripts/build_edgeiq_results_master_v1.py",
            "scripts/build_edgeiq_results_intelligence_history_v1.py",
            "scripts/build_edgeiq_official_results_backfill_v1.py",
            "scripts/build_edgeiq_graphql_results_warehouse_week1_2025_v1.py",
            "scripts/build_edgeiq_graphql_results_warehouse_sample_v1.py",
            "scripts/audit_edgeiq_results_warehouse_inventory_v1.py",
            "scripts/audit_edgeiq_historical_results_warehouse_v2_graphql_quality.py",
            "scripts/audit_edgeiq_results_data_contract_v1.py",
        ],
        "data_patterns": [
            "edgeiq_results_master*.csv",
            "edgeiq_canonical_results_truth*.csv",
            "edgeiq_historical_results_warehouse*.csv",
            "edgeiq_graphql_*results*.csv",
            "edgeiq_racingcom_results_warehouse*.csv",
            "edgeiq_results_intelligence_history*.csv",
            "results_enriched.csv",
            "results_report.csv",
        ],
    },
    "sectional_warehouse": {
        "scripts": [
            "scripts/build_edgeiq_vic_sectional_warehouse_v1.py",
            "scripts/build_edgeiq_vic_historical_sectional_warehouse_v1.py",
            "scripts/build_edgeiq_vic_dom_sectional_warehouse_v1.py",
            "scripts/build_racingcom_sectional_warehouse_v1.py",
            "scripts/build_racingcom_sectional_warehouse_v2.py",
            "scripts/build_racingcom_sectional_history_master_v1.py",
            "scripts/build_edgeiq_standardised_sectionals_v1.py",
            "scripts/build_edgeiq_trusted_sectional_universe.py",
            "scripts/build_edgeiq_trusted_sectional_universe_v2.py",
            "scripts/build_edgeiq_sectional_normalisation_v1.py",
            "scripts/build_edgeiq_sectional_schema_v2.py",
            "scripts/build_edgeiq_sectional_master_reconciliation_v1.py",
            "scripts/audit_edgeiq_sectional_pipeline.py",
            "scripts/audit_racingcom_sectional_warehouse_readiness_v1.py",
        ],
        "data_patterns": [
            "*sectional*warehouse*.csv",
            "racingcom_sectional_history_master*.csv",
            "racingcom_sectionals_normalised*.csv",
            "edgeiq_standardised_sectionals*.csv",
            "edgeiq_trusted_sectional_universe*.csv",
            "edgeiq_sectional_schema*.csv",
            "edgeiq_sectional_pipeline_audit*.csv",
        ],
    },
    "benchmark_engine": {
        "scripts": [
            "scripts/build_edgeiq_standard_times_v1.py",
            "scripts/build_edgeiq_standardised_sectionals_v1.py",
            "scripts/build_edgeiq_race_strength_v1.py",
            "scripts/build_edgeiq_race_strength_v2.py",
            "scripts/build_edgeiq_race_strength_v3.py",
            "scripts/build_edgeiq_race_strength_history_v1.py",
            "scripts/build_edgeiq_sectional_strength_v2.py",
            "scripts/build_edgeiq_performance_rating_engine_audit_v1.py",
            "scripts/audit_edgeiq_benchmark_sectional_display_v1.py",
        ],
        "data_patterns": [
            "edgeiq_standard_times*.csv",
            "edgeiq_standardised_sectionals*.csv",
            "edgeiq_race_strength*.csv",
            "edgeiq_sectional_strength*.csv",
            "*benchmark*.csv",
        ],
    },
    "identity_engine": {
        "scripts": [
            "scripts/build_edgeiq_sectional_identity_engine_v1.py",
            "scripts/build_edgeiq_sectional_identity_engine_v2.py",
            "scripts/build_edgeiq_sectional_identity_engine_v3.py",
            "scripts/build_edgeiq_canonical_results_truth_v1.py",
            "scripts/build_edgeiq_temporal_identity_memory_v1.py",
            "scripts/build_edgeiq_canonical_market_entity_graph_v1.py",
            "scripts/build_edgeiq_results_master.py",
            "scripts/build_racingcom_sectional_warehouse_v2.py",
        ],
        "data_patterns": [
            "edgeiq_sectional_identity_engine*.csv",
            "edgeiq_sectional_identity_summary*.csv",
            "edgeiq_temporal_identity_memory*.csv",
            "edgeiq_canonical_market_entity_graph*.csv",
            "*canonical*identity*.csv",
            "*entity*graph*.csv",
        ],
    },
    "performance_ratings": {
        "scripts": [
            "scripts/build_edgeiq_historical_performance_rating_v3_3.py",
            "scripts/build_edgeiq_historical_performance_rating_v5_1.py",
            "scripts/build_edgeiq_performance_rating_engine_audit_v1.py",
            "scripts/build_edgeiq_race_strength_history_v1.py",
            "scripts/build_edgeiq_results_intelligence_history_v1.py",
            "scripts/build_edgeiq_runner_history_detail_v1.py",
            "scripts/build_edgeiq_results_terminal_feed_v1.py",
            "scripts/build_edgeiq_runner_dna_v1.py",
            "scripts/build_edgeiq_runner_dna_v2.py",
        ],
        "data_patterns": [
            "edgeiq_historical_performance_rating*.csv",
            "edgeiq_runner_history_detail*.csv",
            "edgeiq_results_intelligence_history*.csv",
            "edgeiq_race_strength_history*.csv",
            "edgeiq_runner_dna*.csv",
            "*performance_rating*.csv",
            "*epi*.csv",
            "*eri*.csv",
        ],
    },
    "length_conversion": {
        "scripts": [
            "scripts/build_edgeiq_standardised_sectionals_v1.py",
            "scripts/audit_edgeiq_ui_column_data_v1.py",
        ],
        "data_patterns": [
            "edgeiq_standardised_sectionals*.csv",
            "*length*.csv",
            "*seconds*.csv",
        ],
    },
}

REFERENCE_PATTERN = re.compile(
    r"""["']([^"']+\.(?:csv|json|parquet|feather|sqlite|sqlite3|db))["']""",
    re.IGNORECASE,
)

CONSTANT_PATTERN = re.compile(
    r"^([A-Z][A-Z0-9_]*)\s*=\s*(.+)$",
    re.MULTILINE,
)

KEY_TERMS = (
    "seconds_per_length",
    "seconds_to_lengths",
    "benchmark",
    "standard_time",
    "benchmark_mode",
    "benchmark_sample",
    "confidence",
    "quality_state",
    "race_identity_status",
    "trusted_race_identity",
    "trusted_modelling_identity",
    "canonical_horse",
    "canonical_race",
    "horse_id",
    "runner_id",
    "race_id",
    "meeting_id",
    "epi",
    "eri",
    "race_strength",
    "performance_rating",
    "sectional_status",
    "last_800",
    "last_600",
    "last_400",
    "last_200",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def safe_text(path: Path) -> str:
    try:
        with path.open(
            "r",
            encoding="utf-8",
            errors="ignore",
        ) as handle:
            return handle.read(MAX_TEXT_BYTES)
    except OSError:
        return ""


def safe_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def parse_date(value: str) -> str:
    value = str(value or "").strip()

    if not value:
        return ""

    patterns = (
        r"^\d{4}-\d{2}-\d{2}$",
        r"^\d{2}/\d{2}/\d{4}$",
        r"^\d{4}/\d{2}/\d{2}$",
    )

    if any(re.match(pattern, value) for pattern in patterns):
        return value

    return ""


def csv_profile(path: Path) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "path": rel(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "modified_utc": (
            datetime.fromtimestamp(
                path.stat().st_mtime,
                tz=timezone.utc,
            ).isoformat()
            if path.exists()
            else ""
        ),
        "rows": 0,
        "columns": [],
        "column_count": 0,
        "date_column": "",
        "min_date": "",
        "max_date": "",
        "unique_races_estimate": None,
        "unique_horses_estimate": None,
        "quality_columns": [],
        "identity_columns": [],
        "sectional_columns": [],
        "benchmark_columns": [],
        "rating_columns": [],
        "sample_rows": [],
        "error": "",
    }

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            errors="ignore",
            newline="",
        ) as handle:
            reader = csv.DictReader(handle)
            columns = list(reader.fieldnames or [])
            profile["columns"] = columns
            profile["column_count"] = len(columns)

            lower_map = {
                column.lower(): column
                for column in columns
            }

            date_candidates = (
                "race_date",
                "date",
                "run_date_iso",
                "meeting_date",
            )

            date_column = next(
                (
                    lower_map[name]
                    for name in date_candidates
                    if name in lower_map
                ),
                "",
            )

            profile["date_column"] = date_column

            race_keys: set[str] = set()
            horse_keys: set[str] = set()
            dates: list[str] = []

            for row_index, row in enumerate(reader, start=1):
                profile["rows"] = row_index

                if row_index <= MAX_SAMPLE_ROWS:
                    profile["sample_rows"].append(
                        {
                            key: row.get(key, "")
                            for key in columns[:20]
                        }
                    )

                if date_column:
                    parsed = parse_date(row.get(date_column, ""))
                    if parsed:
                        dates.append(parsed)

                race_id = str(
                    row.get("race_id")
                    or row.get("race_key")
                    or ""
                ).strip()

                if not race_id:
                    race_date = str(
                        row.get("race_date")
                        or row.get("date")
                        or ""
                    ).strip()
                    track = str(
                        row.get("track")
                        or row.get("venue_name")
                        or ""
                    ).strip()
                    race_no = str(
                        row.get("race_no")
                        or row.get("race_number")
                        or ""
                    ).strip()

                    if race_date and track and race_no:
                        race_id = "|".join(
                            [race_date, track, race_no]
                        )

                if race_id:
                    race_keys.add(race_id)

                horse_id = str(
                    row.get("runner_id")
                    or row.get("horse_id")
                    or row.get("horse_key")
                    or row.get("horse")
                    or row.get("horse_name")
                    or ""
                ).strip()

                if horse_id:
                    horse_keys.add(horse_id)

            if dates:
                profile["min_date"] = min(dates)
                profile["max_date"] = max(dates)

            profile["unique_races_estimate"] = len(race_keys)
            profile["unique_horses_estimate"] = len(horse_keys)

            profile["quality_columns"] = [
                column
                for column in columns
                if any(
                    term in column.lower()
                    for term in (
                        "quality",
                        "confidence",
                        "status",
                        "excluded",
                        "mismatch",
                        "trusted",
                    )
                )
            ]

            profile["identity_columns"] = [
                column
                for column in columns
                if any(
                    term in column.lower()
                    for term in (
                        "_id",
                        "_key",
                        "canonical",
                        "identity",
                        "runner_id",
                        "horse_id",
                        "race_id",
                        "meeting_id",
                    )
                )
            ]

            profile["sectional_columns"] = [
                column
                for column in columns
                if any(
                    term in column.lower()
                    for term in (
                        "sectional",
                        "last_800",
                        "last_600",
                        "last_400",
                        "last_200",
                        "800_600",
                        "600_400",
                        "400_200",
                        "200_finish",
                        "pos_800",
                        "pos_400",
                    )
                )
            ]

            profile["benchmark_columns"] = [
                column
                for column in columns
                if any(
                    term in column.lower()
                    for term in (
                        "benchmark",
                        "standard_time",
                        "par_time",
                        "sample_races",
                    )
                )
            ]

            profile["rating_columns"] = [
                column
                for column in columns
                if any(
                    term in column.lower()
                    for term in (
                        "epi",
                        "eri",
                        "race_strength",
                        "performance_rating",
                        "run_rating",
                        "rating",
                    )
                )
            ]

    except Exception as exc:
        profile["error"] = str(exc)

    return profile


def python_profile(path: Path) -> dict[str, Any]:
    content = safe_text(path)

    profile: dict[str, Any] = {
        "path": rel(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "modified_utc": (
            datetime.fromtimestamp(
                path.stat().st_mtime,
                tz=timezone.utc,
            ).isoformat()
            if path.exists()
            else ""
        ),
        "functions": [],
        "imports": [],
        "constants": [],
        "references": [],
        "key_evidence": [],
        "syntax_status": "NOT_PARSED",
        "error": "",
    }

    if not content:
        profile["syntax_status"] = "EMPTY_OR_UNREADABLE"
        return profile

    try:
        tree = ast.parse(content)
        profile["syntax_status"] = "PARSED"

        functions = sorted({
            node.name
            for node in ast.walk(tree)
            if isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            )
        })

        imports: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(
                    alias.name
                    for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports.append(module)

        profile["functions"] = functions
        profile["imports"] = sorted(set(imports))

    except SyntaxError as exc:
        profile["syntax_status"] = "SYNTAX_ERROR"
        profile["error"] = str(exc)

    constants = []

    for match in CONSTANT_PATTERN.finditer(content):
        name = match.group(1)
        value = match.group(2).strip()

        if len(value) > 300:
            value = value[:300]

        constants.append(
            {
                "name": name,
                "value": value,
            }
        )

    profile["constants"] = constants[:100]

    references = []

    for match in REFERENCE_PATTERN.finditer(content):
        value = match.group(1).replace("\\", "/")

        if value not in references:
            references.append(value)

    profile["references"] = references[:300]

    evidence: list[dict[str, Any]] = []
    evidence_counts: Counter[str] = Counter()

    for line_number, line in enumerate(
        content.splitlines(),
        start=1,
    ):
        lowered = line.lower()

        for term in KEY_TERMS:
            if evidence_counts[term] >= 10:
                continue

            if term in lowered:
                evidence.append(
                    {
                        "term": term,
                        "line_number": line_number,
                        "line_text": line.strip()[:500],
                    }
                )
                evidence_counts[term] += 1

    profile["key_evidence"] = evidence

    return profile


def discover_data(patterns: list[str]) -> list[Path]:
    discovered: dict[str, Path] = {}

    for pattern in patterns:
        for path in DATA.glob(pattern):
            if not path.is_file():
                continue

            discovered[str(path.resolve()).lower()] = path

    return sorted(
        discovered.values(),
        key=lambda item: (
            -item.stat().st_size,
            item.name.lower(),
        ),
    )


def infer_candidate_status(
    domain: str,
    script_profiles: list[dict[str, Any]],
    data_profiles: list[dict[str, Any]],
) -> dict[str, Any]:
    script_count = sum(
        1
        for item in script_profiles
        if item["exists"]
    )
    data_count = sum(
        1
        for item in data_profiles
        if item["exists"]
    )
    populated_data_count = sum(
        1
        for item in data_profiles
        if item["exists"]
        and item["rows"] > 0
        and not item["error"]
    )

    largest = sorted(
        data_profiles,
        key=lambda item: item["rows"],
        reverse=True,
    )[:10]

    status = "MISSING"

    if script_count and populated_data_count:
        status = "EXISTING_REQUIRES_LINEAGE_VALIDATION"
    elif script_count:
        status = "ENGINE_PRESENT_OUTPUT_NOT_CONFIRMED"
    elif populated_data_count:
        status = "DATA_PRESENT_CREATOR_NOT_CONFIRMED"

    if domain == "length_conversion":
        constants = [
            constant
            for script in script_profiles
            for constant in script["constants"]
            if "LENGTH" in constant["name"]
            or "SECOND" in constant["name"]
        ]

        if constants:
            status = "LEGACY_CONVERSION_PRESENT_REQUIRES_GOVERNANCE"

    return {
        "domain": domain,
        "status": status,
        "scripts_found": script_count,
        "data_files_found": data_count,
        "populated_data_files": populated_data_count,
        "largest_candidate_data_files": [
            {
                "path": item["path"],
                "rows": item["rows"],
                "min_date": item["min_date"],
                "max_date": item["max_date"],
                "unique_races_estimate": item[
                    "unique_races_estimate"
                ],
                "unique_horses_estimate": item[
                    "unique_horses_estimate"
                ],
            }
            for item in largest
        ],
    }


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def flatten_csv_profiles(
    domain: str,
    profiles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for item in profiles:
        rows.append(
            {
                "domain": domain,
                "path": item["path"],
                "exists": item["exists"],
                "size_bytes": item["size_bytes"],
                "modified_utc": item["modified_utc"],
                "rows": item["rows"],
                "column_count": item["column_count"],
                "min_date": item["min_date"],
                "max_date": item["max_date"],
                "unique_races_estimate": item[
                    "unique_races_estimate"
                ],
                "unique_horses_estimate": item[
                    "unique_horses_estimate"
                ],
                "identity_columns": " | ".join(
                    item["identity_columns"]
                ),
                "sectional_columns": " | ".join(
                    item["sectional_columns"]
                ),
                "benchmark_columns": " | ".join(
                    item["benchmark_columns"]
                ),
                "rating_columns": " | ".join(
                    item["rating_columns"]
                ),
                "quality_columns": " | ".join(
                    item["quality_columns"]
                ),
                "error": item["error"],
            }
        )

    return rows


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames: list[str] = []

    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def markdown_report(payload: dict[str, Any]) -> str:
    lines: list[str] = []

    lines.append("# EDGEiQ Performance Intelligence")
    lines.append("## Phase 0.2 Domain Audit")
    lines.append("")
    lines.append(
        f"Generated UTC: `{payload['generated_utc']}`"
    )
    lines.append("")
    lines.append("## Audit rule")
    lines.append("")
    lines.append(
        "No asset is declared canonical merely because it exists, "
        "is highly populated, or has a PASS audit."
    )
    lines.append("")

    for domain_name, domain in payload["domains"].items():
        summary = domain["summary"]

        lines.append(f"## {domain_name}")
        lines.append("")
        lines.append(f"- Status: **{summary['status']}**")
        lines.append(
            f"- Scripts found: **{summary['scripts_found']}**"
        )
        lines.append(
            f"- Data files found: **{summary['data_files_found']}**"
        )
        lines.append(
            "- Populated data files: "
            f"**{summary['populated_data_files']}**"
        )
        lines.append("")
        lines.append("### Largest candidate data files")
        lines.append("")
        lines.append(
            "| Path | Rows | Min date | Max date | "
            "Race estimate | Horse estimate |"
        )
        lines.append("|---|---:|---|---|---:|---:|")

        for item in summary["largest_candidate_data_files"]:
            lines.append(
                f"| `{item['path']}` | "
                f"{item['rows']} | "
                f"{item['min_date']} | "
                f"{item['max_date']} | "
                f"{item['unique_races_estimate']} | "
                f"{item['unique_horses_estimate']} |"
            )

        lines.append("")
        lines.append("### Existing scripts")
        lines.append("")

        for script in domain["scripts"]:
            state = (
                "FOUND"
                if script["exists"]
                else "MISSING"
            )
            lines.append(
                f"- `{script['path']}` — {state}"
            )

        lines.append("")

    lines.append("## Mandatory next step")
    lines.append("")
    lines.append(
        "Select one candidate per domain only after validating its "
        "source evidence, transformation logic, output contract, "
        "coverage, duplication, quality states and downstream consumers."
    )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "audit_name": (
            "EDGEiQ Performance Intelligence Phase 0.2 "
            "Domain Audit"
        ),
        "generated_utc": utc_now(),
        "repository_root": str(ROOT),
        "canonical_status": "NOT_YET_DETERMINED",
        "domains": {},
    }

    all_data_rows: list[dict[str, Any]] = []

    for domain_index, (
        domain_name,
        config,
    ) in enumerate(DOMAINS.items(), start=1):
        print(
            f"DOMAIN_START={domain_index}/{len(DOMAINS)} "
            f"{domain_name}",
            flush=True,
        )

        script_profiles: list[dict[str, Any]] = []

        for script_text in config["scripts"]:
            path = ROOT / script_text
            script_profiles.append(
                python_profile(path)
            )

        data_paths = discover_data(
            config["data_patterns"]
        )

        data_profiles: list[dict[str, Any]] = []

        for data_index, path in enumerate(
            data_paths,
            start=1,
        ):
            if data_index == 1 or data_index % 25 == 0:
                print(
                    f"DOMAIN_DATA={domain_name} "
                    f"{data_index}/{len(data_paths)} "
                    f"{rel(path)}",
                    flush=True,
                )

            profile = csv_profile(path)
            data_profiles.append(profile)

        summary = infer_candidate_status(
            domain_name,
            script_profiles,
            data_profiles,
        )

        payload["domains"][domain_name] = {
            "summary": summary,
            "scripts": script_profiles,
            "data_files": data_profiles,
        }

        all_data_rows.extend(
            flatten_csv_profiles(
                domain_name,
                data_profiles,
            )
        )

        print(
            f"DOMAIN_COMPLETE={domain_name} "
            f"SCRIPTS={summary['scripts_found']} "
            f"DATA={summary['data_files_found']} "
            f"POPULATED={summary['populated_data_files']}",
            flush=True,
        )

    run_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    detail_path = (
        OUT_DIR
        / f"edgeiq_performance_intelligence_phase0_2_detail_{run_id}.json"
    )
    summary_path = (
        OUT_DIR
        / f"edgeiq_performance_intelligence_phase0_2_summary_{run_id}.json"
    )
    csv_path = (
        OUT_DIR
        / f"edgeiq_performance_intelligence_phase0_2_data_assets_{run_id}.csv"
    )
    report_path = (
        OUT_DIR
        / f"edgeiq_performance_intelligence_phase0_2_report_{run_id}.md"
    )
    latest_path = (
        OUT_DIR
        / "edgeiq_performance_intelligence_phase0_2_latest.json"
    )

    summary_payload = {
        "audit_name": payload["audit_name"],
        "generated_utc": payload["generated_utc"],
        "canonical_status": payload[
            "canonical_status"
        ],
        "domain_summaries": {
            name: value["summary"]
            for name, value in payload[
                "domains"
            ].items()
        },
        "next_stage": (
            "Phase 0.3 canonical candidate lineage validation"
        ),
    }

    write_json(detail_path, payload)
    write_json(summary_path, summary_payload)
    write_json(latest_path, summary_payload)
    write_csv(csv_path, all_data_rows)

    report_path.write_text(
        markdown_report(payload),
        encoding="utf-8",
    )

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE0_2_DOMAIN_AUDIT_PASS",
        flush=True,
    )
    print(f"DETAIL={detail_path}", flush=True)
    print(f"SUMMARY={summary_path}", flush=True)
    print(f"DATA_ASSETS={csv_path}", flush=True)
    print(f"REPORT={report_path}", flush=True)


if __name__ == "__main__":
    main()
