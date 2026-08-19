from pathlib import Path

adapters = [
    "RaceShapeAdapter.ts",
    "RunnerDNAAdapter.ts",
    "ExplainabilityAdapter.ts",
]

for name in adapters:
    path = Path("src/edgeiq-os/services/adapters") / name
    text = path.read_text(encoding="utf-8")

    if 'from "../feed-context"' not in text:
        text = text.replace(
            'import { loadBundledCsv',
            'import { getActiveRaceContext, findFirstActiveRaceRow } from "../feed-context";\nimport { loadBundledCsv'
        )

    text = text.replace(
        "const firstRace = feed.rows[0];",
        """const context = getActiveRaceContext();
    const firstRace = findFirstActiveRaceRow(feed.rows, context);"""
    )

    text = text.replace(
        "const row = feed.rows[0];",
        """const context = getActiveRaceContext();
    const row = findFirstActiveRaceRow(feed.rows, context);"""
    )

    path.write_text(text, encoding="utf-8")

print("[EDGEIQ] Active race context wired into live adapters")
