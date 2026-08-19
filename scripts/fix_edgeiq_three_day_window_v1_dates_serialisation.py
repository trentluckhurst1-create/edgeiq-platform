from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / "scripts" / "edgeiq_three_day_window_v1_common.py"

text = target.read_text(encoding="utf-8")

old = '''    def to_dict(self) -> dict[str, object]:
        return asdict(self)
'''

new = '''    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["dates"] = list(payload["dates"])
        return payload
'''

if old not in text:
    raise RuntimeError(
        "Expected to_dict implementation was not found. "
        "No changes were applied."
    )

target.write_text(
    text.replace(old, new, 1),
    encoding="utf-8",
)

print("[EDGEIQ_THREE_DAY_WINDOW_V1_FIX] PASS")
print(f"patched={target}")
