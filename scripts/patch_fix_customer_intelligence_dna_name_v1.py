from pathlib import Path

p = Path(".\\src\\components\\RaceIntelligenceScreen.tsx")
s = p.read_text(encoding="utf-8")

s = s.replace(
'const selectedDnaBand = selected ? firstText(selectedCustomerIntel, ["dna_band"], "--") : "--";',
'const selectedCustomerDnaBand = selected ? firstText(selectedCustomerIntel, ["dna_band"], "--") : "--";'
)

s = s.replace(
'cellTone(selectedDnaBand) }}>{selectedIsScratched ? "SCRATCHED" : selectedDnaBand}</strong></div>',
'cellTone(selectedCustomerDnaBand) }}>{selectedIsScratched ? "SCRATCHED" : selectedCustomerDnaBand}</strong></div>'
)

p.write_text(s, encoding="utf-8")
print("[CUSTOMER_INTELLIGENCE_UI_PATCH_FIX_DNA_NAME] COMPLETE")
