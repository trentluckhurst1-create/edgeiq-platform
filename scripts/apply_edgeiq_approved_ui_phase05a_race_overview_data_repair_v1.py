from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT = ROOT / "docs" / "full-product-implementation" / "checkpoints" / f"CHECKPOINT_APPROVED_UI_PHASE05A_RACE_OVERVIEW_DATA_REPAIR_{STAMP}"


def checkpoint(paths: list[Path]) -> None:
    CHECKPOINT.mkdir(parents=True, exist_ok=True)
    for path in paths:
        if path.exists():
            target = CHECKPOINT / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def patch(path: Path, replacements: list[tuple[str, str]]) -> None:
    text = path.read_text(encoding="utf-8-sig")
    for before, after in replacements:
        if before not in text:
            raise SystemExit(f"Source marker not found in {path}: {before[:120]!r}")
        text = text.replace(before, after)
    path.write_text(text, encoding="utf-8", newline="")


def main() -> None:
    race_workspace = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx"
    race_intel = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceIntelligenceWorkspace.tsx"
    phase_script = ROOT / "scripts" / "apply_edgeiq_approved_ui_phase05_race_overview_v1.py"
    checkpoint([race_workspace, race_intel, phase_script])

    patch(
        race_workspace,
        [
            (
                """          raceKey={clean(official.raceKey) || selectedRaceKey}
          clean={clean}
        />""",
                """          raceKey={clean(official.raceKey) || selectedRaceKey}
          meetingRaces={meetingRaces}
          clean={clean}
        />""",
            )
        ],
    )

    race_replacements = [
        (
            """  formGuide?: FormGuideRaceDisplay | null;
  raceKey?: string | null;
  clean: (value: any) => string;
};""",
            """  formGuide?: FormGuideRaceDisplay | null;
  raceKey?: string | null;
  meetingRaces?: any[];
  clean: (value: any) => string;
};""",
        ),
        (
            """function money(value: unknown): string {
  const raw = text(value, "").replace(/[$,]/g, "");
  const parsed = Number(raw);
  if (!Number.isFinite(parsed) || parsed <= 0) return text(value);
  return `$${parsed.toLocaleString("en-AU", { maximumFractionDigits: 0 })}`;
}""",
            """function money(value: unknown): string {
  const raw = text(value, "").replace(/[$,]/g, "");
  const parsed = Number(raw);
  if (!Number.isFinite(parsed) || parsed <= 0) return "";
  return `$${parsed.toLocaleString("en-AU", { maximumFractionDigits: 0 })}`;
}""",
        ),
        (
            """export function RaceIntelligenceWorkspace({ raceBook, field, formGuide, raceKey, clean }: RaceIntelligenceWorkspaceProps) {""",
            """export function RaceIntelligenceWorkspace({ raceBook, field, formGuide, raceKey, meetingRaces = [], clean }: RaceIntelligenceWorkspaceProps) {""",
        ),
        (
            """                {(raceBook?.meetingRaces ?? []).length ? (
                  raceBook.meetingRaces.map((race: any, index: number) => (""",
            """                {meetingRaces.length ? (
                  meetingRaces.map((race: any, index: number) => (""",
        ),
        (
            """            <strong>{(raceBook?.meetingRaces ?? []).length || text(official.fieldSize, "0")} races</strong>""",
            """            <strong>{meetingRaces.length ? `${meetingRaces.length} races` : "Race list unavailable"}</strong>""",
        ),
    ]
    patch(race_intel, race_replacements)
    patch(phase_script, race_replacements)
    print(f"checkpoint={CHECKPOINT}")
    print("EDGEIQ_APPROVED_UI_PHASE05A_RACE_OVERVIEW_DATA_REPAIR_PASS")


if __name__ == "__main__":
    main()
