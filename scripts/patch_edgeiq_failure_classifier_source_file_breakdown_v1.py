from pathlib import Path

path = Path(
    r"scripts\classify_edgeiq_historical_observation_failures_v1.py"
)

text = path.read_text(encoding="utf-8-sig")

text = text.replace(
    'TRACK_BREAKDOWN_PATH = OUTPUT_DIR / "edgeiq_failure_track_breakdown_v1.csv"\n',
    'TRACK_BREAKDOWN_PATH = OUTPUT_DIR / "edgeiq_failure_track_breakdown_v1.csv"\n'
    'SOURCE_FILE_BREAKDOWN_PATH = OUTPUT_DIR / "edgeiq_failure_source_file_breakdown_v1.csv"\n'
)

text = text.replace(
    '    source_counts: Counter = Counter()\n',
    '    source_counts: Counter = Counter()\n'
    '    source_file_counts: Counter = Counter()\n'
)

text = text.replace(
    '            source_counts[source_system or "UNRESOLVED_SOURCE_SYSTEM"] += 1\n',
    '            source_counts[source_system or "UNRESOLVED_SOURCE_SYSTEM"] += 1\n'
    '            source_file_counts[source_path or "MISSING_SOURCE_PATH"] += 1\n'
)

text = text.replace(
    '    write_counter_table(\n'
    '        YEAR_BREAKDOWN_PATH,\n',
    '    write_counter_table(\n'
    '        SOURCE_FILE_BREAKDOWN_PATH,\n'
    '        "source_path",\n'
    '        source_file_counts,\n'
    '        total_rows,\n'
    '    )\n'
    '    write_counter_table(\n'
    '        YEAR_BREAKDOWN_PATH,\n'
)

text = text.replace(
    '        "source_counts_reconcile": sum(source_counts.values()) == total_rows,\n',
    '        "source_counts_reconcile": sum(source_counts.values()) == total_rows,\n'
    '        "source_file_counts_reconcile": sum(source_file_counts.values()) == total_rows,\n'
)

text = text.replace(
    '        "source_system_count": len(source_counts),\n',
    '        "source_system_count": len(source_counts),\n'
    '        "source_file_count": len(source_file_counts),\n'
)

text = text.replace(
    '            "source_breakdown": sha256_file(SOURCE_BREAKDOWN_PATH),\n',
    '            "source_breakdown": sha256_file(SOURCE_BREAKDOWN_PATH),\n'
    '            "source_file_breakdown": sha256_file(SOURCE_FILE_BREAKDOWN_PATH),\n'
)

text = text.replace(
    '                SOURCE_BREAKDOWN_PATH,\n'
    '                YEAR_BREAKDOWN_PATH,\n',
    '                SOURCE_BREAKDOWN_PATH,\n'
    '                SOURCE_FILE_BREAKDOWN_PATH,\n'
    '                YEAR_BREAKDOWN_PATH,\n'
)

text = text.replace(
    '- `{SOURCE_BREAKDOWN_PATH.relative_to(REPO_ROOT)}`\n',
    '- `{SOURCE_BREAKDOWN_PATH.relative_to(REPO_ROOT)}`\n'
    '- `{SOURCE_FILE_BREAKDOWN_PATH.relative_to(REPO_ROOT)}`\n'
)

path.write_text(text, encoding="utf-8")
