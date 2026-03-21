import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
SYNTHETIC_CSV = DATA_DIR / "synthetic_fungal_growth_dataset.csv"
COMBINED_CSV = DATA_DIR / "intermediate" / "combined_dataset.csv"
PROCESSED_FEATURES = DATA_DIR / "intermediate" / "features.pkl"
MODELS_DIR = DATA_DIR / "models"
UPLOADS_DIR = DATA_DIR / "raw" / "uploads"

# Ensure dirs exist
for d in [DATA_DIR / "intermediate", MODELS_DIR, UPLOADS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Feature columns used as ML inputs
CATEGORICAL_FEATURES = [
    "strain_name", "culture_type", "carbon_source", "nitrogen_source", "mixing"
]

NUMERIC_FEATURES = [
    "total_carbon_g_L", "total_nitrogen_g_L", "phosphate_g_L", "sulfate_g_L",
    "magnesium_g_L", "calcium_g_L", "trace_mix_x", "vitamin_mix_x",
    "pH", "temperature_C", "rpm", "inoculum_g_L", "incubation_time_h"
]

ALL_FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES

# Target columns
TARGET_GROWTH = "growth_rate_h_inv"
TARGET_BIOMASS = "biomass_g_L"
TARGET_BYPRODUCTS = "total_byproducts_g_L"
TARGET_SCORE = "overall_rank_score"
ALL_TARGETS = [TARGET_GROWTH, TARGET_BIOMASS, TARGET_BYPRODUCTS, TARGET_SCORE]

# The 4 strains
STRAINS = [
    "Neurospora crassa OR74A",
    "Rhizopus microsporus var. microsporus ATCC 52814",
    "Aspergillus niger ATCC 13496",
    "Aspergillus oryzae RIB40",
]

# Model hyperparameters
RF_PARAMS = {"n_estimators": 200, "max_depth": 12, "min_samples_leaf": 2, "n_jobs": -1, "random_state": 42}
XGB_PARAMS = {"n_estimators": 200, "max_depth": 6, "learning_rate": 0.05, "random_state": 42, "verbosity": 0}
LGB_PARAMS = {"n_estimators": 200, "max_depth": 6, "learning_rate": 0.05, "random_state": 42, "verbose": -1}

# Recommendation grid sizes
N_CANDIDATES = 2000   # random candidates to generate per strain
TOP_N = 5             # top exploit recommendations
N_EXPLORE = 1         # extra explore recommendation

# Sample weighting
SYNTHETIC_WEIGHT = 1.0
REAL_WEIGHT_BASE = 5.0
REAL_WEIGHT_SCALE = 1.0   # multiplier per retrain round

# Column used to identify real vs synthetic rows
IS_SYNTHETIC_COL = "is_synthetic"
ROUND_COL = "retrain_round"
