from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "public" / "data" / "edgeiq_ui_column_data_audit_v1.txt"

SEARCH_DIRS = [
    ROOT / "src" / "edgeiq-os" / "services",
    ROOT / "src" / "edgeiq-os" / "race",
    ROOT / "public" / "data",
]


FIELD_GROUPS: list[tuple[str, list[tuple[str, list[str], str]]]] = [
    (
        "FORM main columns",
        [
            ("Date", ["date", "race_date"], "KEEP IN MAIN UI"),
            ("Track", ["track", "meeting"], "KEEP IN MAIN UI"),
            ("Distance", ["distance", "dist"], "KEEP IN MAIN UI"),
            ("Class", ["raceClass", "class", "race_class", "className"], "KEEP IN MAIN UI"),
            ("Track Condition", ["condition", "trackCondition", "track_condition", "going"], "KEEP IN MAIN UI"),
            ("Barrier", ["barrier", "bar"], "KEEP IN MAIN UI"),
            ("Weight", ["weight", "wgt"], "KEEP IN MAIN UI"),
            ("Jockey", ["jockey"], "KEEP IN MAIN UI"),
            ("SP", ["sp", "starting_price"], "KEEP IN MAIN UI"),
            ("Finish", ["finish", "fin", "position", "pos"], "KEEP IN MAIN UI"),
            ("Margin", ["margin"], "KEEP IN MAIN UI"),
            ("EPI", ["edgeiqRunRating", "runRating", "epi", "EPI"], "KEEP IN MAIN UI"),
            ("ERI", ["edgeiqRaceStrength", "raceStrength", "eri", "ERI"], "KEEP IN MAIN UI"),
            ("ESI Overall", ["edgeiq", "esi", "ESI", "lengthsVsStandard", "lengths_vs_standard"], "SAFE FALLBACK ONLY"),
            ("Reference Quality", ["assignment", "score", "importance", "reference_quality"], "KEEP IN MAIN UI"),
        ],
    ),
    (
        "FORM expanded detail fields",
        [
            ("Rail Position", ["rail", "rail_position"], "MOVE TO DETAIL"),
            ("Settling Position", ["settlingPosition", "settling", "jump"], "HIDE UNTIL DATA CONNECTED"),
            ("600m Position", ["m600", "position600m", "600m_position"], "HIDE UNTIL DATA CONNECTED"),
            ("400m Position", ["m400", "position400m", "400m_position"], "HIDE UNTIL DATA CONNECTED"),
            ("200m Position", ["m200", "position200m", "200m_position"], "HIDE UNTIL DATA CONNECTED"),
            ("Stewards Report Notes", ["stewards", "stewardsReport", "stewards_notes"], "HIDE UNTIL DATA CONNECTED"),
            ("Pressure", ["pressure", "pressureRating"], "MOVE TO DETAIL"),
            ("Tempo", ["tempo", "tempoRating"], "MOVE TO DETAIL"),
            ("Field Size", ["fieldSize", "field_size", "runners"], "MOVE TO DETAIL"),
        ],
    ),
    (
        "RESULTS fields",
        [
            ("Finish", ["finish", "fin", "position", "pos"], "KEEP IN MAIN UI"),
            ("Runner", ["runner", "horse", "runnerName"], "CONNECT DATA SOURCE"),
            ("Barrier", ["barrier", "bar"], "KEEP IN MAIN UI"),
            ("Weight", ["weight", "wgt"], "KEEP IN MAIN UI"),
            ("Jockey", ["jockey"], "KEEP IN MAIN UI"),
            ("Trainer", ["trainer"], "CONNECT DATA SOURCE"),
            ("SP", ["sp", "starting_price"], "KEEP IN MAIN UI"),
            ("Margin", ["margin"], "KEEP IN MAIN UI"),
            ("EPI", ["edgeiqRunRating", "runRating", "epi"], "KEEP IN MAIN UI"),
            ("ERI", ["edgeiqRaceStrength", "raceStrength", "eri"], "KEEP IN MAIN UI"),
            ("ESI", ["esi", "lengthsVsStandard", "lengths_vs_standard"], "SAFE FALLBACK ONLY"),
            ("Stewards", ["stewards", "stewardsReport", "stewards_notes"], "HIDE UNTIL DATA CONNECTED"),
        ],
    ),
    (
        "MARKET future fields",
        [
            ("Opening Price", ["open", "opening_price"], "CONNECT DATA SOURCE"),
            ("Current Price", ["current", "current_price", "market"], "CONNECT DATA SOURCE"),
            ("High", ["high", "highest"], "CONNECT DATA SOURCE"),
            ("Low", ["low", "lowest"], "CONNECT DATA SOURCE"),
            ("Fair Price", ["fair", "fair_price"], "CONNECT DATA SOURCE"),
            ("Overlay / Edge", ["edge", "overlay"], "CONNECT DATA SOURCE"),
            ("Fluctuation history", ["fluc", "fluctuation", "price_history"], "CONNECT DATA SOURCE"),
            ("Firm / Drift movement state", ["firm", "drift", "movement"], "CONNECT DATA SOURCE"),
        ],
    ),
    (
        "MAP future fields",
        [
            ("Expected settling position", ["settling", "expected_position", "map_position"], "CONNECT DATA SOURCE"),
            ("Run style", ["runStyle", "run_style", "speedProfile"], "CONNECT DATA SOURCE"),
            ("Pressure", ["pressure", "pressureRating"], "KEEP IN MAIN UI"),
            ("Tempo", ["tempo", "tempoRating"], "KEEP IN MAIN UI"),
            ("Rail", ["rail"], "KEEP IN MAIN UI"),
            ("Track condition", ["trackCondition", "track_condition", "condition"], "KEEP IN MAIN UI"),
            ("Weather / wind", ["weather", "wind"], "CONNECT DATA SOURCE"),
            ("Track bias / track intelligence fields", ["bias", "trackSignature", "track_intelligence"], "CONNECT DATA SOURCE"),
        ],
    ),
    (
        "LAB future fields",
        [
            ("Jockey", ["jockey"], "CONNECT DATA SOURCE"),
            ("Trainer", ["trainer"], "CONNECT DATA SOURCE"),
            ("Jockey/trainer combination", ["partnership", "jockey_trainer", "combination"], "CONNECT DATA SOURCE"),
            ("Runs/rides sample size", ["sample", "rides", "runs", "starts"], "CONNECT DATA SOURCE"),
            ("Wins", ["wins"], "CONNECT DATA SOURCE"),
            ("Places", ["places"], "CONNECT DATA SOURCE"),
            ("Strike rate", ["strike_rate", "win_rate"], "CONNECT DATA SOURCE"),
            ("A/E", ["a_e", "ae", "actual_expected"], "CONNECT DATA SOURCE"),
            ("POT", ["pot", "profit_on_turnover"], "CONNECT DATA SOURCE"),
            ("ROI", ["roi"], "CONNECT DATA SOURCE"),
            ("IV", ["iv", "impact_value"], "CONNECT DATA SOURCE"),
            ("Last 50", ["last50", "last_50"], "CONNECT DATA SOURCE"),
            ("Last 100", ["last100", "last_100"], "CONNECT DATA SOURCE"),
            ("Last 200", ["last200", "last_200"], "CONNECT DATA SOURCE"),
            ("Season", ["season"], "CONNECT DATA SOURCE"),
            ("Last season", ["last_season"], "CONNECT DATA SOURCE"),
            ("12 months", ["12_month", "last_12"], "CONNECT DATA SOURCE"),
            ("24 months", ["24_month", "last_24"], "CONNECT DATA SOURCE"),
            ("Lifetime", ["lifetime", "career"], "CONNECT DATA SOURCE"),
            ("Track", ["track"], "CONNECT DATA SOURCE"),
            ("Distance", ["distance", "dist"], "CONNECT DATA SOURCE"),
            ("Condition", ["condition", "going"], "CONNECT DATA SOURCE"),
            ("Class", ["class", "raceClass"], "CONNECT DATA SOURCE"),
            ("Run style", ["runStyle", "run_style"], "CONNECT DATA SOURCE"),
        ],
    ),
]


