import pandas as pd

ratings = pd.read_csv("public/data/ratings_audit_elite_v3.csv", low_memory=False)
form = pd.read_csv("public/data/form_engine.csv", low_memory=False)

print("RATINGS COLS:", list(ratings.columns))
print("FORM COLS:", list(form.columns))
print()
print("RATINGS HORSE/KEY SAMPLE:")
print(ratings[[c for c in ["horse","horse_key","horse_key_norm"] if c in ratings.columns]].head(30).to_string(index=False))
print()
print("FORM HORSE/KEY SAMPLE:")
print(form[[c for c in ["horse","horse_key"] if c in form.columns]].head(30).to_string(index=False))
print()
print("FORM HAS TENENBAUM:", form[form["horse"].astype(str).str.upper().str.contains("TENENBAUM", na=False)].to_string(index=False))
print("FORM HAS ROARING:", form[form["horse"].astype(str).str.upper().str.contains("ROARING", na=False)].to_string(index=False))
print("FORM HAS LAFITE:", form[form["horse"].astype(str).str.upper().str.contains("LAFITE", na=False)].to_string(index=False))
