from pathlib import Path


path = Path(
    r"scripts\patch_edgeiq_benchmark_evidence_mapping_v1.py"
)

text = path.read_text(encoding="utf-8-sig")

old = '''    updated, count = pattern.subn(
        replacement.rstrip() + "\\n\\n",
        text,
        count=1,
    )
'''

new = '''    replacement_text = replacement.rstrip() + "\\n\\n"

    updated, count = pattern.subn(
        lambda _match: replacement_text,
        text,
        count=1,
    )
'''

if old not in text:
    raise RuntimeError(
        "Could not locate replace_function subn block."
    )

text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")

print(
    "Patched literal function replacement handling in:",
    path,
)
