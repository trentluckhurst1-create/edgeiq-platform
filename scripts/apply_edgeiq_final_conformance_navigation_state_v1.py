from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RACE_FILE = ROOT / "src" / "edgeiq-os" / "race" / "RaceFileV3.tsx"
MEETINGS_WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingsWorkspace.tsx"
CHECKPOINT_ROOT = ROOT / "docs" / "full-product-implementation" / "checkpoints"
PHASE_LABEL = "CHECKPOINT_BEFORE_FINAL_APPROVED_PRODUCT_CONFORMANCE_NAVIGATION_STATE"


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
    for source in (RACE_FILE, MEETINGS_WORKSPACE):
        relative = source.relative_to(ROOT)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return destination


def patch_race_file() -> None:
    text = read_text(RACE_FILE)

    text = replace_once(
        text,
        'import { Fragment, type ReactNode, useEffect, useMemo, useState } from "react";',
        'import { Fragment, type ReactNode, useEffect, useMemo, useRef, useState } from "react";',
        "React hook import",
    )

    text = replace_once(
        text,
        'const HOME_ROUTE_AUDIT_MARKER = "<EdgeiqOsHome />";',
        'const HOME_ROUTE_AUDIT_MARKER = "<EdgeiqOsHome />";\n\nconst NAVIGATION_STATE_AUDIT_MARKER = "EDGEIQ_NAVIGATION_STATE_EXPLICIT_SELECTION_V1";',
        "navigation audit marker",
    )

    text = replace_once(
        text,
        """  const [sectionalStandard, setSectionalStandard] = useState<SectionalStandard>(

    initialWorkspaceState.sectionalStandard ?? "sameClass",

  );

  const activeFile = useMemo(""",
        """  const [sectionalStandard, setSectionalStandard] = useState<SectionalStandard>(

    initialWorkspaceState.sectionalStandard ?? "sameClass",

  );

  const explicitSelectionEpoch = useRef(0);

  function markExplicitSelection() {

    explicitSelectionEpoch.current += 1;

  }

  const activeFile = useMemo(""",
        "explicit selection epoch",
    )

    text = replace_once(
        text,
        """  useEffect(() => {

    if (!hasStoredRaceContext) return;

    let cancelled = false;



    loadThreeDayCatalog()""",
        """  useEffect(() => {

    if (!hasStoredRaceContext || restoreAttempted) return;

    let cancelled = false;

    const restoreEpoch = explicitSelectionEpoch.current;



    loadThreeDayCatalog()""",
        "restore guard entry",
    )

    text = replace_once(
        text,
        """      .then((catalog) => {

        if (cancelled) return;""",
        """      .then((catalog) => {

        if (cancelled || explicitSelectionEpoch.current !== restoreEpoch) return;""",
        "stale restore cancellation",
    )

    text = replace_once(
        text,
        "  }, [hasStoredRaceContext, initialWorkspaceState, viewLevel]);",
        "  }, [hasStoredRaceContext, initialWorkspaceState, restoreAttempted, viewLevel]);",
        "restore dependencies",
    )

    text = replace_once(
        text,
        "            onDayChange={setSelectedMeetingsDayKey}",
        """            onDayChange={(dayKey) => {

              markExplicitSelection();

              setSelectedMeetingsDayKey(dayKey);

              setSelectedMeeting(null);

              setSelectedRace(null);

              setSelectedRunnerIndex(0);

            }}""",
        "meetings day explicit selection",
    )

    text = replace_once(
        text,
        """            onSelectMeeting={(meeting) => {

              setSelectedMeeting(meeting);""",
        """            onSelectMeeting={(meeting) => {

              markExplicitSelection();

              setSelectedMeeting(meeting);""",
        "meeting select explicit marker",
    )

    text = replace_once(
        text,
        """            onOpenMeeting={(meeting) => {

              setSelectedMeeting(meeting);""",
        """            onOpenMeeting={(meeting) => {

              markExplicitSelection();

              setSelectedMeeting(meeting);""",
        "meeting open explicit marker",
    )

    text = replace_once(
        text,
        """            onOpenRace={(meeting, race) => {

              setSelectedMeeting(meeting);""",
        """            onOpenRace={(meeting, race) => {

              markExplicitSelection();

              setSelectedMeeting(meeting);""",
        "meetings race open explicit marker",
    )

    write_text(RACE_FILE, text)


def patch_meetings_workspace() -> None:
    text = read_text(MEETINGS_WORKSPACE)
    text = replace_once(
        text,
        "                      onSelect={() => onOpenMeeting(meeting.rawMeeting)}",
        "                      onSelect={() => onSelectMeeting(meeting.rawMeeting)}",
        "meeting row select handler",
    )
    write_text(MEETINGS_WORKSPACE, text)


def main() -> None:
    checkpoint_dir = checkpoint()
    patch_race_file()
    patch_meetings_workspace()
    print(f"Checkpoint created: {checkpoint_dir}")
    print(PHASE_LABEL)
    print("EDGEIQ_NAVIGATION_STATE_PATCH_APPLIED_V1")


if __name__ == "__main__":
    main()
