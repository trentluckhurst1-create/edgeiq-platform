from pathlib import Path
import re, json
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_price_diagnostics\lab231\run_lab231_performance_representation_search.py")
s=P.read_text(encoding="utf-8",errors="replace").splitlines()
terms=re.compile(r"share_near_peak|near_peak|same_class|same_condition|class_epi|cond_epi|track_condition|race_class|read_csv|SOURCE|source|class_col|condition_col",re.I)
hits=[]
for i,line in enumerate(s):
    if terms.search(line):
        lo=max(0,i-8); hi=min(len(s),i+9)
        hits.append({"line":i+1,"context":[f"{j+1}: {s[j]}" for j in range(lo,hi)]})
print("LAB245D18_TARGETED_BUILDER_INSPECTION")
print("PATH="+str(P))
print("LINES="+str(len(s)))
for h in hits:
    print("\n--- HIT LINE",h["line"],"---")
    print("\n".join(h["context"]))
