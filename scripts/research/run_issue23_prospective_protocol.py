"""Issue23: validate frozen provenance and prepare blind prospective scoring contract."""
from pathlib import Path
import hashlib,json
import pandas as pd
R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
O=R/"outputs/research/model_v2/issue23_disagreement_gate"
M=O/"ISSUE23_FROZEN_CANDIDATE_MANIFEST.json"
if not M.is_file():raise RuntimeError("STOP: freeze manifest missing")
m=json.loads(M.read_text(encoding="utf-8"))
if m.get("status")!="FROZEN_UNPROMOTED" or m.get("threshold")!=.01:raise RuntimeError("STOP: frozen candidate contract drift")
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(8*1024*1024),b""):h.update(b)
 return h.hexdigest()
for path,expected in m["sha256"].items():
 p=Path(path)
 if not p.is_file() or sha(p)!=expected:raise RuntimeError("STOP: source/prediction hash mismatch "+path)
print("FROZEN_HASH_AUDIT=PASS FILES="+str(len(m["sha256"])))
a=pd.read_csv(O/"ISSUE23_FROZEN_GATE_RACE_AUDIT.csv")
for year in (2022,2023,2024):
 g=a[a.year.eq(year)]
 print(f"YEAR={year} RACES={len(g)} GATED_HITS={int(g.gated_correct.sum())} BASE_HITS={int(g.base_correct.sum())}")
# Only design a prospective protocol; no sealed historical outcomes accessed.
contract={
 "candidate":"STAGE011_PAIRWISE_TOP2_GATE_001",
 "status":"READY_FOR_BLIND_PROSPECTIVE_PROTOCOL_NOT_VALIDATED",
 "immutable_manifest_sha256":sha(M),
 "scoring_rule":"Use Stage011 unless pairwise top horse is Stage011 rank 2 and Stage011 top-two probability difference <= 0.01",
 "must_freeze_before_race":["race_id","horse_id","scheduled_start_time","prediction_timestamp","stage011_probability","pairwise_score","stage011_rank","selected_horse","candidate_model_sha256","source_snapshot_sha256"],
 "no_postrace_feature_recomputation":True,
 "independent_evaluation":"Collect timestamped predictions before each future race; lock records before results; score only after race outcomes are independently certified",
 "prohibited":["2025-2026 outcome access for model selection","market or SP inputs","threshold retuning","postrace selection edits","production promotion"],
 "minimum_reporting":["eligible races","coverage and exclusions","top1 champion vs challenger","paired gained and lost races","paired confidence interval","race-day and meeting clustering","source freshness and point-in-time audit"]
}
path=O/"ISSUE23_BLIND_PROSPECTIVE_PROTOCOL.json"
path.write_text(json.dumps(contract,indent=2)+"\n",encoding="utf-8")
print("PROTOCOL="+str(path))
print("NO_2025_2026_OUTCOMES_READ; NO_PROMOTION")
