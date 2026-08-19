from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RACE_FILE = ROOT / "src" / "edgeiq-os" / "race" / "RaceFileV3.tsx"
CHECKPOINT_ROOT = ROOT / "docs" / "full-product-implementation" / "checkpoints"
PHASE_LABEL = "CHECKPOINT_BEFORE_FINAL_APPROVED_PRODUCT_CONFORMANCE_RESTORE_LOADING_GUARD"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 match, found {count}")
    return text.replace(old, new, 1)


def checkpoint() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = CHECKPOINT_ROOT / f"{PHASE_LABEL}_{timestamp}"
    destination.mkdir(parents=True, exist_ok=False)
    target = destination / RACE_FILE.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(RACE_FILE, target)
    return destination


def main() -> None:
    checkpoint_dir = checkpoint()
    text = read_text(RACE_FILE)

    text = replace_once(
        text,
        """  const bestRun = displayedRuns[0];



  useEffect(() => {""",
        """  const bestRun = displayedRuns[0];

  const isWaitingForRestoredMeetingContext =

    hasStoredRaceContext &&

    !restoreAttempted &&

    !selectedMeeting &&

    viewLevel !== "meetings";



  useEffect(() => {""",
        "restore loading state",
    )

    text = replace_once(
        text,
        """      ) : viewLevel === "meetings" ? (

        <MeetingsWorkspace""",
        """      ) : isWaitingForRestoredMeetingContext ? (

        <section className="eiq-workspace-panel" aria-label="Restoring meeting context">

          <span>MEETINGS</span>

          <strong>Restoring selected meeting.</strong>

          <p>Loading the governed meeting context before opening the workspace.</p>

        </section>

      ) : viewLevel === "meetings" ? (

        <MeetingsWorkspace""",
        "restore loading render branch",
    )

    write_text(RACE_FILE, text)
    print(f"Checkpoint created: {checkpoint_dir}")
    print(PHASE_LABEL)
    print("EDGEIQ_RESTORE_LOADING_GUARD_PATCH_APPLIED_V1")


if __name__ == "__main__":
    main()
