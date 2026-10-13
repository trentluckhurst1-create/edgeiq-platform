"""Locate original Stage011 margin-per-runner formulas in local research scripts.
Read-only. Prints matching source lines and context, never guesses semantics.
"""
from pathlib import Path
import argparse

def main():
 a=argparse.ArgumentParser()
 a.add_argument("--root",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\scripts\research")
 a.add_argument("--context",type=int,default=4)
 args=a.parse_args()
 root=Path(args.root)
 if not root.is_dir():raise RuntimeError("STOP original research scripts not found: "+str(root))
 terms=("margin_per_runner_last1","margin_per_runner_last2")
 hits=0
 for path in sorted(root.rglob("*.py")):
  try:lines=path.read_text(encoding="utf-8-sig").splitlines()
  except (UnicodeError,OSError):continue
  matched=[i for i,line in enumerate(lines) if any(t in line for t in terms)]
  if not matched:continue
  print("\nFILE",path)
  emitted=set()
  for i in matched:
   for j in range(max(0,i-args.context),min(len(lines),i+args.context+1)):
    if j not in emitted:print(f"{j+1:05d}: {lines[j]}");emitted.add(j)
   print("---")
   hits+=1
 print("\nMATCHES",hits)
 if not hits:print("STOP no source definition found; do not infer formula from feature name")
if __name__=="__main__":main()
