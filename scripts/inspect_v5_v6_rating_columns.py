import pandas as pd

for f in [
    ".\\public\\data\\edgeiq_historical_performance_rating_v5_1.csv",
    ".\\public\\data\\edgeiq_historical_performance_rating_v6_research.csv"
]:
    df = pd.read_csv(f, nrows=3, low_memory=False)
    print("\nFILE:", f)
    print(list(df.columns))
    print(df.head(1).to_string())
