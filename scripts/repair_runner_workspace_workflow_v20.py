from pathlib import Path

tsx = Path("src/edgeiq-os/race/RaceFileV3.tsx")

backup = Path("src/edgeiq-os/race/RaceFileV3_CHECKPOINT_BEFORE_WORKFLOW_FIX_V20.tsx")
backup.write_text(tsx.read_text(encoding="utf-8"), encoding="utf-8")

text = tsx.read_text(encoding="utf-8")

old = '''const displayedRuns = useMemo(() => {
    if (!primary) return [];
    if (mode === "evidence") return (primary as any).evidenceRuns ?? primary.historicalRuns;
    return primary.historicalRuns;
  }, [mode]);'''

new = '''const displayedRuns = useMemo(() => {
    if (!primary) return [];

    switch (mode) {
      case "form":
        return primary.historicalRuns;

      case "compare":
        return primary.historicalRuns;

      case "race":
        return primary.historicalRuns;

      default:
        return primary.historicalRuns;
    }
  }, [primary, mode]);'''

if old in text:
    text = text.replace(old, new)
else:
    raise SystemExit("displayedRuns block not found")

text = text.replace("Â·", "|")
text = text.replace(" pressure", " Pressure")

tsx.write_text(text, encoding="utf-8")

print("[EDGEIQ] Workflow V20 repaired")
print("[EDGEIQ] Removed obsolete evidence workspace")
print("[EDGEIQ] Fixed runner header separators")
print(f"[EDGEIQ] checkpoint: {backup}")
