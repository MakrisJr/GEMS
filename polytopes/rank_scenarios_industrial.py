import pandas as pd

DATA_PATH = "results/dataset_postprocessed.csv"
OUT_PATH = "results/predicted_ranked_scenarios_industrial.csv"

df = pd.read_csv(DATA_PATH)

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
    "economic_score",
    "morphology_score",
    "meatiness_score",
    "industrial_score",
]

ranked = df[cols].sort_values("industrial_score", ascending=False).reset_index(drop=True)
ranked.to_csv(OUT_PATH, index=False)

print("[INFO] saved ->", OUT_PATH)
print(ranked.head(10).to_string(index=False))