from pathlib import Path
from datetime import datetime, timezone
import csv
import json
import re

import pandas as pd


APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA = APP_ROOT / "public" / "data"
RAW_VIC = PROJECT_ROOT / "outputs" / "sectionals" / "raw" / "VIC"
RAW_CSV = RAW_VIC / "racingcom_csv"
RAW_SPEED_DATA = RAW_VIC / "racingcom_speed_data"
RAW_GRAPHQL = RAW_VIC / "racingcom_graphql"

CSV_INGESTION = DATA / "edgeiq_racingcom_csv_ingestion_v1.csv"
CSV_DIAGNOSTICS = DATA / "edgeiq_racingcom_csv_ingestion_diagnostics_v1.csv"
COMPLETED_PROBE = DATA / "edgeiq_racingcom_completed_payload_probe_v1.csv"
NETWORK_PROBE = DATA / "edgeiq_racingcom_speed_network_probe_v1.csv"

REGISTRY_OUT = DATA / "edgeiq_vic_confirmed_csv_registry_v1.csv"
DIAGNOSTICS_OUT = DATA / "edgeiq_vic_confirmed_csv_registry_diagnostics_v1.csv"

CLOUDFRONT_BASE = "https://d3qmfyv6ad9vwv.cloudfront.net"

REGISTRY_COLUMNS = [
    "csv_url",
    "source_discovered_from",
    "meeting_id",
    "race_no",
    "race_date",
    "track",
    "url_status",
    "http_status",
    "rows_if_cached",
    "has_last200",
    "has_last400",
    "has_last600",
    "confidence",
    "promote_to_fetch",
]

DIAG_COLUMNS = ["metric", "value", "notes"]


def log(message: str) -> None:
    print(f"[vic_confirmed_csv_registry_v1] {message}")


def clean(value) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-", "UNKNOWN"} else text


def has_value(value) -> bool:
    return bool(clean(value))


def date_key(value) -> str:
    if not has_value(value):
        return ""
    raw = clean(value)
    dayfirst = not bool(re.match(r"^\d{4}-\d{1,2}-\d{1,2}", raw))
    parsed = pd.to_datetime(pd.Series([raw]), errors="coerce", dayfirst=dayfirst).iloc[0]
    if pd.isna(parsed):
        return ""
    return parsed.strftime("%Y-%m-%d")


def race_no_key(value) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


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


def parse_cached_csv(path: Path) -> dict[str, str]:
    out = {
        "rows_if_cached": "0",
        "has_last200": "FALSE",
        "has_last400": "FALSE",
        "has_last600": "FALSE",
        "race_date": "",
        "track": "",
        "race_no": "",
    }
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle, delimiter=";"))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as handle:
            rows = list(csv.reader(handle, delimiter=";"))
    except Exception:
        return out
    if len(rows) < 2:
        return out
    header = rows[0]
    out["race_date"] = date_key(header[0] if len(header) > 0 else "")
    meeting = clean(header[1] if len(header) > 1 else "")
    out["track"] = meeting.split("-")[0].strip() if meeting else ""
    match = re.search(r"_(\d{2})\.csv$", path.name, flags=re.IGNORECASE)
    if match:
        out["race_no"] = str(int(match.group(1)))

    runner_rows = 0
    has200 = has400 = has600 = False
    for record in rows[1:]:
        if len(record) < 5 or not clean(record[0]):
            continue
        runner_rows += 1
        splits = []
        idx = 2
        while idx + 2 < len(record):
            seconds = to_seconds(record[idx + 2])
            if seconds is not None:
                splits.append(seconds)
            idx += 3
        has200 = has200 or len(splits) >= 1
        has400 = has400 or len(splits) >= 2
        has600 = has600 or len(splits) >= 3
    out["rows_if_cached"] = str(runner_rows)
    out["has_last200"] = str(has200).upper()
    out["has_last400"] = str(has400).upper()
    out["has_last600"] = str(has600).upper()
    return out


def meeting_race_from_url(url: str) -> tuple[str, str]:
    match = re.search(r"/(\d+)_(\d{2})\.csv(?:\?|$)", clean(url), flags=re.IGNORECASE)
    if not match:
        return "", ""
    return match.group(1), str(int(match.group(2)))


def local_csv_url(path: Path) -> str:
    return f"{CLOUDFRONT_BASE}/{path.name}"


def csv_links_from_text(text: str) -> set[str]:
    links = set()
    for match in re.finditer(r"https?://[^\"'\s<>]+?\.csv(?:\?[^\"'\s<>]*)?", text, flags=re.IGNORECASE):
        links.add(match.group(0).replace("\\u0026", "&"))
    for match in re.finditer(r"cloudfront\.net/([^\"'\s<>]+?\.csv)", text, flags=re.IGNORECASE):
        links.add(f"{CLOUDFRONT_BASE}/{match.group(1).split('/')[-1]}")
    return links


