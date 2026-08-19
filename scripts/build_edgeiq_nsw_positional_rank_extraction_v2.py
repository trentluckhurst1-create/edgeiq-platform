from __future__ import annotations

import csv
import re
import zlib
from collections import Counter, defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Iterable

from edgeiq_memory_safe_io import safe_read_csv, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_SECTIONALS = DATA / "edgeiq_nsw_pdf_extracted_sectionals_v1.csv"
IN_FORENSICS = DATA / "edgeiq_nsw_pdf_telemetry_forensics_v1.csv"

OUT_RANKS = DATA / "edgeiq_nsw_positional_rank_telemetry_v2.csv"
OUT_SUMMARY = DATA / "edgeiq_nsw_positional_rank_summary_v2.csv"
OUT_TRANSITIONS = DATA / "edgeiq_nsw_rank_transition_states_v2.csv"
OUT_FAILURES = DATA / "edgeiq_nsw_rank_extraction_failures_v2.csv"

RANK_FIELDS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "split_marker",
    "split_time",
    "rank_at_split",
    "previous_rank",
    "rank_change",
    "position_state",
    "movement_state",
    "race_state_pressure",
    "transition_strength",
    "lineage_reference",
    "extraction_confidence",
    "safe_for_nsw_temporal_research",
    "safe_for_nsw_shadow_research",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

TRANSITION_FIELDS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "rank_observations",
    "first_rank",
    "last_rank",
    "best_rank",
    "worst_rank",
    "net_rank_change",
    "advance_events",
    "fade_events",
    "stable_events",
    "dominant_position_state",
    "dominant_movement_state",
    "position_persistence",
    "transition_status",
    "safe_for_nsw_temporal_research",
    "safe_for_nsw_shadow_research",
    "notes",
]

FAILURE_FIELDS = [
    "source_file",
    "failure_type",
    "failure_reason",
    "affected_rows",
    "recommended_repair",
    "notes",
]

OFFLINE_NOTES = "Offline NSW positional-rank telemetry research only. No predictions, ratings, overlays, live modelling, execution, or VIC/QLD merge."

RUNNER_BLOCK_PATTERN = re.compile(
    r"(?P<jockey>[A-Z][A-Za-z '.-]+?)\s+"
    r"(?P<distance_travelled>\d{4}\.\d)\s+"
    r"(?P<last600>0:\d{2}\.\d{2})\s+"
    r"(?P<splits>(?:\d:\d{2}\.\d{2}\s*\[\d{1,2}\]\s*){6})\s+"
    r"(?P<fastest200>0:\d{2}\.\d{2})\s+"
    r"(?P<top_speed>\d{2}\.\d)\s+"
    r"(?P<tab_no>\d{1,2})\s+"
    r"(?P<horse>[A-Z][A-Z '().-]+?)\s+"
    r"(?P<barrier>\d{1,2})\s+"
    r"(?P<finish_position>\d{1,2})",
    re.S,
)

SPLIT_RANK_PATTERN = re.compile(r"(?P<time>\d:\d{2}\.\d{2})\s*\[\s*(?P<rank>\d{1,2})\s*\]")
RUNNER_BLOCK_SPLIT_MARKERS = ["FINISH", "200", "400", "600", "800", "1000"]


def clean(value: object) -> str:
    return str(value or "").strip()


def normalise_spaces(value: object) -> str:
    return re.sub(r"\s+", " ", clean(value)).strip()


def parse_int(value: object) -> int | None:
    text = clean(value)
    if not text:
        return None
    match = re.search(r"-?\d+", text)
    if not match:
        return None
    try:
        return int(match.group(0))
    except ValueError:
        return None


def normalise_source_name(value: object) -> str:
    return Path(clean(value)).name.lower()


def normalise_time_token(value: object) -> str:
    text = clean(value)
    if not text:
        return ""
    text = text.replace("O", "0").replace("o", "0")
    text = re.sub(r"\s+", "", text)
    if ":" in text:
        left, right = text.rsplit(":", 1)
        try:
            seconds = int(left or "0") * 60 + float(right)
            return f"{seconds:05.2f}" if seconds < 100 else f"{seconds:.2f}"
        except ValueError:
            return right
    try:
        number = float(text)
        return f"{number:05.2f}" if number < 100 else f"{number:.2f}"
    except ValueError:
        return text


