from pathlib import Path
import csv, math
from collections import defaultdict
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2")
PIT=ROOT/"stage006"/"V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv"
PRED=ROOT/"stage011_reproduction"
FEATURES=["hist_runs","lvs_last1","lvs_mean3","lvs_mean5","lvs_median5","lvs_std5","lvs_peak","lvs_worst5","margin_mean5","margin_std5","margin_worst5","margin_last1","margin_last2","last_distance","margin_change_l1_l2","margin_per_runner_last1","margin_per_runner_last2","days_since_last","dist200_runs","dist200_lvs_mean","dist200_lvs_best"]
print("ISSUE23 — RACE-LEVEL PAIRWISE WINNER RANKER")
print("FIT 2022; SELECT C ON 2023; FIXED 2024 EVALUATION; NO MARKET; NO 2025-26")
pit={}
with PIT.open(encoding="utf-8-sig",newline="") as f:
 reader=csv.DictReader(f)
 if not set(FEATURES).issubset(reader.fieldnames or []):raise SystemExit("STOP missing feature")
 for r in reader:
  if (r.get("race_date") or "")[:4] not in {"2022","2023","2024"}:continue
  k=(r["_race"],r["_horse"])
  if k in pit:raise SystemExit("STOP duplicate PIT")
  pit[k]=r
races={}
for year,expected in ((2022,7459),(2023,30163),(2024,31234)):
 rr=defaultdict(list);seen=set()
 with (PRED/f"STAGE011_RUNNER_PROBABILITIES_{year}.csv").open(encoding="utf-8-sig",newline="") as f:
  for r in csv.DictReader(f):
   k=(r["_race"],r["_horse"])
   if k in seen or k not in pit:raise SystemExit("STOP identity mismatch")
   seen.add(k)
   if (r["race_date"] or "")[:4]!=str(year):raise SystemExit("STOP year mismatch")
   x=[]
   for name in FEATURES:
    try:
     v=float(pit[k][name])
     x.append(v if math.isfinite(v) else np.nan)
    except (ValueError,TypeError):x.append(np.nan)
   y=int(float(r["y"]));p=float(r["p"])
   if y not in (0,1) or not 0<=p<=1:raise SystemExit("STOP invalid target/p")
   rr[r["_race"]].append((r["_horse"],y,p,x))
 if len(seen)!=expected or any(sum(z[1] for z in rows)!=1 for rows in rr.values()):raise SystemExit("STOP population drift")
 races[year]=rr
 print(f"YEAR={year} RACES={len(rr)} RUNNERS={len(seen)}")
# Imputation and scaling are fitted on 2022 ONLY.
train_rows=[z for race in races[2022].values() for z in race]
imp=SimpleImputer(strategy="median",add_indicator=False,keep_empty_features=True)
scale=StandardScaler()
scale.fit(imp.fit_transform(np.array([z[3] for z in train_rows],dtype=float)))
def transform(year):
 return {race:scale.transform(imp.transform(np.array([z[3] for z in rows],dtype=float))) for race,rows in races[year].items()}
X={year:transform(year) for year in (2022,2023,2024)}
# Each winner-vs-loser difference yields one positive and one mirrored negative example.
pairs=[]
for race,rows in races[2022].items():
 a=X[2022][race];wi=next(i for i,z in enumerate(rows) if z[1])
 for j in range(len(rows)):
  if j!=wi:pairs.append(a[wi]-a[j])
D=np.array(pairs)
XX=np.concatenate((D,-D),axis=0)
yy=np.concatenate((np.ones(len(D),dtype=int),np.zeros(len(D),dtype=int)))
print(f"TRAIN_PAIR_COMPARISONS={len(D)} TRAIN_SAMPLES={len(XX)} FEATURES={len(FEATURES)}")
def evaluate(year,coef):
 baseline=challenger=corrected=lost=changed=0
 for race,rows in races[year].items():
  scores=X[year][race]@coef
  a=max(range(len(rows)),key=lambda i:(rows[i][2],rows[i][0]))
  b=max(range(len(rows)),key=lambda i:(scores[i],rows[i][0]))
  baseline+=rows[a][1];challenger+=rows[b][1]
  corrected+=rows[a][1]==0 and rows[b][1]==1
  lost+=rows[a][1]==1 and rows[b][1]==0
  changed+=a!=b
 return (baseline,challenger,corrected,lost,changed)
# A single small, predeclared regularization choice on 2023.
models={}
for C in (0.01,0.1,1.0):
 model=LogisticRegression(C=C,fit_intercept=False,max_iter=600,solver="lbfgs")
 model.fit(XX,yy)
 models[C]=model
 result=evaluate(2023,model.coef_[0])
 print(f"SELECT_2023 C={C} BASE={result[0]} PAIRWISE={result[1]} DELTA={result[1]-result[0]:+d} CHANGED={result[4]}")
best=max(models,key=lambda c:(evaluate(2023,models[c].coef_[0])[1],-c))
print(f"FROZEN_C={best}")
for year in (2022,2023,2024):
 a,b,up,down,changed=evaluate(year,models[best].coef_[0])
 print(f"YEAR={year} ROLE={'FIT' if year==2022 else 'SELECT' if year==2023 else 'EVALUATE'} RACES={len(races[year])} BASE_HITS={a} PAIRWISE_HITS={b} DELTA_HITS={b-a:+d} DELTA_PP={100*(b-a)/len(races[year]):+.4f} CORRECTED={up} LOST={down} CHANGED={changed}")
print("NO_PROMOTION: RESEARCH YEARS PREVIOUSLY EXPLORED; FURTHER INDEPENDENT VALIDATION REQUIRED")
