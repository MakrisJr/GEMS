#!/usr/bin/env python3
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

df = pd.read_csv("results/dataset.csv")

# improved biologically interpretable feature set
X = df[[
    "log_volume",
    "anisotropy_log",
    "flux_std",
    "biomass_std",
    "byproduct_mean"
]]

y = df["growth"]

model = RandomForestRegressor(random_state=42)
model.fit(X, y)

df["pred"] = model.predict(X)
df = df.sort_values("pred", ascending=False)

print("Feature importance:", model.feature_importances_)

df.to_csv("results/predicted_ranked_scenarios.csv", index=False)

print(df.head(10))