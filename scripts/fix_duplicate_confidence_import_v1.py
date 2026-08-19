from pathlib import Path

file = Path("src/edgeiq-os/command/EdgeiqCommandWorkspace.tsx")

text = file.read_text(encoding="utf-8")

lines = text.splitlines()

seen = set()
out = []

for line in lines:

    if line.strip() == 'import { ConfidenceProfile } from "./components/ConfidenceProfile";':

        if line in seen:
            continue

        seen.add(line)

    out.append(line)

file.write_text("\n".join(out) + "\n", encoding="utf-8")

print("[EDGEIQ] Duplicate ConfidenceProfile import removed")
