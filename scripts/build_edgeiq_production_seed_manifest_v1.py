from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
PUBLIC_PI = ROOT / "public" / "performance-intelligence"
DOCS_PI = ROOT / "docs" / "performance-intelligence"
MARKET_PRIVATE = ROOT / "data" / "market" / "ladbrokes"
MARKET_DOCS = ROOT / "docs" / "market-intelligence" / "ladbrokes"
OUT = ROOT / "outputs" / "deployment-v1"

MANIFEST_CSV = OUT / "edgeiq_production_seed_manifest_v1.csv"
MANIFEST_JSON = OUT / "edgeiq_production_seed_manifest_v1.json"
CLASSIFICATION_CSV = OUT / "edgeiq_production_data_classification_v1.csv"
CLASSIFICATION_JSON = OUT / "edgeiq_production_data_classification_v1.json"
AUDIT_JSON = OUT / "edgeiq_production_seed_manifest_v1_audit.json"
AUDIT_MD = OUT / "EDGEIQ_PRODUCTION_SEED_MANIFEST_V1_AUDIT.md"

DEPLOYMENT_CLASSES = {
    "RUNTIME_SEED_REQUIRED",
    "RUNTIME_REBUILDABLE",
    "UPSTREAM_RETRIEVABLE",
    "IMMUTABLE_PRODUCTION_AUTHORITY",
    "RESEARCH_ONLY",
    "DEVELOPMENT_ONLY",
    "OBSOLETE_OR_DUPLICATE",
}

CURRENT_FEED_OUTPUTS = {
    "edgeiq_three_day_window_v1.json",
    "edgeiq_vic_three_day_meeting_universe.csv",
    "edgeiq_vic_three_day_meeting_calendar_v1.csv",
    "edgeiq_vic_three_day_race_list_v1.csv",
    "edgeiq_three_day_product_catalog_v1.json",
    "race_fields.csv",
    "edgeiq_race_entry_fact_v1.csv",
    "edgeiq_current_market_v1.csv",
    "edgeiq_current_market_v1.json",
    "edgeiq_current_early_speed_v1.csv",
    "edgeiq_current_early_speed_v1.json",
    "edgeiq_current_late_speed_v1.csv",
    "edgeiq_current_late_speed_v1.json",
    "edgeiq_current_suitability_v1.csv",
    "edgeiq_current_suitability_v1.json",
    "edgeiq_current_form_momentum_v1.csv",
    "edgeiq_current_form_momentum_v1.json",
    "edgeiq_current_race_shape_v2.csv",
    "edgeiq_current_race_shape_v2.json",
    "edgeiq_current_map_v1.csv",
    "edgeiq_current_map_v1.json",
    "edgeiq_form_guide_enriched_v2.csv",
    "edgeiq_form_guide_enriched_v2.json",
    "edgeiq_map_terminal_feed_v1.csv",
    "edgeiq_market_terminal_feed_v1.csv",
    "edgeiq_overview_terminal_feed_v1.csv",
    "edgeiq_insights_terminal_feed_v1.csv",
    "edgeiq_gear_terminal_feed_v1.csv",
    "edgeiq_live_terminal_feed_v1.csv",
    "edgeiq_vic_live_terminal_feed_v1.csv",
    "edgeiq_meeting_results_terminal_feed_v1.csv",
    "edgeiq_on_track_weather_governed_v1_2.csv",
    "edgeiq_on_track_weather_governed_v1_2.json",
    "edgeiq_victorian_track_weather_v1.json",
    "edgeiq_epi_workspace_terminal_feed_v1.csv",
    "edgeiq_current_runner_intelligence_audit_v1.csv",
    "edgeiq_performance_intelligence_product_feeds_v1.json",
    "edgeiq_performance_intelligence_product_manifest_v1.json",
    "edgeiq_race_context_authority_fact_v1.csv",
    "edgeiq_race_entry_performance_context_fact_v1.csv",
    "edgeiq_race_entry_context_eligibility_fact_v1.csv",
    "edgeiq_race_entry_context_parameter_selection_fact_v1.csv",
    "edgeiq_race_entry_context_adjustment_fact_v1.csv",
    "edgeiq_race_entry_context_adjusted_performance_fact_v1.csv",
    "edgeiq_race_entry_suitability_component_fact_v1.csv",
    "edgeiq_race_entry_suitability_aggregate_fact_v1.csv",
    "edgeiq_race_entry_projected_performance_fact_v1.csv",
    "edgeiq_race_entry_epi_component_fact_v1.csv",
    "edgeiq_race_entry_epi_fact_v1.csv",
    "edgeiq_race_epi_distribution_fact_v1.csv",
    "edgeiq_race_entry_epi_relative_context_fact_v1.csv",
    "edgeiq_race_entry_epi_ordering_fact_v1.csv",
    "edgeiq_race_epi_ordering_summary_fact_v1.csv",
    "edgeiq_performance_intelligence_current_publication_v1.csv",
}

