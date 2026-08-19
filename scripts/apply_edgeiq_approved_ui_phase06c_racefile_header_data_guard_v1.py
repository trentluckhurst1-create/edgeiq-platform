from pathlib import Path
import shutil
from datetime import datetime


ROOT = Path(__file__).resolve().parents[1]
RACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx"
CHECKPOINT_ROOT = ROOT / "docs" / "full-product-implementation" / "checkpoints"


def checkpoint() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = CHECKPOINT_ROOT / f"CHECKPOINT_APPROVED_UI_PHASE06C_RACEFILE_HEADER_DATA_GUARD_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(RACE, out / RACE.name)
    return out


def patch() -> None:
    text = RACE.read_text(encoding="utf-8")
    old = '''  const surface = clean(official.surface) || clean(official.trackType);
  const prizeMoney = clean(official.prizeMoney) || clean(official.totalPrizeMoney);
  const raceTitle = clean(official.raceName) || clean(official.name);
  const showRaceFileHeader = tab !== "RACE";'''
    new = '''  const surface = clean(official.surface) || clean(official.trackType);
  const prizeMoneyRaw = clean(official.prizeMoney) || clean(official.totalPrizeMoney);
  const prizeMoney = /^race file$/i.test(prizeMoneyRaw) ? "" : prizeMoneyRaw;
  const raceTitle = clean(official.raceName) || clean(official.name);
  const showRaceFileHeader = tab !== "RACE";'''
    if old not in text:
        raise SystemExit("Expected RaceWorkspace prize money block not found; source changed unexpectedly.")
    RACE.write_text(text.replace(old, new), encoding="utf-8", newline="\n")


def main() -> None:
    cp = checkpoint()
    patch()
    print(f"checkpoint={cp}")
    print(f"files_changed:\\n- {RACE}")
    print("EDGEIQ_APPROVED_UI_PHASE06C_RACEFILE_HEADER_DATA_GUARD_PASS")


if __name__ == "__main__":
    main()
