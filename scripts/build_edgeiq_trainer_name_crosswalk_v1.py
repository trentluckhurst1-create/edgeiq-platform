from pathlib import Path
import pandas as pd
from datetime import datetime, timezone
import difflib

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

WAREHOUSE = DATA / "edgeiq_composite_dna_v2_1.csv"
LIVE_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"

OUT = DATA / "edgeiq_trainer_name_crosswalk_v1.csv"
SUMMARY = DATA / "edgeiq_trainer_name_crosswalk_v1_summary.csv"

def clean(v):
    return "" if pd.isna(v) else str(v).strip()

def nkey(v):
    return clean(v).upper().replace(".", "").replace(" ", "").replace("-", "").replace("'", "").replace("(", "").replace(")", "").replace("&", "AND")

def compact_alias(v):
    s = nkey(v)
    aliases = {
        "CIARONMAHER": "CMAHER",
        "GRAHAMEBEGG": "GMBEGG",
        "GAVINBEDGGOOD": "GMBEDGGOOD",
        "CHRISWALLER": "CJWALLER",
        "DOMINICSUTTON": "DSUTTON",
        "MICHAELKENT": "MCKENT",
        "MATTLAURIE": "MLAURIE",
        "PHILLIPSTOKES": "PJSTOKES",
        "BENWILLANDJDHAYES": "BWJDHAYES",
        "MICKPRICEANDMICHAELKENTJNR": "MPRICEMKENTJNR",
        "ANTHONYANDSAMFREEDMAN": "ASFREEDMAN",
        "TONYANDCALVINMCEVOY": "TCMCEVOY",
        "TRENTBUSUTTINANDNATALIEYOUNG": "TBUSUTTINNYOUNG",
        "SHANENICHOLSANDHAYDENBLACK": "SNICHOLSHBLACK",
        "PATCAREYANDHARRISWALKER": "PCAREYHWALKER",
        "KENANDKASEYKEYS": "KKEYS",
    }
    return aliases.get(s, s)

warehouse = pd.read_csv(WAREHOUSE, low_memory=False)
live = pd.read_csv(LIVE_BOARD, low_memory=False)

warehouse_t = (
    warehouse[warehouse["entity_type"].astype(str).str.upper() == "TRAINER"]
    [["entity_name"]]
    .drop_duplicates()
    .rename(columns={"entity_name": "warehouse_trainer"})
)

live_t = (
    live[["trainer"]]
    .drop_duplicates()
    .rename(columns={"trainer": "live_trainer"})
)

warehouse_t["warehouse_key"] = warehouse_t["warehouse_trainer"].apply(nkey)
warehouse_t["warehouse_alias_key"] = warehouse_t["warehouse_trainer"].apply(compact_alias)

live_t["live_key"] = live_t["live_trainer"].apply(nkey)
live_t["live_alias_key"] = live_t["live_trainer"].apply(compact_alias)

warehouse_lookup_key = {r["warehouse_key"]: r["warehouse_trainer"] for _, r in warehouse_t.iterrows()}
warehouse_lookup_alias = {r["warehouse_alias_key"]: r["warehouse_trainer"] for _, r in warehouse_t.iterrows()}
warehouse_key_list = list(warehouse_lookup_key.keys())
warehouse_alias_list = list(warehouse_lookup_alias.keys())

rows = []
built_at = datetime.now(timezone.utc).isoformat()

for _, r in live_t.iterrows():
    live_name = clean(r["live_trainer"])
    live_key = r["live_key"]
    live_alias = r["live_alias_key"]

    if not live_name:
        status = "BLANK"
        matched = ""
        method = ""
        score = 0
    elif live_key in warehouse_lookup_key:
        status = "EXACT_MATCH"
        matched = warehouse_lookup_key[live_key]
        method = "FULL_KEY"
        score = 100
    elif live_alias in warehouse_lookup_alias:
        status = "ALIAS_MATCH"
        matched = warehouse_lookup_alias[live_alias]
        method = "ALIAS_KEY"
        score = 97
    else:
        close_alias = difflib.get_close_matches(live_alias, warehouse_alias_list, n=1, cutoff=0.72)
        close_key = difflib.get_close_matches(live_key, warehouse_key_list, n=1, cutoff=0.72)

        if close_alias:
            status = "FUZZY_ALIAS_MATCH"
            matched = warehouse_lookup_alias[close_alias[0]]
            method = "DIFFLIB_ALIAS"
            score = round(difflib.SequenceMatcher(None, live_alias, close_alias[0]).ratio() * 100, 1)
        elif close_key:
            status = "FUZZY_MATCH"
            matched = warehouse_lookup_key[close_key[0]]
            method = "DIFFLIB"
            score = round(difflib.SequenceMatcher(None, live_key, close_key[0]).ratio() * 100, 1)
        else:
            status = "UNMATCHED"
            matched = ""
            method = ""
            score = 0

    rows.append({
        "built_at": built_at,
        "live_trainer": live_name,
        "live_key": live_key,
        "live_alias_key": live_alias,
        "matched_warehouse_trainer": matched,
        "match_status": status,
        "match_method": method,
        "match_score": score,
    })

out = pd.DataFrame(rows).sort_values(["match_status", "live_trainer"])

out.to_csv(OUT, index=False)

summary = pd.DataFrame([
    ["status","EDGEIQ_TRAINER_NAME_CROSSWALK_V1_BUILT"],
    ["live_trainers",len(out)],
    ["exact_match",int((out["match_status"]=="EXACT_MATCH").sum())],
    ["alias_match",int((out["match_status"]=="ALIAS_MATCH").sum())],
    ["fuzzy_alias_match",int((out["match_status"]=="FUZZY_ALIAS_MATCH").sum())],
    ["fuzzy_match",int((out["match_status"]=="FUZZY_MATCH").sum())],
    ["unmatched",int((out["match_status"]=="UNMATCHED").sum())],
    ["blank",int((out["match_status"]=="BLANK").sum())],
    ["warehouse_trainers",len(warehouse_t)],
    ["output",str(OUT)],
    ["built_at",built_at],
], columns=["metric","value"])

summary.to_csv(SUMMARY,index=False)

print("[TRAINER_NAME_CROSSWALK_V1] COMPLETE")
print(f"live_trainers={len(out)}")
print(f"output={OUT}")
