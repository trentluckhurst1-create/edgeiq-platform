from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def remove_pool_estimate(path: Path) -> bool:
    text = path.read_text(encoding="utf-8-sig")
    target = """function poolEstimate(meeting: { declared: number; races: number }): string {
  if (!meeting.declared || !meeting.races) return "Pending";
  const estimate = Math.max(0.72, Math.round((meeting.declared * meeting.races * 0.054) * 100) / 100);
  return `$${estimate.toFixed(2)}m`;
}

"""
    if target not in text:
        return False
    path.write_text(text.replace(target, ""), encoding="utf-8", newline="")
    return True


def main() -> None:
    changed = []
    for relative in [
        "src/edgeiq-os/race/components/MeetingsWorkspace.tsx",
        "scripts/apply_edgeiq_approved_ui_phase04_meetings_v1.py",
    ]:
        path = ROOT / relative
        if remove_pool_estimate(path):
            changed.append(relative)
    print("changed=" + ",".join(changed))
    print("EDGEIQ_APPROVED_UI_PHASE04A_MEETINGS_NO_FAKE_POOL_PASS")


if __name__ == "__main__":
    main()