def iter_source_files() -> list[Path]:
    files: list[Path] = []
    for directory in SEARCH_DIRS:
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            lower_parts = {part.lower() for part in path.parts}
            lower_name = path.name.lower()
            if "node_modules" in lower_parts or "dist" in lower_parts:
                continue
            if "checkpoints" in lower_parts or "backups" in lower_parts:
                continue
            if "checkpoint" in lower_name or "backup" in lower_name:
                continue
            if path.suffix.lower() in {".ts", ".tsx", ".csv"}:
                files.append(path)
    return files


def read_csv_headers(path: Path) -> list[str]:
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            sample = handle.read(4096)
            handle.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            except Exception:
                dialect = csv.excel
            reader = csv.reader(handle, dialect)
            return next(reader, [])
    except Exception:
        return []


def source_index(files: list[Path]) -> tuple[dict[Path, str], dict[Path, list[str]]]:
    text_by_file: dict[Path, str] = {}
    headers_by_file: dict[Path, list[str]] = {}
    for path in files:
        if path.suffix.lower() == ".csv":
            headers_by_file[path] = read_csv_headers(path)
        else:
            try:
                text_by_file[path] = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                text_by_file[path] = ""
    return text_by_file, headers_by_file


def find_matches(terms: list[str], text_by_file: dict[Path, str], headers_by_file: dict[Path, list[str]]):
    sources: dict[str, set[str]] = {}
    matched: set[str] = set()
    for term in terms:
        term_lower = term.lower()
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        for path, text in text_by_file.items():
            if pattern.search(text) or term_lower in text.lower():
                sources.setdefault(str(path.relative_to(ROOT)), set()).add(term)
                matched.add(term)
        for path, headers in headers_by_file.items():
            for header in headers:
                if term_lower == header.lower() or term_lower in header.lower():
                    sources.setdefault(str(path.relative_to(ROOT)), set()).add(header)
                    matched.add(header)
    return sources, matched


