import csv, shutil
from pathlib import Path
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public'/'data'; TSX=ROOT/'src'/'components'/'RaceIntelligenceScreen.tsx'; CP=ROOT/'src'/'components'/'checkpoints'
OUT=DATA/'edgeiq_command_v3_ui_update_v1.csv'; SUMMARY=DATA/'edgeiq_command_v3_ui_update_v1_summary.csv'; REPORT=DATA/'edgeiq_command_v3_ui_update_v1_report.txt'

def write_csv(p,rows,fields):
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
status='COMMAND_V3_UI_BLOCKED_SAFE_NO_CHANGE'; err=''; changes=[]; backup=''
try:
    CP.mkdir(parents=True,exist_ok=True)
    backup=str(CP/f'RaceIntelligenceScreen_BEFORE_COMMAND_V3_CONSISTENCY_{datetime.now().strftime("%Y%m%d_%H%M%S")}.tsx')
    shutil.copy2(TSX,backup)
    text=TSX.read_text(encoding='utf-8')
    original=text
    repls=[
        ('commandEvidenceAvailable(row.item, ["edgeiq_connection_evidence_available_v2", "edgeiq_connection_evidence_available"], ["edgeiq_connection_angle_summary_v2", "edgeiq_connection_angle_summary"])','commandEvidenceAvailable(row.item, ["edgeiq_connection_evidence_available_v3", "edgeiq_connection_evidence_available_v2", "edgeiq_connection_evidence_available"], ["edgeiq_connection_angle_summary_v3", "edgeiq_connection_angle_summary_v2", "edgeiq_connection_angle_summary"])','coverage_connection_v3'),
        ('commandEvidenceAvailable(row.item, ["edgeiq_market_evidence_available_v2", "edgeiq_market_evidence_available"], ["edgeiq_market_signal_summary_v2", "edgeiq_market_signal_summary"])','commandEvidenceAvailable(row.item, ["edgeiq_market_evidence_available_v3", "edgeiq_market_evidence_available_v2", "edgeiq_market_evidence_available"], ["edgeiq_market_signal_summary_v3", "edgeiq_market_signal_summary_v2", "edgeiq_market_signal_summary"])','coverage_market_v3'),
        ('commandEvidenceAvailable(row.item, ["edgeiq_hidden_gem_evidence_available_v2", "edgeiq_hidden_gem_evidence_available"], ["edgeiq_hidden_gem_summary_v2", "edgeiq_hidden_gem_summary"])','commandEvidenceAvailable(row.item, ["edgeiq_hidden_gem_evidence_available_v3", "edgeiq_hidden_gem_evidence_available_v2", "edgeiq_hidden_gem_evidence_available"], ["edgeiq_hidden_gem_summary_v3", "edgeiq_hidden_gem_summary_v2", "edgeiq_hidden_gem_summary"])','coverage_hidden_v3'),
        ('firstNum(source, ["race_field_size_v2"])','firstNum(source, ["race_field_size_v3", "race_field_size_v2"])','race_field_v3'),
        ('firstNum(commandRaceSummary, ["race_field_size_v2"])','firstNum(commandRaceSummary, ["race_field_size_v3", "race_field_size_v2"])','field_count_v3'),
        ('firstNum(commandRaceSummary, ["race_connection_count_v2"])','firstNum(commandRaceSummary, ["race_connection_available_count_v3", "race_connection_count_v2"])','connection_count_v3'),
        ('firstNum(commandRaceSummary, ["race_market_count_v2"])','firstNum(commandRaceSummary, ["race_market_available_count_v3", "race_market_count_v2"])','market_count_v3'),
        ('firstNum(commandRaceSummary, ["race_hidden_gem_count_v2"])','firstNum(commandRaceSummary, ["race_hidden_gem_available_count_v3", "race_hidden_gem_count_v2"])','hidden_count_v3'),
        ('{ label: "Connections", count: connectionsCoverageCount, explanation: "Trainer, jockey and combination evidence for the current race universe." }','{ label: "Connections", count: displayConnectionsCoverageCount, explanation: "Trainer, jockey and combination evidence for the current race universe." }','tile_connection_count'),
        ('{ label: "Market", count: marketCoverageCount, explanation: "Current market signal evidence surfaced from the governed runner board." }','{ label: "Market", count: displayMarketCoverageCount, explanation: "Current market signal evidence surfaced from the governed runner board." }','tile_market_count'),
        ('{ label: "Hidden Gem", count: hiddenGemCoverageCount, explanation: "Performance intelligence flags surfaced from current evidence." }','{ label: "Hidden Gem", count: displayHiddenGemCoverageCount, explanation: "Performance intelligence flags surfaced from current evidence." }','tile_hidden_count'),
        ('firstNum(source, ["edgeiq_active_display_fair_price", "edgeiq_v7_2g2_guarded_display_fair_price", "edgeiq_v7_2g2_active_display_fair_price_shadow", "edgeiq_v7_2g2_on_preview_display_fair_price"])','firstNum(source, ["edgeiq_active_display_fair_price", "edgeiq_v7_2g2_guarded_display_fair_price", "edgeiq_v7_2g2_active_display_fair_price_shadow", "edgeiq_v7_2g2_on_preview_display_fair_price"])','active_fair_keep'),
        ('commandEvidenceAvailable(item, ["edgeiq_market_evidence_available_v2", "edgeiq_market_evidence_available"], ["edgeiq_market_signal_summary_v2", "edgeiq_market_signal_summary"])','commandEvidenceAvailable(item, ["edgeiq_market_evidence_available_v3", "edgeiq_market_evidence_available_v2", "edgeiq_market_evidence_available"], ["edgeiq_market_signal_summary_v3", "edgeiq_market_signal_summary_v2", "edgeiq_market_signal_summary"])','market_rows_v3'),
        ('firstText(source, ["edgeiq_market_signal_summary_v2", "edgeiq_market_signal_summary"], "")','firstText(source, ["edgeiq_market_signal_summary_v3", "edgeiq_market_signal_summary_v2", "edgeiq_market_signal_summary"], "")','market_summary_v3'),
        ('firstText(source, ["command_market_role_v2", "command_market_role"], "")','firstText(source, ["command_market_role_v3", "command_market_role_v2", "command_market_role"], "")','market_role_v3'),
        ('commandEvidenceAvailable(item, ["edgeiq_connection_evidence_available_v2", "edgeiq_connection_evidence_available"], ["edgeiq_connection_angle_summary_v2", "edgeiq_connection_angle_summary"])','commandEvidenceAvailable(item, ["edgeiq_connection_evidence_available_v3", "edgeiq_connection_evidence_available_v2", "edgeiq_connection_evidence_available"], ["edgeiq_connection_angle_summary_v3", "edgeiq_connection_angle_summary_v2", "edgeiq_connection_angle_summary"])','connection_rows_v3'),
        ('firstText(source, ["edgeiq_connection_angle_summary_v2", "edgeiq_connection_angle_summary"], "")','firstText(source, ["edgeiq_connection_angle_summary_v3", "edgeiq_connection_angle_summary_v2", "edgeiq_connection_angle_summary"], "")','connection_summary_v3'),
        ('firstNum(source, ["edgeiq_score_connections_v2"])','firstNum(source, ["edgeiq_score_connections_v3", "edgeiq_score_connections_v2"])','connection_score_v3'),
        ('firstText(scoreBreakdownSource, ["edgeiq_score_source_v2"], "")','firstText(scoreBreakdownSource, ["edgeiq_score_source_v3", "edgeiq_score_source_v2"], "")','score_source_v3'),
    ]
    for old,new,label in repls:
        if old in text and old!=new:
            text=text.replace(old,new)
            changes.append(label)
    # Insert additional race aggregate counts.
    marker='''  const commandRaceHiddenGemCount = firstNum(commandRaceSummary, ["race_hidden_gem_available_count_v3", "race_hidden_gem_count_v2"]);\n'''
    insert=marker+'''  const commandRaceConnectionSourceMatchedCount = firstNum(commandRaceSummary, ["race_connection_source_matched_count_v3"]);\n  const commandRaceEdgeiqPriceCount = firstNum(commandRaceSummary, ["race_edgeiq_price_count_v3"]);\n'''
    if marker in text and 'commandRaceConnectionSourceMatchedCount' not in text:
        text=text.replace(marker,insert,1); changes.append('source_checked_and_price_counts')
    marker2='''  const displayHiddenGemCoverageCount = commandRaceHiddenGemCount ?? hiddenGemCoverageCount;\n  const displayEvidenceFieldSize = commandRaceFieldSize ?? factorFieldSize;\n'''
    insert2='''  const displayHiddenGemCoverageCount = commandRaceHiddenGemCount ?? hiddenGemCoverageCount;\n  const displayConnectionSourceMatchedCount = commandRaceConnectionSourceMatchedCount ?? displayConnectionsCoverageCount;\n  const displayEdgeiqPriceCount = commandRaceEdgeiqPriceCount ?? coverageCount((row) => fairPrice(row.item.row, row.item.bet) !== null);\n  const displayEvidenceFieldSize = commandRaceFieldSize ?? factorFieldSize;\n'''
    if marker2 in text and 'displayConnectionSourceMatchedCount' not in text:
        text=text.replace(marker2,insert2,1); changes.append('display_checked_and_price_counts')
    # Score rows prefer v3.
    score_repls=[
        ('["edgeiq_score_overall_v2"]','["edgeiq_score_overall_v3", "edgeiq_score_overall_v2"]'),
        ('["edgeiq_score_distance_v2"]','["edgeiq_score_distance_v3", "edgeiq_score_distance_v2"]'),
        ('["edgeiq_score_condition_v2"]','["edgeiq_score_condition_v3", "edgeiq_score_condition_v2"]'),
        ('["edgeiq_score_class_v2"]','["edgeiq_score_class_v3", "edgeiq_score_class_v2"]'),
        ('["edgeiq_score_campaign_v2"]','["edgeiq_score_campaign_v3", "edgeiq_score_campaign_v2"]'),
        ('["edgeiq_score_pace_v2"]','["edgeiq_score_pace_v3", "edgeiq_score_pace_v2"]'),
        ('["edgeiq_score_connections_v2"]','["edgeiq_score_connections_v3", "edgeiq_score_connections_v2"]'),
        ('["edgeiq_score_market_v2"]','["edgeiq_score_market_v3", "edgeiq_score_market_v2"]'),
        ('["edgeiq_score_confidence_v2"]','["edgeiq_score_confidence_v3", "edgeiq_score_confidence_v2"]'),
    ]
    for old,new in score_repls:
        if old in text:
            text=text.replace(old,new); changes.append('score_breakdown_v3')
    # Insert race-level market command fields after market rows.
    marker3='''          const marketWatchCommand = marketCommandRows.find((entry) => entry.hasMarketEvidence) ?? marketCommandRows[0] ?? null;\n'''
    insert3='''          const commandBestValueHorse = firstText(commandRaceSummary, ["command_best_value_horse_v3"], "");\n          const commandBestValueSummary = firstText(commandRaceSummary, ["command_best_value_summary_v3"], "");\n          const commandOverbetHorse = firstText(commandRaceSummary, ["command_overbet_horse_v3"], "");\n          const commandOverbetSummary = firstText(commandRaceSummary, ["command_overbet_summary_v3"], "");\n          const commandMarketWatchHorse = firstText(commandRaceSummary, ["command_market_watch_horse_v3"], "");\n          const commandMarketWatchSummary = firstText(commandRaceSummary, ["command_market_watch_summary_v3"], "");\n          const marketHorseMatches = (entry: (typeof marketCommandRows)[number], target: string) => cleanHorse(horse(entry.item.row)) === cleanHorse(target);\n          const bestValueCommandV3 = commandBestValueHorse ? marketCommandRows.find((entry) => marketHorseMatches(entry, commandBestValueHorse)) ?? null : null;\n          const overbetCommandV3 = commandOverbetHorse ? marketCommandRows.find((entry) => marketHorseMatches(entry, commandOverbetHorse)) ?? null : null;\n          const marketWatchCommandV3 = commandMarketWatchHorse ? marketCommandRows.find((entry) => marketHorseMatches(entry, commandMarketWatchHorse)) ?? null : null;\n          const marketWatchCommand = marketWatchCommandV3 ?? marketCommandRows.find((entry) => entry.hasMarketEvidence) ?? marketCommandRows[0] ?? null;\n'''
    if marker3 in text and 'commandBestValueHorse' not in text:
        text=text.replace(marker3,insert3,1); changes.append('market_race_v3_fields')
    text=text.replace('const bestValueCommand = [...marketCommandRows]\n            .filter((entry) => entry.edge !== null)\n            .sort((a, b) => (b.edge ?? -999) - (a.edge ?? -999))[0] ?? null;','const bestValueCommand = bestValueCommandV3 ?? ([...marketCommandRows]\n            .filter((entry) => entry.edge !== null && entry.edge > 0)\n            .sort((a, b) => (b.edge ?? -999) - (a.edge ?? -999))[0] ?? null);')
    text=text.replace('const overbetCommand = [...marketCommandRows]\n            .filter((entry) => entry.edge !== null)\n            .sort((a, b) => (a.edge ?? 999) - (b.edge ?? 999))[0] ?? null;','const overbetCommand = overbetCommandV3 ?? ([...marketCommandRows]\n            .filter((entry) => entry.edge !== null && entry.edge < 0)\n            .sort((a, b) => (a.edge ?? 999) - (b.edge ?? 999))[0] ?? null);')
    # If the previous constants now appear before V3 declarations, fix ordering by moving V3 block above best/over.
    if 'const bestValueCommand = bestValueCommandV3' in text and text.find('const bestValueCommand = bestValueCommandV3') < text.find('const commandBestValueHorse'):
        block_start=text.find('          const commandBestValueHorse')
        block_end=text.find('          const connectionCommandRows', block_start)
        block=text[block_start:block_end]
        text=text[:block_start]+text[block_end:]
        insert_at=text.find('          const bestValueCommand = bestValueCommandV3')
        text=text[:insert_at]+block+text[insert_at:]
        changes.append('market_order_fix')
    # Market card summary override.
    text=text.replace('{ label: "Best Value", entry: bestValueCommand, fallback: "No value edge currently identified." }','{ label: "Best Value", entry: bestValueCommand, fallback: "No value edge currently identified.", summary: commandBestValueSummary }')
    text=text.replace('{ label: "Most Overbet / Risk", entry: overbetCommand, fallback: "No overbet risk identified." }','{ label: "Most Overbet / Risk", entry: overbetCommand, fallback: "No overbet risk identified.", summary: commandOverbetSummary }')
    text=text.replace('{ label: "Market Watch", entry: marketWatchCommand, fallback: "No market signal loaded." }','{ label: "Market Watch", entry: marketWatchCommand, fallback: "No market signal loaded.", summary: commandMarketWatchSummary }')
    text=text.replace('{card.entry.summary || "Market evidence loaded."}','{card.summary || card.entry.summary || "Market evidence loaded."}')
    # Connection fallback true zero/source missing.
    text=text.replace('{displayConnectionsCoverageCount}/{displayEvidenceFieldSize} runners with connection evidence','{displayConnectionsCoverageCount}/{displayEvidenceFieldSize} runners with qualifying connection angle{displayConnectionsCoverageCount === 0 ? ` | ${displayConnectionSourceMatchedCount}/${displayEvidenceFieldSize} checked` : ""}')
    text=text.replace('No trainer, jockey or combination angle is currently triggered.','{displayConnectionSourceMatchedCount > 0 ? "Connection evidence checked: no qualifying trainer, jockey or combination angle for this race." : "Connection source not loaded for this race."}')
    # Footer price count.
    text=text.replace('{ label: "EDGEiQ Price", count: coverageCount((row) => fairPrice(row.item.row, row.item.bet) !== null) }','{ label: "EDGEiQ Price", count: displayEdgeiqPriceCount }')
    if text!=original:
        TSX.write_text(text,encoding='utf-8')
        status='COMMAND_V3_UI_UPDATED'
    else:
        status='COMMAND_V3_UI_BLOCKED_SAFE_NO_CHANGE'; err='No replacements applied.'
except Exception as e:
    err=str(e)
row={'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'checkpoint_file':backup,'changes':'|'.join(dict.fromkeys(changes)),'error':err}
write_csv(OUT,[row],list(row.keys())); write_csv(SUMMARY,[row],list(row.keys()))
REPORT.write_text('\n'.join(['EDGEiQ Command V3 UI Update V1','='*36,f'Status: {status}',f'Checkpoint: {backup}',f'Changes: {row["changes"]}',f'Error: {err or "None"}'])+'\n',encoding='utf-8')
print(status)
