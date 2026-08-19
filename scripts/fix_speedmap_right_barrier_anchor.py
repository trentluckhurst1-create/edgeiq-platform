from pathlib import Path

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

text = text.replace(
'''                <div
                  className={`racenet-band-fill ${runner ? bandClass(runner.band) : "empty"}`}
                  style={runner ? { width: `${clamp(runner.xPct + 10, 12, 95)}%` } : undefined}
                />''',
'''                <div
                  className={`racenet-band-fill ${runner ? bandClass(runner.band) : "empty"}`}
                  style={runner ? { left: `${clamp(runner.xPct, 4, 88)}%` } : undefined}
                />'''
)

text = text.replace(
'''                    style={{ left: `${runner.xPct}%` }}''',
'''                    style={{ right: "34px" }}'''
)

text = text.replace(
'''                    <em>{runner.price}</em>''',
'''                    {runner.price && runner.price !== "-" ? <em>{runner.price}</em> : null}'''
)

path.write_text(text, encoding="utf-8")
print("RIGHT BARRIER ANCHOR TSX FIX APPLIED")
