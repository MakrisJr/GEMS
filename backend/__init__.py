"""GEMS backend package.

Keep package import light so GEM-only workflows do not eagerly import optional
ML dependencies such as xgboost.
"""

__all__ = [
    "config",
    "data_loader",
    "feature_engineering",
    "model_trainer",
    "recommender",
    "lab_exporter",
    "data_ingestion",
    "retrainer",
    "main",
    "pipeline_runner",
]
