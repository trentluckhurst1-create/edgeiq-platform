from pathlib import Path

path = Path(r".\src\components\FormTab.tsx")
text = path.read_text(encoding="utf-8")

text = text.replace(
'''  const selectedSpeed = speedRows.find((row) =>
    String(row.horse ?? "").toUpperCase().replace(/[^A-Z0-9]/g, "") ===
    String(selected?.horse ?? "").toUpperCase().replace(/[^A-Z0-9]/g, "")
  );''',
'''  function canonHorse(v: unknown): string {
    return String(v ?? "")
      .toUpperCase()
      .replace(/\\([^)]*\\)/g, "")
      .replace(/[^A-Z0-9]/g, "");
  }

  const selectedSpeed = speedRows.find((row) =>
    canonHorse(row.horse ?? row.horse_name ?? row.runner_name) === canonHorse(selected?.horse)
  );'''
)

path.write_text(text, encoding="utf-8")

print("FORMTAB SPEED ROW MATCHING FIXED FOR HORSE SUFFIXES")
