from pathlib import Path

path = Path("src/edgeiq-os/race/RaceFileV3.tsx")
backup = Path("src/edgeiq-os/race/RaceFileV3_CHECKPOINT_BEFORE_LIVE_FIELD_UI_CLEANUP_20260709.tsx")
backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

text = path.read_text(encoding="utf-8")

text = text.replace('function clean(value: any): string {', '''function displayMarket(value: any): string {
  const raw = String(value ?? "").trim();
  if (!raw || raw.toUpperCase() === "MISSING") return "Market pending";
  if (raw.toUpperCase() === "SCRATCHED") return "Scratched";
  const n = Number(raw);
  return Number.isFinite(n) ? `$${n.toFixed(n < 10 ? 2 : 0)}` : raw;
}

function displayDNA(value: any): string {
  const raw = String(value ?? "").trim();
  if (!raw || raw.toUpperCase().includes("HTTP")) return "DNA pending";
  return raw;
}

function displayWeight(value: any): string {
  const raw = String(value ?? "").trim();
  return raw ? raw : "Weight pending";
}

function clean(value: any): string {''')

text = text.replace('{clean(primary.official.weight)}', '{displayWeight(primary.official.weight)}')
text = text.replace('{clean(primary.official.market)}', '{displayMarket(primary.official.market)}')
text = text.replace('{clean(primary.runnerDNA)}', '{displayDNA(primary.runnerDNA)}')

text = text.replace('{clean(official.sp)}', '{displayMarket(official.sp)}')
text = text.replace('{clean(official.weight)}', '{displayWeight(official.weight)}')

text = text.replace('DNA pending', 'DNA pending')

path.write_text(text, encoding="utf-8")
print("[EDGEIQ] Live field UI cleanup applied")
print(f"[EDGEIQ] checkpoint: {backup}")
