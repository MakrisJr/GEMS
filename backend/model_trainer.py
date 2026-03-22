"""Train, evaluate, and persist regression models."""
import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score, KFold
from sklearn.metrics import r2_score, mean_absolute_error
import xgboost as xgb
import lightgbm as lgb
from typing import Dict, Tuple, Any, Optional
from .config import *
from .data_loader import load_combined
from .feature_engineering import fit_and_save_pipeline, transform_features, compute_sample_weights

MODEL_TYPES = ["random_forest", "xgboost", "lightgbm"]


def _make_model(model_type: str):
    if model_type == "random_forest":
        return RandomForestRegressor(**RF_PARAMS)
    elif model_type == "xgboost":
        return xgb.XGBRegressor(**XGB_PARAMS)
    elif model_type == "lightgbm":
        return lgb.LGBMRegressor(**LGB_PARAMS)
    raise ValueError(f"Unknown model type: {model_type}")


def train_all(
    df: Optional[pd.DataFrame] = None,
    current_round: int = 0,
) -> Dict[str, Any]:
    """
    Full training pipeline:
    1. Load data (or use provided df)
    2. Fit feature pipeline
    3. Train 3 model types x 4 targets
    4. Cross-validate and pick best model per target
    5. Save everything to a timestamped model directory
    Returns a metadata dict with CV scores and paths.
    """
    if df is None:
        df = load_combined()

    encoders, scaler = fit_and_save_pipeline(df)
    X = transform_features(df, encoders, scaler)
    sample_weights = compute_sample_weights(df, current_round)

    run_id   = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    model_dir = MODELS_DIR / f"run_{run_id}"
    model_dir.mkdir(parents=True, exist_ok=True)

    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    results = {}

    for target in ALL_TARGETS:
        y = df[target].fillna(0).values
        best_score = -np.inf
        best_type  = None
        cv_scores  = {}

        for mtype in MODEL_TYPES:
            model = _make_model(mtype)
            # CV without sample weights for unbiased scoring
            scores = cross_val_score(model, X, y, cv=cv, scoring="r2")
            cv_scores[mtype] = float(np.mean(scores))
            if cv_scores[mtype] > best_score:
                best_score = cv_scores[mtype]
                best_type  = mtype

        # Refit best model on full data with sample weights
        best_model = _make_model(best_type)
        if best_type in ("xgboost", "lightgbm"):
            best_model.fit(X, y, sample_weight=sample_weights)
        else:
            best_model.fit(X, y, sample_weight=sample_weights)

        model_path = model_dir / f"{target}.pkl"
        joblib.dump(best_model, model_path)

        # Also always keep a RandomForest for uncertainty estimation
        rf = RandomForestRegressor(**RF_PARAMS)
        rf.fit(X, y, sample_weight=sample_weights)
        rf_path = model_dir / f"{target}_rf_uncertainty.pkl"
        joblib.dump(rf, rf_path)

        y_pred = best_model.predict(X)
        results[target] = {
            "best_model_type": best_type,
            "cv_r2_scores": cv_scores,
            "best_cv_r2": best_score,
            "train_r2": float(r2_score(y, y_pred)),
            "train_mae": float(mean_absolute_error(y, y_pred)),
            "model_path": str(model_path),
            "rf_uncertainty_path": str(rf_path),
        }

    # Save metadata
    metadata = {
        "run_id": run_id,
        "timestamp": datetime.utcnow().isoformat(),
        "n_samples": len(df),
        "retrain_round": current_round,
        "targets": results,
    }
    with open(model_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    # Write a "latest" pointer
    latest_ptr = MODELS_DIR / "latest.json"
    with open(latest_ptr, "w") as f:
        json.dump({"run_dir": str(model_dir)}, f)

    return metadata


def load_latest_models() -> Tuple[Dict, str]:
    """Load all models from the latest training run.
    Returns (models_dict, run_dir_str).
    models_dict keys: target names, values: {"model": ..., "rf_uncertainty": ...}
    """
    latest_ptr = MODELS_DIR / "latest.json"
    if not latest_ptr.exists():
        raise FileNotFoundError("No trained models found. Please train first.")
    with open(latest_ptr) as f:
        run_dir = Path(json.load(f)["run_dir"])

    models = {}
    for target in ALL_TARGETS:
        mpath = run_dir / f"{target}.pkl"
        rfpath = run_dir / f"{target}_rf_uncertainty.pkl"
        if not mpath.exists():
            raise FileNotFoundError(f"Model file missing: {mpath}")
        models[target] = {
            "model": joblib.load(mpath),
            "rf_uncertainty": joblib.load(rfpath) if rfpath.exists() else None,
        }
    return models, str(run_dir)


def get_training_metadata() -> dict:
    """Return metadata from the latest training run, or None if not trained."""
    latest_ptr = MODELS_DIR / "latest.json"
    if not latest_ptr.exists():
        return None
    with open(latest_ptr) as f:
        run_dir = Path(json.load(f)["run_dir"])
    meta_path = run_dir / "metadata.json"
    if not meta_path.exists():
        return None
    with open(meta_path) as f:
        return json.load(f)


def _extract_feature_importance(model) -> Tuple[Optional[np.ndarray], Optional[str]]:
    """Return model-native feature importance values and a short type label."""
    if hasattr(model, "feature_importances_"):
        values = np.asarray(model.feature_importances_, dtype=float).ravel()
        return values, "feature_importance"

    if hasattr(model, "coef_"):
        values = np.asarray(model.coef_, dtype=float).ravel()
        return values, "coefficient"

    return None, None


def get_latest_feature_importances() -> Dict[str, Any]:
    """
    Return feature-importance data for the latest trained models.

    Output shape:
      {
        target_name: {
          "model_type": str,
          "importance_type": str,
          "features": [{"feature": str, "importance": float}, ...]
        },
        ...
      }
    """
    metadata = get_training_metadata()
    if metadata is None:
        return {}

    models, _ = load_latest_models()
    feature_names = list(ALL_FEATURES)
    feature_payload = {}

    for target in ALL_TARGETS:
        model_info = models.get(target, {})
        model = model_info.get("model")
        if model is None:
            continue

        values, importance_type = _extract_feature_importance(model)
        if values is None:
            continue

        n_features = min(len(feature_names), len(values))
        rows = [
            {"feature": feature_names[idx], "importance": float(values[idx])}
            for idx in range(n_features)
        ]
        rows.sort(key=lambda row: abs(row["importance"]), reverse=True)

        feature_payload[target] = {
            "model_type": metadata["targets"].get(target, {}).get("best_model_type", "unknown"),
            "importance_type": importance_type,
            "features": rows,
        }

    return feature_payload
