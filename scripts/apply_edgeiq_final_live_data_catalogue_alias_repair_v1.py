from pathlib import Path
path = Path('scripts/build_edgeiq_three_day_product_catalog_v1.py')
text = path.read_text(encoding='utf-8')
text = text.replace('''    "COLAC",\n    "CRANBOURNE",''', '''    "COLAC",\n    "COLERAINE",\n    "CRANBOURNE",''')
text = text.replace('''        "GEELONG SYNTHETIC": "GEELONG",\n    }''', '''        "GEELONG SYNTHETIC": "GEELONG",\n        "PAKENHAM SYNTHETIC": "PAKENHAM",\n    }''')
path.write_text(text, encoding='utf-8')
print('EDGEIQ_PRODUCT_CATALOG_VICTORIAN_SYNTHETIC_ALIASES_PATCHED')
