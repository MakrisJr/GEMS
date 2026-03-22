import numpy as np
import pandas as pd

DATA_PATH = "results/dataset.csv"
OUT_PATH = "results/dataset_postprocessed.csv"

df = pd.read_csv(DATA_PATH).copy()

if df.empty:
    raise RuntimeError("results/dataset.csv is empty")

# ----------------------------
# 1) Simple techno-economic layer
# ----------------------------
# Cheap placeholders for hackathon MVP:
# - substrate cost from uptake proxies
# - mixing cost penalty
# - low yield penalized
#
# You can change these coefficients later.
GLUCOSE_COST = 1.00
AMMONIUM_COST = 0.25
PHOSPHATE_COST = 0.15
SULFATE_COST = 0.10

MIXING_COST_MAP = {
    "low": 0.10,
    "medium": 0.20,
    "high": 0.35,
}

df["substrate_cost_proxy"] = (
    GLUCOSE_COST * df["glucose_uptake"].fillna(0.0) +
    AMMONIUM_COST * df["ammonium_uptake"].fillna(0.0) +
    PHOSPHATE_COST * df["phosphate_uptake"].fillna(0.0) +
    SULFATE_COST * df["sulfate_uptake"].fillna(0.0)
)

df["mixing_cost_proxy"] = df["mixing"].map(MIXING_COST_MAP).fillna(0.2)

# if biomass_yield is low, cost per useful biomass gets worse
df["economic_cost_proxy"] = (
    df["substrate_cost_proxy"] + df["mixing_cost_proxy"]
) / np.maximum(df["biomass_yield"], 1e-8)

# ----------------------------
# 2) Morphology proxy
# ----------------------------
# Based on your fungi notes:
# - low shear / low mixing -> larger mycelia / more fibrous
# - high shear / high mixing -> smaller pellets / less fibrous
# plus growth contributes positively
#
# very lightweight proxy, but pitchable.
MIXING_FIBROUSNESS = {
    "low": 1.00,
    "medium": 0.70,
    "high": 0.35,
}
df["mixing_fibrousness"] = df["mixing"].map(MIXING_FIBROUSNESS).fillna(0.7)

# pH penalty away from fungal-friendly region near ~5.5-6.5
df["pH_morph_penalty"] = np.abs(df["pH"] - 6.0)

# morphology proxy: higher growth helps structure, high mixing hurts, off-pH hurts
df["morphology_score_raw"] = (
    1.2 * df["growth"] +
    0.8 * df["mixing_fibrousness"] -
    0.25 * df["pH_morph_penalty"]
)

# ----------------------------
# 3) Meatiness proxy
# ----------------------------
# Your notes suggest meatiness uses growth + morphology metrics + composition-style proxies.
# Here we make a simple proxy:
# growth + biomass + morphology - byproducts
df["meatiness_score_raw"] = (
    1.0 * df["growth"] +
    0.8 * df["biomass_flux_mean"] +
    1.0 * df["morphology_score_raw"] -
    0.5 * df["byproduct_total"]
)

# ----------------------------
# 4) Normalization helpers
# ----------------------------
def norm01(s):
    s = pd.Series(s, dtype=float)
    lo = s.min()
    hi = s.max()
    if hi - lo < 1e-12:
        return pd.Series(np.ones(len(s)), index=s.index)
    return (s - lo) / (hi - lo)

df["economic_score"] = 1.0 - norm01(df["economic_cost_proxy"])   # lower cost = better
df["morphology_score"] = norm01(df["morphology_score_raw"])
df["meatiness_score"] = norm01(df["meatiness_score_raw"])

# ----------------------------
# 5) Updated industrial score
# ----------------------------
# Stronger industrial framing:
# growth + biomass + yield + meatiness + economics - byproducts
df["industrial_score"] = (
    0.25 * norm01(df["growth"]) +
    0.15 * norm01(df["biomass_flux_mean"]) +
    0.15 * norm01(df["biomass_yield"]) +
    0.20 * df["economic_score"] +
    0.15 * df["morphology_score"] +
    0.10 * df["meatiness_score"] -
    0.20 * norm01(df["byproduct_total"])
)

df = df.sort_values("industrial_score", ascending=False).reset_index(drop=True)
df.to_csv(OUT_PATH, index=False)

print("[INFO] saved ->", OUT_PATH)
print(df[[
    "scenario", "growth", "biomass_yield", "byproduct_total",
    "economic_score", "morphology_score", "meatiness_score", "industrial_score"
]].head(10).to_string(index=False))