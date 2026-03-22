import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

DATA_PATH = "results/dataset_postprocessed.csv"
OUT_PATH = "results/plot_industrial_tradeoff.png"
TOP_K = 10

df = pd.read_csv(DATA_PATH)

if df.empty:
    raise RuntimeError("dataset_postprocessed.csv is empty")

# sort by industrial score
df = df.sort_values("industrial_score", ascending=False).reset_index(drop=True)
df["is_top"] = False
df.loc[:TOP_K-1, "is_top"] = True

# choose coloring variable
COLOR_BY = "byproduct_total"   # change to "economic_score" if you want

cvals = df[COLOR_BY].values

plt.figure(figsize=(8, 6))

# base points
sc = plt.scatter(
    df["growth"],
    df["industrial_score"],
    c=cvals,
    alpha=0.7
)

# highlight top
top = df[df["is_top"]]
plt.scatter(
    top["growth"],
    top["industrial_score"],
    s=120,
    edgecolors="black"
)

# annotate top points
for _, row in top.iterrows():
    plt.text(
        row["growth"],
        row["industrial_score"],
        str(int(row["scenario"])),
        fontsize=9
    )

# colorbar
cbar = plt.colorbar(sc)
cbar.set_label(COLOR_BY)

plt.figure(figsize=(8, 6))

# scatter (all points)
sc = plt.scatter(
    df["growth"],
    df["industrial_score"],
    c=cvals,
    alpha=0.7
)

# highlight top
top = df[df["is_top"]]
plt.scatter(
    top["growth"],
    top["industrial_score"],
    s=120,
    edgecolors="black"
)

# annotate top points
for _, row in top.iterrows():
    plt.text(
        row["growth"],
        row["industrial_score"],
        str(int(row["scenario"])),
        fontsize=9
    )

# 🔥 ADD THIS PART (trend line)
z = np.polyfit(df["growth"], df["industrial_score"], 1)
p = np.poly1d(z)

x_sorted = np.sort(df["growth"].values)
plt.plot(
    x_sorted,
    p(x_sorted),
    linestyle="--",
    alpha=0.6,
    linewidth=2,
    label="Trend"
)

# colorbar
cbar = plt.colorbar(sc)
cbar.set_label(COLOR_BY)

plt.xlabel("Growth")
plt.ylabel("Industrial Score")
plt.title(f"Industrial Tradeoff: Growth vs Industrial Score (colored by {COLOR_BY})")

plt.legend()
plt.grid(alpha=0.2)
plt.tight_layout()

plt.savefig(OUT_PATH, dpi=200)
print(f"[INFO] saved -> {OUT_PATH}")


