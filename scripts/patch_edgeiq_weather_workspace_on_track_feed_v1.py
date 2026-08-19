from pathlib import Path


TARGET = Path("src/edgeiq-os/race/components/MeetingWeatherWorkspace.tsx")


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    old = """        setFeeds({
          metropolitan: [],
          raceWeather: [],
          generatedAt: null,
          sourceError: message,
        });"""
    new = """        setFeeds({
          metropolitan: [],
          raceWeather: [],
          onTrack: [],
          generatedAt: null,
          sourceError: message,
        });"""
    if old not in text:
        if "onTrack: []" in text:
            print("EDGEIQ_WEATHER_WORKSPACE_ON_TRACK_FEED_PATCH_V1_ALREADY_APPLIED")
            return
        raise SystemExit("Expected weather fallback block was not found.")
    TARGET.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("EDGEIQ_WEATHER_WORKSPACE_ON_TRACK_FEED_PATCH_V1_APPLIED")


if __name__ == "__main__":
    main()
