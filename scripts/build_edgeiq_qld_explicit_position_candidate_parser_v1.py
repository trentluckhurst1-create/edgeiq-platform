from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data"

CANDIDATES = PUBLIC / "edgeiq_qld_explicit_position_schema_candidates_v1.csv"

OUT_TOKENS = PUBLIC / "edgeiq_qld_position_schema_tokens_v1.csv"
OUT_PATTERNS = PUBLIC / "edgeiq_qld_position_schema_patterns_v1.csv"
OUT_CONFIDENCE = PUBLIC / "edgeiq_qld_position_schema_confidence_v1.csv"
OUT_LINEAGE = PUBLIC / "edgeiq_qld_position_schema_lineage_v1.csv"
OUT_SUMMARY = PUBLIC / "edgeiq_qld_explicit_position_candidate_parser_summary_v1.csv"
OUT_FAILURES = PUBLIC / "edgeiq_qld_explicit_position_candidate_parser_failures_v1.csv"

PARSER_VERSION = "EDGEIQ_QQLD_EXPLICIT_POSITION_CANDIDATE_PARSER_V1"
USER_AGENT = "EDGEiQ Research Parser/1.0"

TOKEN_RE = re.compile(r"[A-Za-z0-9_\-./:]+")
POSITION_HINTS = {
    "path", "lane", "barrier", "time", "long", "date", "position",
    "rank", "saddle", "saddles", "plate", "tab"
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

def fetch_text(url: str) -> tuple[str, str]:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=25) as res:
        raw = res.read()
    digest = hashlib.sha256(raw).hexdigest()
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return raw.decode(enc), digest
        except UnicodeDecodeError:
            pass
    return raw.decode("latin-1", errors="replace"), digest

def normalise_token(value: str) -> str:
    return str(value or "").strip().lower()

def detect_delimiter(sample: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample[:5000], delimiters=",\t;|")
        return dialect.delimiter
    except Exception:
        return ","

def parse_table(text: str) -> tuple[list[str], list[dict]]:
    sample = text[:5000]
    delim = detect_delimiter(sample)
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return [], []

    reader = csv.DictReader(lines, delimiter=delim)
    rows = []
    for row in reader:
        clean = {}
        for k, v in row.items():
            if k is None:
                continue
            clean[str(k).strip()] = "" if v is None else str(v).strip()
        if any(v for v in clean.values()):
            rows.append(clean)
    return list(reader.fieldnames or []), rows

def confidence_for(candidate: dict, fields: list[str], rows: list[dict]) -> dict:
    detected = set(normalise_token(x) for x in candidate.get("schema_fields_detected", "").split("|") if x)
    actual = set(normalise_token(x) for x in fields if x)
    overlap = sorted(detected.intersection(actual))

    status = candidate.get("schema_status", "")
    base = 70 if "EXPLICIT_POSITION_SCHEMA_CONFIRMED" in status else 45
    base += min(len(overlap) * 4, 20)
    base += 10 if len(rows) > 0 else 0
    base = min(base, 95)

    ambiguity = "LOW" if base >= 85 else "MEDIUM" if base >= 65 else "HIGH"
    grade = "A" if base >= 85 else "B" if base >= 70 else "C" if base >= 50 else "D"

    return {
        "schema_confidence_score": base,
        "parser_confidence_grade": grade,
        "ambiguity_grade": ambiguity,
        "field_overlap_count": len(overlap),
        "field_overlap": "|".join(overlap),
    }

