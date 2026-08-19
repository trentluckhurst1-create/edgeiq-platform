import csv, shutil
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public/data'; TSX=ROOT/'src/components/RaceIntelligenceScreen.tsx'; CP=ROOT/'src/components/checkpoints'
out=DATA/'edgeiq_zero_score_display_fix_v1.csv'; sumout=DATA/'edgeiq_zero_score_display_fix_v1_summary.csv'; report=DATA/'edgeiq_zero_score_display_fix_v1_report.txt'
status='ZERO_SCORE_DISPLAY_FIX_APPLIED'; err=''; changes=[]; backup=''
def write(path,row):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(row.keys())); w.writeheader(); w.writerow(row)
try:
    CP.mkdir(parents=True,exist_ok=True); backup=CP/f'RaceIntelligenceScreen_BEFORE_ZERO_SCORE_DISPLAY_FIX_{datetime.now().strftime("%Y%m%d_%H%M%S")}.tsx'; shutil.copy2(TSX,backup)
    text=TSX.read_text(encoding='utf-8'); original=text
    old='''                { label: "Overall", value: firstNum(scoreBreakdownSource, ["edgeiq_score_overall_v2"]), tone: scoreToneValue(firstNum(scoreBreakdownSource, ["edgeiq_score_overall_v2"])) },\n                { label: "Distance", value: firstNum(scoreBreakdownSource, ["edgeiq_score_distance_v2"]), tone: scoreToneValue(firstNum(scoreBreakdownSource, ["edgeiq_score_distance_v2"])) },\n                { label: "Condition", value: firstNum(scoreBreakdownSource, ["edgeiq_score_condition_v2"]), tone: scoreToneValue(firstNum(scoreBreakdownSource, ["edgeiq_score_condition_v2"])) },\n                { label: "Class", value: firstNum(scoreBreakdownSource, ["edgeiq_score_class_v2"]), tone: scoreToneValue(firstNum(scoreBreakdownSource, ["edgeiq_score_class_v2"])) },\n                { label: "Campaign", value: firstNum(scoreBreakdownSource, ["edgeiq_score_campaign_v2"]), tone: scoreToneValue(firstNum(scoreBreakdownSource, ["edgeiq_score_campaign_v2"])) },\n                { label: "Pace", value: firstNum(scoreBreakdownSource, ["edgeiq_score_pace_v2"]), tone: scoreToneValue(firstNum(scoreBreakdownSource, ["edgeiq_score_pace_v2"])) },\n                { label: "Connections", value: firstNum(scoreBreakdownSource, ["edgeiq_score_connections_v2"]), tone: scoreToneValue(firstNum(scoreBreakdownSource, ["edgeiq_score_connections_v2"])) },\n                { label: "Market", value: firstNum(scoreBreakdownSource, ["edgeiq_score_market_v2"]), tone: scoreToneValue(firstNum(scoreBreakdownSource, ["edgeiq_score_market_v2"])) },\n                { label: "Confidence", value: firstNum(scoreBreakdownSource, ["edgeiq_score_confidence_v2"]), tone: scoreToneValue(firstNum(scoreBreakdownSource, ["edgeiq_score_confidence_v2"])) },'''
    new='''                { label: "Overall", sourceKey: "OVERALL", value: firstNum(scoreBreakdownSource, ["edgeiq_score_overall_v2"]), tone: scoreToneValue(firstNum(scoreBreakdownSource, ["edgeiq_score_overall_v2"])) },\n                { label: "Distance", sourceKey: "DISTANCE", value: firstNum(scoreBreakdownSource, ["edgeiq_score_distance_v2"]), tone: scoreToneValue(firstNum(scoreBreakdownSource, ["edgeiq_score_distance_v2"])) },\n                { label: "Condition", sourceKey: "CONDITION", value: firstNum(scoreBreakdownSource, ["edgeiq_score_condition_v2"]), tone: scoreToneValue(firstNum(scoreBreakdownSource, ["edgeiq_score_condition_v2"])) },\n                { label: "Class", sourceKey: "CLASS", value: firstNum(scoreBreakdownSource, ["edgeiq_score_class_v2"]), tone: scoreToneValue(firstNum(scoreBreakdownSource, ["edgeiq_score_class_v2"])) },\n                { label: "Campaign", sourceKey: "CAMPAIGN", value: firstNum(scoreBreakdownSource, ["edgeiq_score_campaign_v2"]), tone: scoreToneValue(firstNum(scoreBreakdownSource, ["edgeiq_score_campaign_v2"])) },\n                { label: "Pace", sourceKey: "PACE", value: firstNum(scoreBreakdownSource, ["edgeiq_score_pace_v2"]), tone: scoreToneValue(firstNum(scoreBreakdownSource, ["edgeiq_score_pace_v2"])) },\n                { label: "Connections", sourceKey: "CONNECTIONS", value: firstNum(scoreBreakdownSource, ["edgeiq_score_connections_v2"]), tone: scoreToneValue(firstNum(scoreBreakdownSource, ["edgeiq_score_connections_v2"])) },\n                { label: "Market", sourceKey: "MARKET", value: firstNum(scoreBreakdownSource, ["edgeiq_score_market_v2"]), tone: scoreToneValue(firstNum(scoreBreakdownSource, ["edgeiq_score_market_v2"])) },\n                { label: "Confidence", sourceKey: "CONFIDENCE", value: firstNum(scoreBreakdownSource, ["edgeiq_score_confidence_v2"]), tone: scoreToneValue(firstNum(scoreBreakdownSource, ["edgeiq_score_confidence_v2"])) },'''
    if old in text:
        text=text.replace(old,new,1); changes.append('score_rows_source_keys')
    else:
        raise RuntimeError('score rows block not found')
    old2='''                  {scoreBreakdownRows.map((entry) => {\n                    const value = entry.value !== null && Number.isFinite(entry.value) ? Math.max(0, Math.min(100, entry.value)) : null;\n                    return ('''
    new2='''                  {scoreBreakdownRows.map((entry) => {\n                    const scoreSource = firstText(scoreBreakdownSource, ["edgeiq_score_source_v2"], "").toUpperCase();\n                    const sourceMissing = scoreSource.includes(`${entry.sourceKey}:MISSING`);\n                    const value = !sourceMissing && entry.value !== null && Number.isFinite(entry.value) ? Math.max(0, Math.min(100, entry.value)) : null;\n                    return ('''
    if old2 in text:
        text=text.replace(old2,new2,1); changes.append('source_missing_suppresses_zero_bar')
    else:
        raise RuntimeError('score render value block not found')
    text=text.replace('>{value !== null ? renderMetricValue(value, 0) : "not loaded"}</strong>','>{value !== null ? renderMetricValue(value, 0) : "NOT LOADED"}</strong>')
    text=text.replace('width: `${value !== null ? value : 4}%`','width: `${value !== null ? value : 0}%`')
    changes.append('not_loaded_label_and_zero_width_missing_bar')
    TSX.write_text(text,encoding='utf-8')
except Exception as e:
    status='BLOCKED'; err=str(e)
row={'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'checkpoint_file':str(backup),'changes':'|'.join(changes),'error':err}
write(out,row); write(sumout,row)
report.write_text('\n'.join(['EDGEiQ Zero Score Display Fix V1','='*40,f'Status: {status}',f'Checkpoint: {backup}',f'Changes: {row["changes"]}',f'Error: {err or "None"}'])+'\n',encoding='utf-8')
print(status); print('changes',row['changes']); print('error',err)
