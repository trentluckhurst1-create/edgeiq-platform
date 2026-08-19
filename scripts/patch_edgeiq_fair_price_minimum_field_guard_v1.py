from pathlib import Path
p=Path('scripts/build_edgeiq_performance_recovery_current_lineage_v1.py')
s=p.read_text(encoding='utf-8')
old="        if not av: continue\n        scores=[m['model_score_v7_2'] for m in av]; mean=sum(scores)/len(scores); sd=(sum((x-mean)**2 for x in scores)/len(scores))**0.5 or 1.0; ws=[math.exp(((m['model_score_v7_2']-mean)/sd)/TEMP) for m in av]; total=sum(ws)"
new="        if len(av)<2:\n            for m in av:\n                m['availability_status']='FAIR_PRICE_UNAVAILABLE'\n                m['unavailable_reason']='INSUFFICIENT_GOVERNED_MODEL_FIELD'\n            continue\n        scores=[m['model_score_v7_2'] for m in av]; mean=sum(scores)/len(scores); sd=(sum((x-mean)**2 for x in scores)/len(scores))**0.5 or 1.0; ws=[math.exp(((m['model_score_v7_2']-mean)/sd)/TEMP) for m in av]; total=sum(ws)"
if old not in s:
    raise SystemExit('fair price len guard target not found')
p.write_text(s.replace(old,new),encoding='utf-8')
print('PATCHED fair price minimum model field guard')
