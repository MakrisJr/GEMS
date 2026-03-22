import pandas as pd

DATA_PATH = "results/predicted_ranked_scenarios.csv"
OUT_TXT = "results/top_region_summary.txt"
TOP_K = 10

df = pd.read_csv(DATA_PATH)
top = df.head(TOP_K).copy()

num_cols = [
    "glucose",
    "ammonium",
    "phosphate",
    "sulfate",
    "temperature",
    "pH",
    "growth",
    "biomass_flux_mean",
    "biomass_yield",
    "byproduct_total",
    "overall_rank_score",
]

lines = []
lines.append(f"Top-{TOP_K} region summary\n")

for col in num_cols:
    med = top[col].median()
    lo = top[col].min()
    hi = top[col].max()
    lines.append(f"{col}: median={med:.4f}, range=[{lo:.4f}, {hi:.4f}]")

mixing_counts = top["mixing"].value_counts(dropna=False)
lines.append("\nMixing distribution:")
for k, v in mixing_counts.items():
    lines.append(f"{k}: {v}")

summary_text = "\n".join(lines)

with open(OUT_TXT, "w") as f:
    f.write(summary_text)

print(summary_text)
print(f"\n[INFO] saved -> {OUT_TXT}")