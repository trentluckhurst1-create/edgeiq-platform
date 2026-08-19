from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw" / "racing-com-visible-v1"
OP_ROOT = ROOT / "data" / "operational" / "racing-com-visible-v1"
FIELDS = ["source_provider","source_method","source_url","meeting_date","venue","meeting_code","race_number","race_distance_metres","runner_name","saddlecloth_number","finish_position","section_start_metres","section_end_metres","section_distance_metres","section_time_seconds","section_rank","cumulative_time_seconds","timing_unit_original","timing_unit_normalised","source_retrieved_at","visible_table_hash","identity_status","unit_semantics_status","validation_status","raw_dir"]
SECTION_RE = re.compile(r"(\d{3,4})m\s*[\u2013\u2014-]\s*((?:\d{3,4})m|Finish)", re.I)
TIME_RE = re.compile(r"(?<!\d)(\d{1,2}(?:\.\d{1,3})?)(?!\d)")
RANK_RE = re.compile(r"(?:^|\D)(\d{1,2})(?:st|nd|rd|th|\)|$)", re.I)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or ["empty"], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def sha_text(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()


def parse_section(label: str) -> tuple[str, str, str]:
    match = SECTION_RE.search(label or "")
    if not match:
        return "", "", ""
    start = match.group(1)
    end = "0" if match.group(2).lower() == "finish" else re.sub(r"\D", "", match.group(2))
    try:
        dist = str(abs(int(start) - int(end)))
    except Exception:
        dist = ""
    return start, end, dist


def parse_time(value: str) -> str:
    if not value:
        return ""
    match = TIME_RE.search(str(value).replace(",", ""))
    if not match:
        return ""
    try:
        seconds = float(match.group(1))
    except Exception:
        return ""
    return f"{seconds:.3f}".rstrip("0").rstrip(".")


def parse_rank(value: str) -> str:
    match = RANK_RE.search(value or "")
    return match.group(1) if match else ""


def runner_from_row(row: dict) -> tuple[str, str, str]:
    values = [str(v).strip() for k, v in row.items() if k not in {"source_url","view","table_index","row_index","meeting_date","venue","race_number","page_title"}]
    for value in values[:6]:
        if value and not SECTION_RE.search(value) and not TIME_RE.fullmatch(value):
            saddle = ""
            name = value
            m = re.match(r"^(\d{1,2})\s+(.+)$", value)
            if m:
                saddle, name = m.group(1), m.group(2).strip()
            return name, saddle, ""
    return "", "", ""


def normalise_row(row: dict, raw_dir: str, table_hash: str) -> list[dict]:
    out = []
    runner, saddle, finish = runner_from_row(row)
    for key, value in row.items():
        start, end, dist = parse_section(key)
        if not start:
            continue
        seconds = parse_time(str(value))
        rank = parse_rank(str(value))
        time_float = float(seconds) if seconds else 0.0
        validation = "PASS" if runner and seconds and time_float > 0 and (dist != "200" or 7 <= time_float <= 18) and (dist == "200" or 4 <= time_float <= 60) else "REJECTED_INCOMPLETE_OR_IMPLAUSIBLE"
        out.append({
            "source_provider": "RACING_COM",
            "source_method": "VISIBLE_PUBLIC_PAGE",
            "source_url": row.get("source_url", ""),
            "meeting_date": row.get("meeting_date", ""),
            "venue": row.get("venue", ""),
            "meeting_code": "",
            "race_number": row.get("race_number", ""),
            "race_distance_metres": "",
            "runner_name": runner,
            "saddlecloth_number": saddle,
            "finish_position": finish,
            "section_start_metres": start,
            "section_end_metres": end,
            "section_distance_metres": dist,
            "section_time_seconds": seconds,
            "section_rank": rank,
            "cumulative_time_seconds": "",
            "timing_unit_original": "visible page split range and displayed seconds",
            "timing_unit_normalised": "section_start_metres_to_section_end_metres_from_finish",
            "source_retrieved_at": now_utc(),
            "visible_table_hash": table_hash,
            "identity_status": "MATCHED" if runner else "UNMATCHED",
            "unit_semantics_status": "PROVEN" if start and end and seconds else "UNPROVEN",
            "validation_status": validation,
            "raw_dir": raw_dir,
        })
    return out


def normalise(raw_root: Path = RAW_ROOT) -> dict:
    rows = []
    rejected = []
    for csv_path in raw_root.rglob("visible_table.csv"):
        raw_dir = str(csv_path.parent.relative_to(ROOT))
        table_json = csv_path.parent / "visible_table.json"
        table_hash = sha_text(table_json.read_text(encoding="utf-8", errors="ignore")) if table_json.exists() else ""
        for source_row in read_csv(csv_path):
            parsed = normalise_row(source_row, raw_dir, table_hash)
            if parsed:
                rows.extend(parsed)
            elif any(SECTION_RE.search(str(k)) for k in source_row.keys()):
                rejected.append({"raw_dir": raw_dir, "reason": "SECTION_COLUMNS_PRESENT_BUT_UNPARSED", "row_index": source_row.get("row_index", "")})
    valid = [r for r in rows if r["identity_status"] == "MATCHED" and r["unit_semantics_status"] == "PROVEN" and r["validation_status"] == "PASS"]
    write_csv(OP_ROOT / "normalised_visible_sectionals_v1.csv", rows, FIELDS)
    write_csv(OP_ROOT / "normalised_visible_sectionals_rejected_v1.csv", rejected)
    summary = {"normalised_rows": len(rows), "valid_rows": len(valid), "rejected_rows": len(rows) - len(valid) + len(rejected), "raw_tables_scanned": len(list(raw_root.rglob("visible_table.csv"))), "status": "PASS" if valid else "NO_VALID_VISIBLE_SECTIONALS"}
    write_json(OP_ROOT / "normalised_visible_sectionals_summary_v1.json", summary)
    print(json.dumps(summary, indent=2))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", default=str(RAW_ROOT))
    args = parser.parse_args()
    summary = normalise(Path(args.raw_root))
    return 0 if summary.get("status") in {"PASS", "NO_VALID_VISIBLE_SECTIONALS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
