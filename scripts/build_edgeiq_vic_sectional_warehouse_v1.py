from pathlib import Path
from datetime import datetime, timezone
import csv
import re

import pandas as pd


APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA = APP_ROOT / "public" / "data"
RAW_VIC = PROJECT_ROOT / "outputs" / "sectionals" / "raw" / "VIC"
RAW_CSV = RAW_VIC / "racingcom_csv"
BROWSER_DOWNLOAD_CACHE = RAW_VIC / "racingcom_browser_csv_downloads"

REGISTRY_V2 = DATA / "edgeiq_vic_confirmed_csv_registry_v2.csv"
REGISTRY_V1 = DATA / "edgeiq_vic_confirmed_csv_registry_v1.csv"
LIVE_BOARD = DATA / "edgeiq_execution_board_live.csv"

WAREHOUSE_OUT = DATA / "edgeiq_vic_sectional_warehouse_v1.csv"
DIAGNOSTICS_OUT = DATA / "edgeiq_vic_sectional_diagnostics_v1.csv"
COVERAGE_OUT = DATA / "edgeiq_vic_sectional_coverage_by_race_v1.csv"

WAREHOUSE_COLUMNS = [
    "race_date",
    "track",
    "race_no",
    "meeting_id",
    "csv_url",
    "horse",
    "horse_key",
    "distance",
    "last200",
    "last400",
    "last600",
    "source_type",
    "source_file",
    "source_confidence",
    "registry_confidence",
    "ingestion_status",
]

COVERAGE_COLUMNS = [
    "race_date",
    "track",
    "meeting_id",
    "race_no",
    "csv_url",
    "promoted",
    "cached",
    "rows",
    "unique_horses",
    "last200_coverage_pct",
    "last400_coverage_pct",
    "last600_coverage_pct",
    "ingestion_status",
]

DIAG_COLUMNS = ["metric", "value", "notes"]


def log(message: str) -> None:
    print(f"[vic_sectional_warehouse_v1] {message}")


def clean(value) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-", "UNKNOWN"} else text


def has_value(value) -> bool:
    return bool(clean(value))


def norm(value) -> str:
    text = re.sub(r"\([^)]*\)", "", clean(value).upper())
    return re.sub(r"[^A-Z0-9]+", "", text)


def race_no_key(value) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def date_key(value) -> str:
    if not has_value(value):
        return ""
    raw = clean(value)
    dayfirst = not bool(re.match(r"^\d{4}-\d{1,2}-\d{1,2}", raw))
    parsed = pd.to_datetime(pd.Series([raw]), errors="coerce", dayfirst=dayfirst).iloc[0]
    if pd.isna(parsed):
        return ""
    return parsed.strftime("%Y-%m-%d")


def pct(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0.00"
    return f"{(numerator / denominator) * 100:.2f}"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype=str, encoding="utf-8-sig", on_bad_lines="skip").fillna("")
    except Exception:
        return pd.DataFrame()


def to_seconds(value: str):
    text = clean(value)
    if not text:
        return None
    try:
        parts = [float(part) for part in text.split(":")]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        return parts[0]
    except Exception:
        try:
            return float(text)
        except Exception:
            return None


def fmt_number(value, decimals: int = 3) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{float(value):.{decimals}f}".rstrip("0").rstrip(".")


def csv_filename_from_url(url: str) -> str:
    return Path(clean(url).split("?", 1)[0]).name


def cached_path_for_url(url: str) -> Path:
    return RAW_CSV / csv_filename_from_url(url)


