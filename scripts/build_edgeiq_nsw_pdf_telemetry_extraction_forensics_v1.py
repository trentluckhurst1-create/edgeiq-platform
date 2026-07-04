from __future__ import annotations

import csv
import re
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from edgeiq_memory_safe_io import write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUT_FORENSICS = DATA / "edgeiq_nsw_pdf_telemetry_forensics_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_nsw_pdf_telemetry_summary_v1.csv"
OUT_SECTIONALS = DATA / "edgeiq_nsw_pdf_extracted_sectionals_v1.csv"
OUT_FAILURES = DATA / "edgeiq_nsw_pdf_extraction_failures_v1.csv"

FORENSICS_FIELDS = [
    "source_file",
    "pages_detected",
    "races_detected",
    "horses_detected",
    "split_rows_detected",
    "rank_rows_detected",
    "distance_travelled_rows",
    "top_speed_rows",
    "position_data_statement_detected",
    "swiss_timing_detected",
    "schema_consistency_score",
    "pdf_extraction_quality_grade",
    "recommended_next_step",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

SECTIONAL_FIELDS = [
    "race_date",
    "track",
    "race_no",
    "race_name",
    "distance",
    "track_rating",
    "weather",
    "rail_position",
    "horse",
    "tab_no",
    "barrier",
    "jockey",
    "finish_position",
    "top_speed",
    "fastest_200m",
    "last_600m",
    "distance_travelled",
    "split_marker",
    "split_time",
    "sectional_time",
    "rank_at_split",
    "official_finish_time",
    "source_file",
    "page_no",
    "lineage_reference",
    "extraction_confidence",
    "safe_for_nsw_temporal_research",
    "safe_for_nsw_shadow_research",
    "notes",
]

FAILURE_FIELDS = [
    "source_file",
    "failure_type",
    "failure_reason",
    "affected_pages",
    "recommended_repair",
    "notes",
]

GRADE_LABEL = {
    "A": "ELITE_NSW_PDF_TELEMETRY",
    "B": "STRONG_NSW_PDF_TELEMETRY",
    "C": "USABLE_NSW_PDF_TELEMETRY",
    "D": "WEAK_NSW_PDF_TELEMETRY",
    "F": "FAILED_NSW_PDF_TELEMETRY",
}


def clean(value: object) -> str:
    return str(value or "").strip()


def upper(value: object) -> str:
    return clean(value).upper()


def normalise_spaces(value: object) -> str:
    return re.sub(r"\s+", " ", clean(value)).strip()


def parse_float(value: object) -> float | None:
    text = clean(value).replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def discover_pdfs() -> list[Path]:
    roots = [
        ROOT / "outputs" / "sectionals" / "raw" / "NSW",
        DATA,
        ROOT / "dashboard" / "racing-dashboard" / "public" / "data",
        ROOT,
    ]
    candidates: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.pdf"):
            text = str(path).lower()
            if "\\node_modules\\" in text or "\\dist\\" in text or "\\.git\\" in text:
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
                pages.append((index, page.extract_text(x_tolerance=1, y_tolerance=3) or ""))
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


def extract_raw_strings(path: Path) -> list[tuple[int, str]]:
    try:
        raw = path.read_bytes()
    except Exception:
        return []
    chunks = re.findall(rb"[\x20-\x7E]{4,}", raw)
    text = "\n".join(chunk.decode("latin-1", errors="ignore") for chunk in chunks)
    text = text.replace("\\r", "\n").replace("\\n", "\n")
    return [(1, text)] if text else []


def extract_pages(path: Path) -> tuple[list[tuple[int, str]], str]:
    for method, extractor in (
        ("pdfplumber", extract_with_pdfplumber),
        ("pypdf", extract_with_pypdf),
        ("raw_pdf_strings", extract_raw_strings),
    ):
        pages = extractor(path)
        if any(clean(text) for _, text in pages):
            return pages, method
    return [], "none"


def infer_race_date(path: Path, text: str) -> str:
    for pattern in (r"\b(\d{2})[/-](\d{2})[/-](20\d{2})\b", r"\b(20\d{2})[/-](\d{2})[/-](\d{2})\b"):
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            try:
                if len(groups[0]) == 4:
                    return datetime(int(groups[0]), int(groups[1]), int(groups[2])).strftime("%Y-%m-%d")
                return datetime(int(groups[2]), int(groups[1]), int(groups[0])).strftime("%Y-%m-%d")
            except ValueError:
                pass
    name_match = re.search(r"(\d{2})(\d{2})([A-Z])", path.stem.upper())
    if name_match:
        day, month, _ = name_match.groups()
        year = datetime.now().year
        try:
            return datetime(year, int(month), int(day)).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


def infer_track(path: Path, text: str) -> str:
    known = {
        "FM": "WARWICK FARM",
        "RANDWICK": "RANDWICK",
        "ROSEHILL": "ROSEHILL",
        "WARWICK FARM": "WARWICK FARM",
        "CANTERBURY": "CANTERBURY",
        "KENSINGTON": "KENSINGTON",
    }
    stem = path.stem.upper()
    for token, track in known.items():
        if token in stem or token in upper(text):
            return track
    match = re.search(r"\b(RANDWICK|ROSEHILL|WARWICK FARM|CANTERBURY|KENSINGTON|NEWCASTLE|GOSFORD|HAWKESBURY)\b", upper(text))
    return match.group(1) if match else ""


def find_value(patterns: list[str], text: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return normalise_spaces(match.group(1))
    return ""


def page_metadata(path: Path, page_text: str, full_text: str) -> dict[str, str]:
    text = f"{page_text}\n{full_text[:4000]}"
    race_no = find_value([r"\bRace\s+(\d{1,2})\b", r"\bR(?:ace)?\s*No\.?\s*(\d{1,2})\b"], text)
    distance = find_value([r"\b(\d{3,4})\s*m\b", r"\bDistance\s*[:\-]?\s*(\d{3,4})"], text)
    return {
        "race_date": infer_race_date(path, text),
        "track": infer_track(path, text),
        "race_no": race_no,
        "race_name": find_value([r"Race\s+\d+\s+[-–]\s+([A-Z0-9 ,'()&./-]+)", r"\bRace Name\s*[:\-]?\s*([A-Z0-9 ,'()&./-]+)"], text)[:120],
        "distance": distance,
        "track_rating": find_value([r"Track Rating\s*[:\-]?\s*([A-Za-z0-9 +.-]+)", r"\bTrack\s*[:\-]?\s*(Good\s*\d|Soft\s*\d|Heavy\s*\d|Synthetic)"], text),
        "weather": find_value([r"Weather\s*[:\-]?\s*([A-Za-z0-9 +.-]+)"], text),
        "rail_position": find_value([r"Rail\s*(?:Position)?\s*[:\-]?\s*([A-Za-z0-9 +./-]+)"], text),
    }


def parse_ranked_time(value: str) -> tuple[str, str]:
    text = clean(value)
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)(?:\s*\((\d+)\))?", text)
    if not match:
        return "", ""
    return match.group(1), match.group(2) or ""


def parse_runner_lines(page_text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw_line in page_text.splitlines():
        line = normalise_spaces(raw_line)
        if len(line) < 12:
            continue
        if not re.search(r"\d+\.\d+", line):
            continue
        if not re.search(r"[A-Za-z]{3,}", line):
            continue
        lower = line.lower()
        if any(skip in lower for skip in ("track rating", "swiss timing", "timing is based", "fastest last")):
            continue
        tab = ""
        finish = ""
        horse = ""
        jockey = ""
        barrier = ""
        front = re.match(r"^\s*(\d{1,2})\s+([A-Za-z][A-Za-z0-9 '\-().]+?)\s{2,}", raw_line)
        if front:
            tab = front.group(1)
            horse = normalise_spaces(front.group(2))
        else:
            compact = re.match(r"^\s*(\d{1,2})\s+([A-Za-z][A-Za-z0-9 '\-().]+?)(?:\s+\d|\s+[0-9]+\.)", line)
            if compact:
                tab = compact.group(1)
                horse = normalise_spaces(compact.group(2))
        if not horse:
            words_before_numbers = re.split(r"\s+\d+\.\d+", line, maxsplit=1)[0]
            horse_match = re.match(r"^\s*(?:\d{1,2}\s+)?([A-Za-z][A-Za-z0-9 '\-().]{2,})", words_before_numbers)
            horse = normalise_spaces(horse_match.group(1)) if horse_match else ""
        if not horse or len(horse) > 80:
            continue
        finish_match = re.search(r"\b(?:F(?:in)?|Pos|Place)?\s*(\d{1,2})(?:st|nd|rd|th)?\b", line)
        if finish_match and finish_match.start() < 10:
            finish = finish_match.group(1)
        numbers = re.findall(r"\d+(?:\.\d+)?(?:\s*\(\d+\))?", line)
        if len(numbers) < 3:
            continue
        rows.append(
            {
                "line": line,
                "horse": horse,
                "tab_no": tab,
                "barrier": barrier,
                "jockey": jockey,
                "finish_position": finish,
                "numbers": "|".join(numbers),
            }
        )
    return rows


def split_rows_from_runner(runner: dict[str, str], meta: dict[str, str], path: Path, page_no: int, method: str) -> list[dict[str, object]]:
    numbers = [number.strip() for number in runner.get("numbers", "").split("|") if number.strip()]
    parsed = [parse_ranked_time(number) for number in numbers]
    parsed = [(time_value, rank) for time_value, rank in parsed if time_value]
    if not parsed:
        return []
    official_finish = parsed[-1][0] if parsed else ""
    top_speed = ""
    fastest_200m = ""
    last_600m = ""
    distance_travelled = ""
    if len(parsed) >= 4:
        top_speed = parsed[-4][0]
        fastest_200m = parsed[-3][0]
        last_600m = parsed[-2][0]
        distance_travelled = parsed[-1][0] if len(parsed[-1][0]) >= 4 else ""
    split_candidates = parsed[:-4] if len(parsed) >= 7 else parsed[:-1]
    markers = ["200", "400", "600", "800", "1000", "1200", "1400", "1600", "1800", "2000", "2200", "2400"]
    rows: list[dict[str, object]] = []
    for index, (time_value, rank) in enumerate(split_candidates):
        marker = markers[index] if index < len(markers) else f"SPLIT_{index + 1}"
        confidence = 58.0
        if rank:
            confidence += 14.0
        if method != "raw_pdf_strings":
            confidence += 14.0
        if meta.get("track") and meta.get("race_date"):
            confidence += 8.0
        confidence = min(92.0, confidence)
        rows.append(
            {
                "race_date": meta.get("race_date", ""),
                "track": meta.get("track", ""),
                "race_no": meta.get("race_no", ""),
                "race_name": meta.get("race_name", ""),
                "distance": meta.get("distance", ""),
                "track_rating": meta.get("track_rating", ""),
                "weather": meta.get("weather", ""),
                "rail_position": meta.get("rail_position", ""),
                "horse": runner.get("horse", ""),
                "tab_no": runner.get("tab_no", ""),
                "barrier": runner.get("barrier", ""),
                "jockey": runner.get("jockey", ""),
                "finish_position": runner.get("finish_position", ""),
                "top_speed": top_speed,
                "fastest_200m": fastest_200m,
                "last_600m": last_600m,
                "distance_travelled": distance_travelled,
                "split_marker": marker,
                "split_time": time_value,
                "sectional_time": time_value,
                "rank_at_split": rank,
                "official_finish_time": official_finish,
                "source_file": path.name,
                "page_no": page_no,
                "lineage_reference": f"{path.name}|page:{page_no}|method:{method}|runner:{runner.get('horse', '')}",
                "extraction_confidence": f"{confidence:.2f}",
                "safe_for_nsw_temporal_research": "YES" if confidence >= 60 else "NO",
                "safe_for_nsw_shadow_research": "YES" if confidence >= 78 and rank else "NO",
                "notes": "NSW PDF sectional extraction forensics only. No predictions, ratings, overlays, live modelling, or execution.",
            }
        )
    return rows


def grade_file(pages: int, races: int, horses: int, splits: int, rank_rows: int, distance_rows: int, top_speed_rows: int, position_statement: bool, swiss: bool, method: str) -> tuple[str, float]:
    if pages == 0:
        return "F", 0.0
    score = 20.0
    score += min(18.0, races * 6.0)
    score += min(18.0, horses / 5.0)
    score += min(18.0, splits / 20.0)
    score += min(10.0, rank_rows / 15.0)
    score += 5.0 if distance_rows else 0.0
    score += 5.0 if top_speed_rows else 0.0
    score += 4.0 if position_statement else 0.0
    score += 4.0 if swiss else 0.0
    if method == "raw_pdf_strings":
        score -= 12.0
    if score >= 86:
        return "A", score
    if score >= 74:
        return "B", score
    if score >= 58:
        return "C", score
    if score >= 38:
        return "D", score
    return "F", score


def main() -> None:
    pdfs = discover_pdfs()
    forensics_rows: list[dict[str, object]] = []
    sectional_rows: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []

    if not pdfs:
        failures.append(
            {
                "source_file": "NO_LOCAL_NSW_PDF_FOUND",
                "failure_type": "MISSING_INPUT_PDF",
                "failure_reason": "No NSW/ATC sectional PDFs were found in outputs/sectionals/raw/NSW, public/data, or repo root.",
                "affected_pages": 0,
                "recommended_repair": "Copy 0605W_FM-1.pdf or NSW/ATC sectional PDFs into the repo/public data path and rerun.",
                "notes": "Offline forensics only; no scraping attempted.",
            }
        )

    for pdf in pdfs:
        pages, method = extract_pages(pdf)
        if not pages:
            failures.append(
                {
                    "source_file": pdf.name,
                    "failure_type": "PDF_TEXT_EXTRACTION_FAILED",
                    "failure_reason": "No readable text was extracted. Install pdfplumber/pypdf locally or provide text-extractable PDF.",
                    "affected_pages": 0,
                    "recommended_repair": "Use a text-based ATC/Racing NSW sectional PDF or install a PDF text extraction library.",
                    "notes": "No values inferred from unreadable PDF.",
                }
            )
            grade, consistency = "F", 0.0
            forensics_rows.append(
                {
                    "source_file": pdf.name,
                    "pages_detected": 0,
                    "races_detected": 0,
                    "horses_detected": 0,
                    "split_rows_detected": 0,
                    "rank_rows_detected": 0,
                    "distance_travelled_rows": 0,
                    "top_speed_rows": 0,
                    "position_data_statement_detected": "NO",
                    "swiss_timing_detected": "NO",
                    "schema_consistency_score": "0.00",
                    "pdf_extraction_quality_grade": GRADE_LABEL[grade],
                    "recommended_next_step": "Repair PDF text extraction before telemetry use.",
                    "notes": "Failed NSW PDF telemetry forensics. No live modelling or execution.",
                }
            )
            continue
        full_text = "\n".join(text for _, text in pages)
        position_statement = "timing is based on position data" in full_text.lower()
        swiss = "swiss timing" in full_text.lower()
        file_rows: list[dict[str, object]] = []
        races_seen: set[str] = set()
        horses_seen: set[str] = set()
        for page_no, page_text in pages:
            meta = page_metadata(pdf, page_text, full_text)
            if meta.get("race_no"):
                races_seen.add(clean(meta.get("race_no")))
            runner_rows = parse_runner_lines(page_text)
            for runner in runner_rows:
                horses_seen.add(upper(runner.get("horse")))
                rows = split_rows_from_runner(runner, meta, pdf, page_no, method)
                file_rows.extend(rows)
        sectional_rows.extend(file_rows)
        rank_rows = sum(1 for row in file_rows if clean(row.get("rank_at_split")))
        distance_rows = sum(1 for row in file_rows if clean(row.get("distance_travelled")))
        top_speed_rows = sum(1 for row in file_rows if clean(row.get("top_speed")))
        grade, consistency = grade_file(
            len(pages),
            len(races_seen),
            len(horses_seen),
            len(file_rows),
            rank_rows,
            distance_rows,
            top_speed_rows,
            position_statement,
            swiss,
            method,
        )
        if not file_rows:
            failures.append(
                {
                    "source_file": pdf.name,
                    "failure_type": "NO_SECTIONAL_ROWS_PARSED",
                    "failure_reason": "PDF text was extracted but runner split rows were not confidently parsed.",
                    "affected_pages": len(pages),
                    "recommended_repair": "Inspect PDF text layout and add a source-specific row parser for this ATC report template.",
                    "notes": f"extraction_method={method}",
                }
            )
        forensics_rows.append(
            {
                "source_file": pdf.name,
                "pages_detected": len(pages),
                "races_detected": len(races_seen),
                "horses_detected": len(horses_seen),
                "split_rows_detected": len(file_rows),
                "rank_rows_detected": rank_rows,
                "distance_travelled_rows": distance_rows,
                "top_speed_rows": top_speed_rows,
                "position_data_statement_detected": "YES" if position_statement else "NO",
                "swiss_timing_detected": "YES" if swiss else "NO",
                "schema_consistency_score": f"{consistency:.2f}",
                "pdf_extraction_quality_grade": GRADE_LABEL[grade],
                "recommended_next_step": "Validate parsed rows against official PDF layout before NSW shadow research." if grade in {"A", "B", "C"} else "Improve PDF parsing/template extraction before research use.",
                "notes": f"NSW PDF telemetry forensics only. extraction_method={method}. No VIC/QLD merge, modelling, ratings, overlays, or execution.",
            }
        )

    grades = Counter(clean(row.get("pdf_extraction_quality_grade")) for row in forensics_rows)
    summary_rows = [
        {"metric": "nsw_pdf_files_discovered", "value": len(pdfs)},
        {"metric": "forensic_rows", "value": len(forensics_rows)},
        {"metric": "sectional_rows_extracted", "value": len(sectional_rows)},
        {"metric": "extraction_failures", "value": len(failures)},
        {"metric": "pages_detected", "value": sum(int(row.get("pages_detected") or 0) for row in forensics_rows)},
        {"metric": "races_detected", "value": sum(int(row.get("races_detected") or 0) for row in forensics_rows)},
        {"metric": "horses_detected", "value": sum(int(row.get("horses_detected") or 0) for row in forensics_rows)},
        {"metric": "split_rows_detected", "value": sum(int(row.get("split_rows_detected") or 0) for row in forensics_rows)},
        {"metric": "rank_rows_detected", "value": sum(int(row.get("rank_rows_detected") or 0) for row in forensics_rows)},
        {"metric": "position_data_statement_detected_files", "value": sum(1 for row in forensics_rows if row.get("position_data_statement_detected") == "YES")},
        {"metric": "swiss_timing_detected_files", "value": sum(1 for row in forensics_rows if row.get("swiss_timing_detected") == "YES")},
        {"metric": "grade_A_elite", "value": grades.get(GRADE_LABEL["A"], 0)},
        {"metric": "grade_B_strong", "value": grades.get(GRADE_LABEL["B"], 0)},
        {"metric": "grade_C_usable", "value": grades.get(GRADE_LABEL["C"], 0)},
        {"metric": "grade_D_weak", "value": grades.get(GRADE_LABEL["D"], 0)},
        {"metric": "grade_F_failed", "value": grades.get(GRADE_LABEL["F"], 0)},
        {"metric": "safe_for_nsw_temporal_research_yes", "value": sum(1 for row in sectional_rows if row.get("safe_for_nsw_temporal_research") == "YES")},
        {"metric": "safe_for_nsw_shadow_research_yes", "value": sum(1 for row in sectional_rows if row.get("safe_for_nsw_shadow_research") == "YES")},
        {"metric": "merged_into_vic_or_qld", "value": "NO"},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "offline_research_only", "value": "YES"},
    ]

    write_csv_atomic(OUT_FORENSICS, forensics_rows, FORENSICS_FIELDS)
    write_csv_atomic(OUT_SUMMARY, summary_rows, SUMMARY_FIELDS)
    write_csv_atomic(OUT_SECTIONALS, sectional_rows, SECTIONAL_FIELDS)
    write_csv_atomic(OUT_FAILURES, failures, FAILURE_FIELDS)

    print("=" * 88)
    print("EDGEIQ NSW PDF TELEMETRY EXTRACTION FORENSICS V1")
    print("=" * 88)
    for row in summary_rows:
        print(f"{row['metric']}: {row['value']}")
    print(f"saved: {OUT_FORENSICS}")
    print(f"saved: {OUT_SUMMARY}")
    print(f"saved: {OUT_SECTIONALS}")
    print(f"saved: {OUT_FAILURES}")


if __name__ == "__main__":
    main()
