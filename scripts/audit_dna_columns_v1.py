from pathlib import Path
import csv, re

dna = Path("public/data/edgeiq_runner_dna_v6_2.csv")
out = Path("public/data/edgeiq_dna_column_audit_v1.txt")

with dna.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
    reader = csv.DictReader(f)
    fields = reader.fieldnames or []
    rows = [row for _, row in zip(range(8), reader)]

lines = ["DNA COLUMN AUDIT", "", "FIELDS:", *fields, "", "SAMPLE:"]
for row in rows:
    lines.append(str(row))

out.write_text("\n".join(lines), encoding="utf-8")
print("[EDGEIQ] DNA audit:", out)
