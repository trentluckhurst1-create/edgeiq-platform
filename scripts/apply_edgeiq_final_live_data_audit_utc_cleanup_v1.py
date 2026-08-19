from pathlib import Path
path = Path('scripts/audit_edgeiq_final_live_data_population_v1.py')
text = path.read_text(encoding='utf-8')
text = text.replace('from datetime import datetime\n', 'from datetime import datetime, timezone\n')
text = text.replace('f"Generated: {datetime.utcnow().isoformat()}Z", "",', 'f"Generated: {datetime.now(timezone.utc).isoformat()}", "",')
path.write_text(text, encoding='utf-8')
print('EDGEIQ_FINAL_LIVE_DATA_AUDIT_UTC_WARNING_CLEANED')
