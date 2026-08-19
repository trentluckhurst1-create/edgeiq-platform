import pandas as pd
import re

def clean_name(x):
    if pd.isna(x):
        return ""

    s = str(x).upper().strip()

    # remove country suffix (NZ, USA, FR etc)
    s = re.sub(r"\s*\([A-Z]+\)", "", s)

    # remove apostrophes
    s = s.replace("’","").replace("'","")

    # remove non-alphanumeric
    s = re.sub(r"[^A-Z0-9 ]", "", s)

    # collapse spaces
    s = re.sub(r"\s+", " ", s).strip()

    return s

print("="*80)
print("FIX FORM JOIN - NORMALISED KEYS")
print("="*80)

fields = pd.read_csv("public/data/race_fields.csv", low_memory=False)
form = pd.read_csv("public/data/form_engine_context.csv", low_memory=False)

fields["horse_clean"] = fields["horse"].apply(clean_name)
form["horse_clean"] = form["horse"].apply(clean_name)

merged = fields.merge(
    form,
    on="horse_clean",
    how="left",
    suffixes=("","_form")
)

merged["form_rating"] = merged["form_rating"].fillna(45)

out = "public/data/fields_with_form.csv"
merged.to_csv(out, index=False)

match_rate = merged["form_rating"].ne(45).sum()

print("MATCH RATE:", match_rate, "/", len(merged))

print("\nUNMATCHED SAMPLE:")
print(
    merged[merged["form_rating"] == 45][["horse"]]
    .head(30)
    .to_string(index=False)
)
