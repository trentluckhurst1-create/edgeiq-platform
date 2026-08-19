from pathlib import Path

targets = [
    Path("src/edgeiq-os/command/components/CommandExecutiveBrief.tsx"),
    Path("src/edgeiq-os/command/components/AgreementMatrix.tsx"),
    Path("src/edgeiq-os/command/components/ConfidenceProfile.tsx"),
    Path("src/edgeiq-os/command/components/IntelligenceTimeline.tsx"),
]

for path in targets:
    if not path.exists():
        continue

    text = path.read_text(encoding="utf-8")

    lines = text.splitlines()

    new_lines = []
    command_import_written = False

    for line in lines:

        if 'import { CommandService } from "../../services/CommandService";' in line:
            if command_import_written:
                continue
            command_import_written = True

        new_lines.append(line)

    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

print("[EDGEIQ] Duplicate CommandService imports removed")
