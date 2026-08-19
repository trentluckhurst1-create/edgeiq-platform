from pathlib import Path

path = Path("src/components/RaceIntelligenceScreen.tsx")
text = path.read_text(encoding="utf-8")

backup = Path("src/components/RaceIntelligenceScreen_BEFORE_FACTOR_JOIN_KEY_FIX.tsx")
backup.write_text(text, encoding="utf-8")

old = '''      const factorRows = factorScorecardRows
        .filter((factorRow) => cleanTrack(track(factorRow)) === cleanTrack(track(row)) && raceNo(factorRow) === raceNo(row) && cleanHorse(horse(factorRow)) === cleanHorse(horse(row)))
        .sort((a, b) => (num(a.factor_order) ?? 999) - (num(b.factor_order) ?? 999));'''

new = '''      const rowJoinKey = firstText(dna, ["join_key"], "") || firstText(row, ["join_key"], "");
      const factorRows = factorScorecardRows
        .filter((factorRow) => {
          const factorJoinKey = firstText(factorRow, ["join_key"], "");
          if (rowJoinKey && factorJoinKey) return factorJoinKey === rowJoinKey;
          return cleanTrack(track(factorRow)) === cleanTrack(track(row)) && raceNo(factorRow) === raceNo(row) && cleanHorse(horse(factorRow)) === cleanHorse(horse(row));
        })
        .sort((a, b) => (num(a.factor_order) ?? 999) - (num(b.factor_order) ?? 999));'''

if old not in text:
    raise RuntimeError("Target factorRows block not found")

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")
print("[FACTOR_JOIN_KEY_FIX] COMPLETE")
