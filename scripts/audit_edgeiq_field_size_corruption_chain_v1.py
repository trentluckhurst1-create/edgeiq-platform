import pandas as pd

files = [
    r".\public\data\edgeiq_historical_replay_settled_v1.csv",
    r".\public\data\edgeiq_pricing_replay_spine_v2.csv",
    r".\public\data\edgeiq_pricing_replay_spine_v3_1_reconstructed.csv",
    r".\public\data\edgeiq_pricing_replay_spine_v3_2_reconstructed_normalised.csv",
    r".\public\data\edgeiq_pricing_replay_spine_v3_3_temperature6.csv"
]

for f in files:
    print("")
    print("=" * 100)
    print(f)

    try:
        df = pd.read_csv(f, nrows=5, low_memory=False)

        print("")
        print("columns:")
        print(df.columns.tolist())

        if "field_size" in df.columns:
            x = pd.read_csv(
                f,
                usecols=["field_size"],
                low_memory=False
            )

            print("")
            print("field_size distribution:")
            print(
                pd.to_numeric(
                    x["field_size"],
                    errors="coerce"
                )
                .value_counts(dropna=False)
                .sort_index()
                .head(25)
                .to_string()
            )
        else:
            print("")
            print("NO FIELD_SIZE COLUMN")

    except Exception as e:
        print(e)
