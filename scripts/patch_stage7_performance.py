
from pathlib import Path

path = Path(r"scripts\build_edgeiq_historical_run_observation_fact_v2.py")
text = path.read_text(encoding="utf-8-sig")

old_master = '''master_ids = {
    row["canonical_horse_id"]
    for row in master_rows
}
'''
new_master = '''master_ids = {
    row["canonical_horse_id"]
    for row in master_rows
}

master_name_by_id = {
    row["canonical_horse_id"]: row["canonical_horse_name"]
    for row in master_rows
}
'''
if old_master not in text:
    raise SystemExit("PATCH FAILED: master_ids block not found")
text = text.replace(old_master, new_master, 1)

old_source = '''    source_system = source_system_from_path(
        source_path
    )
'''
new_source = '''    source_system = source_system_from_path(
        source_path
    )

    source_file_hash = sha256_file(
        source_path
    )
'''
if old_source not in text:
    raise SystemExit("PATCH FAILED: source_system block not found")
text = text.replace(old_source, new_source, 1)

old_name = '''        canonical_name = next(
            (
                row["canonical_horse_name"]
                for row in master_rows
                if row["canonical_horse_id"]
                == canonical_horse_id
            ),
            source_horse_name,
        )
'''
new_name = '''        canonical_name = master_name_by_id.get(
            canonical_horse_id,
            source_horse_name,
        )
'''
if old_name not in text:
    raise SystemExit("PATCH FAILED: canonical_name lookup block not found")
text = text.replace(old_name, new_name, 1)

old_hash = '''sha256_file(
                source_path
            )'''
count = text.count(old_hash)
if count < 2:
    raise SystemExit(f"PATCH FAILED: expected at least 2 repeated source hashes, found {count}")
text = text.replace(old_hash, "source_file_hash")

path.write_text(text, encoding="utf-8")
print("PATCH PASS: removed repeated full-file hashing and linear horse-name scans")