def row_split_order(row: dict[str, str], fallback: int) -> tuple[int, int]:
    marker = parse_int(row.get("split_marker"))
    if marker is None:
        return (999999, fallback)
    return (marker, fallback)


def discover_pdfs() -> list[Path]:
    roots = [
        ROOT / "outputs" / "sectionals" / "raw" / "NSW",
        DATA,
        ROOT,
    ]
    candidates: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.pdf"):
            lowered = str(path).lower()
            if "\\node_modules\\" in lowered or "\\dist\\" in lowered or "\\.git\\" in lowered:
                continue
            name = path.name.lower()
            if any(token in name for token in ("0605w", "nsw", "atc", "sectional", "racing", "fm-", "rosehill", "randwick", "canterbury", "warwick", "farm")):
                resolved = path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    candidates.append(path)
    return sorted(candidates, key=lambda item: str(item).lower())


def extract_with_pdfplumber(path: Path) -> list[tuple[int, str]]:
    try:
        import pdfplumber  # type: ignore
    except Exception:
        return []
    pages: list[tuple[int, str]] = []
    try:
        with pdfplumber.open(str(path)) as pdf:
            for index, page in enumerate(pdf.pages, start=1):
                text_parts = [
                    page.extract_text(x_tolerance=1, y_tolerance=3) or "",
                    page.extract_text(x_tolerance=2, y_tolerance=6) or "",
                ]
                try:
                    words = page.extract_words(keep_blank_chars=False, use_text_flow=True) or []
                    text_parts.append(" ".join(clean(word.get("text")) for word in words))
                except Exception:
                    pass
                pages.append((index, "\n".join(part for part in text_parts if part)))
    except Exception:
        return []
    return pages


def extract_with_pypdf(path: Path) -> list[tuple[int, str]]:
    reader_cls = None
    try:
        from pypdf import PdfReader  # type: ignore

        reader_cls = PdfReader
    except Exception:
        try:
            from PyPDF2 import PdfReader  # type: ignore

            reader_cls = PdfReader
        except Exception:
            return []
    pages: list[tuple[int, str]] = []
    try:
        reader = reader_cls(str(path))
        for index, page in enumerate(reader.pages, start=1):
            try:
                pages.append((index, page.extract_text() or ""))
            except Exception:
                pages.append((index, ""))
    except Exception:
        return []
    return pages


def printable_strings(data: bytes, minimum: int = 4) -> str:
    chunks = re.findall(rb"[\x09\x0A\x0D\x20-\x7E]{%d,}" % minimum, data)
    return "\n".join(chunk.decode("latin-1", errors="ignore") for chunk in chunks)


def extract_raw_and_stream_strings(path: Path) -> list[tuple[int, str]]:
    try:
        raw = path.read_bytes()
    except Exception:
        return []

    parts = [printable_strings(raw)]
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, flags=re.DOTALL):
        payload = match.group(1).strip(b"\r\n")
        for candidate in (payload, payload.replace(b"\r\n", b"\n")):
            try:
                parts.append(printable_strings(zlib.decompress(candidate)))
                break
            except Exception:
                continue
    text = "\n".join(part for part in parts if part)
    text = text.replace("\\r", "\n").replace("\\n", "\n")
    return [(1, text)] if text else []


def extract_pdf_text(path: Path) -> tuple[list[tuple[int, str]], str]:
    best_pages: list[tuple[int, str]] = []
    best_method = "none"
    best_score = -1
    for method, extractor in (
        ("pypdf", extract_with_pypdf),
        ("pdfplumber", extract_with_pdfplumber),
        ("raw_stream_strings", extract_raw_and_stream_strings),
    ):
        pages = extractor(path)
        useful = [(page_no, text) for page_no, text in pages if clean(text)]
        token_count = 0
        for page_no, text in useful:
            token_count += len(extract_rank_tokens(text, path.name, page_no, method))
        if token_count > best_score:
            best_pages = useful
            best_method = method
            best_score = token_count
        if method == "pypdf" and token_count:
            break
    return best_pages, best_method


