#!/usr/bin/env python3
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

df = pd.read_csv(os.path.join(RESULTS_DIR, "predicted_ranked_scenarios.csv"))

required = [
    "scenario",
    "growth",
    "log_volume",
    "byproduct_mean",
    "pred",
]
missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns: {missing}")


def add_fit_line(ax, x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) >= 2 and np.std(x) > 1e-12:
        m, b = np.polyfit(x, y, 1)
        xs = np.linspace(np.min(x), np.max(x), 100)
        ax.plot(xs, m * xs + b)


def annotate_points(ax, x, y, labels):
    for xi, yi, lab in zip(x, y, labels):
        ax.annotate(
            str(lab),
            (xi, yi),
            fontsize=8,
            xytext=(4, 3),
            textcoords="offset points"
        )


# --------------------------------------------------
# Correlations
# --------------------------------------------------
corr_volume = df["log_volume"].corr(df["growth"])
corr_byprod = df["byproduct_mean"].corr(df["growth"])
corr_pred = df["pred"].corr(df["growth"])

print(f"[INFO] corr(log_volume, growth) = {corr_volume:.4f}")
print(f"[INFO] corr(byproduct_mean, growth) = {corr_byprod:.4f}")
print(f"[INFO] corr(pred, growth) = {corr_pred:.4f}")


# --------------------------------------------------
# 3-panel figure
# --------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(17, 5))

# 1) Geometry vs growth
ax = axes[0]
ax.scatter(df["log_volume"], df["growth"])
add_fit_line(ax, df["log_volume"], df["growth"])
annotate_points(ax, df["log_volume"], df["growth"], df["scenario"])
ax.set_xlabel("Feasible Metabolic Space (log-volume)")
ax.set_ylabel("Growth")
ax.set_title(f"Geometry vs Growth\nr = {corr_volume:.2f}")

# 2) Byproduct vs growth
ax = axes[1]
ax.scatter(df["byproduct_mean"], df["growth"])
add_fit_line(ax, df["byproduct_mean"], df["growth"])
annotate_points(ax, df["byproduct_mean"], df["growth"], df["scenario"])
ax.set_xlabel("Metabolic Waste Production")
ax.set_ylabel("Growth")
ax.set_title(f"Byproduct Pressure vs Growth\nr = {corr_byprod:.2f}")

# 3) Predicted vs actual
ax = axes[2]
ax.scatter(df["pred"], df["growth"])
annotate_points(ax, df["pred"], df["growth"], df["scenario"])

lo = min(df["pred"].min(), df["growth"].min())
hi = max(df["pred"].max(), df["growth"].max())
ax.plot([lo, hi], [lo, hi], linestyle="--")
ax.set_xlabel("Predicted Growth")
ax.set_ylabel("Actual Growth")
ax.set_title(f"ML Validation\nr = {corr_pred:.2f}")

plt.tight_layout()
plt.savefig(os.path.join(RESULTS_DIR, "final_3panel_figure.png"), dpi=250)
plt.close()


# --------------------------------------------------
# Individual high-quality plots
# --------------------------------------------------
# Geometry vs growth
fig, ax = plt.subplots(figsize=(6.5, 5))
ax.scatter(df["log_volume"], df["growth"])
add_fit_line(ax, df["log_volume"], df["growth"])
annotate_points(ax, df["log_volume"], df["growth"], df["scenario"])
ax.set_xlabel("Feasible Metabolic Space (log-volume)")
ax.set_ylabel("Growth")
ax.set_title(f"Geometry vs Growth (r = {corr_volume:.2f})")
plt.tight_layout()
plt.savefig(os.path.join(RESULTS_DIR, "plot_geometry_vs_growth.png"), dpi=250)
plt.close()

# Byproduct vs growth
fig, ax = plt.subplots(figsize=(6.5, 5))
ax.scatter(df["byproduct_mean"], df["growth"])
add_fit_line(ax, df["byproduct_mean"], df["growth"])
annotate_points(ax, df["byproduct_mean"], df["growth"], df["scenario"])
ax.set_xlabel("Metabolic Waste Production")
ax.set_ylabel("Growth")
ax.set_title(f"Byproduct Pressure vs Growth (r = {corr_byprod:.2f})")
plt.tight_layout()
plt.savefig(os.path.join(RESULTS_DIR, "plot_byproduct_vs_growth.png"), dpi=250)
plt.close()

# Predicted vs actual
fig, ax = plt.subplots(figsize=(6.5, 5))
ax.scatter(df["pred"], df["growth"])
annotate_points(ax, df["pred"], df["growth"], df["scenario"])
ax.plot([lo, hi], [lo, hi], linestyle="--")
ax.set_xlabel("Predicted Growth")
ax.set_ylabel("Actual Growth")
ax.set_title(f"Predicted vs Actual Growth (r = {corr_pred:.2f})")
plt.tight_layout()
plt.savefig(os.path.join(RESULTS_DIR, "plot_predicted_vs_actual.png"), dpi=250)
plt.close()

print("[INFO] Saved:")
print(" - results/final_3panel_figure.png")
print(" - results/plot_geometry_vs_growth.png")
print(" - results/plot_byproduct_vs_growth.png")
print(" - results/plot_predicted_vs_actual.png")