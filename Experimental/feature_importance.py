import joblib
import pandas as pd
import numpy as np

MODEL_PATH = "results/model.pkl"
DATA_PATH = "results/dataset.csv"
OUT_PATH = "results/feature_importances.csv"

feature_cols = [
    "glucose",
    "ammonium",
    "phosphate",
    "sulfate",
    "temperature",
    "pH",
    "mixing",
    "log_volume",
    "anisotropy_log",
    "flux_std",
    "fva_range",
]

df = pd.read_csv(DATA_PATH)
model = joblib.load(MODEL_PATH)

pre = model.named_steps["pre"]
rf = model.named_steps["rf"]

feature_names = pre.get_feature_names_out(feature_cols)
importances = rf.feature_importances_

imp_df = pd.DataFrame({
    "feature": feature_names,
    "importance": importances
}).sort_values("importance", ascending=False).reset_index(drop=True)

imp_df.to_csv(OUT_PATH, index=False)

print("[INFO] saved ->", OUT_PATH)
print(imp_df.to_string(index=False))