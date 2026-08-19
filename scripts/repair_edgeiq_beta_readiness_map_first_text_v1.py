from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MapWorkspace.tsx"


def main() -> None:
    text = PATH.read_text(encoding="utf-8", errors="replace")
    target = """function text(value: unknown): string {
  if (value === null || value === undefined) return "";
  const output = String(value).trim();
  return output === "-" ? "" : output;
}
"""
    insertion = target + """
function firstText(...values: unknown[]): string {
  for (const value of values) {
    const output = text(value);
    if (output) return output;
  }
  return "";
}
"""
    if "function firstText(...values: unknown[]): string" in text:
        print("firstText helper already present.")
        return
    if target not in text:
        raise RuntimeError("Could not locate MapWorkspace text helper.")
    PATH.write_text(text.replace(target, insertion, 1), encoding="utf-8", newline="")
    print("Added MapWorkspace firstText helper.")


if __name__ == "__main__":
    main()
