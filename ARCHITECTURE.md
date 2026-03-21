# GEMS — Growth Environment ML System
## Architecture Document

**Version:** 1.0  
**Date:** 2026-03-21  
**Purpose:** Complete specification for the ML-based fungal growth optimisation system. This document governs all implementation subtasks.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Complete File Tree](#2-complete-file-tree)
3. [Module Interfaces](#3-module-interfaces)
4. [Data Flow Diagram](#4-data-flow-diagram)
5. [Data Storage Strategy](#5-data-storage-strategy)
6. [Key Algorithms](#6-key-algorithms)
7. [Frontend Tabs Design](#7-frontend-tabs-design)
8. [Requirements.txt Content](#8-requirementstxt-content)
9. [Design Decisions Log](#9-design-decisions-log)

---

## 1. Project Overview

GEMS is a Streamlit-based ML application that:

1. Trains ensemble ML models on synthetic fungal growth data
2. Recommends optimised culture conditions per strain
3. Exports lab-ready Excel sheets for wet-lab validation
4. Ingests wet-lab results and retrains with adaptive sample weighting

### System Workflow

```
synthetic_data → train_ML_model → recommend_conditions → export_lab_sheet
                                                          ↓
                                           test_in_lab → upload_results
                                                          ↓
                                                       retrain → improve
```

### Four Target Strains

| Strain Name | Species | Assembly |
|---|---|---|
| Neurospora crassa OR74A | Neurospora crassa | NC12 |
| Rhizopus microsporus var. microsporus ATCC 52814 | Rhizopus microsporus var. microsporus | Rhimi_ATCC52814_1 |
| Aspergillus niger ATCC 13496 | Aspergillus niger | Aspni_bvT_1 |
| Aspergillus oryzae RIB40 | Aspergillus oryzae | ASM18445v3 |

---

## 2. Complete File Tree

```
GEMS/
├── frontend_app.py              # Single Streamlit app (5 tabs) — REPLACE existing
├── requirements.txt             # Updated dependency list
├── ARCHITECTURE.md              # This document
├── README.md                    # Project README (existing)
├── USAGE.md                     # Usage guide (existing)
├── .gitignore                   # (existing)
│
├── backend/
│   ├── __init__.py              # Package init (existing, keep)
│   ├── config.py                # Constants, paths, feature lists — NEW
│   ├── data_loader.py           # Load, validate, split synthetic/real — NEW
│   ├── feature_engineering.py   # Encode cats, scale numerics, composite score — NEW
│   ├── model_trainer.py         # Train RF/XGB/LGBM, cross-validate, save — NEW
│   ├── recommender.py           # Generate top-5+1 conditions per strain — NEW
│   ├── lab_exporter.py          # Generate Excel lab sheets — NEW
│   ├── data_ingestion.py        # Validate and ingest wet-lab CSV uploads — NEW
│   ├── retrainer.py             # Adaptive retraining with sample weights — NEW
│   │
│   # Files below are REPLACED (old pipeline is FastAPI/ModelSEED, not needed)
│   ├── main.py                  # REPLACE: was FastAPI; now empty or removed
│   └── pipeline_runner.py       # REPLACE: was CLI runner; now empty or removed
│
├── data/
│   ├── synthetic_fungal_growth_dataset.csv   # 720-row synthetic dataset (existing)
│   │
│   ├── raw/
│   │   ├── .gitkeep
│   │   └── uploads/             # Wet-lab CSV uploads land here
│   │       └── .gitkeep
│   │
│   ├── processed/               # Processed/feature-engineered parquet files
│   │   └── .gitkeep
│   │
│   ├── models/                  # Saved model artefacts (joblib)
│   │   └── .gitkeep
│   │
│   └── intermediate/            # Temporary files, scaler objects, encoders
│       └── .gitkeep
│
└── config/
    └── media_library.yml        # (existing, separate pipeline — keep)
```

> **Note on replacement files:** `backend/main.py` and `backend/pipeline_runner.py` are the old FastAPI/ModelSEED pipeline. They will be replaced with minimal stubs (`# Deprecated — see ARCHITECTURE.md`) so the package does not break on import, but all GEMS ML logic lives in the new modules.

---

## 3. Module Interfaces

All modules are pure Python. No FastAPI, no network calls. The Streamlit frontend imports the backend modules directly.

---

### 3.1 `backend/config.py`

Central registry for all constants, paths, and feature definitions.

```python
# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT: Path          # GEMS/ directory root
DATA_DIR: Path              # GEMS/data/
RAW_DIR: Path               # GEMS/data/raw/
UPLOADS_DIR: Path           # GEMS/data/raw/uploads/
PROCESSED_DIR: Path         # GEMS/data/processed/
MODELS_DIR: Path            # GEMS/data/models/
INTERMEDIATE_DIR: Path      # GEMS/data/intermediate/
SYNTHETIC_CSV: Path         # GEMS/data/synthetic_fungal_growth_dataset.csv

# ── Dataset Schema ─────────────────────────────────────────────────────────
METADATA_COLS: list[str]    # experiment_id, replicate_id, batch_id, experiment_date,
                             # is_synthetic, notes, rank_within_strain

CATEGORICAL_FEATURES: list[str]
# strain_name, species, assembly, culture_type, fermentation_type,
# reactor_scale, search_stage, carbon_source, nitrogen_source, mixing

NUMERIC_FEATURES: list[str]
# glucose_g_L, sucrose_g_L, maltose_g_L, total_carbon_g_L,
# ammonium_g_L, nitrate_g_L, yeast_extract_g_L, total_nitrogen_g_L,
# phosphate_g_L, sulfate_g_L, magnesium_g_L, calcium_g_L,
# trace_mix_x, vitamin_mix_x, pH, temperature_C, rpm, agar_percent,
# inoculum_g_L, incubation_time_h

BOOLEAN_FEATURES: list[str]    # feasible_growth (0/1 encoded)

TARGET_COLS: list[str]
# growth_rate_h_inv, biomass_g_L, total_byproducts_g_L, overall_rank_score

PRIMARY_TARGET: str         # "overall_rank_score"

# ── Composite Score ─────────────────────────────────────────────────────────
# The dataset already contains pre-computed normalised columns:
# growth_norm, biomass_norm, yield_norm, byproduct_penalty_norm, overall_rank_score
# overall_rank_score = growth_norm + biomass_norm + yield_norm - byproduct_penalty_norm
# See Section 6.1 for full formula.

# ── Model ───────────────────────────────────────────────────────────────────
MODEL_TYPES: list[str]      # ["random_forest", "xgboost", "lightgbm"]
CV_FOLDS: int               # 5
RANDOM_STATE: int           # 42

# ── Retraining ──────────────────────────────────────────────────────────────
REAL_DATA_BASE_WEIGHT: float  # 5.0  (real data weight multiplier vs synthetic)
WEIGHT_GROWTH_RATE: float     # 1.0  (grows with each retraining round)

# ── Recommendation ──────────────────────────────────────────────────────────
TOP_N_RECOMMENDATIONS: int    # 5
N_EXPLORATORY: int            # 1
GRID_SEARCH_N_SAMPLES: int    # 2000  (random samples from feature space per strain)
UNCERTAINTY_PERCENTILE: float # 90.0  (top-10% uncertainty = exploratory candidate)

# ── File names ──────────────────────────────────────────────────────────────
ENCODER_FILE: str           # "label_encoders.joblib"
SCALER_FILE: str            # "feature_scaler.joblib"
MODEL_FILE_TEMPLATE: str    # "{model_type}_model.joblib"
CV_RESULTS_FILE: str        # "cv_results.json"
TRAINING_LOG_FILE: str      # "training_log.json"
```

---

### 3.2 `backend/data_loader.py`

Responsible for loading, validating, and splitting dataset rows.

```python
def load_dataset(csv_path: Path | None = None) -> pd.DataFrame:
    """
    Load the main dataset CSV.
    Falls back to SYNTHETIC_CSV if csv_path is None.
    Validates that all expected columns are present.
    Returns DataFrame with correct dtypes.
    Raises: FileNotFoundError, ValueError (schema mismatch)
    """

def validate_schema(df: pd.DataFrame, required_cols: list[str] | None = None) -> bool:
    """
    Check that df contains all required columns.
    If required_cols is None, uses the full METADATA_COLS + CATEGORICAL_FEATURES
    + NUMERIC_FEATURES + TARGET_COLS list from config.
    Returns True on success, raises ValueError with a descriptive message on failure.
    """

def split_synthetic_real(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split df into synthetic rows (is_synthetic == True) and
    real wet-lab rows (is_synthetic == False).
    Returns: (synthetic_df, real_df)
    """

def get_strain_subset(df: pd.DataFrame, strain_name: str) -> pd.DataFrame:
    """
    Filter df to rows matching strain_name.
    Raises ValueError if strain_name not in known strains.
    """

def get_dataset_summary(df: pd.DataFrame) -> dict:
    """
    Return a summary dict with:
      - n_total: int
      - n_synthetic: int
      - n_real: int
      - strains: list of unique strain names
      - date_range: (min_date, max_date) strings
      - target_stats: dict of mean/std for each TARGET_COL
    """
```

---

### 3.3 `backend/feature_engineering.py`

Encodes categorical features and scales numeric features. Persists transformers for reuse at inference time.

```python
def build_feature_matrix(
    df: pd.DataFrame,
    fit: bool = True,
    encoders: dict | None = None,
    scaler: object | None = None,
) -> tuple[np.ndarray, dict, object]:
    """
    Build the model-ready feature matrix X from df.

    Steps:
      1. Label-encode each categorical column (fit new or use provided encoders)
      2. Cast boolean features to int (0/1)
      3. Standard-scale numeric + encoded features (fit new or use provided scaler)

    Args:
      df     : input dataframe
      fit    : if True, fit new encoders/scaler and return them
               if False, encoders and scaler must be provided
      encoders: dict mapping col_name -> fitted LabelEncoder
      scaler  : fitted StandardScaler

    Returns:
      (X: np.ndarray, encoders: dict, scaler: StandardScaler)

    The column order in X is: CATEGORICAL_FEATURES + BOOLEAN_FEATURES + NUMERIC_FEATURES
    (always in the same deterministic order defined in config.py)
    """

def extract_targets(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return the target columns (TARGET_COLS) as a DataFrame.
    """

def save_transformers(encoders: dict, scaler: object, save_dir: Path) -> None:
    """
    Persist encoders dict and scaler to save_dir using joblib.
    Files: ENCODER_FILE, SCALER_FILE from config.
    """

def load_transformers(save_dir: Path) -> tuple[dict, object]:
    """
    Load and return (encoders, scaler) from save_dir.
    Raises FileNotFoundError if files are missing.
    """

def encode_strain_name(strain_name: str, encoder: object) -> int:
    """
    Convenience: encode a single strain name using the fitted LabelEncoder.
    Raises ValueError if strain_name was not seen during fit.
    """
```

---

### 3.4 `backend/model_trainer.py`

Trains, cross-validates, and serialises the three model types.

```python
def build_models() -> dict[str, object]:
    """
    Instantiate the three model estimators with sensible defaults:
      - random_forest  : RandomForestRegressor(n_estimators=200, n_jobs=-1, random_state=RANDOM_STATE)
      - xgboost        : XGBRegressor(n_estimators=200, learning_rate=0.05, random_state=RANDOM_STATE)
      - lightgbm       : LGBMRegressor(n_estimators=200, learning_rate=0.05, random_state=RANDOM_STATE, verbose=-1)
    Returns dict[model_type_str -> estimator].
    """

def cross_validate_model(
    model: object,
    X: np.ndarray,
    y: np.ndarray,
    sample_weight: np.ndarray | None = None,
    cv: int = CV_FOLDS,
) -> dict:
    """
    Run stratified (time-series safe: KFold) cross-validation.
    Returns dict with:
      - mean_r2: float
      - std_r2: float
      - mean_mae: float
      - std_mae: float
      - mean_rmse: float
      - std_rmse: float
      - fold_scores: list[float]  (R2 per fold)
    """

def train_all_models(
    X: np.ndarray,
    y: np.ndarray,
    sample_weight: np.ndarray | None = None,
) -> tuple[dict[str, object], dict[str, dict]]:
    """
    Train all three models on (X, y).
    Run cross-validation for each.
    Returns:
      (trained_models: dict[name -> fitted_model],
       cv_results: dict[name -> cv_metrics_dict])
    """

def select_best_model(cv_results: dict[str, dict]) -> str:
    """
    Select the model_type string with the highest mean_r2.
    Returns: model type name string (e.g. "xgboost")
    """

def save_models(
    models: dict[str, object],
    cv_results: dict[str, dict],
    save_dir: Path,
) -> None:
    """
    Persist each model to save_dir using joblib.
    Also write cv_results to CV_RESULTS_FILE (JSON).
    Write training_log (timestamp, n_samples, n_real, best_model) to TRAINING_LOG_FILE.
    """

def load_models(save_dir: Path) -> tuple[dict[str, object], dict[str, dict]]:
    """
    Load all three models and cv_results from save_dir.
    Returns (models_dict, cv_results_dict).
    Raises FileNotFoundError if required files are missing.
    """

def models_exist(save_dir: Path) -> bool:
    """
    Return True if all three model files exist in save_dir.
    """

def get_training_log(save_dir: Path) -> dict | None:
    """
    Return the training log dict, or None if not found.
    """
```

---

### 3.5 `backend/recommender.py`

Generates recommendation candidates by grid-searching the feature space, then ranks by predicted composite score. Uncertainty is the std of individual tree predictions from RandomForest.

```python
def build_candidate_grid(
    strain_name: str,
    df_reference: pd.DataFrame,
    n_samples: int = GRID_SEARCH_N_SAMPLES,
    random_state: int = RANDOM_STATE,
) -> pd.DataFrame:
    """
    Generate a DataFrame of candidate conditions for a given strain.

    Strategy:
      - Fix strain_name, species, assembly to the strain's known values.
      - Fix culture_type, fermentation_type to "submerged" (most common).
      - For categorical features (reactor_scale, search_stage, carbon_source,
        nitrogen_source, mixing): sample uniformly from the observed values
        in df_reference for that strain.
      - For numeric features: sample uniformly between the min and max observed
        values in df_reference for that strain.
      - n_samples rows are generated.

    Returns: DataFrame with all CATEGORICAL_FEATURES + NUMERIC_FEATURES columns.
    """

def predict_candidates(
    candidates_df: pd.DataFrame,
    models: dict[str, object],
    encoders: dict,
    scaler: object,
    best_model_type: str,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Transform candidates_df through feature engineering, then predict.

    Returns:
      (predictions: np.ndarray shape [n_samples],
       uncertainties: np.ndarray shape [n_samples])

    Uncertainty calculation:
      - For the best model (if random_forest): collect predictions from each
        Decision Tree in the ensemble, compute std across trees per sample.
      - For XGBoost / LightGBM as best model: still use RandomForest uncertainty
        as the uncertainty proxy (RandomForest is always trained alongside).
    """

def select_top_recommendations(
    candidates_df: pd.DataFrame,
    predictions: np.ndarray,
    uncertainties: np.ndarray,
    top_n: int = TOP_N_RECOMMENDATIONS,
    n_exploratory: int = N_EXPLORATORY,
    uncertainty_percentile: float = UNCERTAINTY_PERCENTILE,
) -> pd.DataFrame:
    """
    Select the final recommendations.

    Steps:
      1. Rank all candidates by predicted score descending.
      2. Take top_n rows as exploitation recommendations.
      3. From the remaining candidates, select the one with highest uncertainty
         that is in the top uncertainty_percentile → 1 exploratory recommendation.
      4. Mark each row with a "recommendation_type" column:
         "exploitation" or "exploration".
      5. Add "predicted_score" and "uncertainty" columns.

    Returns: DataFrame with top_n + n_exploratory rows.
    """

def get_recommendations(
    strain_name: str,
    df_reference: pd.DataFrame,
    models: dict[str, object],
    encoders: dict,
    scaler: object,
    best_model_type: str,
    top_n: int = TOP_N_RECOMMENDATIONS,
    n_exploratory: int = N_EXPLORATORY,
) -> pd.DataFrame:
    """
    High-level convenience function.
    Calls build_candidate_grid → predict_candidates → select_top_recommendations.
    Returns the final recommendations DataFrame.
    """
```

---

### 3.6 `backend/lab_exporter.py`

Generates a multi-sheet Excel workbook ready for wet-lab use.

```python
def build_lab_sheet(
    recommendations_df: pd.DataFrame,
    strain_name: str,
    n_replicates: int = 3,
) -> bytes:
    """
    Build an Excel workbook in memory and return as bytes.

    Sheets:
      Sheet 1 — "Recommendations":
        Columns: rank, recommendation_type, predicted_score, uncertainty, +
                 all controllable input columns (carbon_source, nitrogen_source,
                 glucose_g_L, sucrose_g_L, maltose_g_L, total_carbon_g_L,
                 ammonium_g_L, nitrate_g_L, yeast_extract_g_L, total_nitrogen_g_L,
                 phosphate_g_L, sulfate_g_L, magnesium_g_L, calcium_g_L,
                 trace_mix_x, vitamin_mix_x, pH, temperature_C, mixing, rpm,
                 agar_percent, inoculum_g_L, incubation_time_h)

      Sheet 2 — "Condition Details":
        One row per condition (same as Sheet 1) but transposed for easy reading,
        with a "notes" column for the researcher.

      Sheet 3 — "Replicate Template":
        One row per replicate (n_replicates per condition).
        Columns: experiment_id (placeholder: EXP_001_R1 etc.), strain_name,
                 all input columns (copied from recommendation), + blank columns
                 for the researcher to fill in:
                 growth_rate_h_inv, biomass_g_L, total_byproducts_g_L,
                 overall_rank_score, notes, is_synthetic (should be FALSE)

    Args:
      recommendations_df : output of get_recommendations()
      strain_name        : used for filename metadata and sheet headers
      n_replicates       : number of replicate rows per condition in Sheet 3

    Returns: bytes of the Excel file (use with st.download_button)
    """

def get_lab_sheet_filename(strain_name: str) -> str:
    """
    Return a filesystem-safe filename for the export.
    E.g. "GEMS_lab_sheet_Neurospora_crassa_OR74A_20260321.xlsx"
    """
```

---

### 3.7 `backend/data_ingestion.py`

Validates and ingests uploaded wet-lab result CSV files.

```python
UPLOAD_REQUIRED_COLS: list[str]
# Minimum required columns for a valid wet-lab upload:
# strain_name, carbon_source, nitrogen_source, glucose_g_L, sucrose_g_L,
# maltose_g_L, total_carbon_g_L, ammonium_g_L, nitrate_g_L, yeast_extract_g_L,
# total_nitrogen_g_L, phosphate_g_L, sulfate_g_L, magnesium_g_L, calcium_g_L,
# trace_mix_x, vitamin_mix_x, pH, temperature_C, mixing, rpm, agar_percent,
# inoculum_g_L, incubation_time_h,
# growth_rate_h_inv, biomass_g_L, total_byproducts_g_L

def validate_upload(
    uploaded_df: pd.DataFrame,
) -> tuple[bool, list[str]]:
    """
    Validate the uploaded wet-lab DataFrame.

    Checks:
      1. All UPLOAD_REQUIRED_COLS are present.
      2. Numeric columns contain numeric values (no free text).
      3. strain_name values are in the known STRAINS list.
      4. No all-NaN rows.
      5. growth_rate_h_inv >= 0 for all rows.

    Returns:
      (is_valid: bool, error_messages: list[str])
    If is_valid is False, error_messages contains human-readable descriptions.
    """

def ingest_upload(
    uploaded_df: pd.DataFrame,
    existing_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Merge the validated uploaded data into the existing dataset.

    Steps:
      1. Set is_synthetic = False for all uploaded rows.
      2. Auto-generate experiment_id values (REAL_0001, REAL_0002, ...).
      3. Set experiment_date to today's date if not provided.
      4. Compute overall_rank_score using the composite score formula
         (re-normalising against the combined dataset).
      5. Append uploaded rows to existing_df and return the combined DataFrame.

    Returns: combined DataFrame (existing + new real rows)
    """

def save_ingested_data(
    combined_df: pd.DataFrame,
    save_path: Path | None = None,
) -> Path:
    """
    Save the combined DataFrame to CSV.
    Default save_path: UPLOADS_DIR / "combined_dataset_{timestamp}.csv"
    Returns the save path.
    """

def compute_composite_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    (Re-)compute normalised columns and overall_rank_score for all rows in df.
    Uses min-max normalisation across the full df.
    Adds/updates columns: growth_norm, biomass_norm, yield_norm,
    byproduct_penalty_norm, overall_rank_score.
    Returns the modified df.
    """
```

---

### 3.8 `backend/retrainer.py`

Adaptive retraining that up-weights real experimental data.

```python
def compute_sample_weights(
    df: pd.DataFrame,
    base_real_weight: float = REAL_DATA_BASE_WEIGHT,
    weight_growth_rate: float = WEIGHT_GROWTH_RATE,
    round_number: int = 1,
) -> np.ndarray:
    """
    Compute per-sample weights for training.

    Formula:
      synthetic samples → weight = 1.0
      real samples      → weight = base_real_weight * (1 + weight_growth_rate * round_number)

    The round_number is read from the TRAINING_LOG_FILE (increments by 1 each retrain).
    This makes real data progressively more influential over time.

    Returns: np.ndarray of shape [n_samples] matching df row order.
    """

def retrain(
    combined_df: pd.DataFrame,
    save_dir: Path | None = None,
    round_number: int | None = None,
) -> tuple[dict[str, object], dict[str, dict]]:
    """
    Full retraining pipeline on combined synthetic + real data.

    Steps:
      1. Load existing training log to determine round_number (if not provided).
      2. compute_sample_weights(combined_df, round_number=round_number).
      3. build_feature_matrix(combined_df, fit=True) → X, encoders, scaler.
      4. extract_targets(combined_df) → y (using PRIMARY_TARGET).
      5. train_all_models(X, y, sample_weight=weights).
      6. save_models + save_transformers to save_dir.
      7. Update training log (round_number += 1, n_real, timestamp).

    Returns: (trained_models, cv_results)
    """

def get_current_round(save_dir: Path) -> int:
    """
    Return the current retraining round number from the training log.
    Returns 1 if no log exists (first training).
    """
```

---

### 3.9 `frontend_app.py` (replacement)

Single Streamlit app with 5 tabs. Imports backend modules directly — no HTTP.

```python
# Key imports
from backend.config import *
from backend.data_loader import load_dataset, get_dataset_summary, split_synthetic_real
from backend.feature_engineering import build_feature_matrix, load_transformers
from backend.model_trainer import (load_models, models_exist, get_training_log,
                                    train_all_models, select_best_model, save_models)
from backend.recommender import get_recommendations
from backend.lab_exporter import build_lab_sheet, get_lab_sheet_filename
from backend.data_ingestion import validate_upload, ingest_upload, save_ingested_data
from backend.retrainer import retrain, get_current_round

# Session state keys:
#   st.session_state.df            : current working DataFrame
#   st.session_state.models        : loaded models dict
#   st.session_state.cv_results    : loaded CV results
#   st.session_state.encoders      : loaded encoders
#   st.session_state.scaler        : loaded scaler
#   st.session_state.best_model    : best model type string
#   st.session_state.recommendations : last recommendations DataFrame
```

See [Section 7](#7-frontend-tabs-design) for full tab specifications.

---

## 4. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GEMS DATA FLOW                                   │
└─────────────────────────────────────────────────────────────────────────┘

INPUTS:
  data/synthetic_fungal_growth_dataset.csv  (720 rows, is_synthetic=True)
  data/raw/uploads/*.csv                    (wet-lab results, is_synthetic=False)

──────────────────────── TRAINING PIPELINE ───────────────────────────────

  [data_loader.load_dataset]
         │
         │ raw DataFrame (720+ rows)
         ▼
  [data_loader.split_synthetic_real]
         │                    │
         │ synthetic_df        │ real_df (empty initially)
         └─────────┬───────────┘
                   │ combined_df
                   ▼
  [data_ingestion.compute_composite_score]
         │
         │ df with overall_rank_score
         ▼
  [retrainer.compute_sample_weights]
         │
         │ sample_weights array
         ▼
  [feature_engineering.build_feature_matrix(fit=True)]
         │
         │ X (feature matrix)   encoders   scaler
         ▼              └──────────────────────────►  data/intermediate/
  [model_trainer.train_all_models(X, y, weights)]
         │
         │ trained_models   cv_results
         ▼              └──────────────────────────►  data/models/
  [feature_engineering.save_transformers]
  [model_trainer.save_models]
         │
         │ artefacts on disk
         ▼
  [model_trainer.get_training_log update]

──────────────────────── RECOMMENDATION PIPELINE ─────────────────────────

  user selects strain_name in UI
         │
         ▼
  [recommender.build_candidate_grid(strain_name, df_reference, n_samples=2000)]
         │
         │ candidates_df (2000 rows)
         ▼
  [feature_engineering.build_feature_matrix(fit=False, encoders, scaler)]
         │
         │ X_candidates
         ▼
  [recommender.predict_candidates(X_candidates, models, best_model_type)]
         │
         │ predictions array   uncertainties array
         ▼
  [recommender.select_top_recommendations(top_n=5, n_exploratory=1)]
         │
         │ recommendations_df (6 rows)
         ▼
  [lab_exporter.build_lab_sheet]
         │
         │ Excel bytes → st.download_button

──────────────────────── RETRAINING PIPELINE ─────────────────────────────

  user uploads wet-lab CSV
         │
         ▼
  [data_ingestion.validate_upload]
         │ (error → UI warning, stop)
         ▼
  [data_ingestion.ingest_upload(uploaded_df, existing_df)]
         │
         │ combined_df (synthetic + real)
         ▼
  [data_ingestion.save_ingested_data]
         │
         ▼
  [retrainer.retrain(combined_df)]
         │  (compute_sample_weights → build_feature_matrix(fit=True)
         │   → train_all_models → save_models + save_transformers)
         ▼
  updated models + transformers on disk
         │
         ▼
  UI shows new CV metrics + training log diff
```

---

## 5. Data Storage Strategy

### 5.1 File-Based Storage (no database)

GEMS uses the local filesystem for all persistence — no SQLite, no PostgreSQL.

| Path | Content | Format |
|---|---|---|
| `data/synthetic_fungal_growth_dataset.csv` | Seed dataset (read-only) | CSV |
| `data/raw/uploads/combined_dataset_{ts}.csv` | Combined synthetic + real (appended after each upload) | CSV |
| `data/intermediate/label_encoders.joblib` | Fitted LabelEncoders per categorical col | joblib |
| `data/intermediate/feature_scaler.joblib` | Fitted StandardScaler | joblib |
| `data/models/random_forest_model.joblib` | Trained RandomForest | joblib |
| `data/models/xgboost_model.joblib` | Trained XGBoost | joblib |
| `data/models/lightgbm_model.joblib` | Trained LightGBM | joblib |
| `data/models/cv_results.json` | Cross-validation metrics for all 3 models | JSON |
| `data/models/training_log.json` | Training metadata (timestamp, round, n_real) | JSON |

### 5.2 Session State (Streamlit)

Heavy objects (loaded models, DataFrame) are cached in `st.session_state` to avoid re-loading on each UI interaction.

### 5.3 Version Strategy

Each upload/retrain creates a new timestamped combined CSV rather than overwriting. This preserves a full audit trail. The most recent file is used for retraining (determined by filename timestamp sort).

---

## 6. Key Algorithms

### 6.1 Composite Score Formula

The dataset already contains pre-computed normalised sub-scores. The formula is:

```
overall_rank_score = growth_norm + biomass_norm + yield_norm - byproduct_penalty_norm
```

Where:
- `growth_norm`           = min-max normalised `growth_rate_h_inv` (0–1)
- `biomass_norm`          = min-max normalised `biomass_g_L` (0–1)
- `yield_norm`            = min-max normalised `biomass_yield_g_per_g_carbon` (0–1), capped at 1
- `byproduct_penalty_norm`= min-max normalised `total_byproducts_g_L` (0–1)

Range of `overall_rank_score`: approximately −0.25 to +1.0 (can be negative when byproducts dominate).

When new real data is ingested, `compute_composite_score()` re-normalises **all rows** (synthetic + real) together to maintain consistent scaling.

### 6.2 Feature Engineering Pipeline

```
categorical cols → LabelEncoder (per-column, handles unseen via try/except)
boolean cols     → cast to int32 (True→1, False→0)
numeric cols     → StandardScaler (zero mean, unit variance)

Feature order in X (total ≈ 33 columns):
  [10 label-encoded categoricals]
  [1 boolean: feasible_growth]
  [22 scaled numerics]
```

The **same encoder+scaler** fitted at training time is used at inference (recommendation). This is why they are saved to `data/intermediate/`.

> **Critical:** `strain_name` is label-encoded as a numeric feature, enabling the global model to learn cross-strain patterns while treating strain identity as a learnable signal.

### 6.3 Recommendation Strategy (Grid Search + Ranking)

```
For a given strain_name:
  1. Fix strain identity columns.
  2. Sample 2,000 candidate conditions uniformly within observed ranges.
  3. Predict overall_rank_score for all 2,000 candidates using best model.
  4. Compute uncertainty for all 2,000 candidates using RandomForest std.
  5. Sort by predicted score descending.
  6. Top 5 → exploitation recommendations.
  7. From remaining candidates, pick the one with the highest uncertainty
     in the top-90th percentile → 1 exploration recommendation.
  8. Return all 6 with metadata columns.
```

**Deduplication:** If two candidates are within 5% of each other on all numeric features and have identical categoricals, keep only the higher-scored one.

### 6.4 Uncertainty Estimation

RandomForest prediction variance is used as uncertainty proxy:

```python
# For RandomForest model rf:
tree_preds = np.array([tree.predict(X) for tree in rf.estimators_])
# tree_preds shape: [n_trees, n_samples]
uncertainty = tree_preds.std(axis=0)  # shape: [n_samples]
```

This is computed **even when XGBoost or LightGBM is the best-performing model**. The RandomForest (which is always in the ensemble) is used solely for uncertainty estimation in that case.

### 6.5 Adaptive Sample Weighting (Retraining)

```
round 1: synthetic=1.0,  real=5.0   (5× emphasis)
round 2: synthetic=1.0,  real=10.0  (10× emphasis)
round 3: synthetic=1.0,  real=15.0  (15× emphasis)
...
round k: real = REAL_DATA_BASE_WEIGHT * (1 + WEIGHT_GROWTH_RATE * k)
```

This implements a **curriculum** where the model starts from synthetic data and gradually shifts trust to empirical measurements. The weighting is passed to `fit(X, y, sample_weight=weights)` for all three model types.

### 6.6 Cross-Validation Strategy

- **5-fold KFold** (not stratified — regression task)
- Metrics reported: R², MAE, RMSE
- Folds are fit-only on training split (no data leakage through scaler/encoder)
- The best model (by mean R²) is used for recommendations

---

## 7. Frontend Tabs Design

The Streamlit app has a single `main()` function with `st.tabs(["Data Overview", "Train Model", "Get Recommendations", "Export Lab Sheet", "Upload Results & Retrain"])`.

---

### Tab 1 — Data Overview

**Purpose:** Explore the dataset; understand what is synthetic vs real.

**UI Components:**
- `st.metric` row: Total rows | Synthetic | Real | Strains
- `st.selectbox` "Filter by strain" (All + 4 strain names)
- `st.dataframe` showing filtered dataset (paginated, 50 rows)
- `st.expander("Column statistics")` → `df.describe()` table for numeric cols
- Bar chart: `overall_rank_score` distribution per strain (using `st.bar_chart` or Plotly)
- Scatter plot: `growth_rate_h_inv` vs `biomass_g_L`, coloured by strain
- Info box: "Data is synthetic. Real lab data can be uploaded in Tab 5."

---

### Tab 2 — Train Model

**Purpose:** Trigger training; view cross-validation metrics and model comparison.

**UI Components:**
- Status indicator: "Models found — trained on {date}" or "No models found"
- `st.button("Train / Retrain from Scratch")` → runs full training pipeline
- Progress bar or spinner during training
- After training, display a **model comparison table**:

| Model | CV R² (mean ± std) | CV MAE | CV RMSE |
|---|---|---|---|
| RandomForest | 0.82 ± 0.04 | 0.031 | 0.048 |
| XGBoost | 0.85 ± 0.03 | 0.028 | 0.044 |
| LightGBM | 0.84 ± 0.03 | 0.029 | 0.045 |

- Highlight best model row in green
- `st.metric` row: Best Model | Training Round | n_synthetic | n_real
- `st.expander("Training Log")` → JSON-rendered training log

---

### Tab 3 — Get Recommendations

**Purpose:** Select a strain; view top-5 exploitation + 1 exploration conditions.

**UI Components:**
- `st.selectbox("Select strain")` (4 strain names)
- `st.button("Generate Recommendations")`
- If no models trained → warning "Please train models first (Tab 2)"
- Spinner during recommendation generation
- **Recommendations table** (6 rows by default):
  - Columns: Rank, Type (exploitation/exploration), Predicted Score, Uncertainty, + key condition columns (carbon_source, nitrogen_source, pH, temperature_C, rpm, inoculum_g_L, incubation_time_h, glucose_g_L, sucrose_g_L, maltose_g_L, ammonium_g_L)
  - Exploration row highlighted in orange
- **Uncertainty bar chart** (Plotly `go.Bar`): x=Rank, y=Uncertainty
- `st.expander("Full condition details")` → full recommendation DataFrame with all feature columns

---

### Tab 4 — Export Lab Sheet

**Purpose:** Download the Excel file for the selected strain/recommendations.

**UI Components:**
- Shows the last generated recommendations (from Tab 3 session state)
- If no recommendations yet → "Generate recommendations in Tab 3 first."
- `st.selectbox` "Number of replicates per condition" (1, 2, 3, 4, 5)
- `st.button("Generate Excel Sheet")`
- After generation:
  - Preview of Sheet 1 (Recommendations) as `st.dataframe`
  - `st.download_button("Download Excel", data=excel_bytes, file_name=filename)`
- Info box explaining the three sheets in the Excel file

---

### Tab 5 — Upload Results & Retrain

**Purpose:** Upload wet-lab CSV, validate, ingest, and retrain model.

**UI Components:**
- `st.file_uploader("Upload wet-lab results CSV", type=["csv"])`
- After upload:
  - **Validation section** (runs `validate_upload()`)
    - ✅ Green box if valid: "X rows validated. X unique strains found."
    - ❌ Red expander if invalid: lists all error messages
  - **Preview table**: first 10 rows of uploaded data
  - `st.button("Ingest & Retrain")` (disabled if validation failed)
- After ingestion:
  - `st.success("Ingested X real rows. Combined dataset: Y rows.")`
  - `st.metric` row: New Round | n_real total | Best Model (updated)
  - **Model comparison table** (updated CV results, same format as Tab 2)
  - `st.expander("Download current combined dataset")` → CSV download

**Template Download:**
- `st.download_button("Download upload template CSV")` — provides a blank CSV with all required columns filled with example values (one row per expected format).

---

## 8. Requirements.txt Content

```
# Core data science
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0

# Gradient boosting models
xgboost>=2.0.0
lightgbm>=4.0.0

# Model persistence
joblib>=1.3.0

# Streamlit frontend
streamlit>=1.30.0

# Excel export
openpyxl>=3.1.0

# Plotting in Streamlit
plotly>=5.18.0

# Utilities
python-dateutil>=2.8.0

# Legacy pipeline (keep for existing scripts, not used by GEMS ML)
modelseedpy
pyyaml
fastapi
uvicorn
requests
```

---

## 9. Design Decisions Log

| # | Decision | Rationale |
|---|---|---|
| D1 | **Global model with strain as feature** | Allows cross-strain learning; a strain-specific model would have only ~180 training rows per strain. Label-encoding strain_name preserves ordinal-free encoding while remaining a learnable numeric signal. |
| D2 | **Three models + best selection** | RandomForest, XGBoost, LightGBM cover tree-ensemble spectrum; cross-val picks winner per dataset; RF always available for uncertainty. |
| D3 | **RandomForest uncertainty proxy** | Tree variance is computationally cheap, interpretable, and well-calibrated for ensemble models. No need for MC Dropout or conformal prediction. |
| D4 | **Grid search over observed ranges** | Avoids extrapolation outside biologically plausible conditions. 2,000 samples cover the space adequately while remaining fast (<1s). |
| D5 | **5+1 recommendation structure** | 5 exploitation rows give the wet-lab team actionable diversity; 1 exploration row with high uncertainty encourages active learning and discovery. |
| D6 | **Adaptive retraining weights** | Starts from synthetic data (bootstrapping), progressively shifts trust to empirical results. Linear growth function (not exponential) avoids catastrophic forgetting of synthetic priors early on. |
| D7 | **Composite score = existing overall_rank_score** | The dataset already contains correctly normalised sub-scores. Reusing them avoids re-implementation errors. Re-normalisation on ingest maintains consistency across combined datasets. |
| D8 | **File-based storage** | Keeps the system self-contained, portable, and Git-friendly. No database server dependency. |
| D9 | **Streamlit tabs (no page routing)** | Keeps state between tabs via `st.session_state`. Avoids the need for URL routing or server-side session management. |
| D10 | **Replace main.py and pipeline_runner.py** | The old FastAPI/ModelSEED pipeline is unrelated to the ML optimisation task. Replacing them avoids import conflicts and confusion. |
| D11 | **Excel with 3 sheets** | Recommendations sheet is the primary output; Condition Details is human-readable; Replicate Template is the upload template pre-filled, reducing wet-lab data entry errors. |
| D12 | **KFold CV (not TimeSeriesSplit)** | Data rows are not truly time-ordered (dates are synthetic). Standard KFold provides valid cross-validation. If future real data is time-ordered, switch to TimeSeriesSplit in retrainer.py. |

---

*End of GEMS Architecture Document*
