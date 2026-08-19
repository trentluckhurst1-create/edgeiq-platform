from __future__ import annotations
import csv, hashlib, json, math
from decimal import Decimal, getcontext
from pathlib import Path
from datetime import datetime, timezone

getcontext().prec = 50
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CONFIG = ROOT / "config" / "performance-intelligence"
DOC = ROOT / "docs" / "performance-intelligence" / "horse-performance-rating" / "method-governance"
BASE = DATA / "edgeiq_performance_intelligence_base_fact_v1.csv"
APPROVAL = DOC / "EDGEIQ_HORSE_RATING_METHODOLOGY_OWNER_APPROVAL_V1.md"
CANDIDATE = CONFIG / "edgeiq_performance_normalisation_parameter_source_v1_CANDIDATE.csv"
MANIFEST = DOC / "edgeiq_performance_normalisation_parameter_source_v1_candidate_manifest.json"
POP_AUDIT = DOC / "edgeiq_performance_normalisation_parameter_population_v1.csv"
FIELDS = ["normalisation_method","centre_value","scale_value","normalisation_model_version","parameter_status","effective_from_date","effective_to_date","evidence_reference","evidence_sha256"]
METHOD = "LINEAR_CENTRE_AND_SCALE"
MODEL_VERSION = "HPR-NORM-A-v1"
SEMANTIC_METHOD = "NORM_A_HISTORICAL_POPULATION_LINEAR_CENTRE_SCALE_V1"
MIN_POP = 100

def text(v): return str(v if v is not None else "").strip()
def sha(parts): return hashlib.sha256("\x1f".join(text(p) for p in parts).encode("utf-8")).hexdigest()
def q12(d: Decimal) -> str: return format(d.quantize(Decimal("0.000000000001")), "f")

def read_base():
    with BASE.open(newline='', encoding='utf-8-sig') as f:
        rows=list(csv.DictReader(f))
    eligible=[]
    for row in rows:
        if text(row.get('performance_status')) != 'OBSERVED_GOVERNED':
            continue
        raw=text(row.get('raw_performance_lengths'))
        if raw == '':
            continue
        val=Decimal(raw)
        if not val.is_finite():
            continue
        key=text(row.get('performance_intelligence_base_id')) or sha([row.get('race_key'), row.get('winner_horse_name'), row.get('raw_performance_lengths'), row.get('source_lengths_versus_standard_evidence_sha256')])
        eligible.append((key,row,val))
    eligible.sort(key=lambda item: item[0])
    return eligible

def main():
    if not APPROVAL.exists():
        raise RuntimeError(f"Missing approval document: {APPROVAL}")
    eligible=read_base()
    n=len(eligible)
    if n < MIN_POP:
        raise RuntimeError(f"Approved minimum population not met: {n} < {MIN_POP}")
    values=[v for _,_,v in eligible]
    centre=sum(values) / Decimal(n)
    variance=sum((v-centre)*(v-centre) for v in values) / Decimal(n)
    scale=variance.sqrt()
    if not scale.is_finite() or scale <= 0:
        raise RuntimeError(f"Invalid scale value: {scale}")
    pop_hash = sha(["HPR-NORM-A-v1", n] + [f"{key}:{q12(val)}:{text(row.get('performance_intelligence_base_evidence_sha256'))}" for key,row,val in eligible])
    evidence_ref = f"{APPROVAL.as_posix()} | {POP_AUDIT.as_posix()} | population_sha256={pop_hash}"
    evidence_sha = sha([SEMANTIC_METHOD, METHOD, MODEL_VERSION, n, q12(centre), q12(scale), pop_hash, APPROVAL.read_text(encoding='utf-8')])
    min_date=min(text(row.get('race_date')) for _,row,_ in eligible if text(row.get('race_date')))
    source_row={
        "normalisation_method": METHOD,
        "centre_value": q12(centre),
        "scale_value": q12(scale),
        "normalisation_model_version": MODEL_VERSION,
        "parameter_status": "APPROVED",
        "effective_from_date": min_date,
        "effective_to_date": "",
        "evidence_reference": evidence_ref,
        "evidence_sha256": evidence_sha,
    }
    CONFIG.mkdir(parents=True, exist_ok=True)
    with CANDIDATE.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=FIELDS, lineterminator='\n'); w.writeheader(); w.writerow(source_row)
    DOC.mkdir(parents=True, exist_ok=True)
    with POP_AUDIT.open('w', newline='', encoding='utf-8') as f:
        fields=['population_ordinal','performance_intelligence_base_id','race_key','race_date','track_name','official_distance_metres','source_horse_name','raw_performance_lengths','performance_status','source_evidence_sha256']
        w=csv.DictWriter(f, fieldnames=fields, lineterminator='\n'); w.writeheader()
        for idx,(key,row,val) in enumerate(eligible,1):
            w.writerow({
                'population_ordinal': idx,
                'performance_intelligence_base_id': text(row.get('performance_intelligence_base_id')),
                'race_key': text(row.get('race_key')),
                'race_date': text(row.get('race_date')),
                'track_name': text(row.get('track_name')),
                'official_distance_metres': text(row.get('official_distance_metres')),
                'source_horse_name': text(row.get('winner_horse_name')),
                'raw_performance_lengths': q12(val),
                'performance_status': text(row.get('performance_status')),
                'source_evidence_sha256': text(row.get('performance_intelligence_base_evidence_sha256')),
            })
    manifest={
        'status':'NORMALISATION_PARAMETER_CANDIDATE_BUILT',
        'semantic_method':SEMANTIC_METHOD,
        'executable_method':METHOD,
        'model_version':MODEL_VERSION,
        'population_count':n,
        'minimum_population':MIN_POP,
        'centre_value':q12(centre),
        'scale_value':q12(scale),
        'population_sha256':pop_hash,
        'source_evidence_sha256':evidence_sha,
        'effective_from_date':min_date,
        'effective_to_date':'',
        'outlier_method':'NONE_IN_HPR_NORM_A_V1',
        'missing_parameter_rule':'FAIL_CLOSED_NO_FALLBACK_UNLESS_APPROVED',
        'population_method':'GLOBAL_ALL_GOVERNED_HISTORICAL_PERFORMANCE_POPULATION',
        'provenance_status':'OWNER_APPROVED_BOOTSTRAP_POPULATION',
        'built_at_utc':datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'),
        'candidate_path':CANDIDATE.as_posix(),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f"status={manifest['status']}")
    print(f"population_count={n}")
    print(f"centre_value={q12(centre)}")
    print(f"scale_value={q12(scale)}")
    print(f"population_sha256={pop_hash}")
    print(f"candidate={CANDIDATE}")
if __name__ == '__main__': main()