def parse_racingcom_csv(path: Path, registry_row: pd.Series) -> tuple[list[dict[str, str]], str]:
    if not path.exists() or path.stat().st_size <= 0:
        return [], "MISSING_CACHED_CSV"
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            records = list(csv.reader(handle, delimiter=";"))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as handle:
            records = list(csv.reader(handle, delimiter=";"))
    except Exception:
        return [], "CSV_READ_FAILED"
    if len(records) < 2:
        return [], "CSV_EMPTY"

    header = records[0]
    race_date = date_key(registry_row.get("race_date", "")) or date_key(header[0] if len(header) > 0 else "")
    meeting = clean(header[1] if len(header) > 1 else "")
    track = clean(registry_row.get("track", "")) or meeting.split("-")[0].strip()
    race_no = race_no_key(registry_row.get("race_no", ""))
    if not race_no:
        match = re.search(r"_(\d{2})\.csv$", path.name, flags=re.IGNORECASE)
        race_no = str(int(match.group(1))) if match else ""
    distance = ""
    if len(header) > 4:
        distance_match = re.search(r"_(\d+)m_", clean(header[4]), flags=re.IGNORECASE)
        distance = distance_match.group(1) if distance_match else ""

    rows = []
    for record in records[1:]:
        if len(record) < 5:
            continue
        horse = clean(record[0])
        if not horse:
            continue
        splits = []
        idx = 2
        while idx + 2 < len(record):
            seconds = to_seconds(record[idx + 2])
            if seconds is not None:
                splits.append(seconds)
            idx += 3
        rows.append({
            "race_date": race_date,
            "track": track,
            "race_no": race_no,
            "meeting_id": clean(registry_row.get("meeting_id", "")),
            "csv_url": clean(registry_row.get("csv_url", "")),
            "horse": horse,
            "horse_key": norm(horse),
            "distance": distance,
            "last200": fmt_number(splits[-1] if len(splits) >= 1 else None),
            "last400": fmt_number(sum(splits[-2:]) if len(splits) >= 2 else None),
            "last600": fmt_number(sum(splits[-3:]) if len(splits) >= 3 else None),
            "source_type": "RACINGCOM_CONFIRMED_CSV",
            "source_file": path.relative_to(PROJECT_ROOT).as_posix(),
            "source_confidence": "HIGH",
            "registry_confidence": clean(registry_row.get("confidence", "")),
            "ingestion_status": "INGESTED_CACHED_CSV",
        })
    return rows, "INGESTED_CACHED_CSV" if rows else "CSV_NO_RUNNER_ROWS"


def promoted_registry() -> pd.DataFrame:
    registry_path = REGISTRY_V2 if REGISTRY_V2.exists() else REGISTRY_V1
    log(f"registry source: {registry_path.name}")
    registry = read_csv(registry_path)
    if registry.empty:
        return pd.DataFrame(columns=["csv_url"])
    promoted = registry[registry.get("promote_to_fetch", pd.Series(dtype=str)).astype(str).str.upper() == "TRUE"].copy()
    promoted = promoted[promoted.get("csv_url", pd.Series(dtype=str)).map(has_value)].copy()
    return promoted.drop_duplicates(subset=["csv_url"], keep="first")


