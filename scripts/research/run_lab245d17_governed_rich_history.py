from pathlib import Path
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
terms=("race_class_group","track_condition_group")
hits=[]
for base in [ROOT/"outputs/research/model_price_diagnostics",ROOT/"outputs/research"]:
    if not base.exists(): continue
    for p in base.rglob("*.py"):
        try:
            s=p.read_text(encoding="utf-8-sig",errors="ignore")
        except: continue
        if all(t in s for t in terms):
            hits.append((p.stat().st_mtime,p))
for _,p in sorted(hits,reverse=True)[:40]: print(p)
