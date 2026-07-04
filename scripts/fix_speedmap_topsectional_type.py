from pathlib import Path
import re

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

text = text.replace(
"""  const topSectional = [...sectionallyMapped].sort(
    (a: any, b: any) =>
      Number(b.sectionalWeaponScore ?? 0) -
      Number(a.sectionalWeaponScore ?? 0)
  )[0];""",
"""  const topSectional: any = [...sectionallyMapped].sort(
    (a: any, b: any) =>
      Number(b.sectionalWeaponScore ?? 0) -
      Number(a.sectionalWeaponScore ?? 0)
  )[0];"""
)

path.write_text(text, encoding="utf-8")

print("CAST topSectional AS any TO UNBLOCK BUILD")
