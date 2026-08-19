from pathlib import Path
ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
modified=[]

def read(rel): return (ROOT/rel).read_text(encoding='utf-8-sig')
def write(rel,text):
    path=ROOT/rel
    old=path.read_text(encoding='utf-8-sig') if path.exists() else None
    if old!=text:
        path.write_text(text,encoding='utf-8',newline='\n')
        modified.append(rel)

rf=read('src/edgeiq-os/race/RaceFileV3.tsx')
if '  results: "RESULTS",' not in rf:
    marker='  review: "REVIEW",\n\n};'
    if marker not in rf:
        raise SystemExit('raceTabBySection review marker not found')
    rf=rf.replace(marker,'  review: "REVIEW",\n\n  results: "RESULTS",\n\n};',1)
write('src/edgeiq-os/race/RaceFileV3.tsx',rf)

lab=read('src/edgeiq-os/race/components/LabWorkspace.tsx')
lab=lab.replace('<section className="eiq-lab-workspace eiq-lab-final">', '<section className="eiq-lab-workspace eiq-lab-final" data-edgeiq-workspace-key="LAB" data-edgeiq-mounted-component="LabWorkspace">')
lab=lab.replace('<section className="eiq-lab-workspace eiq-lab-final" aria-label="LAB workspace">', '<section className="eiq-lab-workspace eiq-lab-final" data-edgeiq-workspace-key="LAB" data-edgeiq-mounted-component="LabWorkspace" aria-label="LAB workspace">')
write('src/edgeiq-os/race/components/LabWorkspace.tsx',lab)

gr=read('src/edgeiq-os/race/components/GlobalResultsWorkspace.tsx')
gr=gr.replace('<section className="eiq-global-results-workspace">\n      <MeetingResultsWorkspace meeting={meeting} />', '<section className="eiq-global-results-workspace" data-edgeiq-workspace-key="RESULTS" data-edgeiq-mounted-component="GlobalResultsWorkspace">\n      <MeetingResultsWorkspace meeting={meeting} />')
write('src/edgeiq-os/race/components/GlobalResultsWorkspace.tsx',gr)

cap=read('scripts/capture_edgeiq_final_live_runtime_completion_v1.py')
old="""  }} else if (mode === 'race-nav') {{\n    const ok = await ensureRaceWorkspace(page);\n    if (!ok) captureErrors.push({{ type: 'navigation', workspace, message: 'Race workspace could not be opened' }});\n    await clickPrimaryNav(page, label);\n  }}\n  await page.waitForLoadState('networkidle').catch(() => {{}});\n  await capture(page, workspace, label, captureErrors);\n"""
new="""  }} else if (mode === 'race-nav') {{\n    await ensureRaceWorkspace(page);\n    await clickPrimaryNav(page, label);\n    await sleep(900);\n    if ((await page.locator('.eiq-race-workspace').count()) === 0) {{\n      captureErrors.push({{ type: 'navigation', workspace, message: 'Race workspace could not be opened after primary navigation' }});\n    }}\n  }}\n  await page.waitForLoadState('networkidle').catch(() => {{}});\n  await capture(page, workspace, label, captureErrors);\n"""
if old not in cap:
    raise SystemExit('capture race-nav block not found')
cap=cap.replace(old,new,1)
write('scripts/capture_edgeiq_final_live_runtime_completion_v1.py',cap)

print('EDGEIQ_FINAL_RUNTIME_PHASE02_RESULTS_LAB_CAPTURE_REPAIR_PASS')
print('modified_files='+';'.join(modified))
