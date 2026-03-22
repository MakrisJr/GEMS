import pandas as pd

df = pd.read_csv("results/dataset.csv")

if df.empty:
    raise RuntimeError("results/dataset.csv is empty")

cols = [
    "scenario",
    "search_stage",
    "glucose",
    "ammonium",
    "phosphate",
    "sulfate",
    "temperature",
    "pH",
    "mixing",
    "growth",
    "biomass_flux_mean",
    "biomass_yield",
    "byproduct_total",
    "log_volume",
    "overall_rank_score",
]

missing = [c for c in cols if c not in df.columns]
if missing:
    raise RuntimeError(f"Missing columns in dataset.csv: {missing}")

ranked = df[cols].sort_values("overall_rank_score", ascending=False).reset_index(drop=True)
ranked.to_csv("results/predicted_ranked_scenarios.csv", index=False)

print("[INFO] saved -> results/predicted_ranked_scenarios.csv")
print(ranked.head(10).to_string(index=False))