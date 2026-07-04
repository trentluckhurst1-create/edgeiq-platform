from pathlib import Path
import re

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

pattern = r'''          \{runners\.map\(\(runner\) => \{[\s\S]*?          \}\)\}'''

replacement = r'''          {runners.map((runner) => {
            const selected = clean(selectedHorse) === clean(runner.horse);

            return (
              <button
                key={`${runner.horse}-${runner.saddlecloth}`}
                type="button"
                className={`edgeiq-speed-row ${selected ? "selected" : ""}`}
                onClick={() => onSelectHorse?.(runner.horse)}
              >
                <span>{runner.saddlecloth || "-"}</span>

                <span className="horse">
                  <img
                    src={getSilksUrl(runner.horse, runner.silkUrl)}
                    alt=""
                    onError={silkFallback}
                  />
                  <strong>{runner.horse}</strong>
                </span>

                <span>{runner.jockey || "-"}</span>
                <span>{runner.barrier || "-"}</span>
                <span className="spd">{runner.spd}</span>

                <div
                  className="edgeiq-speed-bar-wrap"
                  style={{ gridColumn: "6 / 17" }}
                >
                  <div
                    className={`edgeiq-speed-bar ${runner.mapPosition.replace(/\s+/g, "-").toLowerCase()}`}
                    style={{ width: `${runner.spd}%` }}
                  />
                </div>
              </button>
            );
          })}'''

text2 = re.sub(pattern, lambda m: replacement, text, count=1)

if text2 == text:
    raise SystemExit("RUNNER MAP BLOCK NOT REPLACED")

path.write_text(text2, encoding="utf-8")

print("REBUILT SPEED BAR RENDERING")
