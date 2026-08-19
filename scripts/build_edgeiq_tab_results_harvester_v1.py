import json
import re
import time
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RACECARDS = DATA / "edgeiq_tab_vic_racecards_v1.csv"
OUT = DATA / "edgeiq_tab_results_warehouse_v1.csv"
AUDIT = DATA / "edgeiq_tab_results_warehouse_v1_audit.csv"
RAW_DIR = DATA / "edgeiq_tab_results_raw_v1"

RAW_DIR.mkdir(parents=True, exist_ok=True)

COLUMNS = [
    "scraped_at","source","meeting_date","track","race_no","horse","horse_canon",
    "runner_no","finish_position_raw","finish_position","result_status",
    "tab_fixed_win","tab_fixed_place","fixed_win_dividend","fixed_place_dividend",
    "tab_fixed_betting_status","api_url","runner_list_path"
]

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 EDGEiQ-Racing/1.0",
    "Accept": "application/json,text/plain,*/*",
})

def canon(x):
    s = "" if pd.isna(x) else str(x).upper().strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]+", "", s)
    return s

def safe(x):
    return "" if x is None or (isinstance(x, float) and pd.isna(x)) else str(x).strip()

def num(x):
    try:
        s = safe(x).replace("$", "")
        return float(s) if s else np.nan
    except Exception:
        return np.nan

def first_value(obj, keys):
    if not isinstance(obj, dict):
        return None
    lower = {str(k).lower(): k for k in obj.keys()}
    for key in keys:
        if key.lower() in lower:
            return obj.get(lower[key.lower()])
    return None

def deep_find_runner_lists(obj):
    found = []
    def walk(x, path=""):
        if isinstance(x, list):
            if x and all(isinstance(i, dict) for i in x):
                keys = set()
                for item in x[:5]:
                    keys |= {str(k).lower() for k in item.keys()}
                if any(k in keys for k in ["runnername","name","runnernumber","result","placing","position","finishposition"]):
                    found.append((path, x))
            for i, v in enumerate(x):
                walk(v, f"{path}[{i}]")
        elif isinstance(x, dict):
            for k, v in x.items():
                walk(v, f"{path}.{k}" if path else str(k))
    walk(obj)
    return found

def runner_name(r):
    return safe(first_value(r, ["runnerName","runner_name","horse","name","selectionName"]))

def runner_no(r):
    return safe(first_value(r, ["runnerNumber","runner_number","runnerNo","runner_no","number","saddlecloth"]))

def finish_pos(r):
    direct = first_value(r, ["finishPosition","finish_position","resultPosition","placing","place","position"])
    if direct is not None:
        return safe(direct)
    res = first_value(r, ["result","runnerResult"])
    if isinstance(res, dict):
        nested = first_value(res, ["finishPosition","resultPosition","placing","place","position"])
        if nested is not None:
            return safe(nested)
    return ""

def norm_pos(x):
    s = safe(x).upper()
    if not s or "SCR" in s:
        return np.nan
    m = re.search(r"\d+", s)
    return float(m.group(0)) if m else np.nan

def get_json_with_retries(url, attempts=3):
    last_err = ""
    for i in range(attempts):
        try:
            r = SESSION.get(url, timeout=60)
            if r.status_code != 200:
                last_err = f"HTTP_{r.status_code}: {r.text[:200]}"
            else:
                return r.json(), ""
        except Exception as e:
            last_err = repr(e)
            time.sleep(2 + i)
    return None, last_err

