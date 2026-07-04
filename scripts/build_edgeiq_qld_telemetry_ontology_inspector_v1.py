from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"

SOURCE = PUBLIC / "edgeiq_qld_position_schema_patterns_v1.csv"

OUT_DECOMPOSED = PUBLIC / "edgeiq_qld_telemetry_ontology_fragments_v1.csv"
OUT_SIGNATURES = PUBLIC / "edgeiq_qld_telemetry_ontology_signatures_v1.csv"
OUT_CLASSES = PUBLIC / "edgeiq_qld_telemetry_ontology_classes_v1.csv"
OUT_SUMMARY = PUBLIC / "edgeiq_qld_telemetry_ontology_summary_v1.csv"

PARSER_VERSION = "EDGEIQ_QQLD_TELEMETRY_ONTOLOGY_INSPECTOR_V1"

TOKEN_RE = re.compile(r"[A-Za-z0-9_\-./:]+")

ONTOLOGY_HINTS = {
    "track": "TRACK_TOPOLOGY_DESCRIPTOR",
    "race": "RACE_STATE_DESCRIPTOR",
    "time": "TIMING_ONTOLOGY_FRAGMENT",
    "path": "POSITIONAL_PATHWAY_FRAGMENT",
    "lane": "POSITIONAL_PATHWAY_FRAGMENT",
    "barrier": "START_STATE_FRAGMENT",
    "date": "TEMPORAL_LINEAGE_FRAGMENT",
    "tab": "MARKET_LINEAGE_FRAGMENT",
    "saddles": "RUNNER_STATE_FRAGMENT",
}

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

def classify_token(token: str) -> str:
    t = token.lower()

    for hint, cls in ONTOLOGY_HINTS.items():
        if hint in t:
            return cls

    if "_track" in t:
        return "TRACK_SURFACE_FRAGMENT"

    if re.match(r"\d{2}/\d{2}/\d{4}", t):
        return "TEMPORAL_LINEAGE_FRAGMENT"

    if re.match(r"\d{2}:\d{2}:\d{2}", t):
        return "TIMING_ONTOLOGY_FRAGMENT"

    if "qld" in t:
        return "JURISDICTION_FRAGMENT"

    if "professional" in t:
        return "RACE_ENVIRONMENT_FRAGMENT"

    return "UNCLASSIFIED_FRAGMENT"

def main() -> None:
    print("=" * 88)
    print("EDGEIQ QLD TELEMETRY ONTOLOGY INSPECTOR V1")
    print("=" * 88)

    rows = read_csv(SOURCE)

    decomposed_rows = []
    signature_rows = []
    class_rows = []

    fragment_counter = Counter()
    ontology_counter = Counter()
    track_signature_counter = defaultdict(Counter)

    total_fragments = 0

    for row in rows:
        track = row.get("track", "")
        example_values = row.get("example_values", "")

        if not example_values:
            continue

        fragments = re.split(r"[;|]", example_values)

        for idx, fragment in enumerate(fragments, start=1):
            fragment = fragment.strip()

            if not fragment:
                continue

            total_fragments += 1

            fragment_hash = hashlib.sha1(
                f"{track}|{fragment}".encode("utf-8")
            ).hexdigest()[:12]

            ontology_class = classify_token(fragment)

            fragment_counter[fragment.lower()] += 1
            ontology_counter[ontology_class] += 1
            track_signature_counter[track][ontology_class] += 1

            tokens = TOKEN_RE.findall(fragment)

            decomposed_rows.append({
                "fragment_id": fragment_hash,
                "track": track,
                "fragment_index": idx,
                "raw_fragment": fragment,
                "token_count": len(tokens),
                "ontology_class": ontology_class,
                "parser_version": PARSER_VERSION,
                "research_boundary": "OFFLINE_RESEARCH_ONLY",
                "live_modelling_yes": 0,
                "live_execution_yes": 0,
                "timestamp_utc": now_iso(),
            })

    for ontology_class, count in ontology_counter.most_common():
        class_rows.append({
            "ontology_class": ontology_class,
            "fragment_count": count,
            "classification_strength": (
                "HIGH" if count >= 25
                else "MEDIUM" if count >= 10
                else "LOW"
            ),
            "research_boundary": "OFFLINE_RESEARCH_ONLY",
        })

    for track, counter in track_signature_counter.items():
        for ontology_class, count in counter.items():
            signature_rows.append({
                "track": track,
                "ontology_signature": ontology_class,
                "signature_frequency": count,
                "signature_strength": (
                    "HIGH" if count >= 20
                    else "MEDIUM" if count >= 8
                    else "LOW"
                ),
                "research_boundary": "OFFLINE_RESEARCH_ONLY",
            })

    summary_rows = [
        {"metric": "input_rows", "value": len(rows)},
        {"metric": "total_fragments", "value": total_fragments},
        {"metric": "unique_fragments", "value": len(fragment_counter)},
        {"metric": "ontology_classes", "value": len(ontology_counter)},
        {"metric": "track_signature_rows", "value": len(signature_rows)},
        {"metric": "offline_research_only", "value": "YES"},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
    ]

    write_csv(
        OUT_DECOMPOSED,
        decomposed_rows,
        [
            "fragment_id",
            "track",
            "fragment_index",
            "raw_fragment",
            "token_count",
            "ontology_class",
            "parser_version",
            "research_boundary",
            "live_modelling_yes",
            "live_execution_yes",
            "timestamp_utc",
        ],
    )

    write_csv(
        OUT_SIGNATURES,
        signature_rows,
        [
            "track",
            "ontology_signature",
            "signature_frequency",
            "signature_strength",
            "research_boundary",
        ],
    )

    write_csv(
        OUT_CLASSES,
        class_rows,
        [
            "ontology_class",
            "fragment_count",
            "classification_strength",
            "research_boundary",
        ],
    )

    write_csv(
        OUT_SUMMARY,
        summary_rows,
        ["metric", "value"],
    )

    print("SUMMARY")
    print("=" * 88)

    for row in summary_rows:
        print(f"{row['metric']}: {row['value']}")

    print("=" * 88)
    print("ONTOLOGY CLASSES")
    print("=" * 88)

    for row in class_rows:
        print(
            f"{row['ontology_class']}: "
            f"{row['fragment_count']} "
            f"({row['classification_strength']})"
        )

    print("=" * 88)
    print("OUTPUTS")
    print("=" * 88)

    print(OUT_DECOMPOSED)
    print(OUT_SIGNATURES)
    print(OUT_CLASSES)
    print(OUT_SUMMARY)

if __name__ == "__main__":
    main()
