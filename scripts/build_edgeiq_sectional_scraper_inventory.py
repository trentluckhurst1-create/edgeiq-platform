from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_sectional_scraper_inventory.csv"

FIELDS = [
    "file_path",
    "file_name",
    "file_type",
    "purpose_guess",
    "rows_if_csv",
    "last_modified",
    "status",
]

PATTERNS = ("sectional", "racingcom", "racing_com", "split", "speed", "tempo")
SKIP_PARTS = {"node_modules", "dist", ".git", "__pycache__"}


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"", "-", "nan", "none", "null", "undefined"} else text


def purpose_guess(path: Path) -> str:
    name = path.name.lower()
    if path.suffix.lower() == ".py":
        if "probe" in name or "discover" in name:
            return "source discovery/probe script"
        if "downloader" in name or "harvest" in name or "backfill" in name:
            return "scraper/harvest script"
        if "parser" in name or "ingestion" in name:
            return "parser/ingestion script"
        if "audit" in name or "diagnostic" in name:
            return "audit/diagnostic script"
        if "engine" in name or "warehouse" in name or "master" in name:
            return "sectional transform engine"
        return "sectional-related script"
    if path.suffix.lower() == ".csv":
        if "diagnostic" in name or "audit" in name or "summary" in name:
            return "diagnostic output csv"
        if "warehouse" in name or "master" in name or "memory" in name:
            return "sectional warehouse csv"
        if "schema" in name or "catalogue" in name:
            return "canonical scaffold csv"
        return "sectional-related csv"
    if path.suffix.lower() in {".json", ".txt", ".html"}:
        return "cache/debug/source artifact"
    return "sectional-related artifact"


def rows_if_csv(path: Path) -> str:
    if path.suffix.lower() != ".csv":
        return ""
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            next(reader, None)
            return str(sum(1 for row in reader if any(clean(cell) for cell in row)))
    except Exception:
        return ""


def status(path: Path) -> str:
    if path.suffix.lower() == ".py" and "patch" in path.name.lower():
        return "LEGACY_PATCH_SCRIPT"
    if path.suffix.lower() == ".csv" and rows_if_csv(path) == "0":
        return "EMPTY_OUTPUT"
    if "backup" in str(path).lower() or "broken" in str(path).lower():
        return "BACKUP_OR_LEGACY"
    return "DETECTED"


def detected_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part.lower() in SKIP_PARTS for part in path.parts):
            continue
        if any(pattern in path.name.lower() for pattern in PATTERNS):
            files.append(path)
    return sorted(files, key=lambda item: str(item).lower())


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{int(datetime.now().timestamp() * 1000)}.tmp")
    try:
        with tmp.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        tmp.replace(path)
    except PermissionError:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)


def main() -> None:
    rows: list[dict[str, object]] = []
    for path in detected_files():
        stat = path.stat()
        rows.append({
            "file_path": str(path.relative_to(ROOT)),
            "file_name": path.name,
            "file_type": path.suffix.lower().lstrip(".") or "unknown",
            "purpose_guess": purpose_guess(path),
            "rows_if_csv": rows_if_csv(path),
            "last_modified": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds"),
            "status": status(path),
        })
    write_csv(OUT, rows)
    print("=" * 90)
    print("EDGEIQ SECTIONAL SCRAPER INVENTORY")
    print("=" * 90)
    print("FILES:", len(rows))
    print("CSV FILES:", sum(1 for row in rows if row["file_type"] == "csv"))
    print("SCRIPTS:", sum(1 for row in rows if row["file_type"] == "py"))
    print("OUT:", OUT)


if __name__ == "__main__":
    main()