def cached_csv_records() -> list[dict[str, str]]:
    records = []
    if not RAW_CSV.exists():
        return records
    for path in sorted(RAW_CSV.glob("*.csv")):
        url = local_csv_url(path)
        meeting_id, race_no = meeting_race_from_url(url)
        parsed = parse_cached_csv(path)
        records.append({
            "csv_url": url,
            "source_discovered_from": path.relative_to(PROJECT_ROOT).as_posix(),
            "meeting_id": meeting_id,
            "race_no": parsed.get("race_no") or race_no,
            "race_date": parsed.get("race_date", ""),
            "track": parsed.get("track", ""),
            "url_status": "CONFIRMED_CACHED",
            "http_status": "200",
            "rows_if_cached": parsed.get("rows_if_cached", "0"),
            "has_last200": parsed.get("has_last200", "FALSE"),
            "has_last400": parsed.get("has_last400", "FALSE"),
            "has_last600": parsed.get("has_last600", "FALSE"),
            "confidence": "HIGH" if int(parsed.get("rows_if_cached", "0") or 0) > 0 else "LOW",
            "promote_to_fetch": "TRUE" if int(parsed.get("rows_if_cached", "0") or 0) > 0 else "FALSE",
        })
    return records


def ingestion_records() -> list[dict[str, str]]:
    df = read_csv(CSV_INGESTION)
    if df.empty or "source_url" not in df.columns:
        return []
    grouped = df.groupby("source_url", dropna=False)
    records = []
    for url, group in grouped:
        url = clean(url)
        if not url:
            continue
        meeting_id, race_no = meeting_race_from_url(url)
        records.append({
            "csv_url": url,
            "source_discovered_from": CSV_INGESTION.relative_to(PROJECT_ROOT).as_posix(),
            "meeting_id": meeting_id,
            "race_no": race_no or race_no_key(group["race_no"].iloc[0] if "race_no" in group else ""),
            "race_date": date_key(group["race_date"].iloc[0] if "race_date" in group else ""),
            "track": clean(group["track"].iloc[0] if "track" in group else ""),
            "url_status": "CONFIRMED_PARSED",
            "http_status": "200",
            "rows_if_cached": str(len(group)),
            "has_last200": str(group["last200"].map(has_value).any() if "last200" in group else False).upper(),
            "has_last400": str(group["last400"].map(has_value).any() if "last400" in group else False).upper(),
            "has_last600": str(group["last600"].map(has_value).any() if "last600" in group else False).upper(),
            "confidence": "HIGH",
            "promote_to_fetch": "TRUE",
        })
    return records


def payload_link_records() -> list[dict[str, str]]:
    records = []
    source_files = []
    for root in [RAW_SPEED_DATA, RAW_GRAPHQL, RAW_VIC / "racingcom_completed_payloads", RAW_VIC / "racingcom_full_payloads", RAW_VIC / "racingcom_network_probe"]:
        if root.exists():
            source_files.extend(path for path in root.rglob("*") if path.is_file())
    for path in sorted(set(source_files)):
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except Exception:
            continue
        for url in csv_links_from_text(text):
            meeting_id, race_no = meeting_race_from_url(url)
            records.append({
                "csv_url": url,
                "source_discovered_from": path.relative_to(PROJECT_ROOT).as_posix(),
                "meeting_id": meeting_id,
                "race_no": race_no,
                "race_date": "",
                "track": "",
                "url_status": "DISCOVERED_IN_PAYLOAD",
                "http_status": "",
                "rows_if_cached": "0",
                "has_last200": "FALSE",
                "has_last400": "FALSE",
                "has_last600": "FALSE",
                "confidence": "MEDIUM",
                "promote_to_fetch": "FALSE",
            })
    return records


def dedupe(records: list[dict[str, str]]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=REGISTRY_COLUMNS)
    df = pd.DataFrame(records, columns=REGISTRY_COLUMNS).fillna("")
    priority = {"CONFIRMED_PARSED": 0, "CONFIRMED_CACHED": 1, "DISCOVERED_IN_PAYLOAD": 2}
    confidence_priority = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    df["_priority"] = df["url_status"].map(priority).fillna(9)
    df["_confidence_priority"] = df["confidence"].map(confidence_priority).fillna(9)
    df["_rows"] = pd.to_numeric(df["rows_if_cached"], errors="coerce").fillna(0)
    df = df.sort_values(["_priority", "_confidence_priority", "_rows"], ascending=[True, True, False])
    df = df.drop_duplicates(subset=["csv_url"], keep="first")
    df = df.drop(columns=["_priority", "_confidence_priority", "_rows"])
    return df[REGISTRY_COLUMNS]


