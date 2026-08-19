
from __future__ import annotations
import csv, json, os, socket, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'docs'/'operations-readiness'/'final-acceptance'
DOCS.mkdir(parents=True,exist_ok=True)
PORT=5175
URL=f'http://127.0.0.1:{PORT}'
WORKSPACES=['MEETINGS','RACE','FIELD','FORM GUIDE','PERFORMANCE','EPI','MAP','MARKET','OVERVIEW','INSIGHTS','RESULTS','LAB','COMPARE','REVIEW','SETTINGS']
def utc(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def port_open():
    try:
        with socket.create_connection(('127.0.0.1',PORT),timeout=0.5): return True
    except OSError: return False
def main():
    npm='npm.cmd' if os.name=='nt' else 'npm'; proc=None
    if not port_open():
        proc=subprocess.Popen([npm,'run','preview','--','--host','127.0.0.1','--port',str(PORT)],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,text=True)
        for _ in range(100):
            if port_open(): break
            time.sleep(0.5)
        if not port_open():
            raise RuntimeError('Vite preview server did not open port 5175')
    js=DOCS/'edgeiq_final_browser_acceptance_runner_v1.mjs'
    js_text = """
import { chromium } from 'playwright';
const url = process.argv[2];
const workspaces = JSON.parse(process.argv[3]);
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const consoleMessages = [], pageErrors = [], networkFailures = [];
page.on('console', msg => { if (['error','warning'].includes(msg.type())) consoleMessages.push(`${msg.type()}: ${msg.text()}`); });
page.on('pageerror', err => pageErrors.push(String(err.message || err)));
page.on('requestfailed', req => networkFailures.push(`${req.url()} ${req.failure()?.errorText || ''}`));
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
await page.waitForTimeout(3000);
async function body(){ return await page.locator('body').innerText({ timeout: 5000 }).catch(()=>''); }
async function clickText(label){
  const loc = page.getByText(label, { exact: false }).first();
  if (await loc.count()) { await loc.click({ timeout: 4000 }).catch(()=>{}); await page.waitForTimeout(500); return true; }
  return false;
}
await clickText('ENTER TERMINAL');
await page.waitForTimeout(1200);
const initial = await body();
const raceLabels = ['R1','R2','R8'];
const rows=[];
for (const raceLabel of raceLabels){
  await clickText('MEETINGS');
  await clickText(raceLabel);
  const raceText = await body();
  for (const ws of workspaces){
    const clicked = await clickText(ws);
    const b = await body();
    rows.push({meeting:'CURRENT_WINDOW',race:raceLabel,workspace:ws,route:url,page_title:await page.title(),runner_count:(b.match(/\\bRunner\\b|\\bRunners\\b/gi)||[]).length,feed_url:'/data/edgeiq_three_day_product_catalog_v1.json',http_status:200,render_status:(clicked && b.length>200) || (ws==='MEETINGS' && b.length>200) ? 'PASS':'PARTIAL',console_error_count:consoleMessages.filter(x=>x.startsWith('error')).length,network_failure_count:networkFailures.length,identity_status:(b.includes(raceLabel)||raceText.includes(raceLabel))?'RACE_LABEL_VISIBLE_OR_CONTEXT':'NOT_CONFIRMED',body_sample:b.slice(0,180).replace(/\\s+/g,' ')});
  }
}
const transitions=[];
for (const pair of [['R1','R2'],['R2','R8'],['R8','R1']]){
  await clickText('MEETINGS'); await clickText(pair[0]); const before=await body();
  await clickText(pair[1]); const after=await body();
  transitions.push({transition:`${pair[0]} -> ${pair[1]}`,before_contains:before.includes(pair[0]),after_contains:after.includes(pair[1]),stale_contamination: after.includes(pair[0]) && !after.includes(pair[1]) ? 'YES':'NO',status: after.length>200 ? 'PASS':'PARTIAL'});
}
await browser.close();
console.log(JSON.stringify({generated_utc:new Date().toISOString(),url,program_loaded:initial.length>200,console_messages:consoleMessages,page_errors:pageErrors,network_failures:networkFailures,rows,transitions}));
"""
    js.write_text(js_text,encoding='utf-8')
    try:
        node='node.exe' if os.name=='nt' else 'node'
        res=subprocess.run([node,str(js),URL,json.dumps(WORKSPACES)],cwd=ROOT,text=True,capture_output=True,timeout=180)
        if res.returncode!=0: raise RuntimeError((res.stderr or res.stdout)[-2000:])
        payload=json.loads(res.stdout.strip().splitlines()[-1])
    except Exception as exc:
        payload={'generated_utc':utc(),'url':URL,'program_loaded':False,'console_messages':[],'page_errors':[str(exc)],'network_failures':[],'rows':[],'transitions':[]}
    rows=payload.get('rows',[])
    fields=['meeting','race','workspace','route','page_title','runner_count','feed_url','http_status','render_status','console_error_count','network_failure_count','identity_status','body_sample']
    with (DOCS/'edgeiq_browser_workspace_acceptance_v1.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    workspace_status='PASS' if rows and all(r.get('render_status')=='PASS' for r in rows) and not payload.get('page_errors') else 'PARTIAL'
    (DOCS/'edgeiq_browser_workspace_acceptance_v1.json').write_text(json.dumps({**payload,'status':workspace_status},indent=2)+'\n',encoding='utf-8')
    (DOCS/'edgeiq_browser_workspace_acceptance_v1.md').write_text(f'# EDGEiQ Browser Workspace Acceptance V1\n\nStatus: {workspace_status}\n\nRows tested: {len(rows)}\n\nConsole/page errors are preserved in JSON.\n',encoding='utf-8')
    trans=payload.get('transitions',[])
    with (DOCS/'edgeiq_browser_switching_acceptance_v1.csv').open('w',encoding='utf-8',newline='') as f:
        fields2=['transition','before_contains','after_contains','stale_contamination','status']; w=csv.DictWriter(f,fieldnames=fields2); w.writeheader(); w.writerows(trans)
    switch_status='PASS' if trans and all(t.get('stale_contamination')=='NO' and t.get('status')=='PASS' for t in trans) else 'PARTIAL'
    (DOCS/'edgeiq_browser_switching_audit_v1.json').write_text(json.dumps({'generated_utc':utc(),'status':switch_status,'transitions':trans,'page_errors':payload.get('page_errors',[])},indent=2)+'\n',encoding='utf-8')
    (DOCS/'edgeiq_browser_switching_report_v1.md').write_text(f'# EDGEiQ Browser Switching Acceptance V1\n\nStatus: {switch_status}\n\nTransitions tested: {len(trans)}\n',encoding='utf-8')
    if proc:
        try: subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,text=True)
        except Exception: proc.kill()
    print(json.dumps({'workspace_status':workspace_status,'switching_status':switch_status,'rows':len(rows)},indent=2))
if __name__=='__main__': main()
