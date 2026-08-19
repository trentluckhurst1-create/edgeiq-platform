from __future__ import annotations

from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
TARGETS = [
    ROOT / "scripts" / "build_edgeiq_racingcom_graphql_request_contract_v1.py",
    ROOT / "scripts" / "build_edgeiq_racingcom_graphql_acquisition_v1.py",
]
CHECKPOINT_SUFFIX = "_CHECKPOINT_PRE_OBSERVED_QUERY_TEMPLATE_20260723.py"


OLD = """      SectionalTimes: times {
        Distance: distance
        Position: position
        Time: time
        AvgSpeed: averageSpeed
      }"""

NEW = """      SectionalTimes: times {
        Distance: distance
        Position: rank
        Time: intermediateTime
        AvgSpeed: avgSpeed
      }
      SplitTimes: splitTimes {
        Distance: distance
        Position: position
        Time: time
        AvgSpeed: avgSpeed
      }
      StartPosition: startPosition
      BarrierNumber: barrierNumber
      RaceTime: finishTime
      TimeVarToWinner: timeVarToWinner
      BeatenMargin: beatenMargin
      DistanceRun: distanceTravelled
      DistanceVarToWinner: distanceVarToWinner
      SixHundredMetresTime: sixHundredMetresTime
      TwoHundredMetresTime: twoHundredMetresTime"""


def main() -> int:
    patched = []
    for target in TARGETS:
        text = target.read_text(encoding="utf-8")
        checkpoint = target.with_name(target.stem + CHECKPOINT_SUFFIX)
        if not checkpoint.exists():
            checkpoint.write_text(text, encoding="utf-8")
        if OLD not in text and NEW not in text:
            raise RuntimeError(f"Expected query block not found in {target}")
        if OLD in text:
            target.write_text(text.replace(OLD, NEW), encoding="utf-8")
            patched.append(str(target))
    print({"status": "PATCH_APPLIED", "patched_files": patched})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
