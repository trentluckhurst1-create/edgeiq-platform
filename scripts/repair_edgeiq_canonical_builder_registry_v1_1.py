from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

SOURCE_PATH = (
    REPOSITORY_ROOT
    / "scripts"
    / "_edgeiq_builder_registry_v1_1_source.tmp"
)

TARGET_PATH = (
    REPOSITORY_ROOT
    / "scripts"
    / "build_edgeiq_canonical_builder_registry_v1_1.py"
)


def main() -> int:
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(
            f"Staged Builder Registry source missing: {SOURCE_PATH}"
        )

    source = SOURCE_PATH.read_text(
        encoding="utf-8-sig",
        errors="strict",
    )

    if len(source.strip()) < 1000:
        raise RuntimeError(
            "Staged Builder Registry source is empty or incomplete: "
            f"{len(source)} characters"
        )

    compile(
        source,
        str(TARGET_PATH),
        "exec",
    )

    TARGET_PATH.write_text(
        source,
        encoding="utf-8",
        newline="\n",
    )

    written = TARGET_PATH.read_text(
        encoding="utf-8",
        errors="strict",
    )

    compile(
        written,
        str(TARGET_PATH),
        "exec",
    )

    if written != source:
        raise RuntimeError(
            "Written Builder Registry source does not match staged source"
        )

    print(f"SOURCE={SOURCE_PATH}")
    print(f"SOURCE_CHARACTERS={len(source)}")
    print(f"TARGET={TARGET_PATH}")
    print(f"TARGET_BYTES={TARGET_PATH.stat().st_size}")
    print("REPAIR_VALIDATION=PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
