"""Validate and ingest new wet-lab results into the combined dataset."""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Tuple, List
from .config import *
from .data_loader import load_combined, save_combined, validate_upload_schema
from .feature_engineering import load_pipeline


def _rename_observed_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map 'observed_*' column names from the lab template to standard names."""
    rename_map = {
        "observed_growth_rate_h_inv": TARGET_GROWTH,
        "observed_biomass_g_L":       TARGET_BIOMASS,
        "observed_byproducts_g_L":    TARGET_BYPRODUCTS,
    }
    return df.rename(columns=rename_map)


def _compute_composite_score(df: pd.DataFrame) -> pd.DataFrame:
    """Recompute overall_rank_score for newly ingested rows using min-max normalisation
    (relative to the full combined dataset, including synthetic).
    Falls back to self-normalisation if the combined dataset cannot be loaded."""
    try:
        combined = load_combined()
        ref = pd.concat([combined, df], ignore_index=True)
    except Exception:
        # Fallback: normalise against the new rows only
        ref = df.copy()

    for col, norm_col in [
        (TARGET_GROWTH,     "growth_norm"),
        (TARGET_BIOMASS,    "biomass_norm"),
        (TARGET_BYPRODUCTS, "byproduct_norm"),
    ]:
        lo  = ref[col].min()
        hi  = ref[col].max()
        rng = hi - lo if hi != lo else 1.0
        df[norm_col] = (df[col] - lo) / rng

    df[TARGET_SCORE] = (
        df["growth_norm"] + df["biomass_norm"] - df["byproduct_norm"]
    )
    return df


def ingest_results(
    upload_df: pd.DataFrame,
    current_round: int,
) -> Tuple[bool, str, pd.DataFrame]:
    """
    Full ingestion pipeline:
    1. Rename observed -> standard column names
    2. Validate schema
    3. Mark as real, set retrain_round
    4. Recompute composite score
    5. Append to combined dataset and save

    Returns (success, message, updated_combined_df)
    """
    df = upload_df.copy()
    df = _rename_observed_columns(df)

    valid, missing = validate_upload_schema(df)
    if not valid:
        return False, f"Missing required columns: {missing}", pd.DataFrame()

    df[IS_SYNTHETIC_COL] = False
    df[ROUND_COL] = current_round

    # Generate experiment IDs for new rows
    if "experiment_id" not in df.columns:
        df["experiment_id"] = [
            f"REAL{current_round:02d}_{i:04d}" for i in range(len(df))
        ]

    # Ensure date column exists
    if "experiment_date" not in df.columns:
        df["experiment_date"] = datetime.utcnow().strftime("%Y-%m-%d")

    # Recompute composite score
    df = _compute_composite_score(df)

    # Drop helper columns
    for c in ["growth_norm", "biomass_norm", "byproduct_norm"]:
        if c in df.columns:
            df.drop(columns=[c], inplace=True)

    # Append and save
    combined = load_combined()
    updated  = pd.concat([combined, df], ignore_index=True)
    save_combined(updated)

    msg = f"Successfully ingested {len(df)} rows (round {current_round}). Combined dataset now has {len(updated)} rows."
    return True, msg, updated
