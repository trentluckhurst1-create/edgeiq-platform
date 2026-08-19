from pathlib import Path
import re

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

pattern = r'const plotted = runners[\s\S]*?const labelOrder ='

replacement = '''const plotted = runners
    .slice()
    .sort((a, b) => {
      const order = {
        LEADER: 0,
        "ON PACE": 1,
        MIDFIELD: 2,
        BACKMARKER: 3,
      };

      const pa = order[a.mapPosition as keyof typeof order] ?? 9;
      const pb = order[b.mapPosition as keyof typeof order] ?? 9;

      if (pa !== pb) return pa - pb;

      return a.barrier - b.barrier;
    })
    .map((r, index) => {
      const laneBase = {
        LEADER: 16,
        "ON PACE": 33,
        MIDFIELD: 54,
        BACKMARKER: 74,
      }[r.mapPosition] ?? 54;

      const barrierFactor =
        ((r.barrier - 1) / Math.max(maxBarrier - 1, 1)) * 18;

      const x = rightHanded
        ? 100 - (laneBase + barrierFactor)
        : laneBase + barrierFactor;

      const yBase = {
        LEADER: 16,
        "ON PACE": 34,
        MIDFIELD: 56,
        BACKMARKER: 79,
      }[r.mapPosition] ?? 56;

      const sameGroup = runners.filter(
        (x) => x.mapPosition === r.mapPosition
      );

      const groupIndex = sameGroup.findIndex(
        (x) => x.horse === r.horse
      );

      const spread =
        sameGroup.length <= 1
          ? 0
          : (groupIndex - (sameGroup.length - 1) / 2) * 4.2;

      return {
        ...r,
        x,
        y: yBase + spread,
      };
    });

  const labelOrder ='''

text2 = re.sub(pattern, replacement, text)

path.write_text(text2, encoding="utf-8")

print("REBUILT SPEED MAP AS TRUE SETTLING POSITION MAP")
