from pathlib import Path
import re

path = Path("src/edgeiq-os/services/race-file-v2.ts")
backup = Path("src/edgeiq-os/services/race-file-v2_CHECKPOINT_BEFORE_FIELD_SOURCE_BUILDER_V2_20260709.ts")
backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

text = path.read_text(encoding="utf-8")

if 'liveRaceRunnerSnapshot' not in text:
    text = text.replace(
        'import { findLiveRunnerSnapshot } from "./live-race-data-snapshot";',
        'import { findLiveRunnerSnapshot, liveRaceRunnerSnapshot } from "./live-race-data-snapshot";'
    )
else:
    text = text.replace(
        'import { findLiveRunnerSnapshot } from "./live-race-data-snapshot";',
        'import { findLiveRunnerSnapshot, liveRaceRunnerSnapshot } from "./live-race-data-snapshot";'
    )

# Replace the demo names array if present.
text = re.sub(
    r'const names\s*=\s*\[[\s\S]*?\];',
    '''const names =
    liveRaceRunnerSnapshot.length > 0
      ? liveRaceRunnerSnapshot.map((runner) => runner.runner).filter(Boolean)
      : ["Runner 1", "Runner 2", "Runner 3", "Runner 4"];''',
    text,
    count=1
)

# Improve fallbacks.
text = text.replace('"Production runner pending"', '"Runner pending"')
text = text.replace('"Primary stable"', '"Stable pending"')
text = text.replace('"Mapped stable"', '"Stable pending"')
text = text.replace('"Primary jockey"', '"Jockey pending"')
text = text.replace('"Mapped jockey"', '"Jockey pending"')
text = text.replace('"Monitor"', '"Market pending"')
text = text.replace('"Neutral"', '"Reference"')
text = text.replace('"Profile pending"', '"Awaiting DNA"')
text = text.replace('"Aligned"', '"DNA aligned"')
text = text.replace('"Watch"', '"Needs review"')

# Add live runner lookup correctly if missing.
if "const liveRunner = findLiveRunnerSnapshot(runner);" not in text:
    text = text.replace(
        "field: names.map((runner, index) => {",
        "field: names.map((runner, index) => {\n      const liveRunner = findLiveRunnerSnapshot(runner);"
    )

# Make assessment less placeholder-like.
text = text.replace(
    'assessment: index === 0 ? "Key reference runner. Historical runs show above-standard SpeedProfile and positive race-strength form." : "Requires more evidence before firm assessment.",',
    '''assessment:
        index === 0
          ? "Primary investigation runner. Historical evidence is available and should be tested against today’s assignment."
          : "Secondary investigation runner. Review historical evidence before forming a position.",'''
)

path.write_text(text, encoding="utf-8")
print("[EDGEIQ] Race file builder now sources field from live snapshot where available")
print(f"[EDGEIQ] checkpoint: {backup}")
