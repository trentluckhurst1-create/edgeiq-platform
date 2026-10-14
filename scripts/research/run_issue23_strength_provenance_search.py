"""Issue23 provenance locator: search local source code for strength-change lineage.

Read-only inventory, no outcome data, no feature promotion. Designed to avoid
scanning enormous CSV files: searches source/config/text files only.
"""
from pathlib import Path
import re

ROOTS=[Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH"),Path(r"C:\EDGEIQ_ISSUE23")]
TERMS=["subsequent_strength_change_last1","subsequent_strength_change_last3",
       "subsequent_strength_change_last5","subsequent_strength_change",
       "strength_change"]
EXT={".py",".md",".json",".yaml",".yml",".toml",".ps1",".sql",".txt"}
SKIP={"node_modules",".git",".venv","venv","__pycache__","outputs","data","dist","build"}
MAX_BYTES=2_000_000
MAX_MATCHES=100
def main():
    found=[]
    scanned=0
    for root in ROOTS:
        if not root.is_dir():continue
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in EXT:continue
            if any(part.lower() in SKIP for part in p.relative_to(root).parts):continue
            try:
                if p.stat().st_size>MAX_BYTES:continue
                lines=p.read_text(encoding="utf-8",errors="replace").splitlines()
            except OSError:continue
            scanned+=1
            for i,line in enumerate(lines):
                if any(t in line.lower() for t in TERMS):
                    lo=max(0,i-2);hi=min(len(lines),i+3)
                    found.append((str(p),i+1,"\n".join(
                        f"  {j+1}: {lines[j][:240]}" for j in range(lo,hi))))
                    if len(found)>=MAX_MATCHES:break
            if len(found)>=MAX_MATCHES:break
        if len(found)>=MAX_MATCHES:break
    print("ISSUE23 — STRENGTH FEATURE PROVENANCE SEARCH")
    print(f"Source files scanned: {scanned}; matches: {len(found)}")
    for path,line,context in found:
        print(f"\n{path}:{line}\n{context}")
    if not found:
        print("\nNO SOURCE LINEAGE FOUND: block feature family. Search historical")
        print("ETL/original upstream repository before considering model use.")
    else:
        print("\nREVIEW REQUIRED: inspect timestamps and dependency chain;")
        print("name/occurrence alone does not certify point-in-time safety.")
if __name__=="__main__":main()
