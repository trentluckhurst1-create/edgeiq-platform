import csv, re, shutil
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'public'/'data'
ts=ROOT/'src'/'components'/'RaceIntelligenceScreen.tsx'; cp=ROOT/'src'/'components'/'checkpoints'
out=DATA/'edgeiq_raceintelligence_evidence_update_v1.csv'; sumout=DATA/'edgeiq_raceintelligence_evidence_update_v1_summary.csv'; report=DATA/'edgeiq_raceintelligence_evidence_update_v1_report.txt'
status='RACEINTELLIGENCESCREEN_UPDATED'; err=''; backup=''; changes=[]
def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
try:
    if not ts.exists(): raise FileNotFoundError(ts)
    cp.mkdir(parents=True, exist_ok=True)
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path=cp/f'RaceIntelligenceScreen_BEFORE_EVIDENCE_UPDATE_{stamp}.tsx'
    shutil.copy2(ts, backup_path); backup=str(backup_path)
    text=ts.read_text(encoding='utf-8')
    original=text

    helper='''function evidenceFlag(row: Row | undefined, keys: string[]): boolean {\n  if (!row) return false;\n  return keys.some((key) => {\n    const value = text(row[key]).trim().toUpperCase();\n    return value === "YES" || value === "TRUE" || value === "1" || value === "Y";\n  });\n}\n\nfunction hasMergedEvidencePayload(row: Row | undefined): boolean {\n  return evidenceFlag(row, [\n    "edgeiq_connection_evidence_available",\n    "edgeiq_market_evidence_available",\n    "edgeiq_hidden_gem_evidence_available",\n  ]);\n}\n\n'''
    if 'function evidenceFlag(row: Row | undefined' not in text:
        marker='function isV72FeatureOn(row: Row | undefined): boolean {'
        if marker not in text: raise RuntimeError('Cannot find helper insertion marker')
        text=text.replace(marker, helper+marker, 1)
        changes.append('inserted_evidence_flag_helpers')

    old='''function connectionSourceRow(item: EnrichedRunner): Row | undefined {\n  if (hasConnectionPayload(item.connection)) return item.connection;\n  if (hasConnectionPayload(item.explainability)) return item.explainability;\n  return item.explainability || item.connection;\n}\n'''
    new='''function connectionSourceRow(item: EnrichedRunner): Row | undefined {\n  if (hasMergedEvidencePayload(item.row)) return item.row;\n  if (hasConnectionPayload(item.connection)) return item.connection;\n  if (hasConnectionPayload(item.explainability)) return item.explainability;\n  return item.explainability || item.connection || item.row;\n}\n'''
    if old in text:
        text=text.replace(old,new,1); changes.append('connection_source_prefers_governed_evidence_fields')
    elif 'hasMergedEvidencePayload(item.row)' not in text:
        raise RuntimeError('Cannot replace connectionSourceRow')

    old='''function hasConnectionPayload(row: Row | undefined): boolean {\n  if (!row) return false;\n  const band = firstText(row, ["connection_band"], "").toUpperCase();\n  if (band === "NO_EVIDENCE") return false;\n  return [\n'''
    new='''function hasConnectionPayload(row: Row | undefined): boolean {\n  if (!row) return false;\n  if (evidenceFlag(row, ["edgeiq_connection_evidence_available"])) return true;\n  const band = firstText(row, ["connection_band"], "").toUpperCase();\n  if (band === "NO_EVIDENCE") return false;\n  return [\n'''
    if old in text:
        text=text.replace(old,new,1); changes.append('has_connection_payload_reads_evidence_flag')

    old='''  const selectedConnectionAngles = selectedIsScratched\n    ? []\n    : [\n        firstText(selectedConnectionSource, ["connection_angle_1"], ""),\n        firstText(selectedConnectionSource, ["connection_angle_2"], ""),\n        firstText(selectedConnectionSource, ["connection_angle_3"], ""),\n      ]\n'''
    new='''  const selectedConnectionAngles = selectedIsScratched\n    ? []\n    : [\n        firstText(selectedConnectionSource, ["edgeiq_connection_angle_summary"], ""),\n        firstText(selectedConnectionSource, ["connection_angle_1"], ""),\n        firstText(selectedConnectionSource, ["connection_angle_2"], ""),\n        firstText(selectedConnectionSource, ["connection_angle_3"], ""),\n      ]\n'''
    if old in text:
        text=text.replace(old,new,1); changes.append('connection_angles_read_merged_summary')

    old='''  const selectedConnectionNarrative = selected\n    ? firstText(selectedConnectionSource, ["connection_summary_for_decision_engine", "connection_narrative"], "")\n    : "";\n'''
    new='''  const selectedConnectionNarrative = selected\n    ? firstText(selectedConnectionSource, ["edgeiq_connection_angle_summary", "connection_summary_for_decision_engine", "connection_narrative"], "")\n    : "";\n  const selectedMergedMarketAvailable = selected ? evidenceFlag(selected.row, ["edgeiq_market_evidence_available"]) : false;\n  const selectedMergedMarketSummary = selected ? firstText(selected.row, ["edgeiq_market_signal_summary"], "") : "";\n  const selectedMergedHiddenGemAvailable = selected ? evidenceFlag(selected.row, ["edgeiq_hidden_gem_evidence_available"]) : false;\n  const selectedMergedHiddenGemSummary = selected ? firstText(selected.row, ["edgeiq_hidden_gem_summary"], "") : "";\n'''
    if old in text:
        text=text.replace(old,new,1); changes.append('selected_market_hidden_merged_evidence_variables')
    elif 'selectedMergedMarketAvailable' not in text:
        raise RuntimeError('Cannot insert selected merged market/hidden variables')

    old='''  const connectionsCoverageCount = coverageCount((row) => row.connectionLoaded);\n  const factorCoverageTiles = [\n'''
    new='''  const connectionsCoverageCount = coverageCount((row) => row.connectionLoaded || evidenceFlag(row.item.row, ["edgeiq_connection_evidence_available"]));\n  const marketCoverageCount = coverageCount((row) => evidenceFlag(row.item.row, ["edgeiq_market_evidence_available"]));\n  const hiddenGemCoverageCount = coverageCount((row) => evidenceFlag(row.item.row, ["edgeiq_hidden_gem_evidence_available"]));\n  const factorCoverageTiles = [\n'''
    if old in text:
        text=text.replace(old,new,1); changes.append('footer_counts_use_evidence_flags')

    old='''    { label: "Connections", count: connectionsCoverageCount, explanation: "Trainer, jockey and combination evidence for the current race universe." },\n  ].map((tile) => ({\n'''
    new='''    { label: "Connections", count: connectionsCoverageCount, explanation: "Trainer, jockey and combination evidence for the current race universe." },\n    { label: "Market", count: marketCoverageCount, explanation: "Current market signal evidence surfaced from the governed runner board." },\n    { label: "Hidden Gem", count: hiddenGemCoverageCount, explanation: "Performance intelligence flags surfaced from current evidence." },\n  ].map((tile) => ({\n'''
    if old in text:
        text=text.replace(old,new,1); changes.append('footer_tiles_include_market_hidden_gem')

    old='''          currentRead: selectedIsScratched\n            ? "Runner scratched."\n            : selectedLivePrice !== "--"\n              ? "Live TAB reference loaded."\n              : "TAB price pending; EDGEiQ reference available.",\n'''
    # not present; use factor market block replacement below
    old='''          evidenceDetail: selectedIsScratched\n            ? "SCRATCHED"\n            : selectedLivePrice !== "--"\n              ? "Live TAB reference loaded."\n              : "TAB price pending; EDGEiQ reference available.",\n'''
    new='''          evidenceDetail: selectedIsScratched\n            ? "SCRATCHED"\n            : selectedMergedMarketAvailable\n              ? selectedMergedMarketSummary || "Market signal evidence loaded."\n              : selectedLivePrice !== "--"\n                ? "Live TAB reference loaded. No market signals triggered."\n                : "No market signals triggered.",\n'''
    if old in text:
        text=text.replace(old,new,1); changes.append('factor_market_evidence_detail_uses_merged_summary')

    old='''              ? [\n                  selectedHiddenGemTrigger,\n                  selectedHiddenGemHistorical && selectedHiddenGemDate !== "--"\n                    ? `Profile evidence from ${formatHistoryDate(selectedHiddenGemDate)}`\n                    : "",\n                  !selectedHiddenGemActionable && !selectedHiddenGemHistorical\n                    ? "Neutral current performance intelligence."\n                    : "",\n                ].filter(Boolean).join(" | ") || selectedHiddenGemNarrative\n              : "Neutral performance intelligence for this runner.",\n'''
    new='''              ? [\n                  selectedMergedHiddenGemAvailable ? selectedMergedHiddenGemSummary : "",\n                  selectedHiddenGemTrigger,\n                  selectedHiddenGemHistorical && selectedHiddenGemDate !== "--"\n                    ? `Profile evidence from ${formatHistoryDate(selectedHiddenGemDate)}`\n                    : "",\n                  !selectedHiddenGemActionable && !selectedHiddenGemHistorical\n                    ? "Neutral current performance intelligence."\n                    : "",\n                ].filter(Boolean).join(" | ") || selectedHiddenGemNarrative\n              : selectedMergedHiddenGemAvailable\n                ? selectedMergedHiddenGemSummary || "Hidden gem evidence loaded."\n                : "No hidden gem flagged.",\n'''
    if old in text:
        text=text.replace(old,new,1); changes.append('performance_detail_uses_merged_hidden_gem_summary')

    if 'No connection angles triggered.' in text:
        changes.append('connection_fallback_text_preserved')
    else:
        changes.append('connection_fallback_text_not_found')

    if text==original: raise RuntimeError('No TSX changes were applied')
    ts.write_text(text, encoding='utf-8')
except Exception as e:
    status='BLOCKED'; err=str(e)

rows=[{'status':status,'generated_at':datetime.now().isoformat(timespec='seconds'),'file':str(ts),'checkpoint_file':backup,'changes_applied':'|'.join(changes),'error':err}]
write_csv(out, rows, list(rows[0].keys()))
write_csv(sumout, rows, list(rows[0].keys()))
report.write_text('\n'.join(['EDGEiQ RaceIntelligenceScreen Evidence Update V1','='*58,f'Status: {status}',f'Checkpoint: {backup}',f'Changes: {"|".join(changes)}',f'Error: {err or "None"}'])+'\n',encoding='utf-8')
print(status); print('changes', '|'.join(changes)); print('error', err)
