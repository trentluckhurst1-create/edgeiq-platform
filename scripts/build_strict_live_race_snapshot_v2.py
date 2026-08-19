from pathlib import Path
import csv
import re

snapshot = Path("src/edgeiq-os/services/live-race-data-snapshot.ts")
backup = Path("src/edgeiq-os/services/live-race-data-snapshot_CHECKPOINT_BEFORE_STRICT_COLUMN_BUILDER_20260709.ts")
if snapshot.exists():
    backup.write_text(snapshot.read_text(encoding="utf-8"), encoding="utf-8")

def clean_key(value):
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())

def exact_first(row, candidates):
    keyed = {clean_key(k): v for k, v in row.items()}
    for cand in candidates:
        key = clean_key(cand)
        if key in keyed and keyed[key] not in (None, ""):
            return str(keyed[key]).strip()
    return ""

def contains_first(row, candidates, reject_url=False, reject_numeric=False):
    for cand in candidates:
        ck = clean_key(cand)
        for k, v in row.items():
            if ck in clean_key(k) and v not in (None, ""):
                value = str(v).strip()
                if reject_url and value.lower().startswith(("http://", "https://", "www.")):
                    continue
                if reject_numeric and re.fullmatch(r"\d+(\.\d+)?", value):
                    continue
                return value
    return ""

def first_value(row, exact_names, contains_names=None, reject_url=False, reject_numeric=False):
    value = exact_first(row, exact_names)
    if value:
        if reject_url and value.lower().startswith(("http://", "https://", "www.")):
            value = ""
        if reject_numeric and re.fullmatch(r"\d+(\.\d+)?", value):
            value = ""
    if value:
        return value
    return contains_first(row, contains_names or exact_names, reject_url=reject_url, reject_numeric=reject_numeric)

def is_url(value):
    return str(value).lower().startswith(("http://", "https://", "www."))

def esc(x):
    return str(x).replace("\\", "\\\\").replace('"', '\\"')

candidate_files = []
for p in Path("public/data").rglob("*.csv"):
    try:
        with p.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames or []
            rows = [row for _, row in zip(range(80), reader)]
        if not rows:
            continue

        score = 0
        keys = [clean_key(c) for c in fields]

        if any(k in keys for k in ["runner", "runnername", "horsename", "horse"]):
            score += 12
        if any("trainer" in k for k in keys):
            score += 4
        if any("jockey" in k for k in keys):
            score += 4
        if any(k in keys for k in ["barrier", "bar"]):
            score += 2
        if any("weight" in k or k == "wt" for k in keys):
            score += 2
        if any("price" in k or "market" in k or "fixedwin" in k or "live" in k for k in keys):
            score += 2

        # Penalise files where the likely horse field is mostly numeric.
        sample_runner_values = [
            first_value(row, ["runner_name", "runnerName", "horse_name", "horseName", "runner", "horse"], reject_numeric=False)
            for row in rows[:20]
        ]
        numeric_count = sum(1 for v in sample_runner_values if re.fullmatch(r"\d+(\.\d+)?", str(v or "")))
        if numeric_count >= max(3, len([v for v in sample_runner_values if v]) // 2):
            score -= 8

        if score >= 8:
            candidate_files.append((score, p, fields, rows))
    except Exception:
        pass

candidate_files.sort(key=lambda x: (x[0], str(x[1])), reverse=True)

records = []
source_file = ""

if candidate_files:
    score, source, fields, rows = candidate_files[0]
    source_file = str(source)

    for row in rows[:40]:
        runner = first_value(
            row,
            ["runner_name", "runnerName", "horse_name", "horseName", "runner", "horse"],
            ["runner", "horse", "name"],
            reject_numeric=True
        )

        if not runner:
            # Try exact horse_name again without numeric rejection only as a last resort.
            runner = first_value(row, ["horse_name", "horseName", "runner_name", "runnerName"], reject_numeric=False)

        if not runner or is_url(runner):
            continue

        form_url = first_value(
            row,
            ["formUrl", "form_url", "horseFormUrl", "interactiveForm", "interactive_form", "horseProfileUrl", "profileUrl"],
            ["interactiveform", "formurl", "profileurl", "horseform"],
            reject_url=False
        )

        dna = first_value(
            row,
            ["runnerDNA", "runner_dna", "dnaBand", "dna_band", "dnaScore", "dna_score"],
            ["runnerdna", "dnaband", "dnascore"],
            reject_url=True
        )

        records.append({
            "runner": runner,
            "trainer": first_value(row, ["trainer", "trainer_name", "trainerName"], ["trainer"]),
            "jockey": first_value(row, ["jockey", "jockey_name", "jockeyName"], ["jockey"]),
            "barrier": first_value(row, ["barrier", "bar"], ["barrier", "bar"]),
            "weight": first_value(row, ["weight", "wt"], ["weight", "wt"]),
            "market": first_value(row, ["market", "live_price", "livePrice", "fixed_win", "fixedWin", "price"], ["market", "price", "fixedwin", "live"]),
            "runnerDNA": dna,
            "edgeRating": first_value(row, ["edgeRating", "edge_rating", "edge_score", "edgeScore", "rating"], ["edgerating", "rating", "score"]),
            "formUrl": form_url if is_url(form_url) else "",
        })

snapshot.write_text(
'''export type LiveRaceRunnerSnapshot = {
  runner: string;
  trainer?: string;
  jockey?: string;
  barrier?: string;
  weight?: string;
  market?: string;
  runnerDNA?: string;
  edgeRating?: string;
  formUrl?: string;
};

export const LIVE_RACE_DATA_SOURCE = "%s";

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
    esc(source_file),
    ",\n".join(
        '  { runner: "%s", trainer: "%s", jockey: "%s", barrier: "%s", weight: "%s", market: "%s", runnerDNA: "%s", edgeRating: "%s", formUrl: "%s" }'
        % tuple(esc(r.get(k, "")) for k in ["runner","trainer","jockey","barrier","weight","market","runnerDNA","edgeRating","formUrl"])
        for r in records
    )
),
encoding="utf-8"
)

print("[EDGEIQ] Strict live snapshot rebuilt")
print("[EDGEIQ] Source:", source_file or "NO SUITABLE CSV FOUND")
print("[EDGEIQ] Rows:", len(records))
if backup.exists():
    print("[EDGEIQ] checkpoint:", backup)
