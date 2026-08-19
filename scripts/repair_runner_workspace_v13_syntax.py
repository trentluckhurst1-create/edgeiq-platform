from pathlib import Path

path = Path("src/edgeiq-os/race/RaceFileV3.tsx")
backup = Path("src/edgeiq-os/race/RaceFileV3_CHECKPOINT_BEFORE_V13_SYNTAX_REPAIR_20260709.tsx")
backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

text = path.read_text(encoding="utf-8")

# The V13 replacement left the old function return tail behind. Remove duplicate trailing return close.
bad = '''
  );
}
'''
# If the file ends with duplicated closing tail, trim after final valid export function close pattern.
idx = text.rfind('    </section>\n  );')
if idx != -1:
    close_idx = text.find('\n}', idx)
    if close_idx != -1:
        text = text[:close_idx + 2] + "\n"

path.write_text(text, encoding="utf-8")
print("[EDGEIQ] V13 syntax tail repaired")
print(f"[EDGEIQ] checkpoint: {backup}")
