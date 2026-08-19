from pathlib import Path


target = Path(
    "scripts/"
    "lock_edgeiq_historical_observation_v3_"
    "raw_authority_phase1a_6b_1b_v1.py"
)

text = target.read_text(
    encoding="utf-8-sig"
)

old = '''        if (
            not path.exists()
            or path.suffix.lower()
            not in {
                ".py",
                ".ps1",
                ".json",
                ".md",
                ".csv",
                ".txt",
            }
        ):
            continue
'''

new = '''        if not path.exists():
            continue

        suffix = path.suffix.lower()

        if suffix not in {
            ".py",
            ".ps1",
            ".json",
            ".md",
            ".csv",
            ".txt",
        }:
            continue

        # Governance wording does not need to be searched
        # inside warehouse-sized CSV datasets.
        if (
            suffix == ".csv"
            and path.stat().st_size > 5_000_000
        ):
            continue
'''

if old not in text:
    raise RuntimeError(
        "Expected semantic scan block was not found. "
        "The target script was not modified."
    )

updated = text.replace(
    old,
    new,
    1,
)

target.write_text(
    updated,
    encoding="utf-8",
)

print(
    "PATCHED:",
    target.as_posix(),
)
print(
    "Large CSV semantic scanning is now excluded."
)
