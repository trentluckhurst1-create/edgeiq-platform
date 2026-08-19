from pathlib import Path

path = Path("src/edgeiq-os/services/race-file-v2.ts")
backup = Path("src/edgeiq-os/services/race-file-v2_CHECKPOINT_BEFORE_LIVE_WIRE_FIX_20260709.ts")
backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

text = path.read_text(encoding="utf-8")

text = text.replace(
'''    field: names.map((runner, index) => ({
      official: {''',
'''    field: names.map((runner, index) => {
      const liveRunner = findLiveRunnerSnapshot(runner);

      return {
      official: {'''
)

text = text.replace(
'''      edgeRating: liveRunner?.edgeRating || (index === 0 ? "89.6" : index < 3 ? "84.0" : "Developing",''',
'''      edgeRating: liveRunner?.edgeRating || (index === 0 ? "89.6" : index < 3 ? "84.0" : "Developing"),'''
)

text = text.replace(
'''      historicalRuns: [sampleRun(0, runner), sampleRun(1, runner)],
    })),''',
'''      historicalRuns: [sampleRun(0, runner), sampleRun(1, runner)],
    };
    }),'''
)

path.write_text(text, encoding="utf-8")
print("[EDGEIQ] race-file-v2 live wire syntax fixed")
print(f"[EDGEIQ] checkpoint: {backup}")
