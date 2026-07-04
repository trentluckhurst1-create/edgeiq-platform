from pathlib import Path
import re

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

text = re.sub(
r'''const plotted = runners[\s\S]*?const labelOrder =''',
'''const plotted = runners
    .slice()
    .sort((a, b) => {
      const order = { LEADER: 0, "ON PACE": 1, MIDFIELD: 2, BACKMARKER: 3 };
      const pa = order[a.mapPosition as keyof typeof order] ?? 9;
      const pb = order[b.mapPosition as keyof typeof order] ?? 9;
      if (pa !== pb) return pa - pb;
      return Number(a.saddlecloth || 999) - Number(b.saddlecloth || 999);
    })
    .map((r) => {
      const group = runners
        .filter((x) => x.mapPosition === r.mapPosition)
        .sort((a, b) => Number(a.saddlecloth || 999) - Number(b.saddlecloth || 999));

      const index = Math.max(0, group.findIndex((x) => x.horse === r.horse));
      const groupSize = Math.max(group.length, 1);

      const baseY = {
        LEADER: 14,
        "ON PACE": 31,
        MIDFIELD: 55,
        BACKMARKER: 78,
      }[r.mapPosition] ?? 55;

      const laneOffsets = [-18, -9, 0, 9, 18];
      const lane = index % laneOffsets.length;
      const row = Math.floor(index / laneOffsets.length);

      const railToWide = laneOffsets[lane];
      const depth = row * 6;

      const barrierWide =
        ((r.barrier - 1) / Math.max(maxBarrier - 1, 1)) * 10 - 5;

      const xBase = rightHanded ? 100 - 50 : 50;

      return {
        ...r,
        x: Math.max(9, Math.min(91, xBase + railToWide + barrierWide)),
        y: Math.max(8, Math.min(92, baseY + depth)),
      };
    });

  const labelOrder =''',
text
)

path.write_text(text, encoding="utf-8")
print("REBUILT plotted geometry as 200m settling map")
