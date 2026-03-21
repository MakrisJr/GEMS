"""Load, validate, and merge datasets."""
import pandas as pd
from pathlib import Path
from typing import Tuple, Optional
from .config import *


def load_synthetic() -> pd.DataFrame:
    """Load the base synthetic dataset."""
    df = pd.read_csv(SYNTHETIC_CSV)
    df[IS_SYNTHETIC_COL] = True
    if ROUND_COL not in df.columns:
        df[ROUND_COL] = 0
    return df


def load_combined() -> pd.DataFrame:
    """Load the combined dataset (synthetic + any uploaded real data).
    Falls back to synthetic-only if no combined file exists."""
    if COMBINED_CSV.exists():
        return pd.read_csv(COMBINED_CSV)
    return load_synthetic()


def save_combined(df: pd.DataFrame) -> None:
    """Persist the combined dataset."""
    df.to_csv(COMBINED_CSV, index=False)


def get_dataset_stats(df: pd.DataFrame) -> dict:
    """Return summary statistics for display."""
    return {
        "total_rows": len(df),
        "synthetic_rows": int(df[IS_SYNTHETIC_COL].sum()),
        "real_rows": int((~df[IS_SYNTHETIC_COL]).sum()),
        "strains": df["strain_name"].value_counts().to_dict(),
        "retrain_rounds": int(df[ROUND_COL].max()) if ROUND_COL in df.columns else 0,
    }


def validate_upload_schema(df: pd.DataFrame) -> Tuple[bool, list]:
    """Check that an uploaded CSV has the minimum required columns.
    Requires ALL_FEATURES + the three observed outcome columns.
    Does NOT require overall_rank_score since ingestion computes it.
    Returns (is_valid, list_of_missing_columns)."""
    required = ALL_FEATURES + [TARGET_GROWTH, TARGET_BIOMASS, TARGET_BYPRODUCTS]
    missing = [c for c in required if c not in df.columns]
    return len(missing) == 0, missing