def main():
    if not RACECARDS.exists():
        raise FileNotFoundError(f"Missing {RACECARDS}")

    cards = pd.read_csv(RACECARDS)
    races = cards[["meeting_date","meeting_name","race_no","api_url"]].drop_duplicates()

    rows = []
    audit = []

    for _, race in races.iterrows():
        meeting_date = safe(race["meeting_date"])[:10]
        track = safe(race["meeting_name"]).upper()
        race_no = safe(race["race_no"])
        url = safe(race["api_url"])

        data, err = get_json_with_retries(url)
        before = len(rows)

        if data is None:
            audit.append({"meeting_date":meeting_date,"track":track,"race_no":race_no,"status":"ERROR","rows_added":0,"error":err})
            continue

        raw_path = RAW_DIR / f"{meeting_date}_{track}_R{race_no}.json".replace(" ","_")
        raw_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        lists = deep_find_runner_lists(data)
        best_path, best = "", []

        for path, lst in lists:
            usable = [r for r in lst if runner_name(r) or runner_no(r) or finish_pos(r)]
            if len(usable) > len(best):
                best_path, best = path, usable

        if not best:
            audit.append({"meeting_date":meeting_date,"track":track,"race_no":race_no,"status":"NO_RUNNER_LIST_FOUND","rows_added":0,"error":""})
            continue

        for r in best:
            h = runner_name(r)
            rn = runner_no(r)
            fp_raw = finish_pos(r)
            fp = norm_pos(fp_raw)

            cm = cards[
                (cards["meeting_date"].astype(str).str.slice(0,10) == meeting_date) &
                (cards["meeting_name"].astype(str).str.upper().str.strip() == track) &
                (cards["race_no"].astype(str) == str(race_no)) &
                (cards["horse"].apply(canon) == canon(h))
            ]

            tab_win = np.nan
            tab_place = np.nan
            status = ""

            if len(cm):
                last = cm.iloc[-1]
                tab_win = num(last.get("tab_fixed_win"))
                tab_place = num(last.get("tab_fixed_place"))
                status = safe(last.get("tab_fixed_betting_status"))

            result_status = "RESULT" if pd.notna(fp) else "PENDING_OR_NO_POSITION"
            if "SCRATCH" in status.upper():
                result_status = "SCRATCHED"

            rows.append({
                "scraped_at": datetime.now().isoformat(timespec="seconds"),
                "source": "TAB",
                "meeting_date": meeting_date,
                "track": track,
                "race_no": race_no,
                "horse": h,
                "horse_canon": canon(h),
                "runner_no": rn,
                "finish_position_raw": fp_raw,
                "finish_position": fp,
                "result_status": result_status,
                "tab_fixed_win": tab_win,
                "tab_fixed_place": tab_place,
                "fixed_win_dividend": tab_win,
                "fixed_place_dividend": tab_place,
                "tab_fixed_betting_status": status,
                "api_url": url,
                "runner_list_path": best_path,
            })

        audit.append({"meeting_date":meeting_date,"track":track,"race_no":race_no,"status":"ROWS_BUILT","rows_added":len(rows)-before,"error":""})
        time.sleep(0.5)

    new = pd.DataFrame(rows, columns=COLUMNS)

    if OUT.exists():
        try:
            old = pd.read_csv(OUT)
        except Exception:
            old = pd.DataFrame(columns=COLUMNS)
        combined = pd.concat([old, new], ignore_index=True)
        if len(combined):
            combined = combined.drop_duplicates(["meeting_date","track","race_no","horse_canon"], keep="last")
    else:
        combined = new

    combined = combined.reindex(columns=COLUMNS)
    combined.to_csv(OUT, index=False)

    summary = pd.DataFrame([
        {"metric":"races_checked","value":len(races)},
        {"metric":"rows_built_this_run","value":len(new)},
        {"metric":"warehouse_total_rows","value":len(combined)},
        {"metric":"finish_positions","value":int(pd.to_numeric(combined["finish_position"], errors="coerce").notna().sum()) if len(combined) else 0},
    ])

    pd.concat([summary, pd.DataFrame(audit)], ignore_index=True).to_csv(AUDIT, index=False)

    print("[TAB_RESULTS_HARVESTER_V1] COMPLETE")
    print(f"races_checked={len(races)}")
    print(f"rows_built_this_run={len(new)}")
    print(f"warehouse_total_rows={len(combined)}")
    print(f"finish_positions={int(pd.to_numeric(combined['finish_position'], errors='coerce').notna().sum()) if len(combined) else 0}")
    print(f"wrote={OUT}")
    print(f"audit={AUDIT}")

if __name__ == "__main__":
    main()
