from pathlib import Path
p=Path(__file__).parent/'run_d107_d99_family_ablation.py'
s=p.read_text(encoding='utf-8')
s=s.replace('for yr in [2022,2023,2024]:\n score(yr,"D99",F99)\n for k,v in families.items():\n  if v:score(yr,"DROP_"+k,[c for c in F99 if c not in set(v)])','print("D108_CONTRACT CONFIRM_D99_MINUS_RECENCY_ONLY SAME_L5_T1 NO_SEARCH PASS_BOTH_SELECTION_YEARS_TOP1_FLOOR_MINUS_0.005")\nfor yr in [2022,2023,2024]:\n score(yr,"D99",F99)\n score(yr,"D108_MINUS_RECENCY",[c for c in F99 if c not in set(families["RECENCY"])])')
s=s.replace('D107_COMPLETE 2025_2026_SEALED','D108_COMPLETE 2025_2026_SEALED')
exec(compile(s,'D108','exec'))
