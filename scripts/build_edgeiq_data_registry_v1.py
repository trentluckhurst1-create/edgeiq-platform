from pathlib import Path
import csv, re, json

PUBLIC = Path("public/data")
CONFIG = Path("src/edgeiq-os/config")
SERVICES = Path("src/edgeiq-os/services")
CONFIG.mkdir(parents=True, exist_ok=True)

snapshot = SERVICES / "live-race-data-snapshot.ts"
registry = CONFIG / "dataRegistry.ts"
report = Path("public/data/edgeiq_data_registry_build_report_v1.txt")

def ck(x):
    return re.sub(r"[^a-z0-9]+", "", str(x).lower())

def is_url(x):
    return str(x or "").lower().startswith(("http://", "https://", "www."))

def is_numeric(x):
    return bool(re.fullmatch(r"\d+(\.\d+)?", str(x or "").strip()))

def read_csv(path, limit=None):
    with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for i, row in enumerate(reader):
            if limit and i >= limit:
                break
            rows.append(row)
        return reader.fieldnames or [], rows

def val(row, exact=(), contains=(), reject_url=False, reject_numeric=False):
    keyed = {ck(k): v for k, v in row.items()}
    for name in exact:
        v = keyed.get(ck(name))
        if v not in (None, ""):
            s = str(v).strip()
            if reject_url and is_url(s): continue
            if reject_numeric and is_numeric(s): continue
            return s
    for name in contains:
        needle = ck(name)
        for k, v in row.items():
            if needle in ck(k) and v not in (None, ""):
                s = str(v).strip()
                if reject_url and is_url(s): continue
                if reject_numeric and is_numeric(s): continue
                return s
    return ""

