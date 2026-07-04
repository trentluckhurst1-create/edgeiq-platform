from pathlib import Path

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

old = '''function classifyRows(speedRows: RawRow[], raceRunners: RawRow[]): MapRunner[] {
  const rows = mergeRows(speedRows, raceRunners)
    .filter((row) => horseName(row))
    .filter((row) => !boolish(row.isScratched ?? row.is_scratched ?? row.scratched ?? row.runner_status ?? row.status))
    .sort((a, b) => {
      const ab = barrierNumber(a) ?? 999;
      const bb = barrierNumber(b) ?? 999;
      if (ab !== bb) return bb - ab;
      const an = num(a.horse_no ?? a.saddlecloth ?? a.number ?? a.horseNo) ?? 999;
      const bn = num(b.horse_no ?? b.saddlecloth ?? b.number ?? b.horseNo) ?? 999;
      return an - bn;
    });

  return rows.map((row, index) => {
    const horse = horseName(row);
    const barrier = barrierNumber(row);
    return {
      key: cleanKey(horse) || String(index),
      horse,
      shortName: shortHorseName(horse),
      saddlecloth: saddlecloth(row, index),
      barrier: barrier === null ? index + 1 : Math.trunc(barrier),
      barrierLabel: barrier === null ? "-" : String(Math.trunc(barrier)),
      jockey: val(row, ["jockey", "Jockey", "rider"]),
      price: priceText(row),
      silkUrl: bestSilkUrl(row),
      xPct: xPosition(row, index),
      band: bandOf(row),
    };
  });
}'''

new = '''function classifyRows(speedRows: RawRow[], raceRunners: RawRow[]): MapRunner[] {
  const mergedRows = mergeRows(speedRows, raceRunners).filter((row) => horseName(row));

  const activeRows = mergedRows
    .filter((row) => !boolish(row.isScratched ?? row.is_scratched ?? row.scratched ?? row.runner_status ?? row.status))
    .sort((a, b) => {
      const ab = barrierNumber(a) ?? 999;
      const bb = barrierNumber(b) ?? 999;
      if (ab !== bb) return ab - bb;

      const an = num(a.horse_no ?? a.saddlecloth ?? a.number ?? a.horseNo) ?? 999;
      const bn = num(b.horse_no ?? b.saddlecloth ?? b.number ?? b.horseNo) ?? 999;
      return an - bn;
    });

  const effectiveBarrierByHorse = new Map<string, number>();

  activeRows.forEach((row, index) => {
    const key = cleanKey(horseName(row));
    if (key) effectiveBarrierByHorse.set(key, index + 1);
  });

  return activeRows
    .sort((a, b) => {
      const ae = effectiveBarrierByHorse.get(cleanKey(horseName(a))) ?? 999;
      const be = effectiveBarrierByHorse.get(cleanKey(horseName(b))) ?? 999;
      return be - ae;
    })
    .map((row, index) => {
      const horse = horseName(row);
      const key = cleanKey(horse);
      const rawBarrier = barrierNumber(row);
      const effectiveBarrier = effectiveBarrierByHorse.get(key) ?? index + 1;

      return {
        key: key || String(index),
        horse,
        shortName: shortHorseName(horse),
        saddlecloth: saddlecloth(row, index),
        barrier: effectiveBarrier,
        barrierLabel: rawBarrier === null || rawBarrier === effectiveBarrier
          ? String(effectiveBarrier)
          : `${effectiveBarrier} from ${Math.trunc(rawBarrier)}`,
        jockey: val(row, ["jockey", "Jockey", "rider"]),
        price: priceText(row),
        silkUrl: bestSilkUrl(row),
        xPct: xPosition(row, index),
        band: bandOf(row),
      };
    });
}'''

if old not in text:
    raise SystemExit("Could not find classifyRows block. No changes made.")

text = text.replace(old, new)
path.write_text(text, encoding="utf-8")

print("EFFECTIVE BARRIER FIX APPLIED")