def expand_fragmented_brackets(text: str) -> str:
    expanded = text
    expanded = re.sub(r"\[\s*(\d{1,2})\s*\]", r"[\1]", expanded)
    expanded = re.sub(r"(\d)\s*:\s*(\d{2})\s*\.\s*(\d{2})\s*\[\s*(\d{1,2})\s*\]", r"\1:\2.\3 [\4]", expanded)
    expanded = re.sub(r"(?<!\d)(\d{1,2})\s*\.\s*(\d{2})\s*\[\s*(\d{1,2})\s*\]", r"\1.\2 [\3]", expanded)
    return expanded


def extract_rank_tokens(text: str, source_file: str, page_no: int, method: str) -> list[dict[str, object]]:
    normalised = expand_fragmented_brackets(text)
    tokens: list[dict[str, object]] = []
    patterns = [
        re.compile(r"(?P<time>\b\d{1,2}:\d{2}\.\d{2})\s*\[\s*(?P<rank>\d{1,2})\s*\]"),
        re.compile(r"(?P<time>(?<!\d)\d{1,2}\.\d{2})\s*\[\s*(?P<rank>\d{1,2})\s*\]"),
        re.compile(r"(?P<time>\b\d{1,2}\s*:\s*\d{2}\s*\.\s*\d{2})\s*\[\s*(?P<rank>\d{1,2})\s*\]"),
        re.compile(r"(?P<time>(?<!\d)\d{1,2}\s*\.\s*\d{2})\s*\[\s*(?P<rank>\d{1,2})\s*\]"),
    ]
    seen: set[tuple[int, str, int]] = set()
    for pattern in patterns:
        for match in pattern.finditer(normalised):
            rank = parse_int(match.group("rank"))
            if rank is None or rank <= 0 or rank > 30:
                continue
            time_text = normalise_spaces(match.group("time"))
            start = max(0, match.start() - 80)
            end = min(len(normalised), match.end() + 80)
            key = (match.start(), normalise_time_token(time_text), rank)
            if key in seen:
                continue
            seen.add(key)
            tokens.append(
                {
                    "source_file": source_file,
                    "page_no": page_no,
                    "split_time": time_text,
                    "normalised_time": normalise_time_token(time_text),
                    "rank_at_split": rank,
                    "method": method,
                    "context": normalise_spaces(normalised[start:end]),
                    "token_order": len(tokens),
                }
            )
    tokens.sort(key=lambda item: int(item["token_order"]))
    return tokens