STATIC_AUTHORITY_NAMES = {
    "edgeiq_historical_run_intelligence_fact_v1.csv",
    "edgeiq_historical_results_warehouse_v2_graphql.csv",
    "edgeiq_form_sectional_profile_feed_v1.csv",
    "edgeiq_form_sectional_terminal_feed_v1.csv",
    "edgeiq_runner_profile_stats_v1.csv",
    "edgeiq_speed_master_v1.csv",
    "edgeiq_standardised_sectionals_v1.csv",
    "edgeiq_results_master_v1.csv",
    "edgeiq_historical_run_ratings_master_v1.csv",
    "edgeiq_context_parameter_registry_v1.csv",
    "edgeiq_current_horse_identity_crosswalk_v1.csv",
    "edgeiq_daily_official_results_fact_v1.csv",
    "edgeiq_epi_component_normalisation_parameter_fact_v1.csv",
    "edgeiq_epi_parameter_fact_v1.csv",
    "edgeiq_horse_performance_aggregate_fact_v1.csv",
    "edgeiq_horse_performance_observation_fact_v1.csv",
    "edgeiq_horse_performance_rating_fact_v1.csv",
    "edgeiq_ra_to_rcom_horse_identity_bridge_v1.csv",
    "edgeiq_rcom_to_eiq_horse_identity_bridge_v1.csv",
    "edgeiq_rcom_to_eiq_horse_identity_bridge_v1_exceptions.csv",
    "edgeiq_race_entry_horse_performance_snapshot_fact_v1_exceptions.csv",
    "edgeiq_performance_fact_warehouse_v1.csv",
    "edgeiq_standard_time_fact_v1.csv",
    "edgeiq_race_lengths_v_standard_fact_v1.csv",
    "edgeiq_runner_lengths_v_standard_fact_v1.csv",
    "edgeiq_epi_performance_fact_v1.csv",
    "edgeiq_epi_race_strength_fact_v1.csv",
    "edgeiq_lengths_v_standard_audit_v1.json",
    "edgeiq_standard_time_audit_v1.json",
    "edgeiq_standard_time_audit_v1.md",
    "edgeiq_phase3_1_latest.json",
    "edgeiq_performance_intelligence_platform_foundation_final_report_latest.json",
    "edgeiq_performance_query_engine_v1.sqlite",
    "canonical_performance_facts_v0_2.csv",
    "edgeiq_ladbrokes_market_observation_history_v1.csv",
    "edgeiq_ladbrokes_canonical_market_observation_history_v1.csv",
    "edgeiq_ladbrokes_market_schema_inventory_v1.csv",
    "edgeiq_ladbrokes_market_schema_inventory_v1.json",
    "edgeiq_ladbrokes_market_schema_inventory_v1.md",
    "edgeiq_track_alias_registry_v1.csv",
}

