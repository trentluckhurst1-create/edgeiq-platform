from pathlib import Path

path = Path("scripts/build_edgeiq_data_registry_v1.py")
backup = Path("scripts/build_edgeiq_data_registry_v1_CHECKPOINT_BEFORE_DNA_JOIN_PATCH_20260709.py")
backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

text = path.read_text(encoding="utf-8")

text = text.replace(
'''        runner = val(row, ["runner_name","runnerName","horse_name","horseName","runner","horse"], ["runner","horse","name"], reject_numeric=True)''',
'''        runner = val(row, ["horse","runner_key","runner_name","runnerName","horse_name","horseName","runner"], ["horse","runner"], reject_numeric=True)'''
)

text = text.replace(
'''        band = val(row, ["dna_v6_2_band","dna_band","dnaBand","runnerDNA","runner_dna","band"], ["dnaband","runnerdna"], reject_url=True)
        score = val(row, ["dna_v6_2_score","dna_score","dnaScore","score"], ["dnascore"], reject_url=True)''',
'''        band = val(row, ["runner_dna_band","dna_v6_2_band","dna_band","dnaBand","overall_dna_band","projection_band_V6_1_RESEARCH","distance_fit_band"], ["dnaband","fitband"], reject_url=True)
        score = val(row, ["runner_dna_score","dna_v6_2_score","dna_score","dnaScore","overall_dna_score","distance_fit_score"], ["dnascore","fitscore"], reject_url=True)'''
)

path.write_text(text, encoding="utf-8")
print("[EDGEIQ] Data registry DNA join patched")
print(f"[EDGEIQ] checkpoint: {backup}")
