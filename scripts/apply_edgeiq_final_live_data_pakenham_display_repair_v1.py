from pathlib import Path
path = Path('scripts/build_edgeiq_three_day_product_catalog_v1.py')
text = path.read_text(encoding='utf-8')
text = text.replace('''    text = re.sub(\n        r"SYNTHETIC(?:THETIC)+",\n        "SYNTHETIC",\n        text,\n        flags=re.IGNORECASE,\n    )\n\n    return re.sub(r"\\s+", " ", text).strip()\n''', '''    text = re.sub(\n        r"SYNTHETIC(?:THETIC)+",\n        "SYNTHETIC",\n        text,\n        flags=re.IGNORECASE,\n    )\n    text = re.sub(\n        r"^SOUTHSIDE\\s+PAKENHAM\\s+SYNTHETIC$",\n        "PAKENHAM SYNTHETIC",\n        text,\n        flags=re.IGNORECASE,\n    )\n\n    return re.sub(r"\\s+", " ", text).strip()\n''')
path.write_text(text, encoding='utf-8')
print('EDGEIQ_PRODUCT_CATALOG_SOUTHSIDE_PAKENHAM_NORMALISED')
