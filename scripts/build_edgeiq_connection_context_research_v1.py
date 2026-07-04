import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime

BASE = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = BASE / "public" / "data"

SRC = DATA / "edgeiq_trainer_jockey_runner_history_canonical_v1.csv"
OUT = DATA / "edgeiq_connection_context_research_v1.csv"
SUMMARY = DATA / "edgeiq_connection_context_research_v1_summary.csv"

def clean(v):
    return (v or "").strip()

rows = []
with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

trainer_base = defaultdict(lambda: {"starts":0,"wins":0,"places":0})
jockey_base = defaultdict(lambda: {"starts":0,"wins":0,"places":0})
combo_base = defaultdict(lambda: {"starts":0,"wins":0,"places":0})

for r in rows:
    trainer = clean(r.get("trainer_canonical"))
    jockey = clean(r.get("jockey_canonical"))
    combo = clean(r.get("trainer_jockey_canonical"))

    won = 1 if clean(r.get("won_v1")) == "1" else 0
    placed = 1 if clean(r.get("placed_v1")) == "1" else 0

    if trainer:
        trainer_base[trainer]["starts"] += 1
        trainer_base[trainer]["wins"] += won
        trainer_base[trainer]["places"] += placed

    if jockey:
        jockey_base[jockey]["starts"] += 1
        jockey_base[jockey]["wins"] += won
        jockey_base[jockey]["places"] += placed

    if trainer and jockey and combo:
        combo_base[(trainer, jockey, combo)]["starts"] += 1
        combo_base[(trainer, jockey, combo)]["wins"] += won
        combo_base[(trainer, jockey, combo)]["places"] += placed

out_rows = []

for (trainer, jockey, combo), g in combo_base.items():
    starts = g["starts"]
    if starts < 20:
        continue

    tb = trainer_base[trainer]
    jb = jockey_base[jockey]

    if tb["starts"] < 75 or jb["starts"] < 75:
        continue

    combo_win = g["wins"] / starts
    combo_place = g["places"] / starts

    trainer_win = tb["wins"] / tb["starts"]
    trainer_place = tb["places"] / tb["starts"]

    jockey_win = jb["wins"] / jb["starts"]
    jockey_place = jb["places"] / jb["starts"]

    trainer_win_lift = combo_win - trainer_win
    trainer_place_lift = combo_place - trainer_place

    jockey_win_lift = combo_win - jockey_win
    jockey_place_lift = combo_place - jockey_place

    if starts >= 35 and trainer_win_lift >= 0.04 and trainer_place_lift >= 0.06 and jockey_win_lift >= 0.02:
        signal = "CONNECTION_EDGE"
    elif starts >= 25 and trainer_win_lift >= 0.025 and trainer_place_lift >= 0.04:
        signal = "MILD_CONNECTION_EDGE"
    elif starts >= 35 and trainer_win_lift <= -0.035 and trainer_place_lift <= -0.05:
        signal = "CONNECTION_RISK"
    else:
        signal = "NEUTRAL"

    if signal == "CONNECTION_EDGE":
        insight = "Trainer/Jockey combination has historically outperformed the trainer baseline."
    elif signal == "MILD_CONNECTION_EDGE":
        insight = "Trainer/Jockey combination has shown a mild positive profile versus trainer baseline."
    elif signal == "CONNECTION_RISK":
        insight = "Trainer/Jockey combination has historically performed below trainer baseline."
    else:
        insight = "Trainer/Jockey combination has a neutral historical profile."

    out_rows.append({
        "trainer": trainer,
        "jockey": jockey,
        "connection": combo,
        "starts": starts,
        "wins": g["wins"],
        "places": g["places"],
        "combo_win_pct": round(combo_win * 100, 2),
        "combo_place_pct": round(combo_place * 100, 2),
        "trainer_base_starts": tb["starts"],
        "trainer_base_win_pct": round(trainer_win * 100, 2),
        "trainer_base_place_pct": round(trainer_place * 100, 2),
        "jockey_base_starts": jb["starts"],
        "jockey_base_win_pct": round(jockey_win * 100, 2),
        "jockey_base_place_pct": round(jockey_place * 100, 2),
        "combo_vs_trainer_win_lift_pct": round(trainer_win_lift * 100, 2),
        "combo_vs_trainer_place_lift_pct": round(trainer_place_lift * 100, 2),
        "combo_vs_jockey_win_lift_pct": round(jockey_win_lift * 100, 2),
        "combo_vs_jockey_place_lift_pct": round(jockey_place_lift * 100, 2),
        "signal": signal,
        "insight": insight,
    })

signal_order = {"CONNECTION_EDGE":0, "MILD_CONNECTION_EDGE":1, "CONNECTION_RISK":2, "NEUTRAL":3}
out_rows.sort(key=lambda r: (signal_order.get(r["signal"],9), -int(r["starts"]), r["trainer"], r["jockey"]))

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
    writer.writeheader()
    writer.writerows(out_rows)

summary = [
    {"metric":"status","value":"COMPLETE"},
    {"metric":"source_rows","value":len(rows)},
    {"metric":"unique_trainers","value":len(trainer_base)},
    {"metric":"unique_jockeys","value":len(jockey_base)},
    {"metric":"unique_connections_raw","value":len(combo_base)},
    {"metric":"context_rows","value":len(out_rows)},
    {"metric":"connection_edge","value":sum(1 for r in out_rows if r["signal"]=="CONNECTION_EDGE")},
    {"metric":"mild_connection_edge","value":sum(1 for r in out_rows if r["signal"]=="MILD_CONNECTION_EDGE")},
    {"metric":"connection_risk","value":sum(1 for r in out_rows if r["signal"]=="CONNECTION_RISK")},
    {"metric":"built_at","value":datetime.now().isoformat()},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric","value"])
    writer.writeheader()
    writer.writerows(summary)

print("[EDGEIQ_CONNECTION_CONTEXT_RESEARCH_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
