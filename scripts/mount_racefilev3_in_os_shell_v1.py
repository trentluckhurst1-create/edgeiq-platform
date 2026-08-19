from pathlib import Path

path = Path("src/edgeiq-os/shell/EdgeiqOsShell.tsx")
backup = Path("src/edgeiq-os/shell/EdgeiqOsShell_CHECKPOINT_BEFORE_RACEFILEV3_MOUNT_20260709.tsx")
backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

text = path.read_text(encoding="utf-8")

text = text.replace(
'''        {isRaceMode && raceView === "COMMAND" ? <EdgeiqCommandWorkspace /> : <EdgeiqOsHome />}''',
'''        {isRaceMode && raceView === "COMMAND" ? (
          <EdgeiqCommandWorkspace />
        ) : isRaceMode && raceView === "RACE" ? (
          <EdgeiqRaceWorkspace />
        ) : (
          <EdgeiqOsHome />
        )}'''
)

path.write_text(text, encoding="utf-8")
print("[EDGEIQ] RaceFileV3 mounted on RACES > RACE")
print(f"[EDGEIQ] checkpoint: {backup}")
