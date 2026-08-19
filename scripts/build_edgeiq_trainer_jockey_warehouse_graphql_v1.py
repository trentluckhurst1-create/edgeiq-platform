import re
import json
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_graphql_q1_apr_2025_MASTER_v1.csv"

TRAINER_OUT = DATA / "edgeiq_trainer_warehouse_v1.csv"
JOCKEY_OUT = DATA / "edgeiq_jockey_warehouse_v1.csv"
COMBO_OUT = DATA / "edgeiq_trainer_jockey_combo_warehouse_v1.csv"
RUNNER_OUT = DATA / "edgeiq_trainer_jockey_runner_history_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_trainer_jockey_warehouse_v1_summary.csv"
AUDIT_OUT = DATA / "edgeiq_trainer_jockey_warehouse_v1_audit.json"

def clean_text(x):
    if pd.isna(x):
        return ""
    return re.sub(r"\s+", " ", str(x).strip().upper())

def key_text(x):
    return re.sub(r"[^A-Z0-9]+", "", clean_text(x))

def find_col(df, names):
    lookup = {str(c).strip().lower(): c for c in df.columns}
    for n in names:
        if n.lower() in lookup:
            return lookup[n.lower()]
    return None

def to_num(s):
    return pd.to_numeric(s, errors="coerce")

def first_non_blank(series):
    for v in series:
        if str(v).strip():
            return v
    return ""

def summarise_entity(df, key_col, name_col, label):
    g = df.groupby(key_col, dropna=False)

    rows = []
    for key, x in g:
        if not str(key).strip():
            continue

        starts = len(x)
        wins = int(x["won_v1"].sum())
        places = int(x["placed_v1"].sum())

        rows.append({
            f"{label}_key": key,
            f"{label}_name": first_non_blank(x[name_col]),
            "starts": starts,
            "wins": wins,
            "places": places,
            "win_pct": round(wins / starts * 100, 2) if starts else 0,
            "place_pct": round(places / starts * 100, 2) if starts else 0,
            "unique_horses": int(x["horse_key"].nunique()),
            "unique_races": int(x["race_key_v1"].nunique()),
            "first_meeting_date": str(x["meeting_date"].min()),
            "last_meeting_date": str(x["meeting_date"].max()),
            "avg_finish_position": round(to_num(x["finish_position_v1"]).mean(), 2),
            "median_finish_position": round(to_num(x["finish_position_v1"]).median(), 2),
        })

    out = pd.DataFrame(rows)
    if len(out):
        out = out.sort_values(["wins", "starts"], ascending=False)
    return out

