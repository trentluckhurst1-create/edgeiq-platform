import csv, shutil
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'; TSX=ROOT/'src/components/RaceIntelligenceScreen.tsx'; CP=ROOT/'src/components/checkpoints'
out=DATA/'edgeiq_footer_counts_fix_v1.csv'; sumout=DATA/'edgeiq_footer_counts_fix_v1_summary.csv'; report=DATA/'edgeiq_footer_counts_fix_v1_report.txt'
status='FOOTER_COUNTS_FIX_APPLIED'; err=''; changes=[]; backup=''
def write(path,row):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(row.keys())); w.writeheader(); w.writerow(row)
try:
    CP.mkdir(parents=True,exist_ok=True); backup=CP/f'RaceIntelligenceScreen_BEFORE_FINAL_FOOTER_COUNTS_FIX_{datetime.now().strftime("%Y%m%d_%H%M%S")}.tsx'; shutil.copy2(TSX,backup)
    text=TSX.read_text(encoding='utf-8')
    original=text
    def rep(old,new,label,required=True):
        nonlocal_text[0]=nonlocal_text[0]
    # simple replacements
    if 'runnerBoard: "/data/edgeiq_live_runner_board_v1.csv"' in text:
        text=text.replace('runnerBoard: "/data/edgeiq_live_runner_board_v1.csv"','runnerBoard: "/data/edgeiq_live_runner_board_governed_v1.csv"',1); changes.append('runner_board_source_governed')
    helper_after='''function findSidecar(rows: Row[], base: Row): Row | undefined {\n  return rows.find((row) => sameRunner(row, base));\n}\n\n'''
    helper_insert=helper_after+'''function findCommandEnrichmentSidecar(rows: Row[], base: Row): Row | undefined {\n  const baseDate = raceDate(base);\n  const baseTrack = cleanTrack(track(base));\n  const baseRaceNo = raceNo(base);\n  const baseHorseStrict = cleanHorse(firstText(base, ["horse_key", "horseKey"], "")) || cleanHorse(horse(base));\n  const baseHorseLoose = cleanHorseLoose(horse(base));\n\n  return rows.find((row) => {\n    const rowDate = raceDate(row);\n    const rowTrack = cleanTrack(track(row));\n    const rowRaceNo = raceNo(row);\n    const rowHorseStrict = cleanHorse(firstText(row, ["horse_key", "horseKey"], "")) || cleanHorse(horse(row));\n    const rowHorseLoose = cleanHorseLoose(horse(row));\n    if (baseDate && rowDate && baseDate !== rowDate) return false;\n    if (baseTrack && rowTrack && baseTrack !== rowTrack) return false;\n    if (baseRaceNo && rowRaceNo && baseRaceNo !== rowRaceNo) return false;\n    if (baseHorseStrict && rowHorseStrict && baseHorseStrict === rowHorseStrict) return true;\n    return !!baseHorseLoose && !!rowHorseLoose && baseHorseLoose === rowHorseLoose;\n  });\n}\n\n'''
    if 'function findCommandEnrichmentSidecar' not in text:
        if helper_after not in text: raise RuntimeError('findSidecar marker missing')
        text=text.replace(helper_after,helper_insert,1); changes.append('command_enrichment_sidecar_matcher')
    if 'const commandEnrichment = findSidecar(commandEnrichmentRows, row);' in text:
        text=text.replace('const commandEnrichment = findSidecar(commandEnrichmentRows, row);','const commandEnrichment = findCommandEnrichmentSidecar(commandEnrichmentRows, row);',1); changes.append('use_command_enrichment_matcher')
    insert_marker='''  const connectionsCoverageCount = coverageCount((row) => commandEvidenceAvailable(row.item, ["edgeiq_connection_evidence_available_v2", "edgeiq_connection_evidence_available"], ["edgeiq_connection_angle_summary_v2", "edgeiq_connection_angle_summary"]));\n  const marketCoverageCount = coverageCount((row) => commandEvidenceAvailable(row.item, ["edgeiq_market_evidence_available_v2", "edgeiq_market_evidence_available"], ["edgeiq_market_signal_summary_v2", "edgeiq_market_signal_summary"]));\n  const hiddenGemCoverageCount = coverageCount((row) => commandEvidenceAvailable(row.item, ["edgeiq_hidden_gem_evidence_available_v2", "edgeiq_hidden_gem_evidence_available"], ["edgeiq_hidden_gem_summary_v2", "edgeiq_hidden_gem_summary"]));\n'''
    replacement=insert_marker+'''  const commandRaceSummary = factorEligibleRows.map((row) => commandEvidenceSource(row.item)).find((source) => firstNum(source, ["race_field_size_v2"]) !== null);\n  const commandRaceFieldSize = firstNum(commandRaceSummary, ["race_field_size_v2"]);\n  const commandRaceConnectionCount = firstNum(commandRaceSummary, ["race_connection_count_v2"]);\n  const commandRaceMarketCount = firstNum(commandRaceSummary, ["race_market_count_v2"]);\n  const commandRaceHiddenGemCount = firstNum(commandRaceSummary, ["race_hidden_gem_count_v2"]);\n  const displayConnectionsCoverageCount = commandRaceConnectionCount ?? connectionsCoverageCount;\n  const displayMarketCoverageCount = commandRaceMarketCount ?? marketCoverageCount;\n  const displayHiddenGemCoverageCount = commandRaceHiddenGemCount ?? hiddenGemCoverageCount;\n  const displayEvidenceFieldSize = commandRaceFieldSize ?? factorFieldSize;\n'''
    if 'const commandRaceSummary = factorEligibleRows.map' not in text:
        if insert_marker not in text: raise RuntimeError('coverage count marker missing')
        text=text.replace(insert_marker,replacement,1); changes.append('race_aggregate_footer_counts')
    text=text.replace('{connectionCommandRows.length}/{fieldSize} runners with connection evidence','{displayConnectionsCoverageCount}/{displayEvidenceFieldSize} runners with connection evidence')
    text=text.replace('No connection angle triggered.','No trainer, jockey or combination angle is currently triggered.')
    text=text.replace('{ label: "Best Value", entry: bestValueCommand, fallback: "No market signal loaded." }','{ label: "Best Value", entry: bestValueCommand, fallback: "No value edge currently identified." }')
    text=text.replace('{ label: "Most Overbet / Risk", entry: overbetCommand, fallback: "No overbet risk loaded." }','{ label: "Most Overbet / Risk", entry: overbetCommand, fallback: "No overbet risk identified." }')
    text=text.replace('{ label: "Hidden Gem", count: hiddenGemCoverageCount }','{ label: "Hidden Gem", count: displayHiddenGemCoverageCount }')
    text=text.replace('{ label: "Connections", count: connectionsCoverageCount }','{ label: "Connections", count: displayConnectionsCoverageCount }')
    text=text.replace('{ label: "Market", count: marketCoverageCount }','{ label: "Market", count: displayMarketCoverageCount }')
    text=text.replace('{entry.label} {entry.count}/{factorFieldSize}','{entry.label} {entry.count}/{displayEvidenceFieldSize}')
    if text!=original:
        TSX.write_text(text,encoding='utf-8')
    else:
        status='FOOTER_COUNTS_FIX_NO_CHANGE'
except Exception as e:
    status='BLOCKED'; err=str(e)
row={'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'checkpoint_file':str(backup),'changes':'|'.join(changes),'error':err}
write(out,row); write(sumout,row)
report.write_text('\n'.join(['EDGEiQ Footer Counts Fix V1','='*34,f'Status: {status}',f'Checkpoint: {backup}',f'Changes: {row["changes"]}',f'Error: {err or "None"}'])+'\n',encoding='utf-8')
print(status); print('changes',row['changes']); print('error',err)
