from pathlib import Path
import csv
import re

root = Path(".")
src = Path("src/edgeiq-os/services/race-file-v2.ts")
snapshot = Path("src/edgeiq-os/services/live-race-data-snapshot.ts")

src_backup = Path("src/edgeiq-os/services/race-file-v2_CHECKPOINT_BEFORE_LIVE_DATA_WIRE_20260709.ts")
src_backup.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

candidates = []
for p in Path("public/data").rglob("*.csv"):
    try:
        with p.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
            reader = csv.DictReader(f)
            cols = [c.lower().strip() for c in (reader.fieldnames or [])]
            rows = []
            for _, row in zip(range(40), reader):
                rows.append(row)
        score = 0
        for wanted in ["runner","horse","jockey","trainer","barrier","weight","market","price","dna","rating"]:
            if any(wanted in c for c in cols):
                score += 1
        if rows and score >= 3:
            candidates.append((score, p, reader.fieldnames or [], rows))
    except Exception:
        pass

candidates.sort(key=lambda x: (x[0], str(x[1])), reverse=True)

def first(row, names):
    lowered = {str(k).lower().strip(): v for k, v in row.items()}
    for n in names:
        for k, v in lowered.items():
            if n in k and v not in (None, ""):
                return str(v).strip()
    return ""

records = []
source_file = ""
if candidates:
    score, source, fields, rows = candidates[0]
    source_file = str(source)
    for row in rows[:24]:
        runner = first(row, ["runner", "horse", "name"])
        if not runner:
            continue
        records.append({
            "runner": runner,
            "trainer": first(row, ["trainer"]),
            "jockey": first(row, ["jockey"]),
            "barrier": first(row, ["barrier", "bar"]),
            "weight": first(row, ["weight", "wt"]),
            "market": first(row, ["market", "price", "fixed_win", "live"]),
            "runnerDNA": first(row, ["dna", "profile"]),
            "edgeRating": first(row, ["edge_rating", "rating", "score"]),
        })

def esc(x):
    return str(x).replace("\\", "\\\\").replace('"', '\\"')

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
        '  { runner: "%s", trainer: "%s", jockey: "%s", barrier: "%s", weight: "%s", market: "%s", runnerDNA: "%s", edgeRating: "%s" }'
        % tuple(esc(r.get(k, "")) for k in ["runner","trainer","jockey","barrier","weight","market","runnerDNA","edgeRating"])
        for r in records
    )
),
encoding="utf-8"
)

text = src.read_text(encoding="utf-8")

if 'live-race-data-snapshot' not in text:
    text = text.replace(
        'import',
        'import { findLiveRunnerSnapshot } from "./live-race-data-snapshot";\nimport',
        1
    )

# Insert live lookup inside the first field map callback where index exists.
if "const liveRunner = findLiveRunnerSnapshot" not in text:
    text = re.sub(
        r'(\.map\(\((?:runner|item|profile)[^)]*index[^)]*\)\s*=>\s*\{)',
        r'\1\n    const liveRunner = findLiveRunnerSnapshot((runner as any)?.official?.runner ?? (runner as any)?.runner ?? (runner as any)?.name ?? (runner as any));',
        text,
        count=1
    )

replacements = {
    'jockey: index === 0 ? "Primary jockey" : "Mapped jockey",':
        'jockey: liveRunner?.jockey || (runner as any)?.jockey || (runner as any)?.official?.jockey || "Not listed",',
    'trainer: index === 0 ? "Primary stable" : "Mapped stable",':
        'trainer: liveRunner?.trainer || (runner as any)?.trainer || (runner as any)?.official?.trainer || "Not listed",',
    'market: index === 0 ? "Monitor" : "Neutral",':
        'market: liveRunner?.market || (runner as any)?.market || (runner as any)?.official?.market || "Pending",',
    'runnerDNA: index === 0 ? "Aligned" : index < 3 ? "Positive" : "Watch",':
        'runnerDNA: liveRunner?.runnerDNA || (runner as any)?.runnerDNA || "Profile pending",',
    'marketBehaviour: index === 0 ? "Monitor" : "Neutral",':
        'marketBehaviour: liveRunner?.market ? "Live market available" : "Market pending",',
}

for old, new in replacements.items():
    text = text.replace(old, new)

# Optional rating enrichment if the service has edgeRating placeholder.
text = text.replace(
    'edgeRating: index === 0 ?',
    'edgeRating: liveRunner?.edgeRating || (index === 0 ?'
)

src.write_text(text, encoding="utf-8")

print("[EDGEIQ] Live data snapshot created:", snapshot)
print("[EDGEIQ] Source CSV:", source_file or "NO CSV FOUND")
print("[EDGEIQ] Snapshot rows:", len(records))
print("[EDGEIQ] race-file-v2.ts checkpoint:", src_backup)
