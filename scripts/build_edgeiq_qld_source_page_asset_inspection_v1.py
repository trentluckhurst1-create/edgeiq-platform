from __future__ import annotations

import csv
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

try:
    import requests
except Exception:
    requests = None

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_INSPECTION = DATA / "edgeiq_qld_gps_path_payload_inspection_v1.csv"
IN_CANDIDATES = DATA / "edgeiq_qld_explicit_position_payload_candidates_v1.csv"
IN_INGESTION = DATA / "edgeiq_qld_telemetry_ingestion_v1.csv"

OUT = DATA / "edgeiq_qld_source_page_asset_inspection_v1.csv"
SUMMARY = DATA / "edgeiq_qld_source_page_asset_summary_v1.csv"
FOLLOWUP = DATA / "edgeiq_qld_asset_followup_targets_v1.csv"

OUT_FIELDS = [
    "track","source_url","asset_url","asset_type","asset_hint",
    "gps_signal_hint","path_signal_hint","coordinate_signal_hint",
    "rank_signal_hint","position_signal_hint","downloadable",
    "risk_level","inspection_status","recommended_followup","notes",
]

SUMMARY_FIELDS = ["metric","value"]

FOLLOWUP_FIELDS = [
    "priority","track","source_url","asset_url","asset_type","asset_classification",
    "expected_value","risk_level","recommended_action","notes",
]

def clean(v):
    return str(v or "").strip()

def upper(v):
    return clean(v).upper()

def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig", errors="ignore") as f:
        return list(csv.DictReader(f))

def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{time.time_ns()}")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({field: r.get(field, "") for field in fields})
    tmp.replace(path)

def asset_type(url):
    low = url.lower()
    for ext in [".csv",".zip",".json",".xlsx",".xls",".pdf",".xml",".png",".jpg",".jpeg",".webp"]:
        if ext in low:
            return ext.replace(".","").upper()
    if "position" in low or "map" in low:
        return "POSITION_MAP_HINT"
    if "sectional" in low:
        return "SECTIONAL_HINT"
    if "racingfile" in low:
        return "RACINGFILE_HINT"
    return "HTML_OR_UNKNOWN"

def classify(url, text):
    low = f"{url} {text}".lower()
    gps = any(t in low for t in ["gps","speed","velocity","distance"])
    path = any(t in low for t in ["path","lane","map","position map","distance off rail","track position"])
    coord = any(t in low for t in ["coordinate","latitude","longitude","xpos","ypos","x_pos","y_pos"])
    rank = any(t in low for t in ["rank","running order","position_rank","order"])
    pos = any(t in low for t in ["position","positional","map"])
    downloadable = any(t in low for t in [".csv",".zip",".json",".xlsx",".xls",".pdf",".xml"])

    if rank or ("position" in low and downloadable):
        label = "HIGH_VALUE_POSITION_ASSET"
    elif coord:
        label = "COORDINATE_ASSET"
    elif gps or path:
        label = "GPS_PATH_ASSET"
    elif downloadable or pos:
        label = "WEAK_ASSET_HINT"
    else:
        label = "NO_ASSET_FOUND"

    return label, gps, path, coord, rank, pos, downloadable

def extract_urls(html, base_url):
    urls = set()
    patterns = [
        r'href=["\']([^"\']+)["\']',
        r'src=["\']([^"\']+)["\']',
        r'url\(["\']?([^"\')]+)',
        r'["\']([^"\']+\.(?:csv|zip|json|xlsx|xls|pdf|xml|png|jpg|jpeg|webp)(?:\?[^"\']*)?)["\']',
    ]
    for p in patterns:
        for m in re.finditer(p, html, flags=re.I):
            u = clean(m.group(1))
            if not u or u.startswith(("mailto:", "tel:", "javascript:")):
                continue
            urls.add(urljoin(base_url, u))
    return sorted(urls)