def build_warehouse(registry: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    rows = []
    coverage_rows = []
    rejected_rows = 0
    for _, reg in registry.iterrows():
        path = cached_path_for_url(reg.get("csv_url", ""))
        parsed_rows, status = parse_racingcom_csv(path, reg)
        if status != "INGESTED_CACHED_CSV":
            rejected_rows += 1
        rows.extend(parsed_rows)
        row_count = len(parsed_rows)
        coverage_rows.append({
            "race_date": date_key(reg.get("race_date", "")) or (parsed_rows[0]["race_date"] if parsed_rows else ""),
            "track": clean(reg.get("track", "")) or (parsed_rows[0]["track"] if parsed_rows else ""),
            "meeting_id": clean(reg.get("meeting_id", "")),
            "race_no": race_no_key(reg.get("race_no", "")) or (parsed_rows[0]["race_no"] if parsed_rows else ""),
            "csv_url": clean(reg.get("csv_url", "")),
            "promoted": "TRUE",
            "cached": str(path.exists() and path.stat().st_size > 0).upper(),
            "rows": str(row_count),
            "unique_horses": str(len({row["horse_key"] for row in parsed_rows})),
            "last200_coverage_pct": pct(sum(has_value(row.get("last200", "")) for row in parsed_rows), row_count),
            "last400_coverage_pct": pct(sum(has_value(row.get("last400", "")) for row in parsed_rows), row_count),
            "last600_coverage_pct": pct(sum(has_value(row.get("last600", "")) for row in parsed_rows), row_count),
            "ingestion_status": status,
        })

    warehouse = pd.DataFrame(rows, columns=WAREHOUSE_COLUMNS)
    if not warehouse.empty:
        warehouse["_date_key"] = warehouse["race_date"].map(date_key)
        warehouse["_track_key"] = warehouse["track"].map(norm)
        warehouse["_race_no_key"] = warehouse["race_no"].map(race_no_key)
        warehouse["_split_count"] = warehouse[["last200", "last400", "last600"]].apply(lambda row: sum(has_value(v) for v in row), axis=1)
        warehouse = warehouse.sort_values(["_split_count", "source_confidence"], ascending=[False, True])
        warehouse = warehouse.drop_duplicates(subset=["horse_key", "_date_key", "_track_key", "_race_no_key", "csv_url"], keep="first")
        warehouse = warehouse.drop(columns=["_date_key", "_track_key", "_race_no_key", "_split_count"])
    else:
        warehouse = pd.DataFrame(columns=WAREHOUSE_COLUMNS)

    coverage = pd.DataFrame(coverage_rows, columns=COVERAGE_COLUMNS)
    return warehouse[WAREHOUSE_COLUMNS], coverage, rejected_rows


def build_diagnostics(registry: pd.DataFrame, warehouse: pd.DataFrame, coverage: pd.DataFrame, rejected_rows: int) -> pd.DataFrame:
    promoted_count = len(registry)
    cached_count = int((coverage["cached"] == "TRUE").sum()) if not coverage.empty else 0
    meetings = warehouse["meeting_id"].nunique() if not warehouse.empty else 0
    races = coverage[(coverage["rows"].astype(str) != "0")]["csv_url"].nunique() if not coverage.empty else 0
    rows = [
        {"metric": "run_timestamp_utc", "value": datetime.now(timezone.utc).isoformat(timespec="seconds"), "notes": "UTC run timestamp"},
        {"metric": "registry_promoted_url_count", "value": str(promoted_count), "notes": "promote_to_fetch TRUE URLs from confirmed registry"},
        {"metric": "cached_csv_count", "value": str(cached_count), "notes": "Promoted URLs with local cached CSV files"},
        {"metric": "rejected_rows", "value": str(rejected_rows), "notes": "Promoted URLs that could not be ingested from cache"},
        {"metric": "total_rows", "value": str(len(warehouse)), "notes": "Canonical rows built only from registry-promoted cached CSVs"},
        {"metric": "unique_horses", "value": str(warehouse["horse_key"].nunique() if not warehouse.empty else 0), "notes": "Unique canonical horse keys"},
        {"metric": "meetings_covered", "value": str(meetings), "notes": "Unique Racing.com meeting IDs covered"},
        {"metric": "races_covered", "value": str(races), "notes": "Confirmed CSV races with rows"},
        {"metric": "last200_coverage_pct", "value": pct(int(warehouse["last200"].map(has_value).sum()) if not warehouse.empty else 0, len(warehouse)), "notes": "Rows with last200"},
        {"metric": "last400_coverage_pct", "value": pct(int(warehouse["last400"].map(has_value).sum()) if not warehouse.empty else 0, len(warehouse)), "notes": "Rows with last400"},
        {"metric": "last600_coverage_pct", "value": pct(int(warehouse["last600"].map(has_value).sum()) if not warehouse.empty else 0, len(warehouse)), "notes": "Rows with last600"},
        {"metric": "rows_by_meeting", "value": warehouse["meeting_id"].value_counts().to_json() if not warehouse.empty else "{}", "notes": "Rows by Racing.com meeting ID"},
        {"metric": "rows_by_race", "value": coverage.set_index("race_no")["rows"].to_json() if not coverage.empty else "{}", "notes": "Rows by race number for promoted URLs"},
        {"metric": "rows_by_track", "value": warehouse["track"].value_counts().to_json() if not warehouse.empty else "{}", "notes": "Rows by track"},
        {"metric": "rows_by_date", "value": warehouse["race_date"].value_counts().sort_index().to_json() if not warehouse.empty else "{}", "notes": "Rows by date"},
        {"metric": "source_confidence", "value": warehouse["source_confidence"].value_counts().to_json() if not warehouse.empty else "{}", "notes": "Rows by source confidence"},
        {"metric": "registry_confidence", "value": warehouse["registry_confidence"].value_counts().to_json() if not warehouse.empty else "{}", "notes": "Rows by registry confidence"},
    ]
    return pd.DataFrame(rows, columns=DIAG_COLUMNS)


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    registry = promoted_registry()
    warehouse, coverage, rejected_rows = build_warehouse(registry)
    diagnostics = build_diagnostics(registry, warehouse, coverage, rejected_rows)

    warehouse.to_csv(WAREHOUSE_OUT, index=False, encoding="utf-8")
    diagnostics.to_csv(DIAGNOSTICS_OUT, index=False, encoding="utf-8")
    coverage.to_csv(COVERAGE_OUT, index=False, encoding="utf-8")

    diag = {row["metric"]: row["value"] for _, row in diagnostics.iterrows()}
    log(f"registry-promoted URLs: {diag.get('registry_promoted_url_count', '0')}")
    log(f"cached CSV count: {diag.get('cached_csv_count', '0')}")
    log(f"total rows: {diag.get('total_rows', '0')}")
    log(f"races covered: {diag.get('races_covered', '0')}")
    log(f"meetings covered: {diag.get('meetings_covered', '0')}")
    log(f"last200 coverage: {diag.get('last200_coverage_pct', '0.00')}%")
    log(f"last400 coverage: {diag.get('last400_coverage_pct', '0.00')}%")
    log(f"last600 coverage: {diag.get('last600_coverage_pct', '0.00')}%")
    log(f"rejected rows: {diag.get('rejected_rows', '0')}")
    log(f"wrote {WAREHOUSE_OUT.relative_to(APP_ROOT)}")
    log(f"wrote {DIAGNOSTICS_OUT.relative_to(APP_ROOT)}")
    log(f"wrote {COVERAGE_OUT.relative_to(APP_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

