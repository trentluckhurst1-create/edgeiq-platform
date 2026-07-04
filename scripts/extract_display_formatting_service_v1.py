from pathlib import Path

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
text = path.read_text(encoding="utf-8")

service = root / "src" / "services" / "displayFormattingService.ts"

start = text.index("function cellTone(label: string): string {")
end = text.index("\nexport default function RaceIntelligenceScreen", start)

block = text[start:end]

service_text = '''import type { CSSProperties } from "react";
import type { CsvRow } from "../utils/edgeiqCsv";
import { firstText } from "../utils/raceRowHelpers";
import { edgePct, fairPrice, livePrice } from "./marketPricingService";

type Row = CsvRow;

''' + block

service_text = service_text.replace("React.CSSProperties", "CSSProperties")
service_text = service_text.replace("function ", "export function ")

service.write_text(service_text, encoding="utf-8")

text = text[:start] + text[end:]

import_line = 'import { campaignEvidenceTone, cellTone, connectionTone, coverageStatus, coverageStatusTone, customerPerformanceNarrative, decision, drawerValue, evidenceQualityTone, fitReadLabel, formatCampaignStage, formatCampaignWindow, hiddenGemTone, historyReadLabel, opportunityTone, ordinal, performanceIntelligenceLabel, riskTone, runnerTrendSummary, runnerTrendTone, sourceLabel, trajectoryTone, valueccent } from "../services/displayFormattingService";'

if import_line not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines) + "\n"

path.write_text(text, encoding="utf-8")
print("[DISPLAY_FORMATTING_SERVICE_EXTRACT] complete")