def polite_fetch(url):
    if requests is None:
        return "", "REQUESTS_NOT_AVAILABLE"
    try:
        headers = {
            "User-Agent": "EDGEiQ research asset inspection; polite non-aggressive source-page audit",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code >= 400:
            return "", f"HTTP_{r.status_code}"
        return r.text[:500000], "FETCHED"
    except Exception as e:
        return "", f"FETCH_FAILED:{type(e).__name__}"

def source_urls():
    rows = read_csv(IN_INSPECTION) + read_csv(IN_CANDIDATES) + read_csv(IN_INGESTION)
    urls = {}
    for r in rows:
        url = clean(r.get("source_url"))
        track = clean(r.get("track"))
        if not url:
            continue
        if not url.lower().startswith(("http://","https://")):
            continue
        urls[url] = track or urls.get(url,"")
    return urls

def main():
    urls = source_urls()
    out = []
    follow = []

    if not urls:
        out.append({
            "track":"","source_url":"","asset_url":"","asset_type":"",
            "asset_hint":"NO_SOURCE_URLS_FOUND","gps_signal_hint":"NO","path_signal_hint":"NO",
            "coordinate_signal_hint":"NO","rank_signal_hint":"NO","position_signal_hint":"NO",
            "downloadable":"NO","risk_level":"LOW","inspection_status":"NO_URL_INPUTS",
            "recommended_followup":"Check QLD lineage files for source_url values.",
            "notes":"Offline/non-aggressive source inspection only. No modelling/execution.",
        })

    for source_url, track in urls.items():
        html, status = polite_fetch(source_url)
        candidate_urls = extract_urls(html, source_url) if html else []
        if not candidate_urls:
            label, gps, path, coord, rank, pos, dl = classify(source_url, html)
            out.append({
                "track":track,"source_url":source_url,"asset_url":"",
                "asset_type":"NO_LINKED_ASSET_DETECTED","asset_hint":label,
                "gps_signal_hint":"YES" if gps else "NO",
                "path_signal_hint":"YES" if path else "NO",
                "coordinate_signal_hint":"YES" if coord else "NO",
                "rank_signal_hint":"YES" if rank else "NO",
                "position_signal_hint":"YES" if pos else "NO",
                "downloadable":"YES" if dl else "NO",
                "risk_level":"LOW",
                "inspection_status":status,
                "recommended_followup":"Manually inspect source page/network assets if page is JS-rendered or links are hidden.",
                "notes":"Non-aggressive known URL inspection only.",
            })
            continue

        for asset in candidate_urls:
            label, gps, path, coord, rank, pos, dl = classify(asset, html)
            if label == "NO_ASSET_FOUND":
                continue
            atype = asset_type(asset)
            risk = "LOW" if dl or urlparse(asset).netloc == urlparse(source_url).netloc else "MEDIUM"
            rec = "Download/inspect asset schema offline if permitted; do not brute force." if label in {"HIGH_VALUE_POSITION_ASSET","COORDINATE_ASSET","GPS_PATH_ASSET"} else "Keep as weak follow-up hint."
            row = {
                "track":track,"source_url":source_url,"asset_url":asset,"asset_type":atype,
                "asset_hint":label,
                "gps_signal_hint":"YES" if gps else "NO",
                "path_signal_hint":"YES" if path else "NO",
                "coordinate_signal_hint":"YES" if coord else "NO",
                "rank_signal_hint":"YES" if rank else "NO",
                "position_signal_hint":"YES" if pos else "NO",
                "downloadable":"YES" if dl else "NO",
                "risk_level":risk,
                "inspection_status":status,
                "recommended_followup":rec,
                "notes":"QLD source-page asset inspection only. No modelling/execution.",
            }
            out.append(row)
            if label in {"HIGH_VALUE_POSITION_ASSET","COORDINATE_ASSET","GPS_PATH_ASSET"}:
                follow.append({
                    "priority":"HIGH" if label == "HIGH_VALUE_POSITION_ASSET" else "MEDIUM",
                    "track":track,
                    "source_url":source_url,
                    "asset_url":asset,
                    "asset_type":atype,
                    "asset_classification":label,
                    "expected_value":"Explicit/richer positional, GPS, path, or coordinate telemetry candidate.",
                    "risk_level":risk,
                    "recommended_action":"Inspect/download this known linked asset offline and build a schema parser only if structure is stable.",
                    "notes":"No brute force. No execution. Research-only.",
                })

    counts = {}
    for r in out:
        counts[r["asset_hint"]] = counts.get(r["asset_hint"], 0) + 1

    summary = [
        {"metric":"source_urls_inspected","value":len(urls)},
        {"metric":"asset_rows","value":len(out)},
        {"metric":"followup_rows","value":len(follow)},
        {"metric":"high_value_position_assets","value":counts.get("HIGH_VALUE_POSITION_ASSET",0)},
        {"metric":"gps_path_assets","value":counts.get("GPS_PATH_ASSET",0)},
        {"metric":"coordinate_assets","value":counts.get("COORDINATE_ASSET",0)},
        {"metric":"weak_asset_hints","value":counts.get("WEAK_ASSET_HINT",0)},
        {"metric":"no_asset_found_rows","value":counts.get("NO_ASSET_FOUND",0)},
        {"metric":"live_modelling_yes","value":0},
        {"metric":"live_execution_yes","value":0},
        {"metric":"offline_research_only","value":"YES"},
    ]

    write_csv(OUT, out, OUT_FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    write_csv(FOLLOWUP, follow, FOLLOWUP_FIELDS)

    print("="*88)
    print("EDGEIQ QLD SOURCE PAGE ASSET INSPECTION V1")
    print("="*88)
    for row in summary:
        print(f"{row['metric']}: {row['value']}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {FOLLOWUP}")

if __name__ == "__main__":
    main()
