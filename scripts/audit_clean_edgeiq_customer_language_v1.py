from pathlib import Path
import pandas as pd

DATA = Path.cwd() / "public" / "data"

jobs = [
    DATA / "edgeiq_customer_intelligence_terminal_feed_v1_1.csv",
    DATA / "edgeiq_intelligence_summary_engine_v1_2.csv",
]

replacements = {
    "EDGEIQ": "EDGEiQ",
    "Runner DNA profile is poor": "Runner profile is poor",
    "Runner DNA is POOR": "Runner profile is poor",
    "Runner DNA": "Runner Profile",
    "Stable intent is watch": "Stable profile worth monitoring",
    "Stable intent deserves attention": "Stable profile deserves attention",
    "Stable intent evidence is limited": "Stable profile evidence is limited",
    "Stable intent": "Stable Profile",
    "No major GraphQL context signal": "Limited supporting historical evidence",
    "No major historical context signals exist": "Limited supporting historical evidence exists",
    "historical context signals": "historical signals",
    "Race understanding profile is worth inspection": "Race profile has some positives",
    "Market board shows LEAN": "Market may have overlooked this runner",
    "Market board shows WATCH": "Market interest worth monitoring",
    "EDGEIQ recommendation": "EDGEiQ Assessment",
    "Verdict:": "EDGEiQ Call:",
    "Why:": "Supporting Factors:",
    "Risks:": "Risk Factors:",
}

bad_terms = [
    "EDGEIQ",
    "GraphQL",
    "Runner DNA",
    "Stable intent",
    "Race understanding profile",
    "Verdict:",
    "Why:",
    "Risks:",
]

for path in jobs:
    df = pd.read_csv(path, dtype=str).fillna("")

    for col in df.columns:
        for old, new in replacements.items():
            df[col] = df[col].str.replace(old, new, regex=False)

    df.to_csv(path, index=False)

    bad_hits = []
    for term in bad_terms:
        count = int(df.astype(str).apply(lambda s: s.str.contains(term, regex=False)).sum().sum())
        if count:
            bad_hits.append((term, count))

    print(f"[CLEANED] {path.name} rows={len(df)}")
    if bad_hits:
        print("[WARN] remaining internal terms:")
        for term, count in bad_hits:
            print(f"  {term}: {count}")
    else:
        print("[PASS] no banned customer-facing terms found")

print("[CUSTOMER_LANGUAGE_AUDITED_CLEANUP] COMPLETE")
