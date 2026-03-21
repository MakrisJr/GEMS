"""Feature encoding, scaling, and preprocessing pipeline."""
import pandas as pd
import numpy as np
import joblib
from sklearn.preprocessing import LabelEncoder, StandardScaler
from typing import Tuple, Dict
from .config import *

ENCODERS_PATH = DATA_DIR / "intermediate" / "encoders.pkl"
SCALER_PATH   = DATA_DIR / "intermediate" / "scaler.pkl"


def build_encoders(df: pd.DataFrame) -> Dict[str, LabelEncoder]:
    """Fit a LabelEncoder for each categorical feature."""
    encoders = {}
    for col in CATEGORICAL_FEATURES:
        le = LabelEncoder()
        le.fit(df[col].astype(str).fillna("unknown"))
        encoders[col] = le
    return encoders


def build_scaler(df: pd.DataFrame, encoders: Dict) -> StandardScaler:
    """Fit a StandardScaler on all features after encoding categoricals."""
    X = encode_features(df, encoders)
    scaler = StandardScaler()
    scaler.fit(X)
    return scaler


def encode_features(df: pd.DataFrame, encoders: Dict) -> np.ndarray:
    """Encode categoricals and assemble the feature matrix (no scaling)."""
    parts = []
    for col in CATEGORICAL_FEATURES:
        le = encoders[col]
        vals = df[col].astype(str).fillna("unknown")
        # Handle unseen labels gracefully
        encoded = vals.map(lambda v: le.transform([v])[0] if v in le.classes_ else -1)
        parts.append(encoded.values.reshape(-1, 1))
    for col in NUMERIC_FEATURES:
        parts.append(df[col].fillna(df[col].median()).values.reshape(-1, 1))
    return np.hstack(parts)


def transform_features(df: pd.DataFrame, encoders: Dict, scaler: StandardScaler) -> np.ndarray:
    """Encode + scale features for model prediction."""
    X_raw = encode_features(df, encoders)
    return scaler.transform(X_raw)


def fit_and_save_pipeline(df: pd.DataFrame) -> Tuple[Dict, StandardScaler]:
    """Fit encoders + scaler on df; save to disk; return both."""
    encoders = build_encoders(df)
    scaler   = build_scaler(df, encoders)
    joblib.dump(encoders, ENCODERS_PATH)
    joblib.dump(scaler,   SCALER_PATH)
    return encoders, scaler


def load_pipeline() -> Tuple[Dict, StandardScaler]:
    """Load pre-fitted encoders and scaler from disk."""
    if not ENCODERS_PATH.exists() or not SCALER_PATH.exists():
        raise FileNotFoundError("Feature pipeline not found; train the model first.")
    return joblib.load(ENCODERS_PATH), joblib.load(SCALER_PATH)


def compute_sample_weights(df: pd.DataFrame, current_round: int = 0) -> np.ndarray:
    """Assign higher weight to real lab observations than synthetic rows."""
    weights = np.where(
        df[IS_SYNTHETIC_COL].values,
        SYNTHETIC_WEIGHT,
        REAL_WEIGHT_BASE * (1 + REAL_WEIGHT_SCALE * current_round)
    )
    return weights.astype(float)
