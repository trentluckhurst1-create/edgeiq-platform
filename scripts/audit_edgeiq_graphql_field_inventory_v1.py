from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUTS = [
    DATA / "edgeiq_graphql_playwright_replay_flemington_20250101_v1.json",
    DATA / "edgeiq_graphql_race_results_payload_v1.json",
]

OUT = DATA / "edgeiq_graphql_field_inventory_v1.csv"
SUMMARY = DATA / "edgeiq_graphql_field_inventory_v1_summary.csv"


def clean(v):
    return "" if v is None else str(v).strip()


def dtype(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, list):
        return "list"
    if isinstance(v, dict):
        return "dict"
    return "string"


def sample(v):
    if isinstance(v, (dict, list)):
        txt = json.dumps(v, ensure_ascii=False)
    else:
        txt = clean(v)
    return txt[:500]


def walk(obj, path="", rows=None, source_file=""):
    if rows is None:
        rows = []

    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            rows.append({
                "source_file": source_file,
                "graphql_path": p,
                "field_name": k,
                "data_type": dtype(v),
                "sample_value": sample(v),
            })
            walk(v, p, rows, source_file)

    elif isinstance(obj, list):
        for i, item in enumerate(obj[:3]):
            p = f"{path}[{i}]"
            rows.append({
                "source_file": source_file,
                "graphql_path": p,
                "field_name": f"[{i}]",
                "data_type": dtype(item),
                "sample_value": sample(item),
            })
            walk(item, p, rows, source_file)

    return rows


def load_payload(path: Path):
    txt = path.read_text(encoding="utf-8")
    return json.loads(txt)


def main():
    built_at = datetime.now(timezone.utc).isoformat()
    all_rows = []

    for p in INPUTS:
        if not p.exists():
            continue

        payload = load_payload(p)

        if isinstance(payload, list):
            for idx, item in enumerate(payload):
                op = clean(item.get("operation")) if isinstance(item, dict) else ""
                body = item.get("body") if isinstance(item, dict) else item
                try:
                    body_json = json.loads(body) if isinstance(body, str) else body
                except Exception:
                    body_json = {"raw_body": body}
                all_rows.extend(walk(body_json, f"capture[{idx}].{op}", source_file=p.name))
        else:
            all_rows.extend(walk(payload, "", source_file=p.name))

    seen = set()
    deduped = []
    for r in all_rows:
        key = (r["source_file"], r["graphql_path"], r["field_name"], r["data_type"])
        if key in seen:
            continue
        seen.add(key)
        r["built_at"] = built_at
        deduped.append(r)

    fields = ["source_file", "graphql_path", "field_name", "data_type", "sample_value", "built_at"]

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(deduped)

    wanted = [
        "horseName", "trainerName", "jockeyName", "startingPrice",
        "finish", "margin", "barrierNumber", "positionAt800", "positionAt400",
        "winningTime", "railPosition", "trackCondition", "trackRating",
        "weather", "rainfall", "penetrometer", "standardTimeDifference",
        "hasSectionals", "hasSpeedMap", "hasResults", "rdcClass",
    ]

    summary = [
        {"metric": "status", "value": "EDGEIQ_GRAPHQL_FIELD_INVENTORY_V1_BUILT"},
        {"metric": "input_files_found", "value": sum(1 for p in INPUTS if p.exists())},
        {"metric": "inventory_rows", "value": len(deduped)},
        {"metric": "unique_field_names", "value": len(set(r["field_name"] for r in deduped))},
        {"metric": "built_at", "value": built_at},
    ]

    names = set(r["field_name"] for r in deduped)
    for w in wanted:
        summary.append({"metric": f"has_{w}", "value": "YES" if w in names else "NO"})

    with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("[EDGEIQ_GRAPHQL_FIELD_INVENTORY_V1] COMPLETE")
    print(f"rows={len(deduped)}")
    print(f"output={OUT}")
    print(f"summary={SUMMARY}")


if __name__ == "__main__":
    main()
