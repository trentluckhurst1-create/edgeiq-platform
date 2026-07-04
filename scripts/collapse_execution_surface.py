from pathlib import Path

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

old = '''              <section className="edgeiq-race-bottom">
                <LiveExecutionTerminal rows={executionFeedRows as any} />
              </section>'''

new = '''              <section className="edgeiq-race-bottom">
                <details className="edgeiq-execution-drawer">
                  <summary>
                    <span>EDGEiQ EXECUTION INTELLIGENCE</span>
                    <strong>{executionFeedRows.length} live signals</strong>
                    <em>Open command surface</em>
                  </summary>
                  <LiveExecutionTerminal rows={executionFeedRows as any} />
                </details>
              </section>'''

if old not in text:
    raise SystemExit("Execution bottom block not found")

text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")

print("COLLAPSED LiveExecutionTerminal INTO COMMAND DRAWER")
