from pathlib import Path
import re

path = Path(r".\scripts\run_edgeiq_vic_live_build_poller.py")

content = path.read_text(encoding="utf-8")

content = re.sub(
    r"STEPS\s*=\s*\[[\s\S]*?\]",
    """STEPS = [
    ["python", str(ROOT / "scripts" / "enrich_vic_live_feed_scratchings.py")],
    ["python", str(ROOT / "scripts" / "enrich_vic_live_feed_silks.py")],
]""",
    content,
    count=1,
)

content = re.sub(
    r"\n\s*\]\s*\n\s*POLL_INTERVAL",
    "\n\nPOLL_INTERVAL",
    content,
    count=1,
)

path.write_text(content, encoding="utf-8")

print("FIXED POLLER STEPS BLOCK")
