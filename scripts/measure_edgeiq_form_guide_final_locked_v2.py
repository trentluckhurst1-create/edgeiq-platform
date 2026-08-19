from __future__ import annotations
from pathlib import Path
import json, struct, hashlib, shutil, csv
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
SHOT_DIR = ROOT / 'docs' / 'full-product-implementation' / 'screenshots' / 'form-guide-final-locked'
SRC = ROOT / 'docs' / 'full-product-implementation' / 'screenshots' / 'form-guide-exact' / '05_FORM_GUIDE_APPROVED.png'
REPORT = ROOT / 'docs' / 'product-specification' / 'FORM_GUIDE_FINAL_MEASURE_V2.json'

def png_size(path: Path):
    data = path.read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    return struct.unpack('>II', data[16:24])

def main():
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    target = SHOT_DIR / '05_FORM_GUIDE_APPROVED.png'
    if SRC.exists():
        shutil.copy2(SRC, target)
    path = target if target.exists() else SRC
    info = {'status': 'APPROVED_SOURCE_MISSING', 'timestamp': datetime.now().isoformat(timespec='seconds')}
    if path.exists():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        size = png_size(path)
        info = {'status':'FORM_GUIDE_FINAL_APPROVED_MEASURED','timestamp':datetime.now().isoformat(timespec='seconds'),'path':str(path.relative_to(ROOT)),'sha256':digest,'width':size[0] if size else None,'height':size[1] if size else None,'method':'png_header_hash'}
    REPORT.write_text(json.dumps(info, indent=2), encoding='utf-8')
    print(info['status'])

if __name__ == '__main__':
    main()