MARKET_RUNTIME_NAMES = {
    "edgeiq_ladbrokes_affiliate_market_runtime_v1.csv",
    "edgeiq_ladbrokes_market_observation_history_v1.csv",
    "edgeiq_ladbrokes_canonical_market_observation_history_v1.csv",
    "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv",
}

UPSTREAM_PATTERNS = (
    "racingcom",
    "graphql",
    "cloudfront",
    "raw",
    "payload",
    "getrace",
    "getmeeting",
    "sportsbet",
    "ladbrokes_affiliate_market_runtime",
)

RESEARCH_PATTERNS = (
    "research",
    "replay",
    "experiment",
    "scenario",
    "candidate",
    "h1",
    "h2",
    "phase",
    "sensitivity",
    "predictive",
    "simulation",
    "notebook",
)

DEVELOPMENT_PATTERNS = (
    "checkpoint",
    "backup",
    "tmp",
    "temp",
    "diagnostic",
    "browser_preview",
    "screenshot",
    "before",
    "diff",
    "log",
)

PATH_RE = re.compile(r"[A-Za-z0-9_./\\:-]+\.(?:csv|json|txt|md|sqlite|db)")
WINDOWS_RE = re.compile(r"[A-Za-z]:\\")
SECRET_RE = re.compile(
    r"(API[_-]?KEY|SECRET|TOKEN|PASSWORD|PRIVATE[_-]?KEY|EDGEIQ_LADBROKES_FROM|EDGEIQ_LADBROKES_X_PARTNER)",
    re.IGNORECASE,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_csv_rows(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as handle:
            return max(0, sum(1 for _ in handle) - 1)
    except OSError:
        return 0


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def script_stage_paths() -> list[Path]:
    refresh = ROOT / "scripts" / "run_edgeiq_daily_product_refresh_v1.py"
    paths = [
        "scripts/run_edgeiq_daily_product_refresh_v1.py",
        "scripts/run_edgeiq_current_runner_scoped_performance_chain_v1.py",
        "scripts/build_edgeiq_epi_workspace_terminal_feed_v1.py",
        "scripts/build_edgeiq_current_feed_authority_inventory_v1.py",
        "scripts/audit_edgeiq_current_runner_intelligence_v1.py",
        "scripts/ensure_edgeiq_current_data_rollover_v1.py",
        "scripts/edgeiq_production_refresh_launcher_v1.py",
        "deployment/edgeiq_render_server.mjs",
    ]
    if refresh.exists():
        try:
            tree = ast.parse(refresh.read_text(encoding="utf-8-sig"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "STAGES":
                            paths.extend(ast.literal_eval(node.value))
        except Exception:
            pass
    return [ROOT / p for p in dict.fromkeys(paths)]


def referenced_file_names() -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for path in script_stage_paths():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        consumer = rel(path)
        for match in PATH_RE.findall(text):
            name = Path(match.replace("\\", "/")).name
            out[name].add(consumer)
    return out


def snapshot_required_paths() -> set[Path]:
    required: set[Path] = set()
    phase31 = DOCS_PI / "audits" / "phase3_1" / "edgeiq_phase3_1_latest.json"
    foundation = DOCS_PI / "audits" / "post_phase1_6_1" / "edgeiq_performance_intelligence_platform_foundation_final_report_latest.json"
    required.update(path for path in [phase31, foundation] if path.exists())
    payload = read_json(foundation)
    snapshots = payload.get("snapshots")
    if isinstance(snapshots, dict):
        phase27 = snapshots.get("phase2_7")
        if isinstance(phase27, dict):
            snapshot_id = str(phase27.get("snapshot_id", "")).strip()
            db = DOCS_PI / "warehouse" / "phase2_7" / snapshot_id / "edgeiq_performance_query_engine_v1.sqlite"
            if db.exists():
                required.add(db)
    corrected_id = ""
    phase17 = (snapshots or {}).get("phase1_7") if isinstance(snapshots, dict) else {}
    if isinstance(phase17, dict):
        manifest = phase17.get("manifest")
        if isinstance(manifest, dict):
            corrected_id = str(manifest.get("source_snapshot_id", "")).strip()
    if corrected_id:
        corrected = (
            DOCS_PI
            / "warehouse"
            / "performance-facts-corrected"
            / corrected_id
            / "canonical_performance_facts_v0_2.csv"
        )
        if corrected.exists():
            required.add(corrected)
    return required


def explicit_authority_paths(snapshot_paths: set[Path]) -> set[Path]:
    required = set(snapshot_paths)
    for name in STATIC_AUTHORITY_NAMES | MARKET_RUNTIME_NAMES:
        for base in (DATA, MARKET_PRIVATE, MARKET_DOCS):
            candidate = base / name
            if candidate.exists():
                required.add(candidate)
    for path in [
        DOCS_PI / "warehouse" / "edgeiq_performance_fact_warehouse_v1.csv",
        DOCS_PI / "standard-times" / "edgeiq_standard_time_fact_v1.csv",
        DOCS_PI / "standard-times" / "edgeiq_standard_time_audit_v1.json",
        DOCS_PI / "standard-times" / "edgeiq_standard_time_audit_v1.md",
        DOCS_PI / "lengths-v-standard" / "edgeiq_race_lengths_v_standard_fact_v1.csv",
        DOCS_PI / "lengths-v-standard" / "edgeiq_runner_lengths_v_standard_fact_v1.csv",
        DOCS_PI / "lengths-v-standard" / "edgeiq_lengths_v_standard_audit_v1.json",
        DOCS_PI / "epi" / "edgeiq_epi_performance_fact_v1.csv",
        DOCS_PI / "epi" / "edgeiq_epi_race_strength_fact_v1.csv",
    ]:
        if path.exists():
            required.add(path)
    return required


def iter_scoped_files() -> list[Path]:
    roots = [DATA, DOCS_PI, PUBLIC_PI, MARKET_PRIVATE, MARKET_DOCS]
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(path for path in root.rglob("*") if path.is_file())
    return sorted(dict.fromkeys(files), key=lambda path: rel(path).lower())


def significant(path: Path) -> bool:
    if path.stat().st_size >= 1024 * 1024:
        return True
    if path.suffix.lower() in {".csv", ".json", ".sqlite", ".db"}:
        return True
    if path.name in STATIC_AUTHORITY_NAMES or path.name in CURRENT_FEED_OUTPUTS:
        return True
    return False


def classify(
    path: Path,
    consumers: dict[str, set[str]],
    authority_paths: set[Path],
    snapshot_paths: set[Path],
) -> tuple[str, str, str, bool]:
    name = path.name
    lowered = rel(path).lower()
    if name in CURRENT_FEED_OUTPUTS:
        return "RUNTIME_REBUILDABLE", "current/live feed produced by daily refresh", "daily product refresh", True
    if path in authority_paths:
        if name in MARKET_RUNTIME_NAMES:
            return "RUNTIME_SEED_REQUIRED", "runtime market state/history required for no-auth preservation and movement continuity", "seeded runtime state", True
        if path in snapshot_paths:
            return "IMMUTABLE_PRODUCTION_AUTHORITY", "portable performance-intelligence snapshot file consumed by product builder", "certified performance snapshot", False
        return "IMMUTABLE_PRODUCTION_AUTHORITY", "governed authority consumed by current production builders", "governed warehouse/source", False
    if name in consumers and path.is_relative_to(DATA):
        return "IMMUTABLE_PRODUCTION_AUTHORITY", "referenced by active production script closure but not selected for minimum seed", "active script reference", False
    if any(token in lowered for token in DEVELOPMENT_PATTERNS):
        return "DEVELOPMENT_ONLY", "local audit/development artifact", "local tooling", False
    if "_candidate" in lowered or "_checkpoint" in lowered or "_backup" in lowered:
        return "OBSOLETE_OR_DUPLICATE", "superseded duplicate/checkpoint artifact", "local archive", False
    if any(token in lowered for token in UPSTREAM_PATTERNS):
        return "UPSTREAM_RETRIEVABLE", "raw/source artifact expected to be reacquired or regenerated", "upstream provider/cache", False
    if any(token in lowered for token in RESEARCH_PATTERNS):
        return "RESEARCH_ONLY", "research/certification output not required by product runtime closure", "research pipeline", False
    return "RESEARCH_ONLY", "not referenced by active production closure", "unreferenced local artifact", False


def deployment_relative(path: Path) -> str:
    if path.is_relative_to(DATA):
        return "public/data/" + path.relative_to(DATA).as_posix()
    if path.is_relative_to(PUBLIC_PI):
        return "public/performance-intelligence/" + path.relative_to(PUBLIC_PI).as_posix()
    if path.is_relative_to(DOCS_PI):
        return "docs/performance-intelligence/" + path.relative_to(DOCS_PI).as_posix()
    if path.is_relative_to(MARKET_PRIVATE):
        return "data/market/ladbrokes/" + path.relative_to(MARKET_PRIVATE).as_posix()
    if path.is_relative_to(MARKET_DOCS):
        return "docs/market-intelligence/ladbrokes/" + path.relative_to(MARKET_DOCS).as_posix()
    return rel(path)


def inspect_text(path: Path) -> tuple[bool, bool]:
    if path.suffix.lower() not in {".csv", ".json", ".txt", ".md", ".py", ".js", ".mjs", ".yaml", ".yml"}:
        return False, False
    if path.stat().st_size > 20 * 1024 * 1024:
        return False, False
    try:
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
    except OSError:
        return False, False
    return bool(WINDOWS_RE.search(text)), bool(SECRET_RE.search(text))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["empty"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    generated_at = utc_now()
    consumers = referenced_file_names()
    snapshot_paths = snapshot_required_paths()
    authority_paths = explicit_authority_paths(snapshot_paths)
    rows: list[dict[str, Any]] = []
    seed_rows: list[dict[str, Any]] = []

    for path in iter_scoped_files():
        classification, reason, authority, mutable = classify(path, consumers, authority_paths, snapshot_paths)
        windows_path_reference, secret_marker = inspect_text(path)
        seed_included = path in authority_paths
        row = {
            "generated_at": generated_at,
            "relative_path": rel(path),
            "deployment_relative_path": deployment_relative(path),
            "file_name": path.name,
            "size_bytes": path.stat().st_size,
            "size_mb": round(path.stat().st_size / (1024 * 1024), 3),
            "sha256": sha256(path) if classification in {"RUNTIME_SEED_REQUIRED", "IMMUTABLE_PRODUCTION_AUTHORITY"} else "",
            "deployment_class": classification,
            "seed_included": "TRUE" if seed_included else "FALSE",
            "mutable_at_runtime": "TRUE" if mutable else "FALSE",
            "row_count": count_csv_rows(path) if path.suffix.lower() == ".csv" and path.stat().st_size < 100_000_000 else "",
            "producer_or_authority": authority,
            "consumer_count": len(consumers.get(path.name, set())),
            "consumers": ";".join(sorted(consumers.get(path.name, set()))),
            "classification_reason": reason,
            "windows_path_reference": "TRUE" if windows_path_reference else "FALSE",
            "secret_marker": "TRUE" if secret_marker else "FALSE",
            "significant_object": "TRUE" if significant(path) else "FALSE",
        }
        rows.append(row)
        if seed_included:
            seed_rows.append(row)

    rows.sort(key=lambda row: str(row["relative_path"]).lower())
    seed_rows.sort(key=lambda row: str(row["deployment_relative_path"]).lower())
    write_csv(CLASSIFICATION_CSV, rows)
    write_csv(MANIFEST_CSV, seed_rows)

    class_counts = Counter(str(row["deployment_class"]) for row in rows)
    class_bytes = Counter()
    for row in rows:
        class_bytes[str(row["deployment_class"])] += int(row["size_bytes"])

    payload = {
        "schema_version": "EDGEIQ_PRODUCTION_SEED_MANIFEST_V1",
        "generated_at": generated_at,
        "root": str(ROOT),
        "deployment_root": "/var/data",
        "manifest_csv": rel(MANIFEST_CSV),
        "classification_csv": rel(CLASSIFICATION_CSV),
        "seed_file_count": len(seed_rows),
        "seed_size_bytes": sum(int(row["size_bytes"]) for row in seed_rows),
        "seed_size_mb": round(sum(int(row["size_bytes"]) for row in seed_rows) / (1024 * 1024), 3),
        "classification_counts": dict(sorted(class_counts.items())),
        "classification_size_bytes": dict(sorted(class_bytes.items())),
        "windows_path_reference_seed_files": [
            row["relative_path"] for row in seed_rows if row["windows_path_reference"] == "TRUE"
        ],
        "secret_marker_seed_files": [
            row["relative_path"] for row in seed_rows if row["secret_marker"] == "TRUE"
        ],
        "production_depends_on_audit_outputs": any(
            "form-guide-downstream-trace-v1" in consumer or "form-guide-downstream-trace-v1" in str(row["relative_path"])
            for row in seed_rows
            for consumer in str(row["consumers"]).split(";")
        ),
        "rows": seed_rows,
    }
    MANIFEST_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    CLASSIFICATION_JSON.write_text(
        json.dumps(
            {
                "schema_version": "EDGEIQ_PRODUCTION_DATA_CLASSIFICATION_V1",
                "generated_at": generated_at,
                "rows": rows,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    audit = {
        "EDGEIQ_PRODUCTION_SEED_MANIFEST": "PASS" if seed_rows else "FAIL",
        "PRODUCTION_DEPENDS_ON_AUDIT_OUTPUTS": "FALSE"
        if not payload["production_depends_on_audit_outputs"]
        else "TRUE",
        "DEPLOYMENT_CLASSES_VALID": sorted(DEPLOYMENT_CLASSES),
        "seed_file_count": payload["seed_file_count"],
        "seed_size_mb": payload["seed_size_mb"],
        "classification_counts": payload["classification_counts"],
        "classification_size_bytes": payload["classification_size_bytes"],
        "windows_path_reference_seed_files": payload["windows_path_reference_seed_files"],
        "secret_marker_seed_files": payload["secret_marker_seed_files"],
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# EDGEiQ Production Seed Manifest V1 Audit",
        "",
        f"Generated: {generated_at}",
        "",
        f"EDGEIQ_PRODUCTION_SEED_MANIFEST={audit['EDGEIQ_PRODUCTION_SEED_MANIFEST']}",
        f"PRODUCTION_DEPENDS_ON_AUDIT_OUTPUTS={audit['PRODUCTION_DEPENDS_ON_AUDIT_OUTPUTS']}",
        f"SEED_FILES={payload['seed_file_count']}",
        f"SEED_SIZE_MB={payload['seed_size_mb']}",
        "",
        "## Classification Counts",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in sorted(class_counts.items()))
    lines.extend(["", "## Seed Windows Path References", ""])
    lines.extend(f"- {path}" for path in payload["windows_path_reference_seed_files"][:50])
    if not payload["windows_path_reference_seed_files"]:
        lines.append("- none")
    lines.extend(["", "## Seed Secret Markers", ""])
    lines.extend(f"- {path}" for path in payload["secret_marker_seed_files"][:50])
    if not payload["secret_marker_seed_files"]:
        lines.append("- none")
    AUDIT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if seed_rows and not payload["production_depends_on_audit_outputs"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