def esc(x):
    return str(x or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ")

EXCLUDE = ["stewards", "comment", "comments", "audit", "report", "summary", "archive", "truth", "snapshot_spine"]
PRIORITY_HINTS = [
    "edgeiq_live_runner_board",
    "live_runner_board",
    "edgeiq_live_terminal_feed",
    "terminal_feed",
    "runner_board",
    "current",
    "rated_market",
    "market_depth",
]

DNA_HINTS = [
    "edgeiq_runner_dna_drawer_feed",
    "runner_dna",
    "dna_v6",
    "dna",
]

def file_score(path, fields, rows, dna=False):
    name = path.name.lower()
    if any(x in name for x in EXCLUDE):
        return -999
    keys = [ck(f) for f in fields]
    score = 0
    for i, hint in enumerate(PRIORITY_HINTS if not dna else DNA_HINTS):
        if hint in name:
            score += 80 - i
    if any(k in keys for k in ["runner", "runnername", "horsename", "horse"]): score += 30
    if any("trainer" in k for k in keys): score += 8
    if any("jockey" in k for k in keys): score += 8
    if any(k in keys for k in ["barrier", "bar"]): score += 4
    if any("weight" in k or k == "wt" for k in keys): score += 4
    if any("price" in k or "market" in k or "fixedwin" in k or "liveprice" in k for k in keys): score += 8
    if any("dna" in k for k in keys): score += 8
    if any("rating" in k or "edge" in k for k in keys): score += 8

    sample = []
    for r in rows[:20]:
        sample.append(val(r, ["runner_name","runnerName","horse_name","horseName","runner","horse"], ["runner","horse","name"]))
    usable = [x for x in sample if x and not is_url(x)]
    numeric = [x for x in usable if is_numeric(x)]
    if usable and len(numeric) >= max(3, len(usable)//2):
        score -= 35
    return score

csvs = []
for p in PUBLIC.rglob("*.csv"):
    try:
        fields, rows = read_csv(p, limit=80)
        if rows:
            csvs.append((p, fields, rows))
    except Exception:
        pass

ranked = sorted(
    [(file_score(p, f, r, False), p, f, r) for p, f, r in csvs],
    key=lambda x: (x[0], str(x[1])),
    reverse=True,
)

dna_ranked = sorted(
    [(file_score(p, f, r, True), p, f, r) for p, f, r in csvs],
    key=lambda x: (x[0], str(x[1])),
    reverse=True,
)

base_score, base_file, base_fields, base_rows = ranked[0] if ranked else (0, Path(""), [], [])
dna_score, dna_file, dna_fields, dna_rows = dna_ranked[0] if dna_ranked else (0, Path(""), [], [])

dna_by_runner = {}
if dna_file:
    for row in dna_rows:
        runner = val(row, ["horse","runner_key","runner_name","runnerName","horse_name","horseName","runner"], ["horse","runner"], reject_numeric=True)
        if not runner:
            continue
        band = val(row, ["runner_dna_band","dna_v6_2_band","dna_band","dnaBand","overall_dna_band","projection_band_V6_1_RESEARCH","distance_fit_band"], ["dnaband","fitband"], reject_url=True)
        score = val(row, ["runner_dna_score","dna_v6_2_score","dna_score","dnaScore","overall_dna_score","distance_fit_score"], ["dnascore","fitscore"], reject_url=True)
        if band or score:
            dna_by_runner[ck(runner)] = (score, band)

records = []
seen = set()
for row in base_rows[:80]:
    runner = val(
        row,
        ["runner_name","runnerName","horse_name","horseName","runner","horse"],
        ["runner","horse","name"],
        reject_numeric=True,
        reject_url=True,
    )
    if not runner:
        continue
    key = ck(runner)
    if not key or key in seen:
        continue
    seen.add(key)

    dna_score_val, dna_band_val = dna_by_runner.get(key, ("", ""))
    dna_display = dna_band_val or (f"DNA {dna_score_val}" if dna_score_val else "")

    market = val(row, ["live_price","livePrice","fixed_win","fixedWin","market_price","marketPrice","market","price"], ["liveprice","fixedwin","market","price"])
    if market and market.upper() == "MISSING":
        market = ""

    edge = val(row, ["edge_rating","edgeRating","edge_score","edgeScore","rated_probability","rating","score"], ["edgerating","edgescore","rating"], reject_url=True)

    records.append({
        "runner": runner,
        "trainer": val(row, ["trainer","trainer_name","trainerName"], ["trainer"]),
        "jockey": val(row, ["jockey","jockey_name","jockeyName"], ["jockey"]),
        "barrier": val(row, ["barrier","bar"], ["barrier","bar"]),
        "weight": val(row, ["weight","wt"], ["weight","wt"]),
        "market": market,
        "runnerDNA": dna_display,
        "dnaScore": dna_score_val,
        "dnaBand": dna_band_val,
        "edgeRating": edge,
        "formUrl": val(row, ["formUrl","form_url","interactiveForm","interactive_form","horseFormUrl"], ["interactiveform","formurl","horseform"], reject_url=False),
    })

registry.write_text(f'''export const EDGEIQ_DATA_REGISTRY = {{
  liveRunnerBoard: "/data/{base_file.name}",
  runnerDNA: "/data/{dna_file.name if dna_file else ""}",
  sourceMode: "canonical-registry-v1",
}} as const;

export type EdgeiqDatasetKey = keyof typeof EDGEIQ_DATA_REGISTRY;
''', encoding="utf-8")

snapshot.write_text(
'''export type LiveRaceRunnerSnapshot = {
  runner: string;
  trainer?: string;
  jockey?: string;
  barrier?: string;
  weight?: string;
  market?: string;
  runnerDNA?: string;
  dnaScore?: string;
  dnaBand?: string;
  edgeRating?: string;
  formUrl?: string;
};

export const LIVE_RACE_DATA_SOURCE = "%s";
export const LIVE_RACE_DNA_SOURCE = "%s";

export const liveRaceRunnerSnapshot: LiveRaceRunnerSnapshot[] = [
%s
];

export function normaliseRunnerName(value: string | undefined | null): string {
  return String(value ?? "").trim().toUpperCase().replace(/[^A-Z0-9]+/g, " ");
}

export function findLiveRunnerSnapshot(runner: string | undefined | null): LiveRaceRunnerSnapshot | undefined {
  const key = normaliseRunnerName(runner);
  return liveRaceRunnerSnapshot.find((item) => normaliseRunnerName(item.runner) === key);
}
''' % (
    esc(str(base_file)),
    esc(str(dna_file)),
    ",\n".join(
        '  { runner: "%s", trainer: "%s", jockey: "%s", barrier: "%s", weight: "%s", market: "%s", runnerDNA: "%s", dnaScore: "%s", dnaBand: "%s", edgeRating: "%s", formUrl: "%s" }'
        % tuple(esc(r.get(k, "")) for k in ["runner","trainer","jockey","barrier","weight","market","runnerDNA","dnaScore","dnaBand","edgeRating","formUrl"])
        for r in records[:30]
    )
),
encoding="utf-8"
)

report.write_text("\n".join([
    "EDGEIQ DATA REGISTRY BUILD REPORT V1",
    f"Base source: {base_file} | score={base_score}",
    f"DNA source: {dna_file} | score={dna_score}",
    f"Snapshot rows: {len(records[:30])}",
    "",
    "Top source candidates:",
    *[f"{s:>4}  {p}" for s,p,_,_ in ranked[:12]],
    "",
    "Top DNA candidates:",
    *[f"{s:>4}  {p}" for s,p,_,_ in dna_ranked[:12]],
    "",
    "First generated records:",
    *[json.dumps(r, ensure_ascii=False) for r in records[:8]],
]), encoding="utf-8")

print("[EDGEIQ] Data registry built")
print("[EDGEIQ] Base source:", base_file)
print("[EDGEIQ] DNA source:", dna_file)
print("[EDGEIQ] Snapshot rows:", len(records[:30]))
print("[EDGEIQ] Report:", report)
