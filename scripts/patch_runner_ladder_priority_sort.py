from pathlib import Path
import re

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

old = '''                  <div className="edgeiq-runner-decision-table">
                    {(currentRace?.rows ?? []).filter((row) => !row.isScratched).map((row) => {
                      const action = runnerDecision(row);
                      const edge = saneOverlay(row.edgePct);
                      const map = row.run_style_cluster || row.sectional_profile || "-";

                      return ('''

new = '''                  <div className="edgeiq-runner-decision-table">
                    {(currentRace?.rows ?? [])
                      .filter((row) => !row.isScratched)
                      .map((row) => ({
                        row,
                        action: runnerDecision(row),
                        edge: saneOverlay(row.edgePct),
                      }))
                      .sort((a, b) => {
                        const actionRank = (v: string) => {
                          if (v === "EXECUTE") return 0;
                          if (v === "WATCH") return 1;
                          if (v === "WAIT") return 2;
                          if (v === "PASS") return 3;
                          return 4;
                        };

                        const actionDiff = actionRank(a.action) - actionRank(b.action);
                        if (actionDiff !== 0) return actionDiff;

                        return (b.edge ?? -999) - (a.edge ?? -999);
                      })
                      .map(({ row, action, edge }) => {
                        const map = row.run_style_cluster || row.sectional_profile || "-";

                        return ('''

text = text.replace(old, new)

text = text.replace(
    '''<span className="map">{map}</span>''',
    '''<span className="map">{map.toUpperCase().replaceAll("_", " ")}</span>'''
)

path.write_text(text, encoding="utf-8")

print("=" * 80)
print("RUNNER DECISION LADDER NOW SORTS BY:")
print("1. EXECUTE")
print("2. WATCH")
print("3. WAIT")
print("4. PASS")
print("THEN BY HIGHEST EDGE")
print("=" * 80)