def main() -> None:
    print("=" * 88)
    print("EDGEIQ QLD EXPLICIT POSITION CANDIDATE PARSER V1")
    print("=" * 88)

    candidates = read_csv(CANDIDATES)

    token_rows = []
    pattern_rows = []
    confidence_rows = []
    lineage_rows = []
    failure_rows = []

    summary = Counter()
    field_freq = Counter()
    token_freq_by_track = defaultdict(Counter)

    for idx, c in enumerate(candidates, start=1):
        track = c.get("track", "")
        url = c.get("asset_url") or c.get("source_url") or ""
        schema_id = hashlib.sha1(f"{track}|{url}".encode("utf-8")).hexdigest()[:12]

        summary["candidate_assets"] += 1

        try:
            text, digest = fetch_text(url)
            fields, rows = parse_table(text)

            summary["assets_fetched"] += 1
            summary["raw_rows_observed"] += len(rows)

            for f in fields:
                fn = normalise_token(f)
                field_freq[fn] += 1

            conf = confidence_for(c, fields, rows)

            lineage_rows.append({
                "parser_version": PARSER_VERSION,
                "schema_id": schema_id,
                "track": track,
                "source_url": c.get("source_url", ""),
                "asset_url": url,
                "schema_status": c.get("schema_status", ""),
                "schema_quality_grade": c.get("schema_quality_grade", ""),
                "detected_candidate_fields": c.get("schema_fields_detected", ""),
                "actual_asset_fields": "|".join(fields),
                "asset_sha256": digest,
                "raw_row_count": len(rows),
                "extraction_timestamp_utc": now_iso(),
                "research_boundary": "OFFLINE_RESEARCH_ONLY",
                "live_modelling_yes": 0,
                "live_execution_yes": 0,
            })

            confidence_rows.append({
                "schema_id": schema_id,
                "track": track,
                "schema_status": c.get("schema_status", ""),
                "schema_quality_grade": c.get("schema_quality_grade", ""),
                "schema_confidence_score": conf["schema_confidence_score"],
                "parser_confidence_grade": conf["parser_confidence_grade"],
                "ambiguity_grade": conf["ambiguity_grade"],
                "field_overlap_count": conf["field_overlap_count"],
                "field_overlap": conf["field_overlap"],
                "raw_row_count": len(rows),
                "research_boundary": "OFFLINE_RESEARCH_ONLY",
                "recommended_action": "observe_only_no_execution_no_modelling",
            })

            sample_rows = rows[:250]
            for row_no, row in enumerate(sample_rows, start=1):
                for field, value in row.items():
                    field_norm = normalise_token(field)
                    value_norm = str(value or "").strip()
                    if not value_norm:
                        continue

                    tokens = TOKEN_RE.findall(value_norm)
                    for tok in tokens[:20]:
                        token_norm = normalise_token(tok)
                        if not token_norm:
                            continue

                        hint = (
                            "POSITION_HINT_FIELD"
                            if field_norm in POSITION_HINTS
                            else "POSITION_HINT_TOKEN"
                            if token_norm in POSITION_HINTS
                            else "RAW_STRUCTURAL_TOKEN"
                        )

                        token_freq_by_track[track][f"{field_norm}:{token_norm}"] += 1

                        token_rows.append({
                            "schema_id": schema_id,
                            "track": track,
                            "row_no": row_no,
                            "field_name": field,
                            "field_name_norm": field_norm,
                            "token": tok,
                            "token_norm": token_norm,
                            "token_hint_type": hint,
                            "schema_status": c.get("schema_status", ""),
                            "asset_url": url,
                            "research_boundary": "OFFLINE_RESEARCH_ONLY",
                        })

            for field in fields:
                fn = normalise_token(field)
                values = [normalise_token(r.get(field, "")) for r in rows if normalise_token(r.get(field, ""))]
                unique_values = len(set(values))
                examples = "|".join(list(dict.fromkeys(values[:10])))

                pattern_rows.append({
                    "schema_id": schema_id,
                    "track": track,
                    "pattern_type": "FIELD_VALUE_PROFILE",
                    "field_name": field,
                    "field_name_norm": fn,
                    "row_count": len(rows),
                    "non_empty_count": len(values),
                    "unique_value_count": unique_values,
                    "example_values": examples,
                    "position_hint": "YES" if fn in POSITION_HINTS else "NO",
                    "schema_status": c.get("schema_status", ""),
                    "research_boundary": "OFFLINE_RESEARCH_ONLY",
                })

        except Exception as e:
            summary["failure_rows"] += 1
            failure_rows.append({
                "track": track,
                "asset_url": url,
                "error_type": type(e).__name__,
                "error": str(e),
                "research_boundary": "OFFLINE_RESEARCH_ONLY",
            })

    top_tokens = []
    for track, counts in token_freq_by_track.items():
        for token_key, count in counts.most_common(50):
            field, token = token_key.split(":", 1)
            top_tokens.append({
                "schema_id": "",
                "track": track,
                "pattern_type": "TOKEN_FREQUENCY_PROFILE",
                "field_name": field,
                "field_name_norm": field,
                "row_count": "",
                "non_empty_count": count,
                "unique_value_count": "",
                "example_values": token,
                "position_hint": "YES" if field in POSITION_HINTS or token in POSITION_HINTS else "NO",
                "schema_status": "",
                "research_boundary": "OFFLINE_RESEARCH_ONLY",
            })

    pattern_rows.extend(top_tokens)

    summary_rows = [
        {"metric": "candidate_assets", "value": summary["candidate_assets"]},
        {"metric": "assets_fetched", "value": summary["assets_fetched"]},
        {"metric": "raw_rows_observed", "value": summary["raw_rows_observed"]},
        {"metric": "token_rows", "value": len(token_rows)},
        {"metric": "pattern_rows", "value": len(pattern_rows)},
        {"metric": "confidence_rows", "value": len(confidence_rows)},
        {"metric": "lineage_rows", "value": len(lineage_rows)},
        {"metric": "failure_rows", "value": len(failure_rows)},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "offline_research_only", "value": "YES"},
    ]

    write_csv(OUT_TOKENS, token_rows, [
        "schema_id", "track", "row_no", "field_name", "field_name_norm",
        "token", "token_norm", "token_hint_type", "schema_status",
        "asset_url", "research_boundary"
    ])

    write_csv(OUT_PATTERNS, pattern_rows, [
        "schema_id", "track", "pattern_type", "field_name", "field_name_norm",
        "row_count", "non_empty_count", "unique_value_count", "example_values",
        "position_hint", "schema_status", "research_boundary"
    ])

    write_csv(OUT_CONFIDENCE, confidence_rows, [
        "schema_id", "track", "schema_status", "schema_quality_grade",
        "schema_confidence_score", "parser_confidence_grade", "ambiguity_grade",
        "field_overlap_count", "field_overlap", "raw_row_count",
        "research_boundary", "recommended_action"
    ])

    write_csv(OUT_LINEAGE, lineage_rows, [
        "parser_version", "schema_id", "track", "source_url", "asset_url",
        "schema_status", "schema_quality_grade", "detected_candidate_fields",
        "actual_asset_fields", "asset_sha256", "raw_row_count",
        "extraction_timestamp_utc", "research_boundary",
        "live_modelling_yes", "live_execution_yes"
    ])

    write_csv(OUT_SUMMARY, summary_rows, ["metric", "value"])

    write_csv(OUT_FAILURES, failure_rows, [
        "track", "asset_url", "error_type", "error", "research_boundary"
    ])

    for row in summary_rows:
        print(f"{row['metric']}: {row['value']}")

    print("=" * 88)
    print("OUTPUTS")
    print("=" * 88)
    print(OUT_TOKENS)
    print(OUT_PATTERNS)
    print(OUT_CONFIDENCE)
    print(OUT_LINEAGE)
    print(OUT_SUMMARY)
    print(OUT_FAILURES)

if __name__ == "__main__":
    main()
