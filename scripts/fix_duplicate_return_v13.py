from pathlib import Path

path = Path("src/edgeiq-os/race/RaceFileV3.tsx")
backup = Path("src/edgeiq-os/race/RaceFileV3_CHECKPOINT_BEFORE_REMOVE_DUPLICATE_RETURN_20260709.tsx")
backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

text = path.read_text(encoding="utf-8")
text = text.replace(
'''    </section>
  );
  );
}''',
'''    </section>
  );
}'''
)

path.write_text(text, encoding="utf-8")
print("[EDGEIQ] duplicate return removed")
print(f"[EDGEIQ] checkpoint: {backup}")
