from datetime import datetime
import pandas as pd

out = pd.DataFrame([{
    "built_at": datetime.utcnow().isoformat(),
    "probability_model_status":
        "TEMPERATURE6_CONFIRMED",

    "market_benchmark_status":
        "BLOCKED",

    "market_benchmark_reason":
        "Historical market prices incomplete and distorted",

    "current_production_probability":
        "TEMPERATURE6",

    "current_production_status":
        "NO_CHANGE_REQUIRED"
}])

out.to_csv(
    r".\public\data\edgeiq_probability_benchmark_status_v1.csv",
    index=False
)

print(out.to_string(index=False))
