from pathlib import Path
import re

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

text = text.replace(
'''  let spd = rawSpeed || sectionalWeapon || latePower || 50;

  if (style === "LEADER") spd = Math.max(spd, 82);
  if (style === "ON PACE") spd = Math.max(spd, 68);
  if (style === "MIDFIELD") spd = Math.max(spd, 48);
  if (style === "BACKMARKER") spd = Math.max(spd, 28);''',
'''  let spd = rawSpeed || sectionalWeapon || latePower || 0;

  if (!spd) {
    if (style === "LEADER") spd = 18 + barrier * 2;
    else if (style === "ON PACE") spd = 35 + barrier * 2;
    else if (style === "MIDFIELD") spd = 52 + barrier * 2;
    else if (style === "BACKMARKER") spd = 78 + barrier;
    else spd = 50;
  }'''
)

text = text.replace(
'''    barrier: num(val(row, ["barrier", "Barrier", "bar", "gate"])),''',
'''    barrier: num(val(row, ["barrier", "Barrier", "bar", "gate"])),'''
)

text = text.replace(
'''  let spd = rawSpeed || sectionalWeapon || latePower || 0;''',
'''  const barrier = num(val(row, ["barrier", "Barrier", "bar", "gate"]));
  let spd = rawSpeed || sectionalWeapon || latePower || 0;'''
)

text = text.replace(
'''    barrier: num(val(row, ["barrier", "Barrier", "bar", "gate"])),''',
'''    barrier,''',
1
)

text = re.sub(
r'''<span className="scale">0</span>[\s\S]*?<span className="scale">100</span>''',
'''<span className="scale">0</span>
            <span className="scale">10</span>
            <span className="scale">20</span>
            <span className="scale">30</span>
            <span className="scale">40</span>
            <span className="scale">50</span>
            <span className="scale">60</span>
            <span className="scale">70</span>
            <span className="scale">80</span>
            <span className="scale">90</span>
            <span className="scale">100</span>''',
text,
count=1
)

path.write_text(text, encoding="utf-8")

print("FIXED SPEED MAP SPD FALLBACK AND HEADER SCALE")
