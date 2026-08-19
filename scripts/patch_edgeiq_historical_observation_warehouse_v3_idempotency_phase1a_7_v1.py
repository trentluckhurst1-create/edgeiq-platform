from pathlib import Path


target = Path(
    "scripts/"
    "rebuild_edgeiq_historical_observation_warehouse_v3.py"
)

text = target.read_text(
    encoding="utf-8-sig"
)

old = '''    if final_snapshot_root.exists():
        existing_manifest = (
            final_snapshot_root
            / "manifest.json"
        )

        new_manifest = (
            temporary_snapshot_root
            / "manifest.json"
        )

        if (
            existing_manifest.exists()
            and sha256_file(
                existing_manifest
            )
            == sha256_file(
                new_manifest
            )
        ):
            shutil.rmtree(
                temporary_snapshot_root
            )

            return final_snapshot_root

        raise RuntimeError(
            "Deterministic snapshot path already exists "
            "with different content: "
            f"{relative(final_snapshot_root)}"
        )
'''

new = '''    if final_snapshot_root.exists():
        # The snapshot identity is derived only from deterministic
        # warehouse and contract content. Timestamped reports and the
        # manifest may legitimately differ between equivalent reruns,
        # so they must not determine idempotent equivalence.
        deterministic_files = (
            "historical_observation_warehouse_v3.csv",
            "historical_observation_warehouse_v3_schema_contract.json",
            "historical_observation_warehouse_v3_lineage_contract.json",
            "historical_observation_warehouse_v3_population_contract.json",
        )

        comparison_failures = []

        for filename in deterministic_files:
            existing_file = (
                final_snapshot_root
                / filename
            )

            candidate_file = (
                temporary_snapshot_root
                / filename
            )

            if (
                not existing_file.exists()
                or not candidate_file.exists()
            ):
                comparison_failures.append(
                    f"{filename}:missing"
                )
                continue

            if (
                sha256_file(existing_file)
                != sha256_file(candidate_file)
            ):
                comparison_failures.append(
                    f"{filename}:hash_mismatch"
                )

        if not comparison_failures:
            shutil.rmtree(
                temporary_snapshot_root
            )

            return final_snapshot_root

        raise RuntimeError(
            "Deterministic snapshot path already exists "
            "with different governed content: "
            f"{relative(final_snapshot_root)}; "
            + ", ".join(comparison_failures)
        )
'''

if old not in text:
    raise RuntimeError(
        "Expected snapshot idempotency block was not found. "
        "The builder was not modified."
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
    "Equivalent deterministic snapshots are now "
    "accepted on governed reruns."
)
