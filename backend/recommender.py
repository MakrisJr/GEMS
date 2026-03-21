"""Generate top-N condition recommendations for a given strain."""
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from .config import *
from .data_loader import load_combined
from .feature_engineering import load_pipeline, transform_features, encode_features
from .model_trainer import load_latest_models


# Value ranges for candidate generation (sampled from training data distribution)
def _build_candidate_grid(df: pd.DataFrame, strain_name: str, n: int = N_CANDIDATES) -> pd.DataFrame:
    """Sample random candidate conditions for a strain using observed value ranges."""
    rng = np.random.default_rng(42)

    candidates = {}
    # Fix strain
    candidates["strain_name"] = [strain_name] * n

    # Categorical features: sample from observed values
    for col in CATEGORICAL_FEATURES:
        if col == "strain_name":
            continue
        vals = df[col].dropna().unique()
        candidates[col] = rng.choice(vals, size=n)

    # Numeric features: sample uniformly within [min, max] of training data
    for col in NUMERIC_FEATURES:
        lo = df[col].min()
        hi = df[col].max()
        candidates[col] = rng.uniform(lo, hi, size=n)

    return pd.DataFrame(candidates)


def _rf_uncertainty(rf_model, X: np.ndarray) -> np.ndarray:
    """Compute per-sample prediction std across RF trees (uncertainty proxy)."""
    tree_preds = np.array([t.predict(X) for t in rf_model.estimators_])
    return tree_preds.std(axis=0)


def recommend(
    strain_name: str,
    top_n: int = TOP_N,
    n_explore: int = N_EXPLORE,
) -> Dict[str, Any]:
    """
    Generate top-N exploit + N explore condition recommendations.

    Returns dict with keys:
      - exploit: list of top_n dicts (conditions + predicted outcomes + uncertainty)
      - explore: list of n_explore dicts
      - strain: strain_name
    """
    df = load_combined()
    encoders, scaler = load_pipeline()
    models, run_dir = load_latest_models()

    # Generate candidate conditions
    candidates = _build_candidate_grid(df, strain_name, N_CANDIDATES)

    # Encode and scale
    X_cand = transform_features(candidates, encoders, scaler)

    # Predict all targets
    preds = {}
    uncertainties = {}
    for target in ALL_TARGETS:
        m = models[target]["model"]
        preds[target] = m.predict(X_cand)
        rf = models[target]["rf_uncertainty"]
        if rf is not None:
            uncertainties[target] = _rf_uncertainty(rf, X_cand)
        else:
            uncertainties[target] = np.zeros(len(candidates))

    score_pred = preds[TARGET_SCORE]
    score_unc  = uncertainties[TARGET_SCORE]

    # --- EXPLOIT: top_n by predicted score ---
    top_idx = np.argsort(score_pred)[::-1][:top_n]

    # --- EXPLORE: highest uncertainty at >= 90th percentile score ---
    threshold = np.percentile(score_pred, 90)
    explore_mask = score_pred >= threshold
    explore_candidates = np.where(explore_mask)[0]
    if len(explore_candidates) > 0:
        best_explore_idx = explore_candidates[np.argmax(score_unc[explore_candidates])]
        explore_idx = [best_explore_idx]
    else:
        explore_idx = [np.argmax(score_unc)]

    def _row_to_dict(idx: int, rank: int, run_type: str) -> dict:
        row = candidates.iloc[idx].to_dict()
        row["rank"] = rank
        row["run_type"] = run_type
        row["predicted_growth_rate"] = float(preds[TARGET_GROWTH][idx])
        row["predicted_biomass"]      = float(preds[TARGET_BIOMASS][idx])
        row["predicted_byproducts"]   = float(preds[TARGET_BYPRODUCTS][idx])
        row["predicted_score"]        = float(score_pred[idx])
        row["uncertainty_score"]      = float(score_unc[idx])
        row["uncertainty_growth"]     = float(uncertainties[TARGET_GROWTH][idx])
        row["uncertainty_biomass"]    = float(uncertainties[TARGET_BIOMASS][idx])
        row["uncertainty_byproducts"] = float(uncertainties[TARGET_BYPRODUCTS][idx])
        return row

    exploit_recs = [_row_to_dict(i, rank+1, "exploit") for rank, i in enumerate(top_idx)]
    explore_recs = [_row_to_dict(i, top_n+rank+1, "explore") for rank, i in enumerate(explore_idx)]

    return {
        "strain": strain_name,
        "exploit": exploit_recs,
        "explore": explore_recs,
        "run_dir": run_dir,
        "n_candidates_evaluated": N_CANDIDATES,
    }
