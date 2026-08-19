from pathlib import Path
import re

p = Path(r".\src\components\RaceIntelligenceScreen.tsx")
text = p.read_text(encoding="utf-8", errors="replace")
lines = text.splitlines()

patterns = [
    "EDGEIQ",
    "GraphQL",
    "Positive Signals",
    "Risk Signals",
    "Why We Like It",
    "What Could Beat It",
    "Connection DNA",
    "Jockey Track",
    "Combo Track",
    "SP Delta",
    "pts from",
    "No EDGEiQ summary loaded",
]

out = []
out.append("EDGEiQ COMMAND PRODUCTISATION AUDIT")
out.append("=" * 60)

for pat in patterns:
    hits = []
    for i, line in enumerate(lines, start=1):
        if pat in line:
            hits.append((i, line.strip()))
    out.append("")
    out.append(f"PATTERN: {pat}")
    out.append(f"HITS: {len(hits)}")
    for i, line in hits[:25]:
        out.append(f"{i}: {line}")

audit_path = Path(r".\public\data\edgeiq_command_productisation_ui_audit_v1.txt")
audit_path.write_text("\n".join(out), encoding="utf-8")

print("[COMMAND_PRODUCTISATION_UI_AUDIT] COMPLETE")
print(audit_path)
