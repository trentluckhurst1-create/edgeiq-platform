from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx"


def main() -> int:
    text = PATH.read_text(encoding="utf-8-sig")
    old = '''  field,
  clean,
  market,
  meetingRaces = [],'''
    new = '''  field,
  clean,
  weight,
  market,
  meetingRaces = [],'''
    if old not in text:
        raise RuntimeError("RaceWorkspace destructuring block not found")
    PATH.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("Repaired FieldWorkspace weight prop wiring")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
