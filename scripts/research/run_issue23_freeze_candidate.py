"""Freeze Issue23 candidate provenance, race selections and input digests. No outcome unsealing."""
from pathlib import Path
import hashlib,json,datetime
import pandas as pd
ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
BASE=ROOT/"outputs/research/model_v2"
AUDIT=BASE/"issue23_disagreement_gate/ISSUE23_FROZEN_GATE_RACE_AUDIT.csv"
SRC=ROOT/"scripts/research/run_v2_stage011_reproduction_artifact.py"
REPO=Path(__file__).resolve().parents[2]
OUT=BASE/"issue23_disagreement_gate"
FILES=[
 SRC,
 REPO/"scripts/research/run_issue23_full_feature_pairwise.py",
 REPO/"scripts/research/run_issue23_disagreement_gate.py",
 REPO/"scripts/research/run_issue23_frozen_gate_audit.py",
 AUDIT,
]
for y in (2022,2023,2024):
 FILES.extend([BASE/f"stage011_reproduction/STAGE011_RUNNER_PROBABILITIES_{y}.csv",BASE/f"issue23_full_pairwise/ISSUE23_FULL_PAIRWISE_{y}.csv"])
for p in FILES:
 if not p.is_file():raise RuntimeError(f"STOP missing freeze input {p}")
def digest(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(8*1024*1024),b""):h.update(b)
 return h.hexdigest()
a=pd.read_csv(AUDIT,dtype={"race":str,"base_horse":str,"pair_horse":str,"selected_horse":str})
expected={2022:(612,138,140,27),2023:(2396,495,499,118),2024:(2402,552,567,140)}
for y,(r,b,g,s) in expected.items():
 t=a[a.year.eq(y)]
 if (len(t),int(t.base_correct.sum()),int(t.gated_correct.sum()),int(t.switch.sum()))!=(r,b,g,s):raise RuntimeError(f"STOP audit mismatch {y}")
 if t.race.duplicated().any():raise RuntimeError("STOP duplicate race")
 if (t.loc[t.switch.eq(0),"selected_horse"]!=t.loc[t.switch.eq(0),"base_horse"]).any():raise RuntimeError("STOP non-switch identity")
 if (t.loc[t.switch.eq(1),"selected_horse"]!=t.loc[t.switch.eq(1),"pair_horse"]).any():raise RuntimeError("STOP switch identity")
manifest={
 "research_issue":23,"candidate":"STAGE011_PAIRWISE_TOP2_GATE_001","status":"FROZEN_UNPROMOTED",
 "scope":"REUSED_DEVELOPMENT_ONLY","threshold":0.01,
 "selection_rule":"Switch to full-35-feature pairwise top-ranked horse iff it differs from Stage011 top-ranked horse, is Stage011 rank 2, and Stage011 top-2 p gap <=0.01",
 "selection_year":2022,"confirmation_year":2023,"evaluation_year":2024,
 "no_market":True,"sealed_outcome_years":[2025,2026],
 "no_independent_validation":True,"no_profitability_claim":True,
 "expected":{str(y):{"races":v[0],"champion_hits":v[1],"candidate_hits":v[2],"switches":v[3]} for y,v in expected.items()},
 "sha256":{str(p):digest(p) for p in FILES}
}
path=OUT/"ISSUE23_FROZEN_CANDIDATE_MANIFEST.json"
path.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
print("ISSUE23 FROZEN CANDIDATE MANIFEST")
for y,v in expected.items():print(f"YEAR={y} RACES={v[0]} BASE={v[1]} GATED={v[2]} SWITCHES={v[3]}")
print(f"HASHED_FILES={len(FILES)}")
print("MANIFEST="+str(path))
print("STATUS=FROZEN_UNPROMOTED; NO_2025_2026_OUTCOMES")
