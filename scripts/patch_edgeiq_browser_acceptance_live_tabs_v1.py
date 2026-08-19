from pathlib import Path
p=Path('scripts/run_edgeiq_final_browser_acceptance_v1.py')
s=p.read_text(encoding='utf-8')
old="WORKSPACES=['MEETINGS','RACE','FIELD','PERFORMANCE','FORM GUIDE','MAP','NEXUS','MARKET','RESULTS','TRACK','WEATHER','OVERVIEW','INSIGHTS']"
new="WORKSPACES=['MEETINGS','RACE','FIELD','FORM GUIDE','PERFORMANCE','EPI','MAP','MARKET','OVERVIEW','INSIGHTS','RESULTS','LAB','COMPARE','REVIEW','SETTINGS']"
if old not in s and new not in s:
    raise SystemExit('workspace list target not found')
if old in s: s=s.replace(old,new)
p.write_text(s,encoding='utf-8')
print('PATCHED browser acceptance workspace list to live product tabs')
