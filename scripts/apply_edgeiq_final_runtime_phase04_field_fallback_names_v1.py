from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT = ROOT / "docs" / "full-product-implementation" / "checkpoints" / f"CHECKPOINT_FINAL_RUNTIME_PHASE04_FIELD_FALLBACK_NAMES_{STAMP}"
FILES = [
    "src/edgeiq-os/race/components/PerformanceWorkspace.tsx",
    "src/edgeiq-os/race/components/EpiWorkspaceWorkspace.tsx",
    "src/edgeiq-os/race/components/OverviewWorkspace.tsx",
    "src/edgeiq-os/race/components/InsightsWorkspace.tsx",
]
for rel in FILES:
    src = ROOT / rel
    dst = CHECKPOINT / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def edit(rel, fn):
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    new = fn(text)
    if new == text:
        raise SystemExit(f"No change made to {rel}")
    path.write_text(new, encoding="utf-8", newline="\n")


def must_replace(text, old, new, label):
    if old not in text:
        raise SystemExit(f"Missing target for {label}")
    return text.replace(old, new, 1)

first_text_helper = '''function firstText(...values: unknown[]): string {
  for (const value of values) {
    const text = String(value ?? "").trim();
    if (text && text !== "-" && text.toLowerCase() !== "null" && text.toLowerCase() !== "undefined") return text;
  }
  return "";
}

'''

def patch_performance(text):
    text = must_replace(text,
'''function runnerDisplay(row: any, index: number): { no: string; horse: string } {
  const no = String(row?.number ?? row?.runnerNumber ?? row?.saddlecloth ?? row?.no ?? index + 1).trim();
  const horse = String(row?.runnerName ?? row?.runner ?? row?.horse ?? row?.name ?? "Runner pending").trim();
  return { no, horse };
}
''',
first_text_helper + '''function runnerDisplay(row: any, index: number): { no: string; horse: string } {
  const no = firstText(row?.official?.number, row?.number, row?.runnerNumber, row?.saddlecloth, row?.no, index + 1);
  const horse = firstText(row?.official?.runner, row?.runner, row?.horse, row?.runnerName, row?.name, "Runner pending");
  return { no, horse };
}
''', "performance names")
    return text

edit("src/edgeiq-os/race/components/PerformanceWorkspace.tsx", patch_performance)

def patch_epi(text):
    text = must_replace(text,
'''function fieldRunner(row: any, index: number): { no: string; horse: string; jockey: string; trainer: string } {
  return {
    no: String(row?.number ?? row?.runnerNumber ?? row?.saddlecloth ?? row?.no ?? index + 1).trim(),
    horse: String(row?.runnerName ?? row?.runner ?? row?.horse ?? row?.name ?? "Runner pending").trim(),
    jockey: String(row?.jockey ?? row?.jockeyName ?? row?.rider ?? "Pending").trim(),
    trainer: String(row?.trainer ?? row?.trainerName ?? "Pending").trim(),
  };
}
''',
first_text_helper + '''function fieldRunner(row: any, index: number): { no: string; horse: string; jockey: string; trainer: string } {
  return {
    no: firstText(row?.official?.number, row?.number, row?.runnerNumber, row?.saddlecloth, row?.no, index + 1),
    horse: firstText(row?.official?.runner, row?.runner, row?.horse, row?.runnerName, row?.name, "Runner pending"),
    jockey: firstText(row?.official?.jockey, row?.jockey, row?.jockeyName, row?.rider, "Pending"),
    trainer: firstText(row?.official?.trainer, row?.trainer, row?.trainerName, "Pending"),
  };
}
''', "epi names")
    return text

edit("src/edgeiq-os/race/components/EpiWorkspaceWorkspace.tsx", patch_epi)

def patch_overview(text):
    if first_text_helper.strip() not in text:
        text = must_replace(text,
'''function value(rowValue: unknown): string {

  const text = String(rowValue ?? "").trim();

  if (!text || text === "-" || text === "null" || text === "undefined" || text.toLowerCase() === "none") return "";

  return text;

}
''',
'''function value(rowValue: unknown): string {

  const text = String(rowValue ?? "").trim();

  if (!text || text === "-" || text === "null" || text === "undefined" || text.toLowerCase() === "none") return "";

  return text;

}

function firstText(...values: unknown[]): string {
  for (const value of values) {
    const text = String(value ?? "").trim();
    if (text && text !== "-" && text.toLowerCase() !== "null" && text.toLowerCase() !== "undefined") return text;
  }
  return "";
}
''', "overview firstText")
    text = must_replace(text,
'''{fallbackField.length ? fallbackField.map((runner, index) => { const no = String(runner?.number ?? runner?.runnerNumber ?? runner?.saddlecloth ?? runner?.no ?? index + 1).trim(); const horse = String(runner?.runnerName ?? runner?.runner ?? runner?.horse ?? runner?.name ?? "Runner pending").trim(); return <tr key={`${no}-${horse}`}><td>{no}</td><td><strong>{horse}</strong></td><td>Pending</td><td>Pending</td></tr>; }) : <tr><td colSpan={4}>Select a race with declared runners to populate the runner board.</td></tr>}''',
'''{fallbackField.length ? fallbackField.map((runner, index) => { const no = firstText(runner?.official?.number, runner?.number, runner?.runnerNumber, runner?.saddlecloth, runner?.no, index + 1); const horse = firstText(runner?.official?.runner, runner?.runner, runner?.horse, runner?.runnerName, runner?.name, "Runner pending"); return <tr key={`${no}-${horse}`}><td>{no}</td><td><strong>{horse}</strong></td><td>Pending</td><td>Pending</td></tr>; }) : <tr><td colSpan={4}>Select a race with declared runners to populate the runner board.</td></tr>}''', "overview inline names")
    return text

edit("src/edgeiq-os/race/components/OverviewWorkspace.tsx", patch_overview)

def patch_insights(text):
    if first_text_helper.strip() not in text:
        text = must_replace(text,
'''function value(rowValue: string | null | undefined): string {
  return rowValue && rowValue.trim() ? rowValue : "";
}
''',
'''function value(rowValue: string | null | undefined): string {
  return rowValue && rowValue.trim() ? rowValue : "";
}

function firstText(...values: unknown[]): string {
  for (const value of values) {
    const text = String(value ?? "").trim();
    if (text && text !== "-" && text.toLowerCase() !== "null" && text.toLowerCase() !== "undefined") return text;
  }
  return "";
}
''', "insights firstText")
    text = must_replace(text,
'''      no: String(runner?.number ?? runner?.runnerNumber ?? runner?.saddlecloth ?? runner?.no ?? index + 1).trim(),
      horse: String(runner?.runnerName ?? runner?.runner ?? runner?.horse ?? runner?.name ?? "Runner pending").trim(),''',
'''      no: firstText(runner?.official?.number, runner?.number, runner?.runnerNumber, runner?.saddlecloth, runner?.no, index + 1),
      horse: firstText(runner?.official?.runner, runner?.runner, runner?.horse, runner?.runnerName, runner?.name, "Runner pending"),''', "insights names")
    return text

edit("src/edgeiq-os/race/components/InsightsWorkspace.tsx", patch_insights)

print(f"EDGEIQ_FINAL_RUNTIME_PHASE04_FIELD_FALLBACK_NAMES_PASS checkpoint={CHECKPOINT}")
