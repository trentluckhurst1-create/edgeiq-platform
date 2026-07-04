from pathlib import Path

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
text = path.read_text(encoding="utf-8")

service = root / "src" / "services" / "sidecarLookupService.ts"

block1_start = text.index("function sameRunner(a: Row, b: Row): boolean {")
block1_end = text.index("\nfunction hasConnectionPayload", block1_start)

block2_start = text.index("function compactKey(value: unknown): string {")
block2_end = text.index("\nfunction connectionSourceRow", block2_start)

block1 = text[block1_start:block1_end]
block2 = text[block2_start:block2_end]

service_text = '''import type { CsvRow } from "../utils/edgeiqCsv";
import { cleanHorse, cleanHorseLoose, cleanTrack, text } from "../utils/edgeiqFormat";
import { firstText, horse, raceDate, raceNo, track } from "../utils/raceRowHelpers";

type Row = CsvRow;

''' + block1 + "\n\n" + block2

service_text = service_text.replace("function ", "export function ")

service.write_text(service_text, encoding="utf-8")

text = text[:block1_start] + text[block1_end:]
block2_start = text.index("function compactKey(value: unknown): string {")
block2_end = text.index("\nfunction connectionSourceRow", block2_start)
text = text[:block2_start] + text[block2_end:]

import_line = 'import { compactKey, findCampaignSidecar, findCommandEnrichmentSidecar, findConnectionSidecar, findDnaSidecar, findFormEnrichmentSidecar, findHiddenGemForRunner, findNexusContextualSidecar, findSidecar, findSidecarByRaceHorse, sameRunner } from "../services/sidecarLookupService";'

if import_line not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines) + "\n"

path.write_text(text, encoding="utf-8")
print("[SIDECAR_LOOKUP_SERVICE_EXTRACT] complete")
