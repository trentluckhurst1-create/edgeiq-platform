from pathlib import Path
import pandas as pd
import math
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIMITED = DATA / "edgeiq_limited_data_market_adjusted_v1.csv"

TARGETS = [
    DATA / "edgeiq_live_runner_board_v1.csv",
    DATA / "edgeiq_live_runner_board_governed_v1.csv",
]

def safe(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def canon_track(x):
    return re.sub(r"[^A-Z0-9]", "", safe(x).upper())

def canon_horse(x):
    x = re.sub(r"\([^)]*\)", "", safe(x).upper())
    return re.sub(r"[^A-Z0-9]", "", x)

def race_key(x):
    s = safe(x)
    s = re.sub(r"[^0-9]", "", s)
    return s

def num(x):
    try:
        s = safe(x).replace("$","").replace(",","")
        if not s:
            return math.nan
        return float(s)
    except:
        return math.nan

def fmt(x):
    if math.isnan(x):
        return ""
    return str(round(x, 2)).rstrip("0").rstrip(".")

def edge(live, fair):
    l = num(live)
    f = num(fair)
    if math.isnan(l) or math.isnan(f) or f <= 0:
        return ""
    return str(round(((l / f) - 1) * 100, 1))

def action_from_edge(edge_txt, limited_decision):
    e = num(edge_txt)

    ld = safe(limited_decision).upper()

    if ld == "UPGRADE_WATCH":
        return "WATCH"
    if ld == "SLIGHT_UPGRADE":
        return "WATCH"
    if ld == "PENALISE_HARD":
        return "UNDERLAY"
    if ld == "PENALISE":
        return "UNDERLAY"

    if math.isnan(e):
        return "PASS"
    if e >= 18:
        return "WATCH"
    if e >= 6:
        return "LEAN"
    if e <= -18:
        return "UNDERLAY"
    return "PASS"

if not LIMITED.exists():
    raise SystemExit(f"Missing {LIMITED}")

lim = pd.read_csv(LIMITED, dtype=str).fillna("")
lim["_k"] = lim.apply(lambda r: "|".join([
    canon_track(r.get("track","")),
    race_key(r.get("race_no","")),
    canon_horse(r.get("horse","")),
]), axis=1)

lim = lim.drop_duplicates("_k", keep="last")

lookup = {
    r["_k"]: r
    for _, r in lim.iterrows()
    if safe(r.get("limited_data_adjusted_price_v1",""))
}

summary = []

for target in TARGETS:
    if not target.exists():
        summary.append((target.name, "MISSING", 0, 0))
        continue

    df = pd.read_csv(target, dtype=str).fillna("")

    for col in [
        "model_fair_price_before_limited_v1",
        "edgeiq_price_source_v1",
        "limited_data_adjusted_price_v1",
        "limited_data_factor_score_v1",
        "limited_data_decision_v1",
        "limited_data_reason_v1",
    ]:
        if col not in df.columns:
            df[col] = ""

    matched = 0

    for i, row in df.iterrows():
        k = "|".join([
            canon_track(row.get("track","")),
            race_key(row.get("race_no","")),
            canon_horse(row.get("horse","")),
        ])

        limrow = lookup.get(k)
        if limrow is None:
            continue

        adj = safe(limrow.get("limited_data_adjusted_price_v1",""))
        if not adj:
            continue

        # preserve old model price
        old_fair = safe(row.get("fair_price",""))
        if old_fair and not safe(df.at[i, "model_fair_price_before_limited_v1"]):
            df.at[i, "model_fair_price_before_limited_v1"] = old_fair

        # promote adjusted price into the actual EDGEiQ/Fair fields the UI already reads
        df.at[i, "fair_price"] = adj
        if "fair_price_raw" in df.columns:
            df.at[i, "fair_price_raw"] = adj
        if "fair_price_display" in df.columns:
            df.at[i, "fair_price_display"] = adj
        if "display_fair_price_governed" in df.columns:
            df.at[i, "display_fair_price_governed"] = adj

        df.at[i, "limited_data_adjusted_price_v1"] = adj
        df.at[i, "limited_data_factor_score_v1"] = safe(limrow.get("limited_data_factor_score_v1",""))
        df.at[i, "limited_data_decision_v1"] = safe(limrow.get("limited_data_decision_v1",""))
        df.at[i, "limited_data_reason_v1"] = safe(limrow.get("limited_data_reason_v1",""))
        df.at[i, "edgeiq_price_source_v1"] = "LIMITED_DATA_MARKET_ADJUSTED_V1"

        new_edge = edge(row.get("live_price",""), adj)
        if "edge_pct" in df.columns:
            df.at[i, "edge_pct"] = new_edge
        if "edge_pct_raw" in df.columns:
            df.at[i, "edge_pct_raw"] = new_edge
        if "edge_pct_display" in df.columns:
            df.at[i, "edge_pct_display"] = new_edge

        new_action = action_from_edge(new_edge, limrow.get("limited_data_decision_v1",""))
        if "execution_action" in df.columns:
            df.at[i, "execution_action"] = new_action
        if "execution_action_raw" in df.columns:
            df.at[i, "execution_action_raw"] = new_action
        if "execution_action_governed" in df.columns:
            df.at[i, "execution_action_governed"] = new_action

        matched += 1

    df.to_csv(target, index=False)
    summary.append((target.name, "UPDATED", len(df), matched))

pd.DataFrame(summary, columns=["file","status","rows","limited_prices_promoted"]).to_csv(
    DATA / "edgeiq_promote_limited_data_price_to_runner_board_v1_summary.csv",
    index=False
)

print("[PROMOTE_LIMITED_DATA_PRICE_TO_RUNNER_BOARD_V1] COMPLETE")
for s in summary:
    print(s)
