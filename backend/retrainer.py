"""Adaptive model retraining after new wet-lab data is ingested."""
import json
from pathlib import Path
from typing import Dict, Any
from .config import MODELS_DIR
from .data_loader import load_combined
from .model_trainer import train_all, get_training_metadata

RETRAIN_LOG = MODELS_DIR / "retrain_log.json"


def _load_retrain_log() -> list:
    if RETRAIN_LOG.exists():
        with open(RETRAIN_LOG) as f:
            return json.load(f)
    return []


def _save_retrain_log(log: list) -> None:
    with open(RETRAIN_LOG, "w") as f:
        json.dump(log, f, indent=2)


def get_current_round() -> int:
    """Return the current retrain round number (0 = initial synthetic-only training)."""
    log = _load_retrain_log()
    return len(log)


def retrain(description: str = "") -> Dict[str, Any]:
    """
    Execute one full retrain cycle:
    1. Load the combined dataset (synthetic + all uploaded real data)
    2. Determine the current retrain round from the log
    3. Train all models with adaptive sample weighting
    4. Log the round metadata
    5. Return training metadata
    """
    df = load_combined()
    current_round = get_current_round()

    metadata = train_all(df=df, current_round=current_round)

    # Log this round
    log = _load_retrain_log()
    log_entry = {
        "round": current_round,
        "description": description,
        "n_samples": metadata["n_samples"],
        "n_real": int((~df["is_synthetic"]).sum()),
        "n_synthetic": int(df["is_synthetic"].sum()),
        "run_id": metadata["run_id"],
        "cv_scores": {t: metadata["targets"][t]["best_cv_r2"] for t in metadata["targets"]},
    }
    log.append(log_entry)
    _save_retrain_log(log)

    return metadata


def get_retrain_history() -> list:
    """Return the full training log."""
    return _load_retrain_log()


def compare_rounds() -> list:
    """Return a simplified comparison table across all retrain rounds."""
    log = _load_retrain_log()
    rows = []
    for entry in log:
        row = {
            "Round": entry["round"],
            "Run ID": entry.get("run_id", ""),
            "Description": entry.get("description", ""),
            "N samples": entry["n_samples"],
            "N real": entry["n_real"],
            "CV R2 (score)": round(entry["cv_scores"].get("overall_rank_score", 0), 3),
            "CV R2 (growth)": round(entry["cv_scores"].get("growth_rate_h_inv", 0), 3),
            "CV R2 (biomass)": round(entry["cv_scores"].get("biomass_g_L", 0), 3),
        }
        rows.append(row)
    return rows
