import pandas as pd
import matplotlib.pyplot as plt

DATA_PATH = "results/dataset.csv"
OUT_PATH = "results/pareto_growth_vs_byproduct.png"
TOP_K = 10

df = pd.read_csv(DATA_PATH).copy()
df = df.sort_values("overall_rank_score", ascending=False).reset_index(drop=True)
df["is_top"] = False
df.loc[:TOP_K-1, "is_top"] = True

plt.figure(figsize=(7, 5))

base = df[~df["is_top"]]
top = df[df["is_top"]]

plt.scatter(base["byproduct_total"], base["growth"], alpha=0.7, label="All scenarios")
plt.scatter(top["byproduct_total"], top["growth"], s=90, label=f"Top {TOP_K}")

for idx, row in top.iterrows():
    plt.text(row["byproduct_total"], row["growth"], str(int(row["scenario"])), fontsize=9)

plt.xlabel("Byproduct Total")
plt.ylabel("Growth")
plt.title("Pareto View: Growth vs Byproduct Burden")
plt.legend()
plt.tight_layout()
plt.savefig(OUT_PATH, dpi=200)
print(f"[INFO] saved -> {OUT_PATH}")