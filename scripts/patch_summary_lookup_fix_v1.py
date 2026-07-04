from pathlib import Path

p = Path(".\\src\\components\\RaceIntelligenceScreen.tsx")
s = p.read_text(encoding="utf-8")

checkpoint = Path(".\\checkpoints\\RaceIntelligenceScreen_CHECKPOINT_BEFORE_SUMMARY_LOOKUP_FIX_AND_RUNNER_SELECTOR_20260623.tsx")
checkpoint.write_text(s, encoding="utf-8")

def must_replace(old, new):
    global s
    if old not in s:
        raise SystemExit(f"[PATCH FAILED] anchor not found:\n{old[:500]}")
    s = s.replace(old, new, 1)

helper_anchor = '''function connectionSourceRow(item: EnrichedRunner): Row | undefined {'''

helper = '''function compactKey(value: unknown): string {
  return String(value ?? "").toUpperCase().replace(/[^A-Z0-9]/g, "");
}

function findSidecarByRaceHorse(rows: Row[], row: Row): Row | undefined {
  const raceKey = String(row.race_key ?? "").trim();
  const horseKey = compactKey(row.horse ?? row.runner ?? row.runner_name);
  if (!horseKey) return undefined;

  return rows.find((side) => {
    const sideRaceKey = String(side.race_key ?? "").trim();
    const sideHorseKey = compactKey(side.horse ?? side.runner ?? side.runner_name);
    if (!sideHorseKey || sideHorseKey !== horseKey) return false;
    if (raceKey && sideRaceKey) return sideRaceKey === raceKey;
    return true;
  });
}

'''

must_replace(helper_anchor, helper + helper_anchor)

must_replace(
'''      const intelligenceSummary = findSidecar(intelligenceSummaryRows, row);''',
'''      const intelligenceSummary = findSidecarByRaceHorse(intelligenceSummaryRows, row);'''
)

p.write_text(s, encoding="utf-8")
print("[SUMMARY_LOOKUP_FIX_V1] COMPLETE")
print(f"checkpoint={checkpoint}")
