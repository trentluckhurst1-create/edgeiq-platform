from pathlib import Path

root = Path(".")
out = []

for base in [
    "src/edgeiq-os",
    "src/components",
    "src/styles",
    "scripts",
]:
    p = root / base
    out.append("")
    out.append(f"===== {base} =====")
    if p.exists():
        for f in sorted(p.rglob("*")):
            if f.is_file():
                out.append(str(f))
    else:
        out.append("MISSING")

Path("EDGEIQ_CURRENT_STRUCTURE_AUDIT.txt").write_text("\n".join(out), encoding="utf-8")
print("[EDGEIQ] Current structure audit written")
