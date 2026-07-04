from pathlib import Path
import pandas as pd

DATA = Path.cwd() / "public" / "data"

files = [
    DATA / "edgeiq_customer_intelligence_terminal_feed_v1_1.csv",
    DATA / "edgeiq_intelligence_summary_engine_v1_2.csv",
]

replacements = {
    "EDGEiQ recommendation": "EDGEiQ Assessment",
    "EDGEIQ recommendation": "EDGEiQ Assessment",
    "EDGEiQ VERDICT": "EDGEiQ Assessment",
    "Why inspect:": "Supporting Factors:",
    "Stable Profile watch signal present": "Stable profile worth monitoring",
    "Race setup lists this runner as helped": "Race profile has some positives",
    "Market board decision: LEAN": "Market may have overlooked this runner",
    "Market board decision: WATCH": "Market interest worth monitoring",
    "No major risk flag detected": "No major risk flag identified",
    "Runner profile is poor. Limited supporting historical evidence exists.": "Runner profile is poor. Historical support is limited.",
    "Stable profile deserves attention. Runner profile is poor. Limited supporting historical evidence exists.": "Stable profile deserves attention, but the runner profile is poor and historical support is limited.",
    "EDGEiQ Assessment: EDGEiQ does not currently have enough evidence to support this runner.": "EDGEiQ Assessment: Not enough evidence to support this runner at this stage.",
    "EDGEiQ does not currently have enough evidence to support this runner.": "Not enough evidence to support this runner at this stage.",
}

for path in files:
    df = pd.read_csv(path, dtype=str).fillna("")

    for col in df.columns:
        for old, new in replacements.items():
            df[col] = df[col].str.replace(old, new, regex=False)

    # COMMAND should not rely on this raw source narrative.
    # Keep it for audit/debugging, but make clear it is source detail.
    if "source_customer_narrative_v3_2" in df.columns:
        df["source_customer_narrative_v3_2"] = df["source_customer_narrative_v3_2"].str.replace(
            "GraphQL", "historical", regex=False
        )

    df.to_csv(path, index=False)
    print(f"[FINAL_LANGUAGE_PASS] {path.name} rows={len(df)}")

print("[FINAL_LANGUAGE_PASS] COMPLETE")
