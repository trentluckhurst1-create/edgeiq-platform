#!/usr/bin/env python3
"""Issue #8 pre-2022 source admission.

This is a read-only governance script. It inspects named manifests and prior
admission reports, then fails closed unless a certified pre-2022 all-runner
point-in-time feature matrix is already present.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Iterable


FORBIDDEN_MARKET_TERMS = (
    "sp",
    "bsp",
    "starting_price",
    "odds",
    "price",
    "market",
    "bet",
    "stake",
    "return",
)

PRE2021_EVIDENCE_DOCS = (
    "ai_review/PRE2021_COLUMN_LINEAGE_DISPOSITION_20261009.md",
    "ai_review/PRE2021_LAB245B_HIST_RUNS_LINEAGE_PASS_20261009.md",
    "ai_review/PRE2021_LAB245B_IDENTITY_IMPORTED_UNPROVEN_20261009.md",
    "ai_review/PRE2021_PHASE16_PERFORMANCE_FACT_IDENTITY_STOP_20261009.md",
    "ai_review/PRE2021_STAGE006_HIST_RUNS_STOP_20261009.md",
    "ai_review/PRE2021_BUILDER_LINEAGE_STOP_20261009.md",
)

NAMED_MANIFESTS = (
    "outputs/research/codex_issue5_source_admission/CODEX_ISSUE5_LAB026_CLEAN_PLACING_2021_2024.manifest.json",
    "outputs/research/codex_issue5_source_admission/CODEX_ISSUE5_LAB031_CONTEXT_2021_2024.manifest.json",
    "outputs/research/profitability_program/lab245b/LAB245B_COMPACT_PERFORMANCE_BRIDGE.manifest.json",
    "outputs/research/profitability_program/lab245b/LAB245B_WAREHOUSE_RUNNER_LVS.manifest.json",
)

NAMED_SOURCE_FILES = (
    "outputs/research/codex_issue5_source_admission/CODEX_ISSUE5_LAB026_CLEAN_PLACING_2021_2024.csv",
    "outputs/research/codex_issue5_source_admission/CODEX_ISSUE5_LAB031_CONTEXT_2021_2024.csv",
    "outputs/research/profitability_program/lab245b/LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv",
    "outputs/research/profitability_program/lab245b/LAB245B_WAREHOUSE_RUNNER_LVS.csv",
    "outputs/research/profitability_program/d45/D45_FROZEN_PIT_FEATURE_MATRIX.csv",
    "outputs/research/model_v2/stage006/V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv",
)


@dataclass
class SourceAssessment:
    source_id: str
    path: str
    exists: bool
    role: str
    rows: str
    races: str
    date_min: str
    date_max: str
    status: str
    admissible_for_issue8_fit: str
    blocker: str
    sha256: str = ""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def date_from_manifest(value: object) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def flagged_market_columns(columns: Iterable[str]) -> list[str]:
    flagged = []
    for col in columns:
        lower = col.lower()
        if lower in ("sp", "bsp") or any(term in lower for term in FORBIDDEN_MARKET_TERMS):
            flagged.append(col)
    return flagged


def classify_source_name(name: str) -> tuple[str, str]:
    lower = name.lower()
    if "first_starter" in lower or "first-starter" in lower:
        return "NOT_ALL_RUNNER", "First-starter artifact cannot certify full-field all-runner model population."
    if any(term in lower for term in ("price", "market", "odds", "bsp", "sp_")):
        return "FORBIDDEN_MARKET_SOURCE", "Market/price source is outside Issue #8 admission scope."
    if "2025" in lower or "2026" in lower:
        return "BLOCKED_SEALED_YEAR_NAME", "Path/name indicates sealed-year content."
    if "2021_2024" in lower:
        return "ADMITTED_EXAMPLE_NOT_PRE2022", "Already partitioned to 2021-2024; useful precedent but not pre-2022 expansion evidence."
    return "UNCERTIFIED", "No approved pre-2022 all-runner PIT modelling contract found."


def assess_manifest(repo: Path, rel: str) -> SourceAssessment:
    path = repo / rel
    if not path.is_file():
        return SourceAssessment(
            source_id=Path(rel).stem,
            path=rel,
            exists=False,
            role="manifest",
            rows="",
            races="",
            date_min="",
            date_max="",
            status="MISSING",
            admissible_for_issue8_fit="NO",
            blocker="Named manifest is not present in this checkout.",
        )
    data = load_json(path)
    columns = data.get("columns") or data.get("required_columns") or []
    flagged = flagged_market_columns([str(c) for c in columns])
    min_date = data.get("min_race_date") or data.get("date_min") or ""
    max_date = data.get("max_race_date") or data.get("date_max") or ""
    max_d = date_from_manifest(max_date)
    rows = data.get("output_rows", data.get("rows", ""))
    races = data.get("output_unique_race_count", data.get("races", ""))
    role, reason = classify_source_name(rel)
    status = data.get("status", "UNKNOWN")
    if flagged:
        role = "FORBIDDEN_MARKET_SOURCE"
        reason = "Manifest exposes forbidden market-like columns: " + ",".join(flagged)
        status = "STOP"
    elif max_d and max_d > date(2024, 12, 31):
        role = "BLOCKED_SEALED_YEAR_RANGE"
        reason = "Manifest max date exceeds 2024-12-31."
        status = "STOP"
    elif rel.endswith("LAB245B_COMPACT_PERFORMANCE_BRIDGE.manifest.json"):
        role = "PIT_HISTORY_2021_2024_ONLY"
        reason = "Strict-date hist_runs lineage precedent only; manifest rows/races are 2021-2024, not pre-2022 all-runner expansion."
    elif rel.endswith("LAB245B_WAREHOUSE_RUNNER_LVS.manifest.json"):
        role = "UPSTREAM_IDENTITY_UNCERTIFIED"
        reason = "Canonical identity equivalence for upstream warehouse remains imported/unproven in prior audits."
    return SourceAssessment(
        source_id=Path(rel).stem,
        path=rel,
        exists=True,
        role=role,
        rows=str(rows),
        races=str(races),
        date_min=str(min_date),
        date_max=str(max_date),
        status=str(status),
        admissible_for_issue8_fit="NO",
        blocker=reason,
        sha256=sha256_file(path),
    )


def assess_source_file(repo: Path, rel: str) -> SourceAssessment:
    path = repo / rel
    role, reason = classify_source_name(rel)
    if not path.is_file():
        return SourceAssessment(
            source_id=Path(rel).stem,
            path=rel,
            exists=False,
            role=role,
            rows="",
            races="",
            date_min="",
            date_max="",
            status="MISSING",
            admissible_for_issue8_fit="NO",
            blocker="Named source file is not present in this checkout.",
        )
    if rel.endswith("LAB245B_WAREHOUSE_RUNNER_LVS.csv"):
        role = "UPSTREAM_IDENTITY_UNCERTIFIED"
        reason = "Prior audits found canonical race/horse identity imported, not proven equivalent to historical race_id/runner_id."
    elif rel.endswith("LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"):
        role = "PIT_HISTORY_2021_2024_ONLY"
        reason = "Strict-date construction precedent exists for hist_runs only; this output does not cover pre-2022 all-runner history."
    elif "stage006" in rel.lower():
        role = "STAGE006_2021_2024_ONLY"
        reason = "Stage006 warehouse is part of Stage011-era 2021-2024 development, not certified pre-2022 expansion."
    elif "d45" in rel.lower():
        role = "D45_STAGE011_CONTEXT"
        reason = "D45 supports Stage011-era context; no pre-2022 all-runner PIT admission found."
    return SourceAssessment(
        source_id=Path(rel).stem,
        path=rel,
        exists=True,
        role=role,
        rows="HEADER_NOT_ROW_SCANNED",
        races="HEADER_NOT_ROW_SCANNED",
        date_min="",
        date_max="",
        status="INSPECTED_BY_NAME_ONLY",
        admissible_for_issue8_fit="NO",
        blocker=reason,
        sha256=sha256_file(path),
    )


def extract_pre2021_summary(repo: Path) -> dict:
    summary = {
        "pre2021_rows_inspected": None,
        "provisional_flat_races": None,
        "eligible_single_winner_unique_key_races": None,
        "eligible_flat_rate": None,
        "missing_years": ["2011", "2017"],
        "sparse_years": {"2016": "399 provisional all-runner flat races in prior Gate 2 disposition"},
        "hist_runs_source_code_status": "UNKNOWN",
        "identity_status": "UNKNOWN",
        "builder_status": "UNKNOWN",
    }
    for rel in PRE2021_EVIDENCE_DOCS:
        path = repo / rel
        if not path.is_file():
            continue
        text = read_text(path)
        if "Pre-2021 rows inspected" in text:
            m = re.search(r"Pre-2021 rows inspected[^0-9]+([0-9,]+)", text)
            if m:
                summary["pre2021_rows_inspected"] = int(m.group(1).replace(",", ""))
            m = re.search(r"Provisional flat races[^0-9]+([0-9,]+)", text)
            if m:
                summary["provisional_flat_races"] = int(m.group(1).replace(",", ""))
            m = re.search(r"unique runner-key provisional flat races[^0-9]+([0-9,]+) \(([0-9.]+)%\)", text)
            if m:
                summary["eligible_single_winner_unique_key_races"] = int(m.group(1).replace(",", ""))
                summary["eligible_flat_rate"] = float(m.group(2)) / 100.0
        if "PASS SOURCE-CODE STRICT DATE LINEAGE FOR hist_runs ONLY" in text:
            summary["hist_runs_source_code_status"] = "PASS_FOR_HIST_RUNS_ONLY_SUBJECT_TO_UPSTREAM_INPUT_INTEGRITY"
        if "IMPORTED_UNPROVEN" in text:
            summary["identity_status"] = "IMPORTED_UNPROVEN"
        if "NO_CERTIFIED_PRE_RACE_CANDIDATE_BUILDER" in text:
            summary["builder_status"] = "STOP_NO_CERTIFIED_PRE_RACE_CANDIDATE_BUILDER"
    return summary


def audit_runner_rows(path: Path, max_allowed_date: date = date(2024, 12, 31)) -> dict:
    """Small synthetic-test helper; production admission does not call this on raw sources."""
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"race_id", "runner_id", "race_date", "winner"}
        missing = sorted(required - set(reader.fieldnames or []))
        if missing:
            return {"status": "STOP", "reasons": ["MISSING_COLUMNS:" + ",".join(missing)]}
        seen = set()
        winners_by_race: dict[str, int] = {}
        reasons: list[str] = []
        rows = 0
        for row in reader:
            rows += 1
            try:
                d = date.fromisoformat(row["race_date"][:10])
            except ValueError:
                reasons.append("UNPARSEABLE_DATE")
                continue
            if d > max_allowed_date:
                reasons.append("MIXED_OR_SEALED_YEAR_ROW")
            key = (row["race_id"], row["runner_id"])
            if key in seen:
                reasons.append("DUPLICATE_RUNNER_KEY")
            seen.add(key)
            winners_by_race[row["race_id"]] = winners_by_race.get(row["race_id"], 0) + int(row["winner"] == "1")
        bad_winners = [race for race, count in winners_by_race.items() if count != 1]
        if bad_winners:
            reasons.append("MISSING_OR_MULTIPLE_WINNERS")
        return {
            "status": "PASS" if not reasons else "STOP",
            "rows": rows,
            "races": len(winners_by_race),
            "reasons": sorted(set(reasons)),
        }


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument(
        "--out",
        default="outputs/research/issue8_pre2022_source_admission",
        help="Output directory for small audit artifacts",
    )
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve()
    out = (repo / args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    evidence_docs = []
    for rel in PRE2021_EVIDENCE_DOCS:
        path = repo / rel
        evidence_docs.append(
            {
                "path": rel,
                "exists": path.is_file(),
                "sha256": sha256_file(path) if path.is_file() else "",
            }
        )

    assessments = [assess_manifest(repo, rel) for rel in NAMED_MANIFESTS]
    assessments.extend(assess_source_file(repo, rel) for rel in NAMED_SOURCE_FILES)
    rows = [asdict(a) for a in assessments]
    write_csv(out / "ISSUE8_PRE2022_SOURCE_ADMISSION_SUMMARY.csv", rows)

    blockers = [
        {
            "blocker_id": "NO_CERTIFIED_PRE2022_ALL_RUNNER_PIT_MATRIX",
            "severity": "STOP",
            "evidence": "Prior Gate 2 found outcome inventory but stopped for NO_CERTIFIED_PRE_RACE_CANDIDATE_BUILDER.",
            "minimum_resolution": "Produce a sealed-free pre-2022 all-runner PIT matrix with complete fields, winner labels, date bounds, checksums and lineage.",
        },
        {
            "blocker_id": "CANONICAL_IDENTITY_IMPORTED_UNPROVEN",
            "severity": "STOP",
            "evidence": "LAB245B upstream imports canonical_race_id/canonical_horse_id; equivalence to historical race_id/runner_id remains unproven.",
            "minimum_resolution": "Certify a one-to-one race/runner identity bridge with zero collisions and explicit duplicate/scratch handling.",
        },
        {
            "blocker_id": "FIRST_STARTER_ARTIFACTS_NOT_ALL_RUNNER",
            "severity": "STOP",
            "evidence": "LAB075/LAB076 evidence is first-starter-specialist inventory, not full-field all-runner model rows.",
            "minimum_resolution": "Do not use first-starter universes as the base population; use only complete all-runner race fields.",
        },
        {
            "blocker_id": "MISSING_OR_SPARSE_YEARS",
            "severity": "STOP",
            "evidence": "Prior disposition reports missing 2011 and 2017, with 2016 sparse in provisional all-runner inventory.",
            "minimum_resolution": "Document admissible year coverage and define fixed train/eval windows that exclude or explicitly handle gaps before scoring.",
        },
        {
            "blocker_id": "NO_CERTIFIED_PRE2022_JOCKEY_TRAINER_PIT_COVERAGE",
            "severity": "STOP",
            "evidence": "No admitted pre-2022 all-runner jockey/trainer PIT coverage artifact was found in named manifests or prior docs.",
            "minimum_resolution": "Build and audit strict-prior jockey/trainer history by canonical identity before any model comparison.",
        },
        {
            "blocker_id": "LICENSING_PROVENANCE_NOT_CERTIFIED_FOR_MODEL_USE",
            "severity": "STOP",
            "evidence": "Reviewed pre-2021 docs do not provide a model-admission licensing/provenance pass for the historical warehouse.",
            "minimum_resolution": "Attach source provenance, allowed-use status and immutable lineage manifest to the partition export.",
        },
    ]
    write_csv(out / "ISSUE8_PRE2022_BLOCKERS.csv", blockers)

    audit = {
        "status": "BLOCKED",
        "ready_to_run": False,
        "model_fitting": "NO",
        "model_scoring": "NO",
        "market_access": "NO",
        "sealed_year_access": "NO",
        "stage011_modified": "NO",
        "pre2021_summary": extract_pre2021_summary(repo),
        "evidence_docs": evidence_docs,
        "source_assessments": rows,
        "blockers": blockers,
        "decision": "No certified pre-2022 all-runner PIT feature matrix exists in the admitted evidence; do not fit or score Issue #8 models.",
    }
    (out / "ISSUE8_PRE2022_ADMISSION_AUDIT.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")

    print(json.dumps({"status": audit["status"], "ready_to_run": audit["ready_to_run"], "out": str(out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
