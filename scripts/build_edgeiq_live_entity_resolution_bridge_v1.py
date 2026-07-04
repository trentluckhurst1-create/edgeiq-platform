import csv
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

BASE = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = BASE / "public" / "data"

RES = DATA / "edgeiq_entity_resolution_master_v1.csv"

LIVE_CANDIDATES = [
    DATA / "edgeiq_live_runner_board_governed_v1.csv",
    DATA / "edgeiq_live_runner_board_v1.csv",
    DATA / "edgeiq_live_terminal_feed_v1.csv",
]

OUT = DATA / "edgeiq_live_entity_resolution_bridge_v1.csv"
SUMMARY = DATA / "edgeiq_live_entity_resolution_bridge_v1_summary.csv"

def clean(v):
    return (v or "").strip()

def norm(v):
    return re.sub(r"[^A-Z0-9]", "", clean(v).upper())

def tokens(v):
    return re.findall(r"[A-Z0-9]+", clean(v).upper())

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def pick_source():
    for p in LIVE_CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError("No live runner source found")

def first_value(row, names):
    for n in names:
        v = clean(row.get(n))
        if v:
            return v
    return ""

res_rows = read_csv(RES)
source = pick_source()
live_rows = read_csv(source)

by_exact = {}
by_surname = defaultdict(list)
canonical_rows = []

for r in res_rows:
    et = clean(r.get("entity_type")).upper()
    mk = clean(r.get("match_key")).upper()
    cn = clean(r.get("canonical_name"))
    ck = clean(r.get("canonical_key"))
    rs = int(clean(r.get("rows_seen")) or 0)

    if not et or not mk:
        continue

    by_exact[(et, mk)] = r

    if ck:
        t = tokens(ck)
        if t:
            surname = re.sub(r"[^A-Z0-9]", "", t[-1])
            by_surname[(et, surname)].append(r)

    if cn:
        t = tokens(cn)
        if t:
            surname = re.sub(r"[^A-Z0-9]", "", t[-1])
            by_surname[(et, surname)].append(r)

    canonical_rows.append(r)

for k in list(by_surname.keys()):
    seen = {}
    for r in by_surname[k]:
        ck = clean(r.get("canonical_key"))
        if ck not in seen:
            seen[ck] = r
        else:
            if int(clean(r.get("rows_seen")) or 0) > int(clean(seen[ck].get("rows_seen")) or 0):
                seen[ck] = r
    by_surname[k] = sorted(seen.values(), key=lambda x: int(clean(x.get("rows_seen")) or 0), reverse=True)

def jockey_initial_surname_key(name):
    t = tokens(name)
    if len(t) < 2:
        return norm(name)
    return t[0][0] + t[-1]

def trainer_compact_key(name):
    t = tokens(name)
    if not t:
        return ""

    stop = {"AND", "THE", "STABLE", "RACING", "JNR", "JR"}
    kept = [x for x in t if x not in stop]

    if not kept:
        kept = t

    if len(kept) == 1:
        return kept[0]

    surname = kept[-1]
    initials = "".join(x[0] if not re.fullmatch(r"[A-Z]{1,3}", x) else x for x in kept[:-1])
    return initials + surname

def resolve(entity_type, display_name):
    et = entity_type.upper()
    dn = clean(display_name)
    candidates = []

    exact = norm(dn)
    if exact:
        candidates.append(("EXACT_NORM", exact))

    if et == "JOCKEY":
        candidates.append(("JOCKEY_INITIAL_SURNAME", jockey_initial_surname_key(dn)))

    if et == "TRAINER":
        candidates.append(("TRAINER_COMPACT", trainer_compact_key(dn)))

    for method, cand in candidates:
        if (et, cand) in by_exact:
            r = by_exact[(et, cand)]
            return {
                "method": method,
                "display_name": dn,
                "display_key": exact,
                "canonical_name": clean(r.get("canonical_name")),
                "canonical_key": clean(r.get("canonical_key")),
                "match_status": "MATCHED",
                "rows_seen": clean(r.get("rows_seen")),
            }

    t = tokens(dn)
    surname = t[-1] if t else ""

    if surname and (et, surname) in by_surname:
        options = by_surname[(et, surname)]
        if len(options) == 1:
            r = options[0]
            return {
                "method": "UNIQUE_SURNAME",
                "display_name": dn,
                "display_key": exact,
                "canonical_name": clean(r.get("canonical_name")),
                "canonical_key": clean(r.get("canonical_key")),
                "match_status": "MATCHED",
                "rows_seen": clean(r.get("rows_seen")),
            }

        top = options[0]
        if int(clean(top.get("rows_seen")) or 0) >= 5 * max(1, int(clean(options[1].get("rows_seen")) or 0)):
            return {
                "method": "DOMINANT_SURNAME",
                "display_name": dn,
                "display_key": exact,
                "canonical_name": clean(top.get("canonical_name")),
                "canonical_key": clean(top.get("canonical_key")),
                "match_status": "MATCHED",
                "rows_seen": clean(top.get("rows_seen")),
            }

    return {
        "method": "NO_MATCH",
        "display_name": dn,
        "display_key": exact,
        "canonical_name": "",
        "canonical_key": "",
        "match_status": "NO_MATCH",
        "rows_seen": "",
    }

seen = {}
out_rows = []

for r in live_rows:
    trainer = first_value(r, ["trainer_canonical","trainer","trainer_name"])
    jockey = first_value(r, ["jockey_canonical","jockey","jockey_name"])

    for et, name in [("TRAINER", trainer), ("JOCKEY", jockey)]:
        if not name or name.upper() in {"NOT NOTIFIED", "TBC"}:
            continue

        k = (et, norm(name))
        if k in seen:
            continue
        seen[k] = True

        resolved = resolve(et, name)
        out_rows.append({
            "entity_type": et,
            "display_name": resolved["display_name"],
            "display_key": resolved["display_key"],
            "canonical_name": resolved["canonical_name"],
            "canonical_key": resolved["canonical_key"],
            "match_status": resolved["match_status"],
            "method": resolved["method"],
            "rows_seen": resolved["rows_seen"],
            "source_file": source.name,
            "built_at": datetime.now().isoformat(),
        })

out_rows.sort(key=lambda r: (r["entity_type"], r["match_status"], r["display_name"]))

with OUT.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "entity_type",
            "display_name",
            "display_key",
            "canonical_name",
            "canonical_key",
            "match_status",
            "method",
            "rows_seen",
            "source_file",
            "built_at",
        ]
    )
    writer.writeheader()
    writer.writerows(out_rows)

summary = [
    {"metric":"status","value":"COMPLETE"},
    {"metric":"source_file","value":source.name},
    {"metric":"live_rows","value":len(live_rows)},
    {"metric":"entities_checked","value":len(out_rows)},
    {"metric":"matched","value":sum(1 for r in out_rows if r["match_status"]=="MATCHED")},
    {"metric":"no_match","value":sum(1 for r in out_rows if r["match_status"]=="NO_MATCH")},
    {"metric":"trainer_matched","value":sum(1 for r in out_rows if r["entity_type"]=="TRAINER" and r["match_status"]=="MATCHED")},
    {"metric":"jockey_matched","value":sum(1 for r in out_rows if r["entity_type"]=="JOCKEY" and r["match_status"]=="MATCHED")},
    {"metric":"built_at","value":datetime.now().isoformat()},
]

with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["metric","value"])
    writer.writeheader()
    writer.writerows(summary)

print("[EDGEIQ_LIVE_ENTITY_RESOLUTION_BRIDGE_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
