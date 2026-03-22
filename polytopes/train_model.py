import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error

df = pd.read_csv("results/dataset.csv")

if df.empty:
    raise RuntimeError("results/dataset.csv is empty")

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

target_col = "overall_rank_score"

missing = [c for c in feature_cols + [target_col] if c not in df.columns]
if missing:
    raise RuntimeError(f"Missing columns in dataset.csv: {missing}")

X = df[feature_cols]
y = df[target_col]

cat_cols = ["mixing"]
num_cols = [c for c in feature_cols if c not in cat_cols]

pre = ColumnTransformer(
    [
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
        ("num", "passthrough", num_cols),
    ]
)

model = Pipeline(
    [
        (
            "pre",
            pre,
        ),
        (
            "rf",
            RandomForestRegressor(
                n_estimators=400,
                max_depth=10,
                random_state=42,
                n_jobs=-1,
            ),
        ),
    ]
)

if len(df) >= 10:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    print("[INFO] R2 =", r2_score(y_test, pred))
    print("[INFO] MAE =", mean_absolute_error(y_test, pred))
else:
    model.fit(X, y)
    print("[WARN] Very small dataset; trained on all rows without held-out test set.")

joblib.dump(model, "results/model.pkl")
print("[INFO] model saved -> results/model.pkl")