def metadata_by_source(sectionals: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    metadata: dict[str, dict[str, str]] = {}
    for row in sectionals:
        source = normalise_source_name(row.get("source_file"))
        if not source or source in metadata:
            continue
        metadata[source] = {
            "race_date": row.get("race_date", ""),
            "track": row.get("track", ""),
            "race_no": row.get("race_no", ""),
        }
    return metadata


def extract_runner_rank_blocks(text: str, source_file: str, page_no: int, method: str, race_meta: dict[str, str]) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    expanded = expand_fragmented_brackets(text)
    for block_index, match in enumerate(RUNNER_BLOCK_PATTERN.finditer(expanded)):
        split_pairs = SPLIT_RANK_PATTERN.findall(match.group("splits"))
        if not split_pairs:
            continue
        previous: int | None = None
        horse = normalise_spaces(match.group("horse"))
        for split_index, (split_time, rank_text) in enumerate(split_pairs):
            rank = parse_int(rank_text)
            if rank is None or rank <= 0 or rank > 30:
                continue
            pos_state = position_state(rank)
            move_state, strength, change = movement_state(previous, rank)
            confidence = 92.0 if method in {"pypdf", "pdfplumber"} else 72.0
            split_marker = RUNNER_BLOCK_SPLIT_MARKERS[split_index] if split_index < len(RUNNER_BLOCK_SPLIT_MARKERS) else str(split_index + 1)
            blocks.append(
                {
                    "race_date": race_meta.get("race_date", ""),
                    "track": race_meta.get("track", ""),
                    "race_no": race_meta.get("race_no", ""),
                    "horse": horse,
                    "split_marker": split_marker,
                    "split_time": split_time,
                    "rank_at_split": str(rank),
                    "previous_rank": "" if previous is None else str(previous),
                    "rank_change": change,
                    "position_state": pos_state,
                    "movement_state": move_state,
                    "race_state_pressure": pressure_state(pos_state),
                    "transition_strength": strength,
                    "lineage_reference": f"{source_file}|page:{page_no}|method:{method}|runner_block:{block_index}|tab:{match.group('tab_no')}|barrier:{match.group('barrier')}|finish:{match.group('finish_position')}",
                    "extraction_confidence": f"{confidence:.2f}",
                    "safe_for_nsw_temporal_research": "YES",
                    "safe_for_nsw_shadow_research": "YES" if confidence >= 78 else "NO",
                    "notes": f"runner block positional rank extraction. jockey={normalise_spaces(match.group('jockey'))}; tab={match.group('tab_no')}; barrier={match.group('barrier')}; finish={match.group('finish_position')}. {OFFLINE_NOTES}",
                }
            )
            previous = rank
    return blocks


def build_sectional_index(rows: list[dict[str, str]]) -> tuple[dict[str, deque[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    by_source_time: dict[str, deque[dict[str, str]]] = defaultdict(deque)
    by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
    for index, row in enumerate(rows):
        row["_row_order"] = str(index)
        source = normalise_source_name(row.get("source_file"))
        split_time = normalise_time_token(row.get("split_time"))
        if source and split_time:
            by_source_time[f"{source}|{split_time}"].append(row)
        if source:
            by_source[source].append(row)
    for source in by_source:
        by_source[source].sort(key=lambda item: row_split_order(item, parse_int(item.get("_row_order")) or 0))
    return by_source_time, by_source


def position_state(rank: int) -> str:
    if rank <= 1:
        return "LEADER"
    if rank <= 3:
        return "PRESSURE"
    if rank <= 8:
        return "MIDFIELD"
    return "BACKMARKER"


def movement_state(previous_rank: int | None, rank: int) -> tuple[str, str, str]:
    if previous_rank is None:
        return "STABLE_POSITION", "NONE", ""
    change = previous_rank - rank
    if change > 0:
        movement = "ADVANCING"
    elif change < 0:
        movement = "FADING"
    else:
        movement = "STABLE_POSITION"
    strength = "STABLE"
    if abs(change) >= 3:
        strength = "STRONG"
    elif abs(change) >= 1:
        strength = "MODERATE"
    return movement, strength, str(change)


def pressure_state(state: str) -> str:
    return {
        "LEADER": "FRONT_PRESSURE",
        "PRESSURE": "PACE_PRESSURE",
        "MIDFIELD": "PACK_PRESSURE",
        "BACKMARKER": "REAR_PRESSURE",
    }.get(state, "UNKNOWN_PRESSURE")


def assign_tokens_to_rows(tokens: list[dict[str, object]], sectionals: list[dict[str, str]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    by_source_time, by_source = build_sectional_index(sectionals)
    assigned: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    source_fallback_offsets: Counter[str] = Counter()

    for token in tokens:
        source = normalise_source_name(token.get("source_file"))
        time_key = f"{source}|{token.get('normalised_time', '')}"
        candidate: dict[str, str] | None = None
        confidence = 86.0
        mapping_note = "exact split_time bracket-rank match"

        if by_source_time.get(time_key):
            candidate = by_source_time[time_key].popleft()
        elif by_source.get(source):
            source_rows = by_source[source]
            offset = source_fallback_offsets[source]
            if offset < len(source_rows):
                candidate = source_rows[offset]
                source_fallback_offsets[source] += 1
                confidence = 58.0
                mapping_note = "fallback source-order mapping; no exact split_time match"

        if not candidate:
            failures.append(
                {
                    "source_file": token.get("source_file", ""),
                    "failure_type": "UNMAPPED_BRACKET_RANK",
                    "failure_reason": f"Bracket rank {token.get('rank_at_split')} at {token.get('split_time')} could not be mapped to a sectional row.",
                    "affected_rows": "1",
                    "recommended_repair": "Improve PDF table reconstruction so bracket rank tokens retain runner and split-column context.",
                    "notes": OFFLINE_NOTES,
                }
            )
            continue

        method = clean(token.get("method"))
        if "raw_stream_strings" in method and "pdfplumber" not in method and "pypdf" not in method:
            confidence = min(confidence, 68.0)
        rank = int(token["rank_at_split"])
        assigned.append(
            {
                "base_row": candidate,
                "rank_at_split": rank,
                "token": token,
                "confidence": confidence,
                "mapping_note": mapping_note,
            }
        )
    return assigned, failures


def build_rank_rows(assignments: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, object]]] = defaultdict(list)
    for item in assignments:
        row = item["base_row"]
        if not isinstance(row, dict):
            continue
        key = (
            clean(row.get("race_date")),
            clean(row.get("track")).upper(),
            clean(row.get("race_no")),
            clean(row.get("horse")),
        )
        grouped[key].append(item)

    output: list[dict[str, object]] = []
    for key, items in grouped.items():
        items.sort(key=lambda item: row_split_order(item["base_row"], parse_int(item["base_row"].get("_row_order")) or 0))  # type: ignore[index,union-attr]
        previous: int | None = None
        for item in items:
            base = item["base_row"]
            token = item["token"]
            rank = int(item["rank_at_split"])
            pos_state = position_state(rank)
            move_state, strength, change = movement_state(previous, rank)
            confidence = float(item["confidence"])
            safe_temporal = "YES" if confidence >= 58 else "NO"
            safe_shadow = "YES" if confidence >= 78 else "NO"
            output.append(
                {
                    "race_date": base.get("race_date", ""),
                    "track": base.get("track", ""),
                    "race_no": base.get("race_no", ""),
                    "horse": base.get("horse", ""),
                    "split_marker": base.get("split_marker", ""),
                    "split_time": token.get("split_time") or base.get("split_time", ""),
                    "rank_at_split": str(rank),
                    "previous_rank": "" if previous is None else str(previous),
                    "rank_change": change,
                    "position_state": pos_state,
                    "movement_state": move_state,
                    "race_state_pressure": pressure_state(pos_state),
                    "transition_strength": strength,
                    "lineage_reference": f"{token.get('source_file')}|page:{token.get('page_no')}|method:{token.get('method')}|rank_token:{token.get('token_order')}|base:{base.get('lineage_reference', '')}",
                    "extraction_confidence": f"{confidence:.2f}",
                    "safe_for_nsw_temporal_research": safe_temporal,
                    "safe_for_nsw_shadow_research": safe_shadow,
                    "notes": f"{item['mapping_note']}. {OFFLINE_NOTES}",
                }
            )
            previous = rank
    return output


def build_transition_rows(rank_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rank_rows:
        key = (
            clean(row.get("race_date")),
            clean(row.get("track")).upper(),
            clean(row.get("race_no")),
            clean(row.get("horse")),
        )
        grouped[key].append(row)

    transitions: list[dict[str, object]] = []
    for (_, _, _, _), rows in grouped.items():
        rows.sort(key=lambda row: (parse_int(row.get("split_marker")) or 999999, normalise_time_token(row.get("split_time"))))
        ranks = [parse_int(row.get("rank_at_split")) for row in rows]
        ranks = [rank for rank in ranks if rank is not None]
        if not ranks:
            continue
        movements = Counter(clean(row.get("movement_state")) for row in rows)
        states = Counter(clean(row.get("position_state")) for row in rows)
        advance_events = movements.get("ADVANCING", 0)
        fade_events = movements.get("FADING", 0)
        stable_events = movements.get("STABLE_POSITION", 0)
        persistence = round(stable_events / len(rows) * 100, 2) if rows else 0.0
        if advance_events > fade_events and advance_events > stable_events:
            status = "ADVANCING_PROFILE"
        elif fade_events > advance_events and fade_events > stable_events:
            status = "FADING_PROFILE"
        elif persistence >= 50:
            status = "POSITIONALLY_STABLE_PROFILE"
        else:
            status = "MIXED_POSITION_PROFILE"
        safe_temporal = "YES" if any(clean(row.get("safe_for_nsw_temporal_research")) == "YES" for row in rows) else "NO"
        safe_shadow = "YES" if any(clean(row.get("safe_for_nsw_shadow_research")) == "YES" for row in rows) else "NO"
        first = rows[0]
        transitions.append(
            {
                "race_date": first.get("race_date", ""),
                "track": first.get("track", ""),
                "race_no": first.get("race_no", ""),
                "horse": first.get("horse", ""),
                "rank_observations": str(len(rows)),
                "first_rank": str(ranks[0]),
                "last_rank": str(ranks[-1]),
                "best_rank": str(min(ranks)),
                "worst_rank": str(max(ranks)),
                "net_rank_change": str(ranks[0] - ranks[-1]),
                "advance_events": str(advance_events),
                "fade_events": str(fade_events),
                "stable_events": str(stable_events),
                "dominant_position_state": states.most_common(1)[0][0] if states else "",
                "dominant_movement_state": movements.most_common(1)[0][0] if movements else "",
                "position_persistence": f"{persistence:.2f}",
                "transition_status": status,
                "safe_for_nsw_temporal_research": safe_temporal,
                "safe_for_nsw_shadow_research": safe_shadow,
                "notes": OFFLINE_NOTES,
            }
        )
    return transitions


def write_summary(sectionals: list[dict[str, str]], pdfs: list[Path], rank_rows: list[dict[str, object]], transition_rows: list[dict[str, object]]) -> None:
    movements = Counter(clean(row.get("movement_state")) for row in rank_rows)
    positions = Counter(clean(row.get("position_state")) for row in rank_rows)
    high_conf = 0
    low_conf = 0
    for row in rank_rows:
        try:
            confidence = float(clean(row.get("extraction_confidence")) or 0)
        except ValueError:
            confidence = 0
        if confidence >= 78:
            high_conf += 1
        else:
            low_conf += 1

    summary = [
        {"metric": "pdfs_processed", "value": str(len(pdfs))},
        {"metric": "sectional_rows_processed", "value": str(len(sectionals))},
        {"metric": "rank_rows_detected", "value": str(len(rank_rows))},
        {"metric": "transition_rows_detected", "value": str(len(transition_rows))},
        {"metric": "leader_rows", "value": str(positions.get("LEADER", 0))},
        {"metric": "advancing_rows", "value": str(movements.get("ADVANCING", 0))},
        {"metric": "fading_rows", "value": str(movements.get("FADING", 0))},
        {"metric": "stable_rows", "value": str(movements.get("STABLE_POSITION", 0))},
        {"metric": "high_confidence_rank_rows", "value": str(high_conf)},
        {"metric": "low_confidence_rank_rows", "value": str(low_conf)},
        {"metric": "safe_for_nsw_temporal_research_yes", "value": str(sum(1 for row in rank_rows if clean(row.get("safe_for_nsw_temporal_research")) == "YES"))},
        {"metric": "safe_for_nsw_shadow_research_yes", "value": str(sum(1 for row in rank_rows if clean(row.get("safe_for_nsw_shadow_research")) == "YES"))},
        {"metric": "live_modelling_yes", "value": "0"},
        {"metric": "live_execution_yes", "value": "0"},
        {"metric": "offline_research_only", "value": "YES"},
    ]
    write_csv_atomic(OUT_SUMMARY, summary, SUMMARY_FIELDS)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    sectionals = safe_read_csv(IN_SECTIONALS)
    forensics = safe_read_csv(IN_FORENSICS)
    pdfs = discover_pdfs()
    failures: list[dict[str, object]] = []
    source_metadata = metadata_by_source(sectionals)
    direct_rank_rows: list[dict[str, object]] = []

    if not sectionals:
        failures.append(
            {
                "source_file": IN_SECTIONALS.name,
                "failure_type": "MISSING_SECTIONAL_BASE",
                "failure_reason": "Existing NSW sectional extraction file is missing or empty.",
                "affected_rows": "0",
                "recommended_repair": "Run build_edgeiq_nsw_pdf_telemetry_extraction_forensics_v1.py before V2 rank extraction.",
                "notes": OFFLINE_NOTES,
            }
        )

    expected_sources = {normalise_source_name(row.get("source_file")) for row in sectionals if row.get("source_file")}
    pdf_by_name = {normalise_source_name(path.name): path for path in pdfs}
    missing_pdf_sources = sorted(source for source in expected_sources if source and source not in pdf_by_name)
    for source in missing_pdf_sources:
        failures.append(
            {
                "source_file": source,
                "failure_type": "PDF_SOURCE_NOT_FOUND",
                "failure_reason": "Sectional source file is referenced by V1 extraction but was not found locally for rank extraction.",
                "affected_rows": str(sum(1 for row in sectionals if normalise_source_name(row.get("source_file")) == source)),
                "recommended_repair": "Place the original NSW/ATC sectional PDF under outputs/sectionals/raw/NSW or public/data.",
                "notes": OFFLINE_NOTES,
            }
        )

    tokens: list[dict[str, object]] = []
    for pdf in pdfs:
        pages, method = extract_pdf_text(pdf)
        if not pages:
            failures.append(
                {
                    "source_file": pdf.name,
                    "failure_type": "NO_EXTRACTABLE_PDF_TEXT",
                    "failure_reason": "No text layer or raw printable rank tokens could be extracted from the PDF.",
                    "affected_rows": str(sum(1 for row in sectionals if normalise_source_name(row.get("source_file")) == normalise_source_name(pdf.name))),
                    "recommended_repair": "Use a table-aware PDF extractor or OCR pass that preserves bracketed split ranks.",
                    "notes": OFFLINE_NOTES,
                }
            )
            continue
        source_tokens: list[dict[str, object]] = []
        source_blocks: list[dict[str, object]] = []
        race_meta = source_metadata.get(normalise_source_name(pdf.name), {})
        for page_no, text in pages:
            source_blocks.extend(extract_runner_rank_blocks(text, pdf.name, page_no, method, race_meta))
            source_tokens.extend(extract_rank_tokens(text, pdf.name, page_no, method))
        if source_blocks:
            direct_rank_rows.extend(source_blocks)
            continue
        if not source_tokens:
            failures.append(
                {
                    "source_file": pdf.name,
                    "failure_type": "NO_BRACKET_RANKS_DETECTED",
                    "failure_reason": "PDF text extraction succeeded, but no timing tokens with bracketed positional ranks were detected.",
                    "affected_rows": str(sum(1 for row in sectionals if normalise_source_name(row.get("source_file")) == normalise_source_name(pdf.name))),
                    "recommended_repair": "Improve split-column reconstruction or add OCR/layout extraction for visually embedded rank brackets.",
                    "notes": OFFLINE_NOTES,
                }
            )
        tokens.extend(source_tokens)

    if direct_rank_rows:
        rank_rows = direct_rank_rows
    else:
        assignments, assignment_failures = assign_tokens_to_rows(tokens, sectionals)
        failures.extend(assignment_failures)
        rank_rows = build_rank_rows(assignments)
    transition_rows = build_transition_rows(rank_rows)

    if forensics and not rank_rows:
        rank_hint_sources = [row for row in forensics if clean(row.get("position_data_statement_detected")).upper() == "YES"]
        if rank_hint_sources:
            failures.append(
                {
                    "source_file": ";".join(sorted({clean(row.get("source_file")) for row in rank_hint_sources if row.get("source_file")})),
                    "failure_type": "POSITION_DATA_PRESENT_RANKS_LATENT",
                    "failure_reason": "Forensics confirms position-data statement, but rank brackets remain latent to the available local extraction backends.",
                    "affected_rows": str(len(sectionals)),
                    "recommended_repair": "Run an OCR/table-layout pass that captures visible bracket ranks from the rendered PDF.",
                    "notes": OFFLINE_NOTES,
                }
            )

    write_csv_atomic(OUT_RANKS, rank_rows, RANK_FIELDS)
    write_csv_atomic(OUT_TRANSITIONS, transition_rows, TRANSITION_FIELDS)
    write_csv_atomic(OUT_FAILURES, failures, FAILURE_FIELDS)
    write_summary(sectionals, pdfs, rank_rows, transition_rows)

    print(f"NSW positional rank rows: {len(rank_rows)}")
    print(f"NSW rank transition rows: {len(transition_rows)}")
    print(f"NSW rank failures: {len(failures)}")


if __name__ == "__main__":
    main()