def build_diagnostics(registry: pd.DataFrame) -> pd.DataFrame:
    confirmed = registry[registry["url_status"].isin(["CONFIRMED_PARSED", "CONFIRMED_CACHED"])] if not registry.empty else registry
    promoted = registry[registry["promote_to_fetch"] == "TRUE"] if not registry.empty else registry
    cached = registry[pd.to_numeric(registry["rows_if_cached"], errors="coerce").fillna(0) > 0] if not registry.empty else registry
    rejected = registry[registry["promote_to_fetch"] != "TRUE"] if not registry.empty else registry
    rows_available = int(pd.to_numeric(registry.get("rows_if_cached", pd.Series(dtype=str)), errors="coerce").fillna(0).sum()) if not registry.empty else 0
    coverage = {}
    if not confirmed.empty:
        grouped = confirmed.groupby(["race_date", "track", "meeting_id", "race_no"], dropna=False).size().reset_index(name="urls")
        coverage = {
            "|".join([clean(row["race_date"]), clean(row["track"]), clean(row["meeting_id"]), f"R{clean(row['race_no'])}"]): int(row["urls"])
            for _, row in grouped.iterrows()
        }
    diag_rows = [
        {"metric": "run_timestamp_utc", "value": datetime.now(timezone.utc).isoformat(timespec="seconds"), "notes": "UTC run timestamp"},
        {"metric": "confirmed_urls", "value": str(len(confirmed)), "notes": "URLs confirmed by parsed output or cached CSV"},
        {"metric": "cached_csvs", "value": str(len(cached)), "notes": "Confirmed URLs with cached runner rows"},
        {"metric": "promoted_urls", "value": str(len(promoted)), "notes": "URLs allowed for future fetch workflows"},
        {"metric": "rejected_urls", "value": str(len(rejected)), "notes": "Discovered-only or low-confidence URLs not promoted"},
        {"metric": "rows_available", "value": str(rows_available), "notes": "Runner rows available from confirmed cached/parsed CSVs"},
        {"metric": "has_last200_urls", "value": str(int((registry["has_last200"] == "TRUE").sum()) if not registry.empty else 0), "notes": "URLs with cached final 200m data"},
        {"metric": "has_last400_urls", "value": str(int((registry["has_last400"] == "TRUE").sum()) if not registry.empty else 0), "notes": "URLs with cached final 400m data"},
        {"metric": "has_last600_urls", "value": str(int((registry["has_last600"] == "TRUE").sum()) if not registry.empty else 0), "notes": "URLs with cached final 600m data"},
        {"metric": "coverage_by_meeting_race", "value": json.dumps(coverage, sort_keys=True), "notes": "Confirmed URL coverage by date/track/meeting/race"},
        {"metric": "source_inputs", "value": ",".join([
            CSV_INGESTION.relative_to(PROJECT_ROOT).as_posix(),
            CSV_DIAGNOSTICS.relative_to(PROJECT_ROOT).as_posix(),
            COMPLETED_PROBE.relative_to(PROJECT_ROOT).as_posix(),
            NETWORK_PROBE.relative_to(PROJECT_ROOT).as_posix(),
            RAW_CSV.relative_to(PROJECT_ROOT).as_posix(),
            RAW_SPEED_DATA.relative_to(PROJECT_ROOT).as_posix(),
            RAW_GRAPHQL.relative_to(PROJECT_ROOT).as_posix(),
        ]), "notes": "Audited VIC/Racing.com inputs"},
    ]
    return pd.DataFrame(diag_rows, columns=DIAG_COLUMNS)


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    records = []
    records.extend(cached_csv_records())
    records.extend(ingestion_records())
    records.extend(payload_link_records())
    registry = dedupe(records)
    diagnostics = build_diagnostics(registry)
    registry.to_csv(REGISTRY_OUT, index=False, encoding="utf-8")
    diagnostics.to_csv(DIAGNOSTICS_OUT, index=False, encoding="utf-8")

    diag = {row["metric"]: row["value"] for _, row in diagnostics.iterrows()}
    log(f"confirmed URLs: {diag.get('confirmed_urls', '0')}")
    log(f"cached CSVs: {diag.get('cached_csvs', '0')}")
    log(f"promoted URLs: {diag.get('promoted_urls', '0')}")
    log(f"rejected URLs: {diag.get('rejected_urls', '0')}")
    log(f"rows available: {diag.get('rows_available', '0')}")
    log(f"wrote {REGISTRY_OUT.relative_to(APP_ROOT)}")
    log(f"wrote {DIAGNOSTICS_OUT.relative_to(APP_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
