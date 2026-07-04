import pandas as pd

f = pd.read_csv("public/data/race_fields.csv", low_memory=False)

# build field size per race
f["race_id_fix"] = f["race_date"].astype(str) + "|" + f["track"].astype(str) + "|" + f["race_no"].astype(str)

field_sizes = f.groupby("race_id_fix")["horse"].count().to_dict()

f["field_size"] = f["race_id_fix"].map(field_sizes)

f.to_csv("public/data/race_fields.csv", index=False)

print("FIELD SIZE FIXED")
print(f["field_size"].value_counts().head())