def recommendation(found: bool, default: str) -> str:
    if not found and default in {"KEEP IN MAIN UI", "MOVE TO DETAIL", "SAFE FALLBACK ONLY"}:
        return "HIDE UNTIL DATA CONNECTED"
    return default if found else "CONNECT DATA SOURCE"


def main() -> None:
    files = iter_source_files()
    text_by_file, headers_by_file = source_index(files)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("EDGEIQ UI COLUMN DATA AUDIT V1")
    lines.append(f"ROOT: {ROOT}")
    lines.append(f"FILES SCANNED: {len(files)}")
    lines.append("")

    for group, fields in FIELD_GROUPS:
        lines.append(f"## {group}")
        lines.append("")
        for field, terms, default_recommendation in fields:
            sources, matched = find_matches(terms, text_by_file, headers_by_file)
            found = bool(sources)
            lines.append(f"REQUIRED FIELD: {field}")
            lines.append(f"FOUND: {'yes' if found else 'no'}")
            if found:
                lines.append("SOURCE FILE(S):")
                sorted_sources = sorted(sources)
                for source in sorted_sources[:12]:
                    lines.append(f"- {source}")
                if len(sorted_sources) > 12:
                    lines.append(f"- ... plus {len(sorted_sources) - 12} more")
                lines.append("MATCHED COLUMN/FIELD NAME(S):")
                sorted_matched = sorted(matched)
                for name in sorted_matched[:12]:
                    lines.append(f"- {name}")
                if len(sorted_matched) > 12:
                    lines.append(f"- ... plus {len(sorted_matched) - 12} more")
            else:
                lines.append("SOURCE FILE(S):")
                lines.append("- None found")
                lines.append("MATCHED COLUMN/FIELD NAME(S):")
                lines.append("- None found")
            lines.append(f"RECOMMENDATION: {recommendation(found, default_recommendation)}")
            lines.append("")

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
