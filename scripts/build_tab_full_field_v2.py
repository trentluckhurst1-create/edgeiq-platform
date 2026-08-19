import json
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "public" / "data" / "tab_single_race_raw_v1"
OUT = ROOT / "public" / "data" / "tab_full_field_v2.csv"

def norm_name(x):
    if x is None:
        return ""
    return str(x).replace("’", "'").replace("?", "'").strip().upper()

def safe_get(d, *keys, default=None):
    for k in keys:
        if isinstance(d, dict) and k in d:
            return d[k]
    return default

def parse_meta(name):
    parts = name.replace(".json","").split("_")
    if len(parts) < 3:
        return None
    return {
        "date": parts[0],
        "track": "SANDOWN HILLSIDE",
        "venue": parts[1],
        "race_no": int(parts[-1])
    }

def flatten(payload, meta):
    rows = []
    for r in payload.get("runners", []):
        fixed = r.get("fixedOdds", {}) or {}
        tote = r.get("toteOdds", {}) or {}

        rows.append({
            "race_date": meta["date"],
            "track": meta["track"],
            "venue": meta["venue"],
            "race_no": meta["race_no"],
            "runner_no": r.get("runnerNumber"),
            "horse": norm_name(r.get("runnerName")),
            "barrier": r.get("barrier"),
            "jockey": norm_name(r.get("jockey")),
            "trainer": norm_name(r.get("trainer")),
            "tab_fixed_win": safe_get(fixed,"returnWin"),
            "tab_fixed_place": safe_get(fixed,"returnPlace"),
            "tab_fixed_status": safe_get(fixed,"bettingStatus"),
            "tab_tote_win": safe_get(tote,"returnWin"),
            "tab_tote_place": safe_get(tote,"returnPlace")
        })
    return rows

def main():
    all_rows = []
    files = list(RAW_DIR.glob("*.json"))

    print("[FULL_FIELD_V2] files", len(files))

    for f in files:
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
            meta = parse_meta(f.name)
            if not meta:
                continue

            all_rows.extend(flatten(payload, meta))

        except Exception as e:
            print("[FAIL]", f.name, e)

    df = pd.DataFrame(all_rows)

    if df.empty:
        raise SystemExit("[FATAL] no data built")

    df.to_csv(OUT, index=False)

    print("[FULL_FIELD_V2 COMPLETE]")
    print("rows", len(df))
    print("races", df["race_no"].nunique())
    print("wrote", OUT)

if __name__ == "__main__":
    main()
