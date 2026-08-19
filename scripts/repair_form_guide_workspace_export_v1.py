from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

ACTIVE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceFormGuideWorkspace.tsx"
CHECKPOINT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceFormGuideWorkspace_CHECKPOINT_BEFORE_LOCKED_COMPOSITION_V4_20260721_064116.tsx"

if not ACTIVE.exists():
    raise SystemExit(f"REPAIR_ABORTED: active file missing: {ACTIVE}")

if not CHECKPOINT.exists():
    raise SystemExit(f"REPAIR_ABORTED: checkpoint missing: {CHECKPOINT}")

active = ACTIVE.read_text(encoding="utf-8")
checkpoint = CHECKPOINT.read_text(encoding="utf-8")

export_marker = "export function RaceFormGuideWorkspace("

if export_marker in active:
    print("WORKSPACE_EXPORT_ALREADY_PRESENT")
    raise SystemExit(0)

checkpoint_index = checkpoint.find(export_marker)

if checkpoint_index < 0:
    raise SystemExit(
        "REPAIR_ABORTED: RaceFormGuideWorkspace export was not found in checkpoint."
    )

workspace_export = checkpoint[checkpoint_index:].strip()

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = ACTIVE.with_name(
    f"{ACTIVE.stem}_CHECKPOINT_BEFORE_EXPORT_REPAIR_{stamp}{ACTIVE.suffix}"
)
shutil.copy2(ACTIVE, backup)

active = active.rstrip() + "\n\n" + workspace_export + "\n"

ACTIVE.write_text(active, encoding="utf-8", newline="\n")

print(f"ACTIVE={ACTIVE}")
print(f"REPAIR_CHECKPOINT={backup}")
print("RACE_FORM_GUIDE_WORKSPACE_EXPORT_RESTORED_PASS")
