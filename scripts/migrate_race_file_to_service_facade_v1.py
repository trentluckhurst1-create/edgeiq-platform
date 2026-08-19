from pathlib import Path

services = Path("src/edgeiq-os/services")
race_file = Path("src/edgeiq-os/race/RaceFileV2.tsx")

(services / "RaceFileService.ts").write_text(r'''
import { buildRaceFileV2 } from "./race-file-v2";

export type {
  RaceFileModelV1,
  RaceFileRunnerProfile,
  HistoricalRun,
  OfficialRaceData,
  OfficialRunnerData,
  EdgeiqSpeedProfileSplit,
} from "./race-file-model";

export const RaceFileService = {
  build: buildRaceFileV2,
};

export { buildRaceFileV2, buildRaceFileV2 as buildRaceFile };
'''.lstrip(), encoding="utf-8")

text = race_file.read_text(encoding="utf-8")

text = text.replace(
    'import { buildRaceFileV2 } from "../services/RaceFileService";',
    'import { RaceFileService } from "../services/RaceFileService";'
)

text = text.replace(
    "const file = buildRaceFileV2();",
    "const file = RaceFileService.build();"
)

race_file.write_text(text, encoding="utf-8")

print("[EDGEIQ] Race File migrated to RaceFileService facade")
