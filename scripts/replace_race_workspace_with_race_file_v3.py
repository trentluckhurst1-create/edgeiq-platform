from pathlib import Path
import re

race_ws = Path("src/edgeiq-os/race/EdgeiqRaceWorkspace.tsx")
css = Path("src/styles/edgeiqProductTerminalV1.css")

race_ws.write_text(r'''
import { RaceFileV3 } from "./RaceFileV3";

export function EdgeiqRaceWorkspace() {
  return (
    <main className="eiq-race-workspace-v3">
      <RaceFileV3 />
    </main>
  );
}
'''.lstrip(), encoding="utf-8")

marker = "EDGEiQ Race Workspace V3 Default"
existing = css.read_text(encoding="utf-8")

if marker not in existing:
    css.write_text(existing + r'''

/* ==========================================================================
   EDGEiQ Race Workspace V3 Default
   ========================================================================== */

.eiq-race-workspace-v3 {
  width: 100%;
  min-height: 100%;
  padding: 0 22px 56px;
}

.eiq-race-workspace-v3 .eiq-race-file-v3 {
  padding-top: 0;
}

.eiq-race-workspace-v3 .eiq-race-file-v3__hero {
  margin-top: 0;
}
''', encoding="utf-8")

print("[EDGEIQ] Race workspace replaced with Race File V3 default")