def main():
    if not SRC.exists():
        raise SystemExit(f"Missing source file: {SRC}")

    df = pd.read_csv(SRC, low_memory=False)

    colmap = {
        "meeting_date": find_col(df, ["meeting_date", "race_date", "date"]),
        "track": find_col(df, ["track", "meeting_name", "location"]),
        "race_no": find_col(df, ["race_no", "race_number"]),
        "horse": find_col(df, ["horseName", "horse", "runner", "runner_name"]),
        "trainer": find_col(df, ["trainer", "trainerName", "trainer_name"]),
        "jockey": find_col(df, ["jockey", "jockeyName", "jockey_name"]),
        "finish": find_col(df, ["finish_position", "finish_raw", "finish", "finishPosition", "placing", "place"]),
        "barrier": find_col(df, ["barrier"]),
        "weight": find_col(df, ["weight"]),
        "sp": find_col(df, ["sp", "SP", "starting_price"]),
        "distance": find_col(df, ["distance"]),
        "race_class": find_col(df, ["raceClass", "race_class"]),
        "track_condition": find_col(df, ["trackCondition", "track_condition"]),
    }

    required = ["meeting_date", "track", "race_no", "horse", "trainer", "jockey", "finish"]
    missing = [k for k in required if not colmap[k]]
    if missing:
        raise SystemExit("Missing required result columns: " + ", ".join(missing) + "\nFound map: " + json.dumps(colmap, indent=2))

    out = pd.DataFrame()
    out["meeting_date"] = df[colmap["meeting_date"]].astype(str).str.strip()
    out["track"] = df[colmap["track"]].map(clean_text)
    out["race_no"] = df[colmap["race_no"]].astype(str).str.extract(r"(\d+)", expand=False).fillna(df[colmap["race_no"]].astype(str))
    out["horse"] = df[colmap["horse"]].map(clean_text)
    out["horse_key"] = out["horse"].map(key_text)
    out["trainer"] = df[colmap["trainer"]].map(clean_text)
    out["trainer_key"] = out["trainer"].map(key_text)
    out["jockey"] = df[colmap["jockey"]].map(clean_text)
    out["jockey_key"] = out["jockey"].map(key_text)
    out["finish_position_v1"] = to_num(df[colmap["finish"]])
    out["won_v1"] = out["finish_position_v1"].eq(1).astype(int)
    out["placed_v1"] = out["finish_position_v1"].between(1, 3, inclusive="both").astype(int)

    out["barrier"] = df[colmap["barrier"]] if colmap["barrier"] else ""
    out["weight"] = df[colmap["weight"]] if colmap["weight"] else ""
    out["sp"] = df[colmap["sp"]] if colmap["sp"] else ""
    out["distance"] = df[colmap["distance"]] if colmap["distance"] else ""
    out["race_class"] = df[colmap["race_class"]] if colmap["race_class"] else ""
    out["track_condition"] = df[colmap["track_condition"]] if colmap["track_condition"] else ""

    out["race_key_v1"] = out["meeting_date"] + "|" + out["track"].map(key_text) + "|R" + out["race_no"].astype(str)
    out["trainer_jockey_key_v1"] = out["trainer_key"] + "|" + out["jockey_key"]

    out = out[
        (out["meeting_date"].astype(str).str.len() > 0) &
        (out["track"].astype(str).str.len() > 0) &
        (out["race_no"].astype(str).str.len() > 0) &
        (out["horse_key"].astype(str).str.len() > 0)
    ].copy()

    RUNNER_OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(RUNNER_OUT, index=False)

    trainer = summarise_entity(out, "trainer_key", "trainer", "trainer")
    jockey = summarise_entity(out, "jockey_key", "jockey", "jockey")

    combo_rows = []
    for combo, x in out.groupby("trainer_jockey_key_v1", dropna=False):
        if not str(combo).strip() or combo == "|":
            continue
        starts = len(x)
        wins = int(x["won_v1"].sum())
        places = int(x["placed_v1"].sum())
        combo_rows.append({
            "trainer_jockey_key_v1": combo,
            "trainer_key": first_non_blank(x["trainer_key"]),
            "trainer": first_non_blank(x["trainer"]),
            "jockey_key": first_non_blank(x["jockey_key"]),
            "jockey": first_non_blank(x["jockey"]),
            "starts": starts,
            "wins": wins,
            "places": places,
            "win_pct": round(wins / starts * 100, 2) if starts else 0,
            "place_pct": round(places / starts * 100, 2) if starts else 0,
            "unique_horses": int(x["horse_key"].nunique()),
            "unique_races": int(x["race_key_v1"].nunique()),
            "first_meeting_date": str(x["meeting_date"].min()),
            "last_meeting_date": str(x["meeting_date"].max()),
        })

    combo_df = pd.DataFrame(combo_rows)
    if len(combo_df):
        combo_df = combo_df.sort_values(["wins", "starts"], ascending=False)

    trainer.to_csv(TRAINER_OUT, index=False)
    jockey.to_csv(JOCKEY_OUT, index=False)
    combo_df.to_csv(COMBO_OUT, index=False)

    summary = pd.DataFrame([
        {"metric": "status", "value": "COMPLETE"},
        {"metric": "source", "value": str(SRC)},
        {"metric": "runner_rows", "value": len(out)},
        {"metric": "unique_races", "value": out["race_key_v1"].nunique()},
        {"metric": "unique_horses", "value": out["horse_key"].nunique()},
        {"metric": "unique_trainers", "value": out["trainer_key"].replace("", pd.NA).dropna().nunique()},
        {"metric": "unique_jockeys", "value": out["jockey_key"].replace("", pd.NA).dropna().nunique()},
        {"metric": "unique_trainer_jockey_combos", "value": out["trainer_jockey_key_v1"].replace("|", pd.NA).dropna().nunique()},
        {"metric": "first_meeting_date", "value": out["meeting_date"].min()},
        {"metric": "last_meeting_date", "value": out["meeting_date"].max()},
        {"metric": "trainer_missing_rows", "value": int((out["trainer_key"] == "").sum())},
        {"metric": "jockey_missing_rows", "value": int((out["jockey_key"] == "").sum())},
        {"metric": "trainer_missing_pct", "value": round((out["trainer_key"] == "").mean() * 100, 2)},
        {"metric": "jockey_missing_pct", "value": round((out["jockey_key"] == "").mean() * 100, 2)},
    ])
    summary.to_csv(SUMMARY_OUT, index=False)

    audit = {
        "status": "COMPLETE",
        "source": str(SRC),
        "column_map": colmap,
        "runner_rows": int(len(out)),
        "unique_races": int(out["race_key_v1"].nunique()),
        "unique_horses": int(out["horse_key"].nunique()),
        "unique_trainers": int(out["trainer_key"].replace("", pd.NA).dropna().nunique()),
        "unique_jockeys": int(out["jockey_key"].replace("", pd.NA).dropna().nunique()),
        "outputs": {
            "runner_history": str(RUNNER_OUT),
            "trainer": str(TRAINER_OUT),
            "jockey": str(JOCKEY_OUT),
            "combo": str(COMBO_OUT),
            "summary": str(SUMMARY_OUT),
        }
    }
    AUDIT_OUT.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    print("[TRAINER_JOCKEY_WAREHOUSE_V1] COMPLETE")
    print(f"runner_rows={len(out)}")
    print(f"unique_races={out['race_key_v1'].nunique()}")
    print(f"unique_horses={out['horse_key'].nunique()}")
    print(f"unique_trainers={out['trainer_key'].replace('', pd.NA).dropna().nunique()}")
    print(f"unique_jockeys={out['jockey_key'].replace('', pd.NA).dropna().nunique()}")
    print(f"trainer_missing_pct={round((out['trainer_key'] == '').mean() * 100, 2)}")
    print(f"jockey_missing_pct={round((out['jockey_key'] == '').mean() * 100, 2)}")
    print(f"wrote={RUNNER_OUT}")
    print(f"wrote={TRAINER_OUT}")
    print(f"wrote={JOCKEY_OUT}")
    print(f"wrote={COMBO_OUT}")
    print(f"wrote={SUMMARY_OUT}")

if __name__ == "__main__":
    main()
