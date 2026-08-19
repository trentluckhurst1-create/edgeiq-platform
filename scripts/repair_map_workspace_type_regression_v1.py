from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

map_path = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "race"
    / "components"
    / "MapWorkspace.tsx"
)

race_path = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "race"
    / "components"
    / "RaceWorkspace.tsx"
)

map_text = map_path.read_text(encoding="utf-8")

old_rows = """  const rows = buildMapRows(field ?? raceBook.field ?? [], market);"""

new_rows = """  const sourceField: RaceFieldRunner[] = Array.isArray(field)
    ? field
    : Array.isArray(raceBook?.field)
      ? (raceBook.field as RaceFieldRunner[])
      : [];

  const rows = buildMapRows(sourceField, market);"""

row_count = map_text.count(old_rows)

if row_count != 2:
    raise RuntimeError(
        "Expected exactly 2 MapWorkspace buildMapRows field expressions, "
        f"found {row_count}."
    )

map_text = map_text.replace(old_rows, new_rows)

map_path.write_text(
    map_text,
    encoding="utf-8",
)

race_text = race_path.read_text(encoding="utf-8")

old_callback = """          onOpenRunner={onOpenRunner}"""

new_callback = """          onOpenRunner={(runner) => {
            const sourceField = Array.isArray(field) ? field : [];

            const runnerIndex = sourceField.findIndex((candidate: any) => {
              if (candidate === runner) return true;

              const candidateNumber =
                candidate?.number ??
                candidate?.runnerNumber ??
                candidate?.saddlecloth ??
                candidate?.no;

              const runnerNumber =
                runner?.number ??
                runner?.runnerNumber ??
                runner?.saddlecloth ??
                runner?.no;

              if (
                candidateNumber !== undefined &&
                runnerNumber !== undefined &&
                String(candidateNumber) === String(runnerNumber)
              ) {
                return true;
              }

              const candidateName = String(
                candidate?.runner ??
                candidate?.runnerName ??
                candidate?.name ??
                "",
              )
                .trim()
                .toUpperCase();

              const runnerName = String(
                runner?.runner ??
                runner?.runnerName ??
                runner?.name ??
                "",
              )
                .trim()
                .toUpperCase();

              return Boolean(candidateName && candidateName === runnerName);
            });

            if (runnerIndex >= 0) {
              onOpenRunner(runnerIndex);
            }
          }}"""

callback_count = race_text.count(old_callback)

if callback_count != 1:
    raise RuntimeError(
        "Expected exactly 1 RaceWorkspace Map onOpenRunner binding, "
        f"found {callback_count}."
    )

race_text = race_text.replace(
    old_callback,
    new_callback,
)

race_path.write_text(
    race_text,
    encoding="utf-8",
)

print("[EDGEIQ] MapWorkspace field arrays normalised")
print("[EDGEIQ] RaceWorkspace runner callback adapted to index")
print("[EDGEIQ] Type repair complete")